# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""ATS-conformance heuristic for CV variants (Sprint 7, S7.3).

Scores a CV's `render_text()` plain-text shadow against the
Workday / Greenhouse / Lever / Taleo extraction heuristics. The score
is local, deterministic, fast — no LLM call. Designed to be the
default judge; a future llama.cpp-backed adapter can re-score the
same input for nuance, but the heuristic alone catches the most
common ATS-killers:

  - Non-canonical section headings (ATS parsers map "Experience" →
    Workday's Experience field; "Professional Background" doesn't).
  - Walls of text in role bullets (Greenhouse caps a role bullet at
    ~280 chars before it stops parsing).
  - Missing contact info (phone OR email — at least one required;
    both preferred).
  - Inconsistent date formats across roles (MM/YYYY ↔ "Mar 2024 -
    Present" ↔ "2024-2026" all confuse the parser).
  - Common space-wasters ("References available upon request",
    "Objective:" preamble) that no modern ATS uses.
  - Length: ~2 pages of plain text ≈ 6 KB. Beyond 12 KB recruiters
    skim; beyond 24 KB ATS drops the tail.

The output is a `JudgeReport` dict with a 0-100 score, per-check
findings, and severity-graded actionable recommendations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── Heuristic tables ───────────────────────────────────────────────────


# Canonical section labels (Workday + Greenhouse parser tables).
# Headings that map directly score full marks; near-matches degrade.
CANONICAL_SECTIONS = {
    "experience": ("Experience", "Professional Experience", "Work Experience"),
    "skills": ("Skills", "Technical Skills", "Core Competencies", "Competencies"),
    "education": ("Education", "Academic Background"),
    "summary": ("Summary", "Executive Profile", "Professional Summary", "Profile"),
}

# Phrases ATS parsers either skip or actively penalise.
ATS_KILLERS = (
    "references available upon request",
    "objective:",
    "career objective",
    "responsible for",  # Lever-style: passive voice, often skimmed
    "duties include",
)

# Hard caps (chars).
LENGTH_GREEN = 6_000  # ~2 pages plain text — ideal
LENGTH_YELLOW = 12_000  # recruiter still skims
LENGTH_RED = 24_000  # ATS drops the tail

# Per-bullet caps (chars).
BULLET_GREEN = 200  # crisp, easy to scan
BULLET_YELLOW = 280  # Greenhouse parse threshold
BULLET_RED = 400  # Workday truncates with "..."

# Date pattern catalogue (BCP-47-ish display forms).
DATE_PATTERNS = {
    "mm/yyyy": re.compile(r"\b\d{1,2}/\d{4}\b"),
    "year-year": re.compile(r"\b\d{4}\s*[–\-—]\s*(?:\d{4}|present|current)\b", re.I),
    "month-year": re.compile(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b", re.I
    ),
}


# ── Data shapes ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Finding:
    """One scoring observation.

    Attributes:
        check: short stable id, e.g. "canonical_headings".
        severity: one of "info", "warn", "block".
        message: human-readable finding.
        deduction: integer 0-100, how many points removed.
    """

    check: str
    severity: str
    message: str
    deduction: int = 0


@dataclass
class JudgeReport:
    """Top-level ATS-judge output."""

    score: int = 100  # 0-100, higher = better
    grade: str = "A"  # A/B/C/D/F derived from score
    findings: list[Finding] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of this report."""
        return {
            "score": self.score,
            "grade": self.grade,
            "findings": [
                {
                    "check": f.check,
                    "severity": f.severity,
                    "message": f.message,
                    "deduction": f.deduction,
                }
                for f in self.findings
            ],
            "metrics": dict(self.metrics),
        }


# ── Public API ─────────────────────────────────────────────────────────


def score_cv(plain_text: str) -> JudgeReport:
    """Run every ATS check against *plain_text* and return a JudgeReport.

    *plain_text* should be the output of
    `inclusio.cli.render.render_text(data, "cv")` or equivalent
    — ASCII-where-possible, no Markdown, no LaTeX escapes, hyphen
    bullets (per the Sprint-4 render-text contract).
    """
    report = JudgeReport()
    _check_canonical_headings(plain_text, report)
    _check_contact_info(plain_text, report)
    _check_length(plain_text, report)
    _check_bullet_density(plain_text, report)
    _check_date_consistency(plain_text, report)
    _check_killer_phrases(plain_text, report)
    _finalise_grade(report)
    return report


def score_cv_with_llm(plain_text: str, llm) -> JudgeReport:
    """Run the heuristic + ask a local LLM for ONE additional finding.

    The LLM is used as a *re-ranker*, not a replacement. The heuristic
    catches mechanical issues (missing sections, killer phrases); the
    LLM catches semantic issues (tone-match, role-level mismatch) the
    heuristic can't see.

    Args:
        plain_text: ATS-safe CV text (output of `render_text`).
        llm: a `LocalLLM` instance (or any duck-type with the same
            `complete_json(prompt)` surface) — typically a llama.cpp
            HTTP wrapper. When the call fails (`LLMUnavailable`,
            `LLMTimeout`, `LLMParseError`), the heuristic result is
            returned unchanged with a single info-level finding
            documenting the LLM failure.

    Returns:
        A merged JudgeReport. The LLM's adjustment is bounded to
        [-15, +5] to keep one bad prompt from dominating the grade.
    """
    # Lazy import to keep the heuristic import-light. Note that
    # `score_cv_with_llm` callers must opt-in to the LLM dep.
    from . import local_llm as _llm_mod

    report = score_cv(plain_text)
    prompt = _llm_mod.build_ats_rerank_prompt(plain_text)
    try:
        payload = llm.complete_json(prompt)
    except _llm_mod.LLMError as exc:
        report.findings.append(
            Finding(
                check="llm_rerank",
                severity="info",
                message=f"LLM rerank unavailable: {exc}",
                deduction=0,
            )
        )
        return report

    adj = int(payload.get("score_adjustment", 0))
    adj = max(-15, min(5, adj))  # clamp
    finding_payload = payload.get("finding") or {}
    if finding_payload.get("message"):
        report.findings.append(
            Finding(
                check=str(finding_payload.get("check", "llm_rerank")),
                severity=str(finding_payload.get("severity", "info")),
                message=str(finding_payload["message"]),
                deduction=int(finding_payload.get("deduction", 0)),
            )
        )
    report.score = max(0, min(100, report.score + adj))
    report.metrics["llm_adjustment"] = adj
    _finalise_grade(report)
    return report


# ── Individual checks ──────────────────────────────────────────────────


def _check_canonical_headings(text: str, report: JudgeReport) -> None:
    """Each canonical section (experience/skills/education) MUST appear
    under at least one ATS-compatible label."""
    headings_found = {}
    for key, labels in CANONICAL_SECTIONS.items():
        matched = next((lbl for lbl in labels if lbl in text), None)
        headings_found[key] = matched
        if matched is None:
            report.findings.append(
                Finding(
                    check=f"canonical_heading_{key}",
                    severity="warn" if key == "summary" else "block",
                    message=(
                        f"Missing canonical {key.title()} heading. "
                        f"ATS parsers expect one of: {', '.join(labels)}."
                    ),
                    deduction=15 if key == "summary" else 25,
                )
            )
            report.score -= 15 if key == "summary" else 25
    report.metrics["canonical_headings"] = headings_found


def _check_contact_info(text: str, report: JudgeReport) -> None:
    """Either phone OR email must be reachable in the first 1.5 KB."""
    head = text[:1500]
    has_email = "@" in head and re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", head) is not None
    # Phone heuristic: digit run length >= 7 OR explicit +<country code>.
    has_phone = bool(
        re.search(r"\+\d[\d\s\-().]{6,}", head)
        or re.search(r"\b\d{3,4}[\s\-.]\d{3,4}[\s\-.]\d{3,4}\b", head)
    )
    report.metrics["contact"] = {"email": has_email, "phone": has_phone}
    if not (has_email or has_phone):
        report.findings.append(
            Finding(
                check="contact_info",
                severity="block",
                message=(
                    "No email or phone detected in the first 1.5 KB. "
                    "ATS parsers index contact info from the header — bury it "
                    "and recruiters can't reach you."
                ),
                deduction=30,
            )
        )
        report.score -= 30
    elif not (has_email and has_phone):
        report.findings.append(
            Finding(
                check="contact_info",
                severity="warn",
                message=(
                    "Only one of email/phone present. Including both raises the "
                    "Workday parser confidence and the recruiter response rate."
                ),
                deduction=5,
            )
        )
        report.score -= 5


def _check_length(text: str, report: JudgeReport) -> None:
    """Plain-text length bands roughly correspond to PDF page count."""
    length = len(text)
    report.metrics["length_bytes"] = length
    if length > LENGTH_RED:
        report.findings.append(
            Finding(
                check="length",
                severity="block",
                message=(
                    f"CV is {length} bytes (>{LENGTH_RED}). ATS parsers "
                    "drop content past this cap; recruiters never reach it."
                ),
                deduction=20,
            )
        )
        report.score -= 20
    elif length > LENGTH_YELLOW:
        report.findings.append(
            Finding(
                check="length",
                severity="warn",
                message=(
                    f"CV is {length} bytes (>{LENGTH_YELLOW}). "
                    "Recruiters skim past this threshold; trim earliest roles."
                ),
                deduction=10,
            )
        )
        report.score -= 10


def _check_bullet_density(text: str, report: JudgeReport) -> None:
    """Each `- ` bullet should fit in BULLET_GREEN chars for clarity."""
    bullets = [line.strip() for line in text.splitlines() if line.lstrip().startswith("- ")]
    over_yellow = [b for b in bullets if len(b) > BULLET_YELLOW]
    over_red = [b for b in bullets if len(b) > BULLET_RED]
    report.metrics["bullets"] = {
        "count": len(bullets),
        "over_yellow": len(over_yellow),
        "over_red": len(over_red),
    }
    if over_red:
        report.findings.append(
            Finding(
                check="bullet_length",
                severity="block",
                message=(
                    f"{len(over_red)} bullet(s) > {BULLET_RED} chars. "
                    "Workday truncates with '…'; split into 2-3 lines."
                ),
                deduction=15,
            )
        )
        report.score -= 15
    elif over_yellow:
        report.findings.append(
            Finding(
                check="bullet_length",
                severity="warn",
                message=(
                    f"{len(over_yellow)} bullet(s) > {BULLET_YELLOW} chars "
                    "(Greenhouse parse threshold). Tighten."
                ),
                deduction=5,
            )
        )
        report.score -= 5


def _check_date_consistency(text: str, report: JudgeReport) -> None:
    """A CV should use one date format throughout — mixed forms confuse
    the parser's date-range extractor."""
    formats_seen = {name: bool(pat.search(text)) for name, pat in DATE_PATTERNS.items()}
    distinct = sum(1 for v in formats_seen.values() if v)
    report.metrics["date_formats"] = formats_seen
    if distinct > 1:
        report.findings.append(
            Finding(
                check="date_consistency",
                severity="warn",
                message=(
                    f"Mixed date formats detected: "
                    f"{[n for n, v in formats_seen.items() if v]}. "
                    "Pick one (MM/YYYY recommended for Workday)."
                ),
                deduction=10,
            )
        )
        report.score -= 10


def _check_killer_phrases(text: str, report: JudgeReport) -> None:
    """ATS-killer phrases waste page real-estate without adding signal."""
    lower = text.lower()
    found = [k for k in ATS_KILLERS if k in lower]
    report.metrics["killer_phrases"] = found
    if found:
        report.findings.append(
            Finding(
                check="killer_phrases",
                severity="warn",
                message=(
                    f"Found space-wasters: {found}. Drop them — no modern ATS "
                    "uses them, and recruiters skim past them."
                ),
                deduction=5 * len(found),
            )
        )
        report.score -= 5 * len(found)


def _finalise_grade(report: JudgeReport) -> None:
    """Clamp score to 0-100 and assign a letter grade."""
    report.score = max(0, min(100, report.score))
    grade_thresholds = ((90, "A"), (80, "B"), (70, "C"), (60, "D"))
    report.grade = next((g for threshold, g in grade_thresholds if report.score >= threshold), "F")
