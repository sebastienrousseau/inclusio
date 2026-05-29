# Tutorial 2 — Scoring a CV against an ATS

> 20 minutes · Difficulty: easy · Example:
> [`examples/02-cv-from-jsonresume/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/02-cv-from-jsonresume/)

By the end of this tutorial you'll have a CV PDF built from a JSON
Resume document, plus a graded report from the ATS heuristic and a
fit score against a target job description.

## Why inclusio scores CVs

Applicant Tracking Systems (Workday, Greenhouse, Lever, Taleo, …)
parse PDFs with text-extraction heuristics that vary across vendors.
Lockstep parsing failures sink even strong CVs before a recruiter
sees them. inclusio's `ats` judge replicates the most common
deal-breakers as a local, deterministic check.

> **2026 note:** Workday's Paradox conversational ATS (GA January
> 2026) is shifting high-volume hiring away from keyword extraction
> for frontline roles. The ATS judge remains useful for Greenhouse,
> Lever, and the long-tail; treat it as one signal among many.

## Step 1 — Set up

```bash
pip install inclusio
# LuaLaTeX (for the build step) and Pandoc (optional, for HTML emit).
```

The example folder includes a `resume.json` (jsonresume.org v1
schema) and a `brief.txt` (a sample job description).

## Step 2 — Convert JSON Resume → CV YAML

inclusio's CV template (`templates/cv.tex.j2`) consumes a YAML schema.
The `import-resume` subcommand converts a JSON Resume document into
that schema:

```bash
cd examples/02-cv-from-jsonresume
inclusio import-resume resume.json -o data/cv-data.yaml
```

Mappings applied (full list in
[`inclusio/cli/import_resume.py`](https://github.com/sebastienrousseau/inclusio/blob/main/inclusio/cli/import_resume.py)):

| JSON Resume block | inclusio block |
|---|---|
| `basics.name` / `label` / `summary` | `name` / `role` / `summary` |
| `work[]` + `volunteer[]` | `experience[]` |
| `education[]` | `education[]` |
| `skills[]` | `competencies[]` |
| `languages[]` | `languages` (joined) |
| `awards[]` + `publications[]` | `innovation[]` |
| `projects[]` | `projects[]` (passes through) |

Long summaries (> 200 chars) get promoted to `executive_profile`;
short ones land in `summary`. Dates are normalised from ISO
`YYYY-MM-DD` to `MM/YYYY – Present` because the ATS judge expects
the MM/YYYY form.

## Step 3 — Render + build the PDF

```bash
inclusio build --doc cv --mode draft
```

This is a two-step process under the hood:

1. **Render** — Jinja2 expands `templates/cv.tex.j2` against
   `data/cv-data.yaml` → `build/.cache/rendered/cv.tex`.
2. **Build** — LuaLaTeX compiles that source → `build/cv.pdf`
   (tagged).

The CV uses the `pub-cv` class (in [`core/cls/`](https://github.com/sebastienrousseau/inclusio/tree/main/core/cls/))
which sets up the ATS-friendly column layout, contact-block
typography, and bullet density that ATS parsers expect.

## Step 4 — Run the ATS judge

```bash
inclusio judge --doc cv --judge ats
```

The judge scores six checks:

| Check | Common failure mode |
|---|---|
| Canonical section headings | "Professional Background" ≠ Workday's "Experience" field |
| Contact info | Phone OR email required; both preferred |
| Length | < 12 KB ideal; > 24 KB recruiters skim |
| Bullet density | Greenhouse caps role bullets at ~280 chars |
| Date consistency | MM/YYYY ↔ "Mar 2024 - Present" confuses parsers |
| Killer phrases | "References on request", "Objective:" — drop them |

You'll get a grade (A → F), a numeric score (0-100), and a per-check
finding list:

```
ATS report: cv
Grade: A (96/100)
Findings: 1
  [info] killer_phrases: no banned phrases detected
  ...
```

## Step 5 — Run the JD-fit judge

```bash
inclusio judge --doc cv --judge jd_fit --brief brief.txt
```

JD-fit scores how well the CV matches a target role:

1. **Keyword overlap** (Jaccard set similarity) between the CV's
   tokens and the JD's "Required:" / "Must have:" clauses.
2. **Seniority match** (junior / staff / senior / principal / vice /
   chief — first match in source order, not max).
3. **Required-keyword coverage** — which JD requirements are absent
   from the CV.

```
JD-fit report: cv
Score: 78/100
  required_coverage: 88%
  jaccard: 0.42
  seniority_match: senior (cv) ↔ senior (jd)
  missing_required: [rust, opentelemetry]
```

## Step 6 — Add LLM rerank (optional)

Both judges accept `--llm-url` for an optional LLM-based rerank pass.
Local llama.cpp:

```bash
inclusio judge --doc cv --judge ats \
  --llm-url http://localhost:8080 \
  --llm-timeout 30
```

Cloud (BYO-key):

```bash
export ANTHROPIC_API_KEY="sk-..."
inclusio judge --doc cv --judge ats \
  --llm-url https://api.anthropic.com/v1/messages \
  --llm-model claude-opus-4-7
```

The judges always run the heuristic first and treat the LLM as a
rerank. If the LLM is unreachable, the judge falls back to
heuristic-only with a clear breadcrumb in the report.

inclusio never auto-discovers API keys; you must set the env var
explicitly. See
[`docs/judges.md`](../judges.md) for the full BYO-key contract.

## What's actually happening

```
resume.json ──[import-resume]──> cv-data.yaml ──[render]──> cv.tex
                                                              │
                                                              ▼
                                                       [LuaLaTeX]
                                                              │
                                                              ▼
cv.pdf ──[render --format text]──> cv.txt ──[judge ats]──> report.json
                                            └[judge jd_fit + brief.txt]
```

The text shadow (`cv.txt`) is what ATS pipelines actually parse, so
that's what the judge scores — keeping the visual layout of the PDF
out of the equation.

## Common questions

**Can I skip the JSON Resume step?** Yes. If you already have a CV
YAML in `data/cv-data.yaml`, run `inclusio build --doc cv` directly.

**What if the LLM rerank disagrees with the heuristic?** The
heuristic decides the grade; the LLM adds findings. Treat the LLM
report as advisory.

**Can I rerun against a different JD?** Yes — pass a different
`--brief`. The CV doesn't change.

## Next steps

- [Tutorial 3 — Driving inclusio from an MCP agent](./03-mcp-agent.md)
- [Tutorial 4 — Camera-ready chain](./04-camera-ready.md)
- [`docs/judges.md`](../judges.md) — the reference docs on the judges.
