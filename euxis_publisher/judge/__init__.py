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
