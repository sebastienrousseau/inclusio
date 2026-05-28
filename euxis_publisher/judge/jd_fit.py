# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""JD-to-CV fit judge (Sprint 7, S7.4).

Given a job-description brief + a candidate CV, score how well the CV
fits the JD. The companion to S7.3 (ATS judge) and S7.2 (citation
judge) — same `JudgeReport` shape, same LLM-rerank pattern via S7.1.

Two layers:

  1. **Heuristic** (always-on, local):
       - Keyword overlap (Jaccard) between JD and CV technical terms.
       - Required-keyword extraction from "required" / "must have" /
         "minimum" / "essential" clauses; missing-required is a block.
       - Role-level match: "Senior X" / "Director X" extracted from
         both sides; a >1-level mismatch is a warn.

  2. **LLM rerank** (opt-in, via `LocalLLM`):
       - Asks the LLM for the top strength + top gap in JSON.
       - Merges as a warn finding when the gap is substantive.
       - Falls back gracefully on any `LLMError`.

The judge is intentionally conservative: it nudges, not gates. A
mid-level engineer applying to a senior role should see a clear
diagnostic, not a hard block.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .ats import Finding, JudgeReport, _finalise_grade

# ── Keyword extraction ─────────────────────────────────────────────────


# Lowercase stop tokens that add no signal. Kept compact — the heuristic
# is built around technical terms, not natural-language coverage.
STOPWORDS: frozenset[str] = frozenset(
    """
    a about above after again all also am an and any are as at be because
    been before being below between both but by can did do does doing
    don done down during each etc few for from further had has have
    having he her here hers herself him himself his how i if in
    into is it its itself just like may me might more most must
    my myself no nor not now of off on once one only or other our ours
    ourselves out over own same she should so some such than that the
    their theirs them themselves then there these they this those
    through to too under until up us use used using very was we were
    what when where which while who whom why will with would year years
    you your yours yourself yourselves role roles work experience
    candidate candidates required requirement requirements skills skill
    ability abilities looking opportunity company team teams across
    strong proven excellent good great able including include includes
    new make made making build building built ensure ensures ensured
    drive driving driven lead leading led help helps helped
    """.split()
)


# Phrases that introduce required-skill clauses. The next ~120 chars
# get keyword-extracted as a "required" set.
REQUIRED_TRIGGERS = (
    "required",
    "requirements",
    "must have",
    "must-have",
    "minimum",
    "essential",
    "you have",
    "you will have",
)


# Ordered seniority ladder for the level-match heuristic.
_SENIORITY_LADDER: tuple[tuple[str, int], ...] = (
    ("intern", 0),
    ("junior", 1),
    ("associate", 1),
    ("graduate", 1),
    ("mid", 2),
    ("mid-level", 2),
    ("engineer", 2),
    ("senior", 3),
    ("staff", 4),
    ("principal", 5),
    ("lead", 5),
    ("manager", 5),
    ("director", 6),
    ("head", 6),
    ("vp", 7),
    ("vice", 7),
    ("svp", 7),
    ("chief", 8),
    ("cto", 8),
    ("ceo", 8),
)


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]{0,40}")
_TRAILING_PUNCT = ".,;:!?-"


def extract_keywords(text: str, min_len: int = 2) -> set[str]:
    """Tokenize *text*, lowercase, drop stopwords + short / numeric.

    Preserves common technical sigils — `c++`, `c#`, `node.js`, `ml/ai`
    — by treating `+ # . -` as in-word characters. Default `min_len=2`
    keeps 2-char tech terms (`c#`, `ai`, `ml`, `ui`, `ux`); raise it to
    3 if you want a stricter signal.
    """
    out: set[str] = set()
    for token in _WORD_RE.findall(text):
        # Strip trailing sentence punctuation that the regex's
        # greedy in-word class accidentally consumed
        # ("postgresql." → "postgresql").
        token = token.rstrip(_TRAILING_PUNCT)
        lc = token.lower()
        if len(lc) < min_len:
            continue
        if lc in STOPWORDS:
            continue
        # Pure-numeric tokens add no signal.
        if not any(c.isalpha() for c in lc):
            continue
        out.add(lc)
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    """Symmetric set similarity in [0.0, 1.0]."""
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def extract_required_keywords(jd_text: str, window: int = 240) -> set[str]:
    """Pull keywords from clauses introduced by required-trigger words.

    Scans for any `REQUIRED_TRIGGERS` phrase and harvests the next
    *window* characters OR until the next paragraph break (`\\n\\n`)
    OR the next sentence-end that looks like a new section heading,
    whichever comes first. This stops the harvest from bleeding into
    a "Bonus:" or "You will:" block that follows the required list.
    """
    lower = jd_text.lower()
    chunks: list[str] = []
    for trigger in REQUIRED_TRIGGERS:
        idx = lower.find(trigger)
        while idx != -1:
            tail = jd_text[idx : idx + window]
            # Stop at the next paragraph break.
            para = tail.find("\n\n")
            if para != -1:
                tail = tail[:para]
            chunks.append(tail)
            idx = lower.find(trigger, idx + len(trigger))
    if not chunks:
        return set()
    harvested = extract_keywords(" ".join(chunks))
    # Drop the trigger words themselves so the heuristic doesn't
    # demand "required: required" coverage.
    return harvested - {t.replace("-", "").replace(" ", "") for t in REQUIRED_TRIGGERS}


def _seniority_rank(text: str) -> int | None:
    """Return the seniority rank of the first matched ladder term.

    Uses *first match in source order*, not max, because phrases like
    "Junior Engineer" should rank as junior (1) — not as engineer (2).
    The leading modifier carries the seniority signal in normal English.
    """
    lower = text.lower()
    # Pre-build the alternation regex from the ladder, longest-first
    # so "vice-president" matches before "vice".
    terms = sorted({t for t, _ in _SENIORITY_LADDER}, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.IGNORECASE)
    match = pattern.search(lower)
    if not match:
        return None
    matched = match.group(1).lower()
    for term, rank in _SENIORITY_LADDER:
        if term == matched:
            return rank
    return None


# ── Heuristic scoring ──────────────────────────────────────────────────


@dataclass(frozen=True)
class FitInputs:
    """Lightweight holder so callers can introspect what was scored."""

    jd_keywords: set[str]
    cv_keywords: set[str]
    required: set[str]
    missing_required: set[str]
    jaccard: float
    jd_seniority: int | None
    cv_seniority: int | None


def score_jd_fit(jd_text: str, cv_text: str) -> JudgeReport:
    """Run every JD-fit heuristic against the (JD, CV) pair.

    Score starts at 100 and tracks the keyword overlap; required-kw
    gaps and role-level mismatch each carve deductions. Output shape
    matches `score_cv` / `score_citations` so the same `--json` writer
    and `_print_and_persist_report` helper handle it.
    """
    inputs = _build_inputs(jd_text, cv_text)
    report = JudgeReport()

    # Base score from Jaccard via a stepped curve. Raw Jaccard scores
    # on real JD-CV pairs sit in the 0.15-0.50 band; mapping them
    # linearly to percent buckets puts every reasonable match in the
    # F band, which is useless as a triage signal. The bands below
    # reflect what an experienced recruiter would call a strong /
    # moderate / weak overlap.
    report.score = _jaccard_to_base_score(inputs.jaccard)

    # ── 1. Missing required keywords ──
    if inputs.missing_required:
        missing = sorted(inputs.missing_required)[:8]
        deduction = min(20, 4 * len(missing))
        report.findings.append(
            Finding(
                check="missing_required_keywords",
                severity="block",
                message=(
                    f"{len(inputs.missing_required)} 'required' keyword(s) "
                    f"not found in the CV: {missing}. Reword the CV to "
                    "surface them explicitly or move on to a better-fit role."
                ),
                deduction=deduction,
            )
        )
        report.score -= deduction

    # ── 2. Role-level mismatch ──
    if inputs.jd_seniority is not None and inputs.cv_seniority is not None:
        gap = abs(inputs.jd_seniority - inputs.cv_seniority)
        if gap >= 2:
            severity = "block" if gap >= 3 else "warn"
            deduction = 15 if gap >= 3 else 10
            direction = "under" if inputs.cv_seniority < inputs.jd_seniority else "over"
            report.findings.append(
                Finding(
                    check="role_level_mismatch",
                    severity=severity,
                    message=(
                        f"Seniority gap of {gap} steps — CV reads as "
                        f"{direction}-leveled vs the JD. Recruiters filter "
                        "these out; tailor the headline + summary first."
                    ),
                    deduction=deduction,
                )
            )
            report.score -= deduction

    # ── 3. Low overlap (informational floor) ──
    if inputs.jaccard < 0.10:
        report.findings.append(
            Finding(
                check="low_keyword_overlap",
                severity="warn",
                message=(
                    f"JD-CV Jaccard overlap is {inputs.jaccard:.2f}. The CV "
                    "covers fewer than 1 in 10 JD terms — consider whether "
                    "this is a stretch role."
                ),
                deduction=10,
            )
        )
        report.score -= 10

    report.metrics["jd_fit"] = {
        "jaccard": round(inputs.jaccard, 3),
        "jd_keywords": len(inputs.jd_keywords),
        "cv_keywords": len(inputs.cv_keywords),
        "required_keywords": sorted(inputs.required)[:20],
        "missing_required": sorted(inputs.missing_required)[:20],
        "jd_seniority_rank": inputs.jd_seniority,
        "cv_seniority_rank": inputs.cv_seniority,
    }
    _finalise_grade(report)
    return report


def _jaccard_to_base_score(j: float) -> int:
    """Map raw Jaccard overlap to a 0-100 base score.

    Bands tuned against real JD-CV pairs:
      >= 0.45  → 95   (exceptional overlap — author already tailored)
      >= 0.30  → 85   (strong — most-required terms present)
      >= 0.15  → 70   (moderate — needs some rephrasing)
      >= 0.05  → 55   (weak — substantial gaps)
      else     → 35   (mismatch — likely wrong role family)
    """
    if j >= 0.45:
        return 95
    if j >= 0.30:
        return 85
    if j >= 0.15:
        return 70
    if j >= 0.05:
        return 55
    return 35


def _build_inputs(jd_text: str, cv_text: str) -> FitInputs:
    jd_kw = extract_keywords(jd_text)
    cv_kw = extract_keywords(cv_text)
    required = extract_required_keywords(jd_text)
    return FitInputs(
        jd_keywords=jd_kw,
        cv_keywords=cv_kw,
        required=required,
        missing_required=required - cv_kw,
        jaccard=jaccard(jd_kw, cv_kw),
        jd_seniority=_seniority_rank(jd_text),
        cv_seniority=_seniority_rank(cv_text),
    )


# ── LLM rerank (S7.1-backed) ───────────────────────────────────────────


JD_FIT_SYSTEM = (
    "You are a senior recruiter triaging applications. Compare the job "
    "description and the candidate's CV. Identify ONE substantive gap "
    "the heuristic missed — domain depth, leadership signal, or a "
    "concrete result the CV doesn't surface. Be conservative; reject "
    "obvious skill-list noise. Respond with strict JSON only."
)


JD_FIT_SCHEMA = {
    "top_strength": "string — one sentence",
    "top_gap": {
        "summary": "string — one sentence",
        "severity": "warn | block | info",
        "deduction": "integer 0-15",
    },
}


def build_jd_fit_prompt(jd_text: str, cv_text: str) -> str:
    """Compose the rerank prompt + JSON schema."""
    import json as _json

    return (
        f"{JD_FIT_SYSTEM}\n\n"
        f"Output schema:\n{_json.dumps(JD_FIT_SCHEMA, indent=2)}\n\n"
        f"Job description:\n---\n{jd_text.strip()[:4000]}\n---\n\n"
        f"Candidate CV:\n---\n{cv_text.strip()[:4000]}\n---\n\n"
        "Respond with valid JSON only:"
    )


def score_jd_fit_with_llm(jd_text: str, cv_text: str, llm) -> JudgeReport:
    """Heuristic score + LLM rerank.

    The LLM contributes at most ONE warn (`-deduction` <= 15) finding,
    keeping the grade bounded. `LLMError` paths leave the heuristic
    result intact + drop a single info breadcrumb.
    """
    from . import local_llm as _llm_mod

    report = score_jd_fit(jd_text, cv_text)
    prompt = build_jd_fit_prompt(jd_text, cv_text)
    try:
        payload = llm.complete_json(prompt)
    except _llm_mod.LLMError as exc:
        report.findings.append(
            Finding(
                check="jd_fit_llm",
                severity="info",
                message=f"LLM rerank unavailable: {exc}",
                deduction=0,
            )
        )
        return report

    strength = str(payload.get("top_strength", "")).strip()
    if strength:
        report.findings.append(
            Finding(
                check="top_strength",
                severity="info",
                message=strength,
                deduction=0,
            )
        )

    gap = payload.get("top_gap") or {}
    summary = str(gap.get("summary", "")).strip()
    if summary:
        severity = str(gap.get("severity", "warn"))
        if severity not in ("info", "warn", "block"):
            severity = "warn"
        deduction = max(0, min(15, int(gap.get("deduction", 5))))
        report.findings.append(
            Finding(
                check="top_gap",
                severity=severity,
                message=summary,
                deduction=deduction,
            )
        )
        report.score = max(0, min(100, report.score - deduction))

    report.metrics["llm_rerank"] = {
        "strength_recorded": bool(strength),
        "gap_recorded": bool(summary),
    }
    _finalise_grade(report)
    return report
