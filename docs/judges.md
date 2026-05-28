# LLM / heuristic judges — `euxis_publisher.judge`

Sprint 7 (S7.3) ships the first judge: an **ATS-conformance heuristic**
for CV variants. Closes Forcing Function #5 (LLM judges in the build)
on the deterministic surface; LLM-backed judges (citation grounding,
re-scoring via local llama.cpp) layer on top of the same API.

## ATS judge — `euxis_publisher.judge.ats`

Scores a CV against the Workday / Greenhouse / Lever / Taleo
extraction heuristics. Local, deterministic, sub-millisecond — no
network, no model, no GPU. Designed as the default scoring path.

### What it checks

| Check | Severity | Deduction |
|---|---|---|
| Missing canonical headings (Experience, Skills, Education) | block | 25 each |
| Missing Summary heading | warn | 15 |
| No email AND no phone in first 1.5 KB | block | 30 |
| Only one of email/phone | warn | 5 |
| Length > 24 KB plain text (~5 pages) | block | 20 |
| Length > 12 KB plain text (~3 pages) | warn | 10 |
| Bullets > 400 chars (Workday truncates) | block | 15 |
| Bullets > 280 chars (Greenhouse parse threshold) | warn | 5 |
| Mixed date formats (MM/YYYY ↔ "Mar 2024" ↔ "2024-2026") | warn | 10 |
| Killer phrases ("References available upon request", etc.) | warn | 5 each |

Grades: A (≥90), B (≥80), C (≥70), D (≥60), F otherwise.

### CLI

```bash
# Score a registered CV — runs render --format text under the hood
python -m euxis_publisher.cli.build judge --doc cv --judge ats

# Write JSON to disk
python -m euxis_publisher.cli.build judge --doc cv --json build/ats-report.json

# Strict mode: exits 1 on grade D or F (use in CI for tailored CVs)
python -m euxis_publisher.cli.build judge --doc cv --strict
```

### Python API

```python
from euxis_publisher.cli.render import render_text
from euxis_publisher.judge.ats import score_cv

# `data` is the CV's parsed YAML
plain = render_text(data, "cv")
report = score_cv(plain)
print(report.score, report.grade)
for f in report.findings:
    print(f.check, f.severity, f.message)
```

### Why heuristic-only by default

Per decision D4 (`docs/strategy-2026.md`), judges are local-first.
Sensitive content (unpublished CVs, draft patents, salary signals) must
not leave the machine without explicit opt-in. The heuristic catches
the most-common ATS-killers — adding an LLM re-score on top is Sprint
7.5 work, gated behind the `[mcp]` extra so it stays opt-in.

## LLM rerank (S7.1) — opt-in local llama.cpp

The heuristic catches mechanical issues. An optional LLM rerank
catches semantic ones — tone match, role-level mismatch, keyword
cluster gaps — that no regex sees. The default backend is
[llama.cpp](https://github.com/ggerganov/llama.cpp), reached over
HTTP:

```bash
# 1. Start the server (one-time):
llama-server --model models/Llama-3-8B-Instruct.Q4_K_M.gguf --port 8080

# 2. Score a CV with the rerank enabled:
python -m euxis_publisher.cli.build judge \
    --doc cv --judge ats \
    --llm-url http://localhost:8080 \
    --llm-timeout 30
```

When the server is unreachable, the CLI prints an info-level breadcrumb
and falls back to heuristic-only — never crashes the build.

The rerank prompt asks for **one** additional finding (capped to a
[-15, +5] score adjustment) so a single bad prompt can't dominate the
grade. The JSON contract:

```json
{
  "score_adjustment": -5,
  "finding": {
    "check": "tone_match",
    "severity": "warn",
    "message": "Director-level language mismatched mid-level role keywords.",
    "deduction": 5
  }
}
```

### Python API

```python
from euxis_publisher.judge import LocalLLM, score_cv_with_llm
from euxis_publisher.cli.render import render_text

plain = render_text(data, "cv")
llm = LocalLLM(base_url="http://localhost:8080")
report = score_cv_with_llm(plain, llm)
# `report.metrics["llm_adjustment"]` records the clamped delta.
```

The LLM client is stdlib-only (`urllib.request` + `json`) — no
`httpx` / `requests` dependency. Errors surface as
`LLMUnavailable`, `LLMTimeout`, `LLMParseError`; callers can catch
the umbrella `LLMError`.

## Roadmap

| Sprint | Item | Status |
|---|---|---|
| S7.3 | ATS-scoring heuristic | ✅ done |
| S7.1 | llama.cpp HTTP adapter (local LLM backend) | ✅ done |
| S7.2 | Citation-grounding judge (ScholarCopilot pattern) | ⏸️ Sprint 7.5 |
| S7.4 | Job-description fit scorer (re-rank tailored CVs vs JD) | ⏸️ Sprint 8 |
| S7.5 | MCP-broker BYO-key for Claude / GPT-5 | ⏸️ Sprint 8 |
