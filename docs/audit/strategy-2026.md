# Euxis Publisher — 2026 Strategy & Gap Analysis

> Status: drafted 2026-05-23. Owner: @sebastienrousseau. Companion document:
> [`implementation-plan-2026.md`](implementation-plan-2026.md).
>
> **Decisions log (2026-05-23):**
> - **D1 - `pub-patent` vertical**: scoped down to typesetting-only. P2.4
>   patent-workflow expansion is dropped from the roadmap.
> - **D2 - `pub-guide`**: migrating to Starlight HTML; PDF becomes
>   export, not primary. Pulled forward into Sprints 7-8.
> - **D3 - LuaLaTeX**: hard-required from Sprint 0. pdfTeX/XeTeX paths
>   removed.
> - **D4 - LLM judge**: local open-weight (Llama 3/4) by default; MCP
>   server exposes BYO-key adapters for Claude / GPT-5.

## 0. TL;DR

Euxis today is a **high-quality 2021-era LaTeX renderer with thoughtful
Python orchestration**. The 2026 baseline has shifted:

- **EAA enforcement is live (28 June 2025).** Untagged PDF/A-2u is a
  regulatory exposure for any EU consumer audience. Single most urgent fix.
- **Single-source multi-format (PDF + HTML + JATS + DOCX) is table-stakes**,
  not a differentiator. Quarto and MyST have won this surface for scholarly
  content.
- **AI-native authoring (MCP servers, Claude/Cursor skills, RAG-grounded
  citations, LLM judges) is where new authors live.** A tool without an MCP
  endpoint and a published skill is not visible.
- **Typst is a 24-month strategic threat, not a 6-month one.** Publisher
  acceptance is still effectively zero, but a tier-1 publisher blessing
  Typst in 2027-2028 would trigger 15-25%/year migration of new-author
  papers.

The path to de facto status is three concentric rings: (1) become
*legally compliant* (P0, 6 months), (2) reach *Quarto-parity* on the
engineering surface (P1, 12 months), (3) ship *unique differentiators*
- full patent workflow, JD-to-CV closed-loop tailoring, Typst dual-backend,
MCP-native (P2, 18-24 months).

---

## 1. The eight forcing functions

| # | Forcing function | Concrete trigger | Affected files |
|---|---|---|---|
| 1 | EAA enforcement live | EN 301 549 / WCAG 2.2 AA mandatory for in-scope products to EU consumers since 28 Jun 2025 | `core/sty/pub-metadata.sty`, `core/cls/pub-base.cls`, all `pub-*.cls` |
| 2 | PDF/A-2u to PDF/A-4 + PDF/UA-2 + WTPDF | ISO 14289-2:2024 published; PDF/A-2u is "Unicode-mapped" but not tagged; WTPDF 1.0 baseline expected of new producers | `pub-metadata.sty` (pdfx call), `meta.yaml` `pdf_a` schema |
| 3 | Single-source multi-format | Quarto/MyST/Jupyter Book 2 ship PDF+HTML+JATS+DOCX from one source; tier-1 publishers accept the Quarto manuscript bundle directly | `inclusio/cli/build.py`, `templates/paper.tex.j2`, no JATS/HTML emitter exists |
| 4 | AI authoring layer | Cursor/Claude Code are where 2026 authors live; MCP is the brokered-access protocol per NISO Plus 2026 | No `inclusio-mcp` server, no Claude skill, no Cursor rules |
| 5 | LLM judges in the build | ScholarCopilot/FACTUM-class citation grounding now SOTA; ATS-scoring for CVs is one-click in JobSprout/Rezi | `chktex`+`vale` are the only quality gates; no LLM judge stage |
| 6 | STM AI-disclosure metadata | STM Sept 2025 classification; portal enforcement expected 2026-2027 | `meta.yaml` schema has no `ai_disclosure:` block |
| 7 | PAdES / C2PA / SLSA provenance | eIDAS-aligned PDF signing; C2PA Content Credentials on documents; Sigstore-signed wheels expected in OSS supply chain | `stamp_pdfs.py` does git-hash stamping only |
| 8 | Patent vertical credibility | ClaimMaster 2026 ships LLM-assisted drafting, PatSnap ships prior-art + FTO, Rowan ships drafting-from-scratch | `pub-patent.cls`/`pub-patent-us.cls` are typesetting-only |

Any one of these going unaddressed in 2026 deletes a different audience.

---

## 2. Capability matrix (current state)

| Capability | Status | Evidence |
|---|---|---|
| LaTeX classes (paper/cv/patent/faq/guide/bio/preprint/arxiv/prime) | Strong | 11 classes under `core/cls/` |
| Style packages (typography, colors, buildmodes, metadata, common) | Strong | 5 styles under `core/sty/` |
| PDF/A archival output | Partial | `pub-metadata.sty` defaults to `a-2u`, pdfx-based |
| Structural tagging (PDF/UA-1/2) | Missing | `pdfinfo` reports `Tagged: no`; `tagpdf` optional |
| JATS XML output | Missing | No emitter in `cli/render.py` |
| HTML / MDX / ePub output | Missing | render.py supports `latex|markdown|json` only |
| DOCX export | Partial | `_render_cv_markdown` to pandoc, CV-only |
| DOCX track-changes round-trip | Missing | No comment/track-change ingestion |
| Workday DOCX | Strong | canonical headings + MM/YYYY dates |
| Jinja2 templates with LaTeX-safe delimiters | Strong | `templates/*.tex.j2` + `meta.yaml` registry |
| Build modes (draft/submission/camera-ready) | Strong | `pub-buildmodes.sty` |
| Build CLI commands | Strong | build/render/blog/tailor/sitemap/lint/list/fix/assets |
| Brief promotion (txt/md/rtf/doc/docx/odt/html to tailored YAML) | Strong | `_sync_jobs_to_tailored` in build.py |
| Tailor CLI (LLM-assisted, keyword fallback) | Strong | `cli/tailor.py` uses `claude -p` |
| ATS conformance validator | Missing | No Workday/Greenhouse/Lever scoring |
| JSON Resume ingestion | Missing | YAML schema is bespoke |
| Europass export | Missing | No multi-locale CV source-of-truth |
| Multi-locale CV (one YAML by N languages) | Missing | English-only |
| Crossref/DataCite/Zotero/CSL integration | Missing | Raw `.bib` only |
| ORCID / ROR / CRediT propagation | Missing | No author identifier schema |
| Patent workflow (prior-art, claim graph, USPTO XML) | Missing | Typesetting only |
| Quality gates: chktex, vale, semantic, forbidden commands, XMP | Strong | 178 tests, 114 lint |
| LLM judge in build pipeline | Missing | No prose / citation / class-specific judge |
| PAdES signing | Missing | `stamp_pdfs.py` does pikepdf metadata only |
| C2PA Content Credentials | Missing | No manifest emission |
| SLSA L2 + Sigstore + in-toto attestation | Missing | No release attestation in CI |
| MCP server | Missing | No `inclusio-mcp` |
| Claude Code / Cursor skill | Missing | Not published |
| Real-time collaboration / web editor | Missing | Local-first only |
| LSP for YAML/Jinja2 schemas | Missing | No `euxis-lsp` |
| Reproducible-build distribution | Partial | Dockerfile + flake.nix exist; not discoverable |
| Python package coverage | Strong | 100% enforced |
| AI-use disclosure metadata | Missing | No STM-aligned schema field |
| COAR Notify outbound | Missing | No webhook on build |
| Executable code blocks | Missing | No notebook integration |
| Static docs site for `pub-guide` | Missing | PDF-only deliverable |
| MathML in PDF/UA-2 | Missing | Tied to tagging |

**Score: 14 Strong / 4 Partial / 27 Missing.** Roughly **33% of a 2026
publishing platform**.

---

## 3. Competitor positioning

| Competitor | Strength vs Euxis | Weakness Euxis can exploit | Strategic threat |
|---|---|---|---|
| **Quarto** | PDF+HTML+JATS+DOCX from one source; executable; Posit-backed; journal-bundle accepted | Aesthetics workmanlike not Apple-grade; templating YAML-heavy; LaTeX class layer thin | **HIGHEST** - this is the actual benchmark |
| **MyST / Jupyter Book 2** | AST-based, multi-target, mature community, executable | LaTeX output generic; no CV/patent verticals | **HIGH** - strong in academic publishing |
| **Overleaf** | Real-time collaboration, journal-template library, browser UX | Not local-first, not git-native, AI bolt-on | **MEDIUM** - browser-first audience |
| **Curvenote / Authorea** | Web-native multi-format, publisher partnerships | Less polish than Quarto; smaller community | **MEDIUM** |
| **Typst** | 10-100x faster compile, cleaner DSL, 800+ packages | Publisher acceptance ~zero in 2026 | **LATENT-HIGH** - if tier-1 publisher blesses 2027-2028, steepens fast |
| **Rendercv** | Direct LaTeX competitor in CV-only segment; AI-agent integrations | CV-only; no JATS/HTML/patent | **MEDIUM** - eats `pub-cv` use case |
| **Reactive Resume / JSON Resume** | Open ecosystem, GUI builder, hundreds of themes | Generic templates; no patent/paper | **MEDIUM** - sets schema expectations |
| **ClaimMaster 2026** | LLM-assisted patent drafting; claim charts; image generation | Closed-source, expensive | **PATENT-VERTICAL FATAL** |
| **PatSnap / LexisNexis PatentSight+** | Prior-art + FTO + analytics + custom AI classifiers | Enterprise-only | **PATENT-VERTICAL FATAL** |
| **Pandoc + Lua filters** | De facto AST round-tripper; DOCX track-changes both ways | No classes/templates | **COMPLEMENT** - depend on it more |
| **MS 365 Copilot / Google Docs Gemini** | Real-time co-authoring + AI rewrite + track-changes audit | Not git-native, not reproducible | Sets review-loop expectations |
| **Starlight / Docusaurus 3 / MDX** | Searchable HTML docs sites with PDF export | Not LaTeX-grade typography | **`pub-guide` FATAL** - PDF manuals are 2008 |

**Strategic implication:** Euxis fights on six fronts (papers, CVs,
patents, FAQs, guides, blogs). On scholarly papers you are behind
Quarto/MyST. On CVs you are roughly at parity with Rendercv but behind
JobSprout/Rezi on tailoring. On patents you are not in the fight. On
guides your format choice (PDF) is wrong for the segment.

**Hard recommendation:** triage the surface. Either (a) double down on
**Papers + CVs**, deprecate/scope-down `pub-patent` to "typesetting only",
and re-tool `pub-guide` to emit Starlight HTML; or (b) commit fully to
patent workflow with a 12-month investment. Sitting in the middle on
patents is the worst outcome.

---

## 4. Prioritised roadmap

### P0 - Ship in 6 months (regulatory + table-stakes)

| # | Feature | Files |
|---|---|---|
| P0.1 | **Tagged PDF (WTPDF 1.0 to PDF/UA-2)** | `pub-base.cls`, `pub-metadata.sty`, new `tests/test_pdf_ua.py`, new CI job for veraPDF |
| P0.2 | **PDF/A-4 output option** | `pub-metadata.sty`, `data/meta.schema.yaml` |
| P0.3 | **EAA/WCAG 2.2 AA audit report** | new `cli/audit.py`, `tests/test_eaa.py` |
| P0.4 | **AI-disclosure metadata block** | `data/meta.schema.yaml`, `pub-metadata.sty` |
| P0.5 | **PAdES B-LT signing in CI** | new `tools/sign_pades.py`, CI workflow |
| P0.6 | **JSON Resume ingestion** | new `cli/import.py` |
| P0.7 | **ATS conformance validator** | new `tools/ats_validator.py` |
| P0.8 | **DOCX track-changes round-trip** | new `tools/docx_review.py` |
| P0.9 | **JATS XML emitter for `pub-paper`** | new `cli/render_jats.py` |
| P0.10 | **HTML output (single-source)** | new `templates/paper.html.j2`, `cli/render_html.py` |

### P1 - Ship in 12 months (Quarto parity)

| # | Feature | Files |
|---|---|---|
| P1.1 | **ROR + ORCID + CRediT** in YAML to XMP + JATS | `meta.schema.yaml`, `pub-metadata.sty`, JATS emitter |
| P1.2 | **Schema.org `ScholarlyArticle` JSON-LD** | HTML template |
| P1.3 | **`inclusio-mcp` MCP server** | new `cli/mcp.py` |
| P1.4 | **Claude Code skill + Cursor rules pack** | new `skills/euxis-publishing/` |
| P1.5 | **LLM-judge `validate` stage** | new `tools/llm_judge.py` |
| P1.6 | **Citation hallucination detector** | new `test_citations.py` |
| P1.7 | **RAG over author's prior corpus** | new `tools/rag_index.py` |
| P1.8 | **JD-to-CV closed-loop tailor** | extend `cli/tailor.py` |
| P1.9 | **Multi-locale CV source-of-truth** | `pub-cv.cls`, `cli/render.py` |
| P1.10 | **Europass XML export** | extend `render.py` |
| P1.11 | **SLSA L2 + Sigstore + in-toto** | `.github/workflows/release.yml` |
| P1.12 | **C2PA Content Credentials manifest** | new `tools/c2pa_sign.py` |
| P1.13 | **DOCX comments round-trip** | extend `tools/docx_review.py` |
| P1.14 | **JATS4R-compliant tagging** | JATS emitter |
| P1.15 | **`flake.nix` + `devbox.json` discoverability** | `README.md`, `flake.nix` |

### P2 - Ship in 18-24 months (differentiators)

| # | Feature | Files |
|---|---|---|
| P2.1 | **Typst backend behind Jinja2 templates** | new `core/typ/`, `templates/*.typ.j2` |
| P2.2 | **COAR Notify outbound webhook** | new `tools/coar_notify.py` |
| P2.3 | **`pub-guide` Starlight emitter** | new `templates/guide-starlight/` |
| P2.4 | **Patent workflow expansion** (if vertical kept) | separate sub-repo `euxis-patent-workflow/` |
| P2.5 | **Executable code blocks** | new `core/sty/pub-executable.sty` + sidecar |
| P2.6 | **MathML in PDF/UA-2 namespace** | tagging pipeline |
| P2.7 | **Office-action / examiner-response scaffold** | depends on P2.4 |
| P2.8 | **`euxis tailor --learn`** | `cli/tailor.py` |
| P2.9 | **`euxis serve --collab`** | new `web/` |
| P2.10 | **Per-section semantic diff** | new `cli/diff.py` |

---

## 5. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| EAA enforcement action against an Euxis-published org | Medium | High (€100k or 4% revenue) | P0.1 + P0.3 in next minor |
| Typst captures a tier-1 publisher 2027-2028 | Medium | High (15-25%/yr migration) | P2.1 in 18 months |
| Quarto formalises a `pub-cv`-equivalent template | High | Medium | Ship JSON Resume importer (P0.6) + ATS validator (P0.7) first |
| ClaimMaster/Rowan undercut `pub-patent` to free-for-individuals | Low | High (deletes vertical) | Decide: deprecate `pub-patent` or commit to P2.4 |
| LLM-judge rubrics become vendor lock-in (OpenAI-only) | Medium | Medium | Model-agnostic design (Anthropic, Google, local via llama.cpp) |
| Tagged-PDF migration breaks existing camera-ready output | Medium | Medium | Add `[final-untagged]` documentclass option as fallback for 1 release cycle |
| MCP protocol churns | High | Low | Keep MCP server thin adapter over CLI |
| AI-disclosure schema diverges from STM final | Medium | Low | Use STM Sept-2025 draft; easy migration |

---

## 6. The Typst question

The Jinja2 templating layer is already format-agnostic in principle.
A Typst backend behind the same templates is plausible within 24 months.

**Recommendation:** stay LaTeX-only for P0+P1. In Q3 2027, ship
`pub-paper-typst` as experimental class behind a feature flag. By 2028
either Typst momentum has plateaued (quietly retire) or a tier-1
publisher has accepted Typst (Euxis is the only LaTeX-first tool with
a credible Typst path).

The alternative - LaTeX-only forever - accepts a slow erosion of the
new-author market starting ~2028.

---

## 7. The three things to ship next

1. **`tagpdf` activation in `pub-base.cls` behind feature flag** with
   veraPDF in CI. Kills EAA exposure even partially.
2. **`ai_disclosure:` block in `data/meta.schema.yaml`** mapped to STM
   Sept-2025 categories. Cheap; future-proofs schema.
3. **`inclusio-mcp` server skeleton** exposing `list`, `build`, `validate`
   as MCP tools. Cheapest possible distribution channel today.

Three days of work. Addresses Forcing Functions #1, #6, and #4
simultaneously.

---

## 8. What this analysis is not

It is not a guarantee that doing all the above makes Euxis the de facto
choice. Distribution matters more than features. The largest single
multiplier missing from this roadmap is **partnerships** - a tier-2
journal accepting Euxis-bundled JATS, a research institute standardising
on `pub-paper`, a Y Combinator startup using `pub-cv` for engineering
hiring. Those are sales/community work, not engineering work, but they
are what convert "feature parity with Quarto" into "de facto".

The engineering work above is the necessary condition. It is not
sufficient.

---

## 9. Sources

Selected primary references underlying the analysis:

**Standards / accessibility**
- ISO 14289-2:2024 (PDF/UA-2): https://www.iso.org/standard/82278.html
- PDF/UA-2 (PDF Association): https://pdfa.org/iso-14289-2-pdf-ua-2-the-gold-standard-for-accessibility-in-pdf-2-0-has-arrived/
- ISO 19005-4 (PDF/A-4): https://pdfa.org/resource/iso-19005-4-pdf-a-4/
- WTPDF 1.0: https://pdfa.org/wp-content/uploads/2024/02/Well-Tagged-PDF-WTPDF-1.0.pdf
- European Accessibility Act: https://commission.europa.eu/strategy-and-policy/policies/justice-and-fundamental-rights/disability/european-accessibility-act-eaa_en
- EAA effective June 2025: https://accessible-eu-centre.ec.europa.eu/content-corner/news/eaa-comes-effect-june-2025-are-you-ready-2025-01-31_en
- EAA + PDFs: https://pdfix.net/european-accessibility-act-2025-are-your-pdfs-ready/
- PAdES (Wikipedia): https://en.wikipedia.org/wiki/PAdES
- eIDAS DSS: https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467109107/Digital+Signature+Service+-+DSS

**Scholarly / publishing standards**
- JATS XML: https://sciflow.net/en/jats-xml-explained
- JATS4R: https://jats4r.niso.org/
- ROR adoption (Crossref): https://www.crossref.org/blog/publishers-are-you-ready-to-ror/
- COAR Notify: https://coar-repositories.org/tools-and-resources/notify/
- NISO Plus 2026: https://www.highwirepress.com/blog/niso-plus-2026-ai-scholarly-infrastructure/
- STM AI-use classification: https://www.niso.org/niso-io/2025/09/stm-releases-recommendations-classification-ai-use-manuscript-preparation
- STM AI disclosure consultation: https://stm-assoc.org/global-reporting-standard-for-ai-disclosure-in-research-first-consultation-is-open/

**Competitors**
- Quarto manuscripts: https://quarto.org/docs/manuscripts/
- Jupyter Book 2 (Jan 2026): https://2i2c.org/blog/jupyter-book-release-jan-2026/
- Typst Universe: https://typst.app/universe/
- Typst vs LaTeX (BigGo): https://biggo.com/news/202506230712_Typst_vs_LaTeX_Academic_Publishing
- Overleaf pricing: https://www.overleaf.com/user/subscription/plans
- Rendercv: https://rendercv.com/
- Reactive Resume: https://github.com/amruthpillai/reactive-resume
- JSON Resume: https://jsonresume.org/
- Pandoc track-changes: https://github.com/pandoc/lua-filters/tree/master/track-changes
- ClaimMaster 2026: https://www.patentclaimmaster.com/blog/llm-patent-drafting-improvements-claimmaster-2026/
- USPTO Patent Center: https://www.uspto.gov/about-us/news-updates/patent-center-fully-replaces-uspto-legacy-systems-filing-and-managing-patent

**ATS (CV vertical)**
- Workday ATS guide 2026: https://www.atshiring.com/en/learn/workday-ats-guide-2025
- Greenhouse ATS guide: https://resumeoptimizerpro.com/blog/greenhouse-ats-resume-guide
- Lever ATS guide: https://resumeoptimizerpro.com/blog/lever-ats-resume-guide

**Provenance / supply-chain**
- C2PA Content Credentials 2026: https://www.eyesift.com/faq/c2pa-content-credentials-2026-cryptographic-provenance-adoption/
- Sigstore 2026: https://oneuptime.com/blog/post/2026-01-25-sigstore-supply-chain-security/view

**AI authoring**
- ScholarCopilot (arXiv): https://arxiv.org/pdf/2504.00824
- FACTUM citation hallucination (arXiv): https://arxiv.org/pdf/2601.05866
- Reference Hallucination Score (PMC): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11325115/
- OverleafMCP: https://github.com/mjyoo2/overleafmcp
- LaTeX writing Claude skill: https://claudskills.com/skills/latex-writing/
