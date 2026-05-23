# Euxis Publisher — 2026 Implementation Plan

> Status: drafted 2026-05-23. Owner: @sebastienrousseau. Companion document:
> [`strategy-2026.md`](strategy-2026.md). Horizon: 6 months (P0) with
> follow-on sprints sketched for months 7-12 (P1).

## How to read this plan

- Six-month P0 horizon, broken into **13 two-week sprints** (Sprint 0
  prep + Sprints 1-12). P1 sprints are sketched, not detailed - revisit
  after P0 lands.
- Each work item carries: **ID**, **deliverable**, **files**, **acceptance
  criteria**, **effort** (XS &lt;1d / S 1-2d / M 3-5d / L 1-2w / XL 2-4w),
  **dependencies**, **risk** (Low/Med/High).
- Sprints are sequenced by dependency, not strictly by priority. The
  critical path runs: tagged-PDF foundation → multi-format outputs →
  AI/MCP surface → provenance.
- **Decision gates** (D1-D4) are explicit user/owner choices that gate
  scope. Address them before the sprint that needs them.

---

## Decisions (resolved 2026-05-23)

All four gates resolved by owner. Recorded here as the canonical
decision log; downstream sprints carry these as constraints, not
options.

| Gate | Decision | Rationale | Scope impact |
|---|---|---|---|
| **D1** | **Scope `pub-patent` down to "typesetting only"** | Patent workflow (USPTO/EPO XML, claims numbering, validation) is massive scope creep against ~1.8 FTE constraint; threatens Sprints 4-6. Let patent offices own upstream XML; Euxis renders compliant PDFs from it. | **P2.4 dropped from horizon.** Update `pub-patent.cls` README + main README to scope honestly. No patent-workflow features in P0/P1. |
| **D2** | **Migrate `pub-guide` to Starlight HTML** | Tees up with Sprints 7-9 HTML single-source goal. Starlight is current SOTA for technical docs; eats Markdown natively; accessible by default. | Pull P2.3 forward into Sprint 7-8 timeframe (paired with HTML emitter work). PDF becomes export, not primary. |
| **D3** | **Hard-require LuaLaTeX** | Flexibility across pdfTeX/XeTeX/LuaLaTeX would burn months of QA on tagged-PDF + EAA compliance. LuaLaTeX has native hooks for reliable tagging automation. | **Effective immediately (Sprint 0).** Drop pdfTeX/XeTeX support code paths; update `meta.yaml` `build.compiler` default; deprecate any pdflatex-specific docs. |
| **D4** | **Default LLM judge to local open-weight (Llama 3/4) with MCP-broker BYO-key for Claude/GPT-5** | Pre-publication manuscripts, unreleased patent data, JSON resumes are sensitive. Zero data leakage by default. Heavy reasoning users plug in API keys via the MCP server (Sprint 11). | Sprint 12 LLM judge implementation is **local-first**: `llama.cpp` HTTP adapter is the default; cloud adapters are opt-in. Affects model adapter design in `tools/llm_judge.py`. |

---

## Sprint 0 (week 0) — Foundation

**Goal:** establish baselines so every following sprint can measure
regression.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S0.1 | **Baseline veraPDF report** on every PDF currently in `build/` (across CV/paper/patent/faq/guide) | new `scripts/audit_baseline.sh`, output to `build/.audit/baseline-2026-05.json` | Report committed; numbers documented in this plan | XS | Low |
| S0.2 | **Apply D3 (LuaLaTeX hard-require)** — drop non-LuaLaTeX code paths; default `build.compiler: lualatex` in private `meta.yaml`; document in `docs/architecture.md` | `core/cls/pub-base.cls`, `docs/architecture.md`, `data/meta.yaml` (private) | All build paths assume LuaLaTeX; pdflatex/xelatex code/docs removed or deprecated | S | Low |
| S0.3 | **Sprint cadence + tracking** - decide if work goes in GitHub Issues, Linear, or this doc | repo settings | First five sprints have tickets in chosen tracker | XS | Low |
| S0.4 | **CI matrix expansion plan** - which OS/TeX-distribution combos to support (mactex, texlive-2024, miktex?) | `.github/workflows/*` | Matrix documented; veraPDF available on runners | S | Low |
| S0.5 | **Add `docs/strategy-2026.md` + `docs/implementation-plan-2026.md` to docs index** | `docs/README.md`, `docs/index.md` | Docs site builds; new entries linked | XS | Low |

---

## Sprint 1 (weeks 1-2) — Tagged-PDF foundation (P0.1 part 1)

**Goal:** `tagpdf` activates cleanly in `pub-base.cls` behind a feature
flag; first test paper emits `Tagged: yes`.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S1.1 | **Add `[tagged]` class option** in `pub-base.cls` that loads `tagpdf` and emits `\DocumentMetadata{}` preamble | `core/cls/pub-base.cls`, `core/sty/pub-metadata.sty` | Building any `pub-*` with `[tagged]` option produces `pdfinfo: Tagged: yes` | M | Med (tagpdf is experimental) |
| S1.2 | **Auto-enable `[tagged]` when `pdf_a` in meta.yaml is `a-2` or `a-4` and mode is camera-ready** | `cli/build.py` mode handling | Camera-ready builds set `Tagged: yes` automatically | S | Med |
| S1.3 | **veraPDF CI job** runs on every PDF artefact; tagged PDF must validate as WTPDF 1.0 | new `.github/workflows/verapdf.yml`, `scripts/run_verapdf.sh` | CI fails if camera-ready PDF is not WTPDF-1.0 conformant | M | Med (CI flake potential) |
| S1.4 | **Regression test on existing documents** - what breaks when tagged? | `tests/test_pdf_ua.py` | Test inventory: which classes pass, which need follow-up | M | High (likely several classes need retrofits) |
| S1.5 | **`[final-untagged]` escape hatch** for any class that can't go tagged immediately | `pub-base.cls` | Option exists and is documented as transitional | XS | Low |

**Sprint exit criteria:** at least one of (paper, cv, faq) emits a
`Tagged: yes` WTPDF-1.0-valid PDF in camera-ready mode through the
normal build CLI. Other classes documented as "needs retrofit".

---

## Sprint 2 (weeks 3-4) — Tagged-PDF rollout to all classes (P0.1 part 2)

**Goal:** every `pub-*.cls` produces a WTPDF-1.0-valid tagged PDF in
camera-ready mode.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S2.1 | **Retrofit `pub-paper.cls`** - tag `\section`/`\subsection`/`\item`/`\caption` with proper structure | `pub-paper.cls` | veraPDF green; reading order correct in Adobe Acrobat reading-order pane | L | Med |
| S2.2 | **Retrofit `pub-cv.cls`** | `pub-cv.cls` | veraPDF green; screen reader reads CV in logical order | L | Med |
| S2.3 | **Retrofit `pub-faq.cls`** and `pub-guide.cls` | both classes | veraPDF green | M | Low |
| S2.4 | **Retrofit `pub-patent.cls`/`pub-patent-us.cls`** (gated on D1 - if scoping down, this is "best effort") | both classes | veraPDF green or explicit "untagged" exception with rationale | M | Med |
| S2.5 | **Retrofit `pub-bio.cls`, `pub-arxiv.cls`, `pub-preprint.cls`, `pub-prime.cls`** | each class | All veraPDF green or untagged exception documented | M | Low |
| S2.6 | **Update `docs/classes-and-styles.md`** with tagging matrix | `docs/classes-and-styles.md` | Matrix shows which classes are tagged-ready | XS | Low |

**Sprint exit criteria:** `make publish` against the private repo
produces tagged PDFs for every approved document; veraPDF CI gate is
green on main.

---

## Sprint 3 (weeks 5-6) — PDF/A-4 + EAA audit CLI (P0.2 + P0.3)

**Goal:** Euxis can target PDF/A-4 and ships an `audit` command that
produces an EAA conformance report.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S3.1 | **PDF/A-4 support in `pub-metadata.sty`** - `\setPdfALevel{a-4}` switches pdfx config | `core/sty/pub-metadata.sty` | Building with `\setPdfALevel{a-4}` produces PDF with `pdfinfo: PDF subtype: PDF/A-4` | M | Med (pdfx PDF/A-4 maturity) |
| S3.2 | **Schema update** - `pdf_a` regex accepts `a-4`, `a-4e`, `a-4f` | `data/meta.schema.yaml` (private repo) | YAML lint accepts new levels | XS | Low |
| S3.3 | **New `cli/audit.py`** - runs veraPDF + WCAG-relevant checks; emits machine-readable + human-readable report | new `euxis_publisher/cli/audit.py`, `Makefile` target `make audit` | `python -m euxis_publisher.cli.audit build/papers/foo.pdf` returns exit code + JSON + Markdown summary | L | Med |
| S3.4 | **`tests/test_eaa.py`** parameterised over all built PDFs | new test file | Fails on EAA-relevant veraPDF violations | M | Med |
| S3.5 | **CI gate `eaa-audit`** on tagged release builds | `.github/workflows/release.yml` | Release blocked if EAA audit fails | S | Low |

**Sprint exit criteria:** `make audit` works locally and in CI; release
artefacts pass EAA gate.

---

## Sprint 4 (weeks 7-8) — AI-disclosure metadata + STM mapping (P0.4)

**Goal:** YAML schema carries STM-aligned AI-disclosure metadata that
propagates to PDF XMP + (future) JATS.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S4.1 | **`ai_disclosure:` block** in `meta.schema.yaml` mapped to STM Sept-2025 taxonomy (drafting, editing, translation, code, data, figures) | `data/meta.schema.yaml` (private repo), example in public repo `data/meta.yaml` | Schema validates; example documents declare AI use | S | Low |
| S4.2 | **New `\AIUse{}` macro** in `pub-metadata.sty` that emits XMP custom property | `core/sty/pub-metadata.sty` | `pdfinfo -meta` shows AI-use XMP fields | S | Low |
| S4.3 | **Renderer hook** - `cli/render.py` passes `ai_disclosure` from YAML into Jinja2 templates | `cli/render.py` | Templates can reference `<< ai_disclosure >>` | XS | Low |
| S4.4 | **Documentation page** `docs/ai-disclosure.md` explaining the schema and STM mapping | new `docs/ai-disclosure.md` | Reviewers can self-serve the schema | S | Low |
| S4.5 | **`tests/test_ai_disclosure.py`** validates schema + XMP round-trip | new test file | 100% schema coverage | S | Low |

**Sprint exit criteria:** publishing a paper with `ai_disclosure:` block
in YAML produces a PDF whose XMP carries the disclosure; CI tests pass.

**Decision gate D1 (patent vertical) is due before Sprint 4.** If
scope-down decision: skip patent-specific tagging retrofit; update
`pub-patent.cls` README accordingly; remove "patent workflow" claims
from main README.

---

## Sprint 5 (weeks 9-10) — JSON Resume importer + Workday DOCX consolidation (P0.6)

**Goal:** Euxis ingests the open CV standard; existing Workday DOCX
emit is consolidated into a reusable surface.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S5.1 | **New `cli/import.py`** with `--json-resume` flag converting JSON Resume to Euxis YAML | new `euxis_publisher/cli/import.py` | `python -m euxis_publisher.cli.import --json-resume cv.json --out data/cv-data.yaml` works on jsonresume.org sample | L | Low |
| S5.2 | **JSON Resume schema validator** in tests | `tests/test_import.py` | Imports valid + rejects malformed | M | Low |
| S5.3 | **Refactor `_render_cv_markdown`** out of `cli/render.py` into `tools/cv_docx.py` (cleaner surface; reusable from import path) | `cli/render.py`, new `tools/cv_docx.py` | All existing CV DOCX tests still pass | M | Med |
| S5.4 | **Round-trip test**: import JSON Resume → render to PDF → render to DOCX → check no field loss | `tests/test_json_resume_roundtrip.py` | All fields traceable | M | Med |
| S5.5 | **Docs**: `docs/json-resume-import.md` with worked example | new doc | Tutorial works end-to-end | S | Low |

**Sprint exit criteria:** A user with a `resume.json` from
jsonresume.org can produce a tagged PDF + Workday DOCX in two commands.

---

## Sprint 6 (weeks 11-12) — ATS conformance validator (P0.7)

**Goal:** Euxis tells the user how their CV will score in Workday,
Greenhouse, and Lever before they submit.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S6.1 | **Rule packs** for Workday/Greenhouse/Lever as YAML rule files | new `data/ats-rules/workday.yaml`, `greenhouse.yaml`, `lever.yaml` (in public repo for community contribution) | Rules documented with source URLs | M | Low |
| S6.2 | **New `tools/ats_validator.py`** that takes PDF + DOCX, extracts text via `pdfminer.six` / `python-docx`, runs rules, emits score + remediation | new tool | `python -m euxis_publisher.tools.ats_validator build/cvs/my-cv.pdf --target workday` returns numeric score + diff list | L | Med |
| S6.3 | **CI gate `ats-cv-score`** for CV builds in private repo - fails if Workday score below threshold | `.github/workflows/*` (private repo) | CV PRs blocked if regress below threshold | S | Low |
| S6.4 | **`tests/test_ats.py`** with at least 5 golden CVs (scored + non-scored variants) | tests | 100% rule coverage | M | Low |
| S6.5 | **`docs/ats-validation.md`** explaining each rule, source, and severity | new doc | Rule provenance auditable | S | Low |

**Sprint exit criteria:** running `make publish` on a CV shows its
Workday/Greenhouse/Lever scores in the build log; CI blocks regression.

---

## Sprint 7 (weeks 13-14) — DOCX track-changes round-trip (P0.8)

**Goal:** non-LaTeX reviewers can add comments + track-changes in Word;
Euxis re-imports them as block-level annotations.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S7.1 | **Pandoc Lua filter** for track-changes preservation (extract DOCX → AST with revisions) | new `core/lua/track-changes.lua` | Filter handles `accept`/`reject`/`all` modes | L | Med (Lua is fiddly) |
| S7.2 | **New `tools/docx_review.py`** - takes annotated DOCX, emits review-overlay YAML alongside source | new tool | `euxis review --import reviewed.docx --source data/foo.yaml` produces `data/foo.review.yaml` with anchored comments | XL | High (heuristics for re-anchoring) |
| S7.3 | **Re-anchor anchors** to Jinja2 template block IDs (so comments survive template re-rendering) | template authoring | Anchors are stable; comments don't drift | L | High |
| S7.4 | **`tests/test_docx_review.py`** golden tests | tests | Round-trip lossless on 3 sample documents | M | Med |
| S7.5 | **`docs/word-review-loop.md`** worked example | new doc | Reviewer workflow documented | S | Low |

**Sprint exit criteria:** Author sends DOCX to reviewer; reviewer adds
comments + track-changes in Word; author runs `euxis review --import`;
comments appear as annotations in YAML.

**Decision gate D2 (`pub-guide` Starlight migration) is due before
Sprint 7.** If migrating, Sprint 7 splits in two: half the bandwidth
goes to a Starlight skeleton, deferring DOCX round-trip to Sprint 8.

---

## Sprint 8 (weeks 15-16) — JATS XML emitter (P0.9)

**Goal:** `pub-paper`/`pub-preprint`/`pub-arxiv` emit JATS 1.4 alongside
PDF.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S8.1 | **Pandoc-based JATS emitter** invoked from `cli/render.py --format jats` | new `cli/render_jats.py`, extend `render.py` | Existing whisper paper renders to JATS 1.4 | L | Med |
| S8.2 | **YAML to JATS metadata mapping** - title, abstract, authors, ORCID, ROR, affiliations, CRediT roles, references | `cli/render_jats.py` | jats4r validator green on whisper paper output | L | Med |
| S8.3 | **JATS4R recommendations** - data availability, COI, funding statements, license | extension | jats4r validator green on patent of fields | M | Low |
| S8.4 | **`tests/test_jats.py`** parametrised over all paper-class documents | tests | Validates against `jats-publishing-dtd` XSD | M | Med |
| S8.5 | **`docs/jats-output.md`** | new doc | Tutorial walks through `--format jats` | S | Low |

**Sprint exit criteria:** `make publish` produces both `.pdf` and
`.jats.xml` for every paper-class document; both pass validation.

---

## Sprint 9 (weeks 17-18) — HTML single-source output (P0.10)

**Goal:** Single source emits PDF + JATS + HTML for `pub-paper` and
`pub-bio`.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S9.1 | **New `templates/paper.html.j2`** + `templates/bio.html.j2` | new templates | HTML output renders typographically correct in Chrome/Safari/Firefox | L | Med |
| S9.2 | **Pandoc-based HTML emitter** invoked from `cli/render.py --format html` | extend `render.py`, new `cli/render_html.py` | Whisper paper renders to standalone HTML | L | Med |
| S9.3 | **CSS reset + print stylesheet** with golden-ratio typography parity | new `core/css/pub-paper.css` | HTML reads as well as PDF; prints sensibly | M | Med |
| S9.4 | **JSON-LD `ScholarlyArticle` block** in HTML `<head>` (sets up P1.2) | template | Crossref's structured data tester validates | S | Low |
| S9.5 | **`tests/test_html.py`** - html5lib parse + Pa11y accessibility audit | tests | All HTML outputs WCAG-2.2-AA green | M | Med |
| S9.6 | **`docs/html-output.md`** | new doc | Worked example | S | Low |

**Sprint exit criteria:** Every paper-class document produces a
publication-quality HTML + JATS + PDF triple; HTML passes Pa11y.

---

## Sprint 10 (weeks 19-20) — PAdES signing in CI (P0.5)

**Goal:** Every camera-ready PDF leaving CI is eIDAS-aligned signed.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S10.1 | **New `tools/sign_pades.py`** using pyHanko - B-T (with timestamp) by default, B-LTA for archival | new tool | `python -m euxis_publisher.tools.sign_pades build/papers/foo.pdf` signs in place | M | Med (cert provisioning) |
| S10.2 | **CI workflow** uses GitHub Actions OIDC + eIDAS test CA for signing (production cert path documented) | new `.github/workflows/sign-release.yml` | Tagged releases ship signed PDFs | M | Med |
| S10.3 | **DSS validator** integration - validate every signed PDF against EU Commission DSS | extend `tools/sign_pades.py` | DSS verdict in CI log | S | Low |
| S10.4 | **`tests/test_pades.py`** | tests | Signature verifies; timestamp present | S | Low |
| S10.5 | **`docs/signing-pdfs.md`** with cert-provisioning walkthrough | new doc | User can self-serve cert setup | M | Low |

**Sprint exit criteria:** Releases contain signed PDFs; CI logs show DSS
green verdict.

---

## Sprint 11 (weeks 21-22) — `euxis-mcp` server (P1.3, pulled forward)

**Goal:** Euxis is visible to every Claude Code / Cursor / Continue
user via MCP.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S11.1 | **New `cli/mcp.py`** exposing `list`, `build`, `render`, `tailor`, `validate`, `audit`, `sitemap` as MCP tools using the official Python MCP SDK | new `euxis_publisher/cli/mcp.py`, `pyproject.toml` adds `mcp` dep | `claude mcp add euxis -- python -m euxis_publisher.cli.mcp` registers; tools appear in Claude Code | L | Med (MCP API churn) |
| S11.2 | **Resource provider** - rendered PDFs and JATS appear as MCP resources for AI consumers | extension | `list_resources` returns built artefacts | M | Med |
| S11.3 | **Entitlement gate** - `EUXIS_MCP_ALLOW_BUILD=true` to enable destructive tools | env-var handling | Read-only mode by default; build/tailor only with explicit opt-in | S | Low |
| S11.4 | **`tests/test_mcp.py`** - exercise each tool through the SDK | tests | 100% tool coverage | M | Med |
| S11.5 | **`docs/mcp-server.md`** + add `/euxis` Claude skill stub | new doc, new `skills/euxis-publishing/SKILL.md` | Claude Code user can run "list my documents" and get a useful answer | S | Low |

**Sprint exit criteria:** `claude mcp list` shows `euxis`; the tools
work in Claude Code's tool picker; published as MCP skill.

---

## Sprint 12 (weeks 23-24) — LLM judge stage (P1.5)

**Goal:** `euxis validate` runs three configurable LLM judges and
produces a Markdown report.

| ID | Deliverable | Files | Acceptance | Effort | Risk |
|---|---|---|---|---|---|
| S12.1 | **New `tools/llm_judge.py`** with three judges: prose quality (Grammarly-class), citation grounding (each `\cite{}` resolves via Crossref/DataCite), class-specific (CV ATS / paper claim-evidence ratio / patent §112) | new tool | `euxis validate --llm --doc foo` produces `build/.audit/foo-llm.md` | XL | High (judge prompts need tuning) |
| S12.2 | **Model-agnostic adapter** - pluggable Anthropic / OpenAI / local (llama.cpp via HTTP) per D4 | adapter pattern | Switching model via env var | M | Med |
| S12.3 | **Prompt library** with versioned rubrics per class | new `core/prompts/` directory | Each rubric carries provenance + version | M | Low |
| S12.4 | **Cost guardrails** - estimate tokens before running; opt-in for >$0.10 per doc | tool config | Cost log per run | S | Low |
| S12.5 | **`tests/test_llm_judge.py`** with offline judge stub | tests | Tests pass without network | M | Med |
| S12.6 | **`docs/llm-judge.md`** | new doc | Worked example for each judge | S | Low |

**Sprint exit criteria:** `make validate` runs LLM judges and writes
human-readable reports; CI runs offline judge stub; production opt-in
documented.

---

## Sprints 13-26 (P1 sketch, months 7-12)

Detailed sprint breakdown deferred until P0 ships and Sprint-0
baselines are refreshed. High-level sequence:

- **Sprint 13-14**: ROR + ORCID + CRediT YAML schema + JATS + XMP
  propagation (P1.1, P1.2)
- **Sprint 15-16**: Citation hallucination detector + RAG over author
  corpus (P1.6, P1.7)
- **Sprint 17-18**: JD-to-CV closed-loop tailor with interactive diff
  UI (P1.8) + multi-locale CV (P1.9) + Europass export (P1.10)
- **Sprint 19-20**: SLSA L2 + Sigstore + in-toto attestation (P1.11) +
  C2PA Content Credentials (P1.12)
- **Sprint 21-22**: DOCX comments round-trip (P1.13) + JATS4R full
  tagging (P1.14)
- **Sprint 23-24**: `flake.nix` + Devbox discoverability (P1.15) +
  Claude Code skill + Cursor rules pack (P1.4) + `pub-guide`
  Starlight migration (P2.3 if D2 = migrate)
- **Sprint 25-26**: Buffer + retrospective + P2 planning

---

## P2 sketch (months 13-24, in priority order)

- **P2.1 Typst backend** (Q3 2027): `pub-paper-typst` experimental
  class behind feature flag. ~12 weeks effort.
- **P2.4 Patent workflow expansion** (if D1 = commit): separate
  sub-repo. ~16 weeks effort.
- **P2.5 Executable code blocks**: ~6 weeks.
- **P2.9 `euxis serve --collab`** minimal web editor: ~12 weeks.
- Other P2 items: smaller, opportunistic.

---

## Cumulative effort (P0 only)

Sum of P0 sprints 1-12 effort points:
- XS: 9 items → ~5 days
- S: 18 items → ~27 days
- M: 21 items → ~63 days
- L: 11 items → ~88 days
- XL: 2 items → ~32 days

**Total: ~215 person-days**, against **120 calendar days** (6 months
× 4 working weeks × 5 days). **Implies ~1.8 FTE sustained** for P0 to
land on schedule. With 1.0 FTE the calendar stretches to ~11 months;
with 0.5 FTE to ~22 months and P1 slips off the horizon entirely.

**Recommendation**: if 1 FTE is the realistic capacity, defer Sprints
10-12 (PAdES, MCP, LLM judge) by 3 months and treat them as Sprint
13-15 of an extended P0+P1 plan. The accessibility/EAA P0 items
(Sprints 1-3) are non-negotiable regardless of capacity.

---

## Per-sprint output template

For each sprint, produce in `build/.audit/sprint-NN/`:

```
sprint-NN/
  goal.md              # one-line restatement of sprint goal
  deliverables.md      # check-list of items completed vs deferred
  metrics.json         # tests added, lint rules added, classes touched
  decisions.md         # any micro-decisions made during sprint
  blockers.md          # if non-empty, lifts to next sprint planning
```

This pattern (rather than freeform commit messages) makes the plan
auditable retroactively and feeds into the strategy doc's risk
register.

---

## Definition of done (every sprint)

A sprint is **not** done until all of the following are green:

- [ ] All sprint deliverables shipped or explicitly deferred with reason.
- [ ] `make test` + `make lint` + `make coverage` green on `main`.
- [ ] `make audit` (Sprint 3+) green on all built PDFs.
- [ ] `tests/test_pdf_ua.py` (Sprint 1+) green.
- [ ] No regression in existing build artefact byte size > 20%.
- [ ] `docs/*.md` updated for any new public surface.
- [ ] CHANGELOG entry written.
- [ ] Sprint output written to `build/.audit/sprint-NN/`.

---

## Open questions to track

| Q | Asked of | Owner | Status |
|---|---|---|---|
| Will tier-1 publishers accept JATS bundles from Euxis-built sources by end-2026? | NISO + selected journals | @sebastienrousseau | Investigate during Sprint 8 |
| Is veraPDF licence (MPL-2.0) compatible with Euxis MIT? | legal-style review | @sebastienrousseau | Confirm in Sprint 0 |
| Does pdfx upstream maintain PDF/A-4? | TeX Live mailing list | @sebastienrousseau | Investigate in Sprint 3 |
| What is the smallest viable C2PA manifest for a PDF in 2026? | C2PA WG | @sebastienrousseau | Investigate during Sprint 19 (P1) |
| Will the STM AI-disclosure taxonomy stabilise before Sprint 4? | STM WG | @sebastienrousseau | Track quarterly |

---

## Pointers

- Companion strategy: [`strategy-2026.md`](strategy-2026.md)
- Architecture: [`architecture.md`](architecture.md)
- Classes & styles: [`classes-and-styles.md`](classes-and-styles.md)
- Usage: [`usage.md`](usage.md)
- Public/private boundary: [`public-private-boundary.md`](public-private-boundary.md)
