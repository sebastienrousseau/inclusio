# LLM / heuristic judges — `inclusio.judge`

Sprint 7 (S7.3) ships the first judge: an **ATS-conformance heuristic**
for CV variants. Closes Forcing Function #5 (LLM judges in the build)
on the deterministic surface; LLM-backed judges (citation grounding,
re-scoring via local llama.cpp) layer on top of the same API.

## ATS judge — `inclusio.judge.ats`

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
python -m inclusio.cli.build judge --doc cv --judge ats

# Write JSON to disk
python -m inclusio.cli.build judge --doc cv --json build/ats-report.json

# Strict mode: exits 1 on grade D or F (use in CI for tailored CVs)
python -m inclusio.cli.build judge --doc cv --strict
```

### Python API

```python
from inclusio.cli.render import render_text
from inclusio.judge.ats import score_cv

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
python -m inclusio.cli.build judge \
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
from inclusio.judge import LocalLLM, score_cv_with_llm
from inclusio.cli.render import render_text

plain = render_text(data, "cv")
llm = LocalLLM(base_url="http://localhost:8080")
report = score_cv_with_llm(plain, llm)
# `report.metrics["llm_adjustment"]` records the clamped delta.
```

The LLM client is stdlib-only (`urllib.request` + `json`) — no
`httpx` / `requests` dependency. Errors surface as
`LLMUnavailable`, `LLMTimeout`, `LLMParseError`; callers can catch
the umbrella `LLMError`.

## Citation-grounding judge — `inclusio.judge.citations` (S7.2)

Detects two failure modes in scientific papers:

1. **Hallucinated keys** — `\cite{smith2025}` with no matching
   `\bibitem{smith2025}`. Always-on heuristic; catches every LLM-
   generated paper that invented references whole-cloth.
2. **Mis-attributed claims** — `\cite{smith2025}` matched to a real
   bibitem, but the in-text claim around the citation isn't supported
   by what `smith2025` actually says. LLM-only (ScholarCopilot
   pattern), uses the same `LocalLLM` adapter as S7.1.

### Heuristic checks

| Check | Severity | Deduction |
|---|---|---|
| `dangling_citation` (cite key with no bibitem) | block | 15 each, cap 60 |
| `unused_bibitem` (bibitem never cited) | warn | 5 each, cap 20 |
| `duplicate_bibitem` (same key twice) | warn | 10 each |
| `missing_bibliography` (cites exist but no bibitems) | block | 50 |
| `no_citations` + bibitems (entries but no `\cite`) | warn | 10 |
| `no_citations` + no bibitems | info | 0 (review note) |

Sprint 7 scope: inline `\bibitem{key}` entries. `.bib` files via
BibTeX are Sprint 8 work — they need a BibTeX-aware parser (biber
tool-mode) we don't yet ship.

### LLM grounding (opt-in)

```bash
python -m inclusio.cli.build judge \
    --doc whisper-paper --judge citations \
    --llm-url http://localhost:8080
```

The judge:
1. Runs the heuristic first.
2. For up to 10 matched citations (key found in `\bibitem`), sends the
   in-text context + bibitem body to the LLM with the prompt:

   > Does the in-text claim around this citation accurately reflect
   > what the bibitem describes? Reply JSON: `{supported, confidence, reason}`.

3. Flags any `supported: false` with `confidence ≥ 0.6` as a `warn`
   finding (-5 each, deduped per key).

When the LLM is unreachable, a single info breadcrumb is recorded and
the heuristic result is preserved.

### Python API

```python
from inclusio.judge import score_citations, score_citations_with_llm
from inclusio.judge import LocalLLM

tex = Path("src/papers/whisper.tex").read_text()
report = score_citations(tex)              # heuristic only

llm = LocalLLM(base_url="http://localhost:8080")
report = score_citations_with_llm(tex, llm, max_checks=10)
```

## JD-to-CV fit judge — `inclusio.judge.jd_fit` (S7.4)

Compares a CV against a job-description brief and surfaces:
1. **Missing required keywords** — clauses introduced by "required",
   "must have", "minimum", "essential", "you have" get harvested; any
   key term not present in the CV is a block.
2. **Role-level mismatch** — a seniority ladder
   (intern → junior → engineer → senior → staff → principal → director
   → vp → cto) is matched on both sides; gaps of 2 levels warn, 3+
   block.
3. **Low keyword overlap** — Jaccard < 0.10 warns ("stretch role").

Base score is mapped from raw Jaccard via a stepped curve (>=0.45 →
95, >=0.30 → 85, >=0.15 → 70, >=0.05 → 55, else 35) — calibrated
against realistic JD-CV pairs so a strong tailored CV lands in A/B
and a clear mismatch lands in F.

### CLI

```bash
python -m inclusio.cli.build judge \
    --doc cv --judge jd_fit \
    --brief data/jobs/senior-backend-engineer.md \
    --llm-url http://localhost:8080   # optional rerank
```

### Python API

```python
from inclusio.judge import score_jd_fit, score_jd_fit_with_llm
from inclusio.judge import LocalLLM

jd = Path("data/jobs/role.md").read_text()
cv = Path("build/.cache/rendered/cv.txt").read_text()

report = score_jd_fit(jd, cv)                          # heuristic
report = score_jd_fit_with_llm(jd, cv, LocalLLM())     # + LLM rerank
```

LLM rerank prompt asks for *one* top strength + *one* top gap
(severity warn/block/info, deduction capped at 15). On `LLMError`
the heuristic report is returned with an info breadcrumb.

## Cloud LLM adapter — `CloudLLM` (S7.5)

When the data isn't sensitive (public papers, anonymised CVs, generic
JD fits) and judge quality matters more than data residency, the same
judges route through Anthropic or any OpenAI-compatible endpoint.
BYO-key via env var:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m inclusio.cli.build judge \
    --doc cv --judge jd_fit \
    --brief data/jobs/role.md \
    --llm-url https://api.anthropic.com \
    --llm-model claude-opus-4-7
```

For OpenAI-compatible providers (xAI, Together, Groq, DeepSeek):

```bash
export OPENAI_API_KEY=sk-...
python -m inclusio.cli.build judge \
    --doc cv --judge ats \
    --llm-url https://api.openai.com \
    --llm-model gpt-5-pro
```

Provider detection is automatic from the URL:
- contains `anthropic.com` → Anthropic Messages API
- everything else → OpenAI-compatible `/v1/chat/completions`

The adapter is stdlib-only — no `anthropic` / `openai` / `httpx`
package dependency. HTTP 4xx/5xx (401, 403, 429, 5xx) surface as
`LLMUnavailable`, so the judge falls back to heuristic-only with a
clear breadcrumb rather than crashing the build.

### Python API

```python
from inclusio.judge import CloudLLM, from_url

# Explicit:
llm = CloudLLM(
    base_url="https://api.anthropic.com",
    model="claude-opus-4-7",
    api_key="sk-ant-...",  # or unset → falls back to env var
)

# Or let from_url route by base URL:
llm = from_url("https://api.anthropic.com", timeout=60)
llm = from_url("http://localhost:8080")  # → LocalLLM
```

Per decision D4 (`docs/strategy-2026.md`), default to `LocalLLM` for
sensitive content. Cloud is the explicit opt-in.

## Roadmap

| Sprint | Item | Status |
|---|---|---|
| S7.3 | ATS-scoring heuristic | ✅ done |
| S7.1 | llama.cpp HTTP adapter (local LLM backend) | ✅ done |
| S7.2 | Citation-grounding judge (ScholarCopilot pattern) | ✅ done |
| S7.4 | Job-description fit scorer (re-rank tailored CVs vs JD) | ✅ done |
| S7.5 | Cloud LLM adapter (Anthropic + OpenAI BYO-key) | ✅ done |
| S8.x | BibTeX `.bib` support in citations judge | ⏸️ Sprint 8 |
| S8.x | MCP server tool wiring for cloud judges (broker mode) | ⏸️ Sprint 8 |
