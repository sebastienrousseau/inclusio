# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""LLM-judge bridges for the Inclusio engine.

Sprint 7 (S7.1 - S7.3) — closes Forcing Function #5 (LLM judges in
the build) in docs/strategy-2026.md.

Per decision D4 (2026-05-23), judges are local-first: the default
backend is a heuristic implementation that needs no network calls
and no LLM. Higher-quality judges (citation grounding via Llama-3
local, Claude/GPT-5 via MCP broker) layer on top of the same API.

Judges shipped today:
  - `ats` (S7.3): Workday / Greenhouse / Lever heuristic for CV
    variants. Local, deterministic, fast.
  - `citations` (S7.2): ScholarCopilot-style hallucination detection
    against a citation index.
  - `jd_fit` (S7.4): Jaccard-based job-description ↔ CV match
    scoring with required-keyword coverage + seniority match.
  - `local_llm` / `cloud_llm` (S7.5): llama.cpp HTTP adapter + BYO-
    key cloud (Anthropic / OpenAI) for the optional rerank layer.

## The `Judge` protocol (v0.0.5)

Every judge in `inclusio.judge` conforms to the lightweight
`Judge` protocol below: a name, a heuristic `score(**inputs)` call,
and an optional `score_with_llm(llm, **inputs)` rerank. The
per-input signature differs by judge (ATS takes `plain_text`,
citations takes `tex`, jd_fit takes `jd_text` + `cv_text`); the
protocol documents the shared shape without forcing a single
keyword name.

The `JUDGES` registry below maps each judge's name to its
implementation. The CLI dispatcher in `inclusio.cli.build`'s
`cmd_judge` resolves through this registry, and new judges can
register themselves by appending to it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .ats import JudgeReport, score_cv, score_cv_with_llm
from .citations import (
    BibItem,
    Citation,
    parse_bibitems,
    parse_citations,
    score_citations,
    score_citations_with_llm,
)
from .cloud_llm import CloudLLM, from_url
from .jd_fit import (
    extract_keywords,
    extract_required_keywords,
    jaccard,
    score_jd_fit,
    score_jd_fit_with_llm,
)
from .local_llm import (
    LLMError,
    LLMParseError,
    LLMResponse,
    LLMTimeout,
    LLMUnavailable,
    LocalLLM,
    build_ats_rerank_prompt,
)


@runtime_checkable
class Judge(Protocol):
    """Common surface for every judge in `inclusio.judge`.

    Attributes:
        name: short identifier used by the CLI (`--judge <name>`).
            Must match the key in `JUDGES`.

    Each judge is heuristic-first: `score()` runs the deterministic
    local pass; `score_with_llm()` runs the same heuristic and
    optionally adds findings from an LLM rerank. When the LLM is
    unreachable, the rerank pass falls back to heuristic-only with
    a clear breadcrumb in the report.

    The keyword-arguments accepted by `score` / `score_with_llm`
    differ per judge — see the concrete module's docstrings:

    | Judge | `score(**inputs)` keys |
    |---|---|
    | `ats` | `plain_text: str` |
    | `citations` | `tex: str`, plus optional `max_checks` |
    | `jd_fit` | `jd_text: str`, `cv_text: str` |
    """

    name: str

    def score(self, **inputs: object) -> JudgeReport:
        """Run the heuristic pass with the judge-specific inputs."""
        ...

    def score_with_llm(self, llm: object, **inputs: object) -> JudgeReport:
        """Run heuristic + LLM rerank. Falls back if `llm` is unreachable."""
        ...


class _ATSJudge:
    """ATS conformance scoring for CV plain-text."""

    name = "ats"

    def score(self, *, plain_text: str) -> JudgeReport:
        """Heuristic ATS score."""
        return score_cv(plain_text)

    def score_with_llm(self, llm: object, *, plain_text: str) -> JudgeReport:
        """Heuristic + LLM rerank for ATS."""
        return score_cv_with_llm(plain_text, llm)


class _CitationsJudge:
    """Citation grounding for LaTeX papers."""

    name = "citations"

    def score(self, *, tex: str) -> JudgeReport:
        """Heuristic `\\cite` / `\\bibitem` consistency scoring."""
        return score_citations(tex)

    def score_with_llm(self, llm: object, *, tex: str, max_checks: int = 10) -> JudgeReport:
        """Heuristic + LLM grounding check on up to *max_checks* citations."""
        return score_citations_with_llm(tex, llm, max_checks=max_checks)


class _JDFitJudge:
    """Job-description ↔ CV fit scoring."""

    name = "jd_fit"

    def score(self, *, jd_text: str, cv_text: str) -> JudgeReport:
        """Heuristic JD-fit score."""
        return score_jd_fit(jd_text, cv_text)

    def score_with_llm(self, llm: object, *, jd_text: str, cv_text: str) -> JudgeReport:
        """Heuristic + LLM rerank for JD-fit."""
        return score_jd_fit_with_llm(jd_text, cv_text, llm)


# The canonical registry. Add a new judge by appending here.
JUDGES: dict[str, Judge] = {
    j.name: j
    for j in (
        _ATSJudge(),
        _CitationsJudge(),
        _JDFitJudge(),
    )
}


__all__ = [
    "BibItem",
    "Citation",
    "CloudLLM",
    "JUDGES",
    "Judge",
    "JudgeReport",
    "LLMError",
    "LLMParseError",
    "LLMResponse",
    "LLMTimeout",
    "LLMUnavailable",
    "LocalLLM",
    "build_ats_rerank_prompt",
    "extract_keywords",
    "extract_required_keywords",
    "from_url",
    "jaccard",
    "parse_bibitems",
    "parse_citations",
    "score_citations",
    "score_citations_with_llm",
    "score_cv",
    "score_cv_with_llm",
    "score_jd_fit",
    "score_jd_fit_with_llm",
]
