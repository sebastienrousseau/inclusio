# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Citation-grounding judge for scientific papers (Sprint 7, S7.2).

Detects two failure modes:

  1. **Hallucinated keys** — `\\cite{smith2025}` with no matching
     `\\bibitem{smith2025}`. Always-on heuristic; catches every
     LLM-generated paper that invented references whole-cloth.
  2. **Mis-attributed claims** — `\\cite{smith2025}` matched to a
     real bibitem, but the in-text claim around the citation isn't
     supported by what `smith2025` actually says. LLM-only;
     ScholarCopilot-pattern via `LocalLLM`.

The heuristic layer runs in microseconds and needs no model; the LLM
layer is opt-in and runs through the same `LocalLLM` adapter S7.1
shipped.

Scope (Sprint 7):
  - Inline `\\bibitem{key}` entries (small papers, single-file).
  - `.bib` files via BibTeX are Sprint 8 work — they need a
    BibTeX-aware parser (biblatex, biber tool-mode) we don't ship
    yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .ats import Finding, JudgeReport, _finalise_grade

# ── Data shapes ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Citation:
    """One `\\cite{key}` occurrence in the source."""

    key: str
    context: str  # surrounding sentence (~120 chars on each side)
    line: int  # 1-indexed source line


@dataclass(frozen=True)
class BibItem:
    """One `\\bibitem{key}` entry in the source."""

    key: str
    text: str  # the entry body (after the optional `[label]`)
    line: int


# ── Regexes ────────────────────────────────────────────────────────────


# `\cite{a, b, c}` / `\citep{...}` / `\citet{...}` / `\citeauthor{...}` / `\citeyear{...}`
# Capture group 1 is the comma-separated key list.
_CITE_RE = re.compile(
    r"\\cite(?:p|t|author|year|num|alt|year|p\*|t\*)?\s*"
    r"(?:\[[^\]]*\]\s*){0,2}"
    r"\{([^}]+)\}"
)

# `\bibitem[label]{key}` — label optional.
_BIBITEM_RE = re.compile(r"\\bibitem(?:\[[^\]]*\])?\s*\{([^}]+)\}")


# ── Parsers ────────────────────────────────────────────────────────────


def parse_citations(tex: str) -> list[Citation]:
    """Return every `\\cite{...}` (and variants) in source order.

    Multi-key forms (`\\cite{a, b, c}`) are expanded into one
    Citation per key. Whitespace inside the key list is tolerated.
    """
    out: list[Citation] = []
    lines = tex.splitlines()
    for lineno, line in enumerate(lines, start=1):
        for match in _CITE_RE.finditer(line):
            keys = [k.strip() for k in match.group(1).split(",") if k.strip()]
            start = max(0, match.start() - 120)
            end = min(len(line), match.end() + 120)
            context = line[start:end].strip()
            for key in keys:
                out.append(Citation(key=key, context=context, line=lineno))
    return out


def parse_bibitems(tex: str) -> list[BibItem]:
    """Return every `\\bibitem{key}` (or `\\bibitem[label]{key}`).

    The entry body is captured from the bibitem to the next
    bibitem / `\\end{thebibliography}` / end-of-file, with one
    layer of inline LaTeX (`\\emph`, `\\textit`) stripped for
    readability when the LLM judge reads it.
    """
    out: list[BibItem] = []
    matches = list(_BIBITEM_RE.finditer(tex))
    for i, match in enumerate(matches):
        key = match.group(1).strip()
        body_start = match.end()
        body_end = (
            matches[i + 1].start() if i + 1 < len(matches) else _find_bib_end(tex, body_start)
        )
        body = tex[body_start:body_end].strip()
        # One pass of light markup cleanup so the LLM sees authors/
        # titles, not LaTeX commands.
        body = re.sub(r"\\emph\{([^{}]*)\}", r"\1", body)
        body = re.sub(r"\\textit\{([^{}]*)\}", r"\1", body)
        body = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", body)
        # Resolve line number from the source.
        lineno = tex.count("\n", 0, match.start()) + 1
        out.append(BibItem(key=key, text=body, line=lineno))
    return out


def _find_bib_end(tex: str, start: int) -> int:
    """Locate the end of the bibliography environment after *start*.

    Pandoc-extracted papers often have `\\end{thebibliography}`; raw
    LaTeX may have it; or the bibliography may extend to EOF. Fall
    through to len(tex) when no terminator is found.
    """
    end_match = re.search(r"\\end\{thebibliography\}", tex[start:])
    if end_match:
        return start + end_match.start()
    return len(tex)


# ── Heuristic scoring ──────────────────────────────────────────────────


# Severity bands for the dangling-citation finding. Block at >0 because
# a single hallucinated citation can kill peer review.
DANGLING_BLOCK_DEDUCTION_PER_KEY = 15
DANGLING_MAX_DEDUCTION = 60  # cap so 5+ dangling don't go negative
UNUSED_WARN_DEDUCTION_PER_KEY = 5
UNUSED_MAX_DEDUCTION = 20
DUPLICATE_DEDUCTION_PER_KEY = 10


def score_citations(tex: str) -> JudgeReport:
    """Run every citation-grounding heuristic against *tex*.

    The heuristic is intentionally strict — a paper with even one
    hallucinated `\\cite{key}` should not make it through review.
    """
    report = JudgeReport()
    citations = parse_citations(tex)
    bibitems = parse_bibitems(tex)
    bib_keys = {b.key for b in bibitems}
    citation_keys = {c.key for c in citations}

    # ── 1. dangling citations ──
    dangling = [c for c in citations if c.key not in bib_keys]
    if dangling:
        unique_dangling = sorted({c.key for c in dangling})
        deduction = min(
            DANGLING_BLOCK_DEDUCTION_PER_KEY * len(unique_dangling),
            DANGLING_MAX_DEDUCTION,
        )
        report.findings.append(
            Finding(
                check="dangling_citation",
                severity="block",
                message=(
                    f"{len(unique_dangling)} `\\cite{{key}}` reference(s) without a "
                    f"matching `\\bibitem`: {unique_dangling}. "
                    "Hallucinated or missing bibliography entries."
                ),
                deduction=deduction,
            )
        )
        report.score -= deduction

    # ── 2. unused bibitems ──
    unused = sorted(bib_keys - citation_keys)
    if unused:
        deduction = min(UNUSED_WARN_DEDUCTION_PER_KEY * len(unused), UNUSED_MAX_DEDUCTION)
        report.findings.append(
            Finding(
                check="unused_bibitem",
                severity="warn",
                message=(
                    f"{len(unused)} `\\bibitem` entry/entries never cited: {unused}. "
                    "Remove or cite them; reviewers flag dead entries."
                ),
                deduction=deduction,
            )
        )
        report.score -= deduction

    # ── 3. duplicate bibitems ──
    seen: dict[str, int] = {}
    for b in bibitems:
        seen[b.key] = seen.get(b.key, 0) + 1
    duplicates = sorted(k for k, n in seen.items() if n > 1)
    if duplicates:
        deduction = DUPLICATE_DEDUCTION_PER_KEY * len(duplicates)
        report.findings.append(
            Finding(
                check="duplicate_bibitem",
                severity="warn",
                message=(
                    f"{len(duplicates)} `\\bibitem` key(s) declared twice: {duplicates}. "
                    "Bibliography compilers raise this as a warning; some reject."
                ),
                deduction=deduction,
            )
        )
        report.score -= deduction

    # ── 4. no citations at all (informational) ──
    if not citations and bibitems:
        report.findings.append(
            Finding(
                check="no_citations",
                severity="warn",
                message=(
                    "Bibliography has entries but the body has no `\\cite{}`. "
                    "Either cite them or move them to a 'See also' section."
                ),
                deduction=10,
            )
        )
        report.score -= 10
    elif not citations and not bibitems:
        report.findings.append(
            Finding(
                check="no_citations",
                severity="info",
                message="No citations or bibliography found — fine for a review note.",
                deduction=0,
            )
        )

    # ── 5. paper has citations but no bibliography at all ──
    if citations and not bibitems:
        report.findings.append(
            Finding(
                check="missing_bibliography",
                severity="block",
                message=(
                    f"{len(citations)} `\\cite{{key}}` reference(s) but the document "
                    "ships no `\\bibitem` entries. Every cite is dangling."
                ),
                deduction=50,
            )
        )
        report.score -= 50

    report.metrics["citation_counts"] = {
        "total_cites": len(citations),
        "unique_keys": len(citation_keys),
        "bibitems": len(bibitems),
        "dangling": len({c.key for c in dangling}),
        "unused": len(unused),
        "duplicates": len(duplicates),
    }
    _finalise_grade(report)
    return report


# ── LLM-backed grounding (S7.2 layer) ──────────────────────────────────


CITATION_GROUNDING_SYSTEM = (
    "You are an academic citation reviewer. The author has written a "
    "passage that cites a specific reference. Judge whether the in-text "
    "claim around the citation accurately reflects what the bibitem "
    "describes. Be conservative — flag mis-attribution, but tolerate "
    "general 'see X for Y' style citations. Respond with strict JSON, "
    "no prose, no fences."
)


def build_grounding_prompt(citation: Citation, bibitem: BibItem) -> str:
    """Compose the per-citation LLM prompt.

    Returns a self-contained prompt ready for `LocalLLM.complete_json()`.
    The expected response shape:

        {"supported": bool, "confidence": 0.0-1.0, "reason": str}
    """
    return (
        f"{CITATION_GROUNDING_SYSTEM}\n\n"
        f"In-text context around \\cite{{{citation.key}}}:\n"
        f"---\n{citation.context}\n---\n\n"
        f"Bibliography entry for {citation.key}:\n"
        f"---\n{bibitem.text[:1000]}\n---\n\n"
        'Output schema: {"supported": true|false, '
        '"confidence": <0.0-1.0>, "reason": "<one short sentence>"}\n\n'
        "Respond with valid JSON only:"
    )


def score_citations_with_llm(
    tex: str,
    llm,
    max_checks: int = 10,
) -> JudgeReport:
    """Heuristic score + LLM grounding check for the first *max_checks*
    citations.

    Args:
        tex: LaTeX source containing `\\cite{...}` and `\\bibitem{...}`.
        llm: any `LocalLLM`-shaped object (has `complete_json(prompt)`).
        max_checks: hard cap so a 200-citation paper doesn't blow the
            token budget. Default 10 is enough to surface a systematic
            mis-attribution pattern.

    Returns:
        Merged JudgeReport. Each LLM-flagged mis-attribution surfaces
        as a `citation_grounding` finding (warn, -5). LLM unavailability
        downgrades to a single info breadcrumb — the heuristic result
        is preserved.
    """
    from . import local_llm as _llm_mod

    report = score_citations(tex)
    citations = parse_citations(tex)
    bibitems = {b.key: b for b in parse_bibitems(tex)}

    matched = [c for c in citations if c.key in bibitems][:max_checks]
    if not matched:
        return report  # nothing for the LLM to check

    flagged_keys: set[str] = set()
    fallback_recorded = False
    checked = 0
    for c in matched:
        prompt = build_grounding_prompt(c, bibitems[c.key])
        try:
            payload = llm.complete_json(prompt)
        except _llm_mod.LLMError as exc:
            if not fallback_recorded:
                report.findings.append(
                    Finding(
                        check="citation_grounding_llm",
                        severity="info",
                        message=f"LLM grounding check unavailable: {exc}",
                        deduction=0,
                    )
                )
                fallback_recorded = True
            break
        checked += 1
        supported = bool(payload.get("supported", True))
        confidence = float(payload.get("confidence", 0.0))
        if not supported and confidence >= 0.6 and c.key not in flagged_keys:
            flagged_keys.add(c.key)
            reason = str(payload.get("reason", "")).strip() or "context-bibitem mismatch"
            report.findings.append(
                Finding(
                    check="citation_grounding",
                    severity="warn",
                    message=(
                        f"`\\cite{{{c.key}}}` at line {c.line}: {reason} "
                        f"(LLM confidence {confidence:.2f})."
                    ),
                    deduction=5,
                )
            )
            report.score -= 5

    report.metrics["llm_grounding"] = {
        "checked": checked,
        "flagged": len(flagged_keys),
        "cap": max_checks,
    }
    _finalise_grade(report)
    return report
