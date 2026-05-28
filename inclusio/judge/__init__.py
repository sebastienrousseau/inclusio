"""LLM-judge bridges for the Euxis Publisher engine.

Sprint 7 (S7.1 - S7.3) — closes Forcing Function #5 (LLM judges in
the build) in docs/strategy-2026.md.

Per decision D4 (2026-05-23), judges are local-first: the default
backend is a heuristic implementation that needs no network calls
and no LLM. Higher-quality judges (citation grounding via Llama-3
local, Claude/GPT-5 via MCP broker) layer on top of the same API.

Initial judges:
  - `ats` (S7.3): Workday / Greenhouse / Lever heuristic for CV
    variants. Local, deterministic, fast.
  - `citations` (S7.2): ScholarCopilot-style hallucination detection
    against a citation index. Sprint 7.5.
  - `local_llm` (S7.1): llama.cpp HTTP adapter wrapping any judge.
    Sprint 7.5.
"""

from __future__ import annotations

from .ats import JudgeReport, score_cv
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

__all__ = [
    "JudgeReport",
    "score_cv",
    "score_citations",
    "score_citations_with_llm",
    "parse_citations",
    "parse_bibitems",
    "Citation",
    "BibItem",
    "score_jd_fit",
    "score_jd_fit_with_llm",
    "extract_keywords",
    "extract_required_keywords",
    "jaccard",
    "LocalLLM",
    "CloudLLM",
    "from_url",
    "LLMResponse",
    "LLMError",
    "LLMTimeout",
    "LLMUnavailable",
    "LLMParseError",
    "build_ats_rerank_prompt",
]
