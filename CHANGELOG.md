# Changelog

All notable changes to **Euxis Publisher** are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added

- **Sprint 7 (S7.4) — JD-to-CV fit judge (2026-05-28)**:
  - `euxis_publisher/judge/jd_fit.py` — third judge in the pipeline.
    Compares a job-description brief against a candidate CV; flags
    missing-required keywords (block), role-level mismatch (warn at
    gap ≥2, block at gap ≥3), low-overlap (warn at Jaccard <0.10).
  - Keyword extractor preserves tech sigils (`c++`, `c#`, `node.js`),
    strips trailing punctuation, defaults to `min_len=2` so short
    tech tokens (ai, ml, ui, ux) survive.
  - Required-keyword harvest stops at paragraph break, preventing
    "Required:" sections from bleeding into adjacent "Bonus:" lists.
  - Seniority ladder (intern → junior → engineer → senior → staff →
    principal → director → vp → cto) uses first-match semantics so
    "Junior Engineer" ranks as junior, not engineer.
  - Stepped Jaccard→score curve (>=0.45 → 95, >=0.30 → 85, >=0.15
    → 70, >=0.05 → 55, else 35) calibrated against real JD-CV
    pairs.
  - LLM rerank (`score_jd_fit_with_llm`) asks for top strength +
    top gap; deduction clamped to [0, 15]; invalid severity falls
    back to `warn`; LLMError graceful fallback with info
    breadcrumb.
  - CLI: `--judge jd_fit --brief <path>` reads the brief, renders
    the CV via `render --format text`, runs the score (with
    optional `--llm-url` rerank).
  - 34 tests in `tests/test_judge_jd_fit.py` covering extract_keywords
    (lowercasing, dedup, stopword pruning, tech sigils, 2-char
    tokens, min_len override, pure-numeric drop), jaccard edge
    cases, required-keyword harvesting (paragraph-break stop,
    must-have phrasing, dedupe across triggers), seniority ladder
    (first-match, word-boundary safety), heuristic score (clean
    match, missing-required block, role-mismatch warn/block by gap
    size, low-overlap warn, metrics shape, score clamp to 0), LLM
    rerank (strength+gap merge, deduction clamp, invalid-severity
    fallback, empty-payload, LLMError fallback), prompt builder
    (truncation, schema/system text presence).
  - Docs (`docs/judges.md`) updated with JD-fit section + Python
    API examples; Sprint 7.4 marked done in roadmap.

  Closes Sprint 7 (S7.4) — 4 of 5 Sprint 7 items shipped. Only
  S7.5 (MCP-broker BYO-key cloud opt-in) remains.

- **Sprint 7 (S7.2) — citation-grounding judge (2026-05-28)**:
  - `euxis_publisher/judge/citations.py` — heuristic + LLM-backed
    `\cite` / `\bibitem` consistency check for scientific papers.
    Catches LLM-generated papers with hallucinated references and
    ScholarCopilot-style mis-attribution.
  - Parses `\cite`, `\citep`, `\citet`, `\citeauthor`, `\citeyear`
    (with optional `[label]` and multi-key `\cite{a,b,c}` forms),
    and `\bibitem{key}` / `\bibitem[label]{key}` with light inline
    markup cleanup so the LLM sees authors/titles not LaTeX.
  - Heuristic findings: `dangling_citation` (block, -15/key, cap
    -60), `unused_bibitem` (warn, -5/key, cap -20),
    `duplicate_bibitem` (warn, -10/key), `missing_bibliography`
    (block, -50), `no_citations` (info / warn depending on context).
  - LLM grounding (`score_citations_with_llm`): for up to 10
    matched citations, asks the LLM whether the in-text claim
    matches the bibitem body. Flags `supported: false` +
    `confidence >= 0.6` as warn (-5, deduped per key). Graceful
    fallback on LLMError.
  - CLI `--judge citations` on the existing `judge` subcommand;
    reads the doc's `.tex` source from `meta.documents.<id>.src`.
  - `tests/test_judge_citations.py` — 29 tests covering parsers
    (every cite/bibitem variant + line numbers + context),
    heuristic findings (clean, dangling, unused, duplicate, missing
    bibliography, no-citations branches, dangling-cap), LLM
    grounding (supported / unsupported / low-confidence / dedup /
    no-matched-citations / cap honour / unavailable fallback),
    and `build_grounding_prompt` shape.
  - Docs (`docs/judges.md`) expanded with citation-judge heuristic
    table, LLM grounding section, and Python API examples.

  Closes Sprint 7 (S7.2). Layered on top of S7.1's `LocalLLM`
  adapter; no new runtime dependencies.

- **Sprint 7 (S7.1) — local llama.cpp HTTP adapter for LLM judges (2026-05-28)**:
  - `euxis_publisher/judge/local_llm.py` — stdlib-only HTTP client
    over llama.cpp's `/completion` endpoint. No `httpx` / `requests`
    dependency. `LocalLLM` dataclass with `complete()`,
    `complete_json()` (handles ```json fenced output), and
    `is_available()` probe.
  - Error taxonomy: `LLMError` (base), `LLMUnavailable`
    (ECONNREFUSED / DNS), `LLMTimeout`, `LLMParseError`.
  - `score_cv_with_llm(plain_text, llm)` in `ats.py` — runs heuristic
    first, asks the LLM for ONE additional finding, clamps the
    adjustment to [-15, +5]. Falls back to heuristic-only with an
    info-level breadcrumb when the LLM is unreachable.
  - CLI flags `--llm-url <url>` + `--llm-timeout <seconds>` on
    `judge`. `--llm-url http://localhost:8080` flips on the rerank.
  - `build_ats_rerank_prompt(plain_text_cv)` helper composes the
    rerank prompt + schema; CV text is truncated to 6 KB for short-
    context models.
  - 23 tests in `tests/test_judge_local_llm.py` covering argv
    composition, default values, stop sequences, URL trailing
    slash, raw payload propagation, every error path
    (ECONNREFUSED, socket timeout, native TimeoutError, non-JSON
    body, malformed JSON completion), `complete_json` fence
    stripping (3 forms), `is_available` true/false, prompt builder
    truncation, rerank merge + clamp (lower + upper), graceful
    fallback on `LLMUnavailable` + `LLMParseError`, empty-finding
    handling.
  - Docs (`docs/judges.md`) updated with LLM rerank section,
    llama-server startup recipe, Python API, JSON schema for the
    rerank contract.

  Closes Sprint 7 (S7.1). Unlocks S7.2 (citation grounding) and
  S7.4 (JD-CV reranker) on the same `LocalLLM` surface.

- **Sprint 6 (S6.6) — EPUB3 emitter (2026-05-28)**:
  - `euxis_publisher/emit/pandoc.py::emit_epub` — Pandoc `--to epub3
    --standalone --mathjax` with BCP-47 language metadata. Closes
    the multi-format triad (HTML + JATS + EPUB), fully closing
    Forcing Function #3.
  - `SUPPORTED_FORMATS` extended to `("html", "jats", "epub")`;
    `emit_all` routes the new format through the same dispatch
    surface.
  - CLI default updated: `python -m euxis_publisher.cli.build emit`
    now emits all three formats by default.
  - 4 new tests in `tests/test_emit_pandoc.py` (epub3 argv, lang
    override, blank-title omission, real-pandoc end-to-end with
    PK-magic-bytes + size check). `tests/test_cmd_emit.py` stub
    extended to handle the epub extension.
  - Docs (`docs/multi-format.md`): full EPUB section with what's
    bundled (TOC, lang, MathJax) and what's deferred to Sprint 8
    (DAISY ACE, Schema.org a11y metadata, cover-image extraction).
  - Local verification: real pandoc produces a 4951-byte valid
    EPUB3 archive on a 5-line smoke fixture.

- **Sprint 7 (S7.3) — ATS-scoring judge (2026-05-28)**:
  - `euxis_publisher/judge/ats.py` — Workday / Greenhouse / Lever
    heuristic scoring for CV variants. Local, deterministic, sub-ms.
    Closes Forcing Function #5 on the deterministic surface.
  - 9 checks: canonical headings, contact info, length bands,
    bullet density, date consistency, killer phrases (each tunable
    via module-level constants).
  - 0-100 score + A/B/C/D/F grade derivation; `JudgeReport.to_dict()`
    for JSON serialisation.
  - CLI: `python -m euxis_publisher.cli.build judge --doc cv
    --judge ats [--json path] [--strict]`. Renders the CV via
    `render --format text` then scores the plain-text output.
  - `make judge DOC=cv` shortcut.
  - `tests/test_judge_ats.py` — 23 tests covering every check, grade
    boundaries, JSON round-trip, and the score-clamp-to-0 invariant.
  - `docs/judges.md` — heuristic table, CLI examples, Python API,
    Sprint 7.5+ roadmap (llama.cpp, citation grounding).

- **Sprint 7 — emit CLI wiring (2026-05-28)**:
  - `python -m euxis_publisher.cli.build emit [--doc X] [--formats html,jats] [--strict]`
    is now first-class. Defaults to `html,jats`; `--strict` exits 1 on
    any pandoc failure (CI gate).
  - Make targets: `make emit`, `make emit-html`, `make emit-jats`.
  - Registry filter shared with `audit` — only `documents:` entries
    get emitted, `note: This is an input file used by another`
    entries skipped.
  - Title pulled from `meta.documents.<id>.title` by default.
  - `tests/test_cmd_emit.py` — 11 tests covering dispatch (all docs,
    single-doc, format-subset), error paths (invalid format → exit 2,
    pandoc missing → exit 1, pandoc failure → counted not fatal),
    strict-mode failure (→ exit 1), help registration, title
    propagation.
  - Closes Sprint 6's CLI wiring deliverable (S6.3.CLI).

- **Sprint 6 (S6.2 + S6.3) — HTML5 + JATS XML emitters (2026-05-27)**:
  - `euxis_publisher/emit/pandoc.py` — Pandoc-wrapping emitters with
    `emit_html`, `emit_jats`, and `emit_all` API surface. Optional
    runtime dep (pandoc); `PandocMissing` raised with install hint
    when absent.
  - **HTML5**: `--to html5 --standalone --section-divs --mathjax`
    with idempotent post-processing that injects a skip-to-main
    link (WCAG 2.4.1), an `<html lang>` attribute (WCAG 3.1.1),
    and a generator-provenance comment. Default `lang=en-GB`,
    overridable per call.
  - **JATS XML**: `--to jats_archiving` (JATS 1.3 archiving DTD,
    accepted by Crossref / PMC / preprint servers).
  - `tests/test_emit_pandoc.py` — 15 tests covering pandoc-missing
    paths, argv composition, post-process idempotency, error
    propagation on pandoc failure, multi-format orchestration, plus
    2 real-pandoc integration tests that skip when pandoc isn't
    installed.
  - `docs/multi-format.md` — install + API + WCAG specifics +
    Sprint 7 CLI-wiring roadmap.

  Closes Forcing Function #3 (single-source multi-format) on the
  Python API surface; Sprint 7 wires the CLI (`euxis-publisher emit
  --doc … --formats html,jats`) and adds JATS4R validation + EPUB-A
  emitter.

- **Sprint 6 (S6.4 + S6.5) — MCP server + Claude skill + Cursor rule (2026-05-27)**:
  - `euxis_publisher/mcp/server.py` — FastMCP-based MCP server exposing
    the engine's read + audit surface:
      - Tools: `list_docs`, `audit_pdf`, `render`, `doc_count`
      - Resources: `euxis://meta`, `euxis://audit/latest`, `euxis://version`
  - `euxis-mcp` console script with stdio (Claude Code default) and
    Streamable HTTP (`--http`) transports.
  - `mcp` optional extra (`pip install 'euxis-publisher[mcp]'`,
    `mcp[cli]>=1.27.0`).
  - `.claude/skills/euxis-publisher/SKILL.md` — Claude skill with
    canonical preamble, untagged-content traps, command catalogue,
    EAA compliance context.
  - `.cursor/rules/euxis-publisher.mdc` — Cursor rule auto-loading on
    `.tex / .cls / .sty / meta.yaml / *-data.yaml`.
  - `tests/test_mcp_server.py` — 18 tests covering server creation,
    tool/resource registration, content-root resolution, and the
    missing-dep error path. Skips cleanly when `mcp[cli]` is absent.
  - `docs/mcp-server.md` — install / run / tool reference / Claude
    Code + Cursor integration guide.

  Closes Forcing Function #4 (AI authoring layer) on the engine
  surface; Sprint 7 adds write-side tools (tailor, lint, LLM judge).

### Added (earlier in Sprint 5)

- **Sprint 5 — public fixtures migrated to tagged-PDF; veraPDF gate strict (2026-05-27)**:
  - All 9 public fixtures (`whisper-mps-realtime-asr`, `arxiv-paper`,
    `preprint-paper`, `prime-paper`, `patent`, `cv`, `bio`, `faqs`,
    `user-guide`) now ship with the canonical Sprint-2 preamble:
    `\DocumentMetadata{pdfversion=2.0, pdfstandard=ua-2,
    pdfstandard=a-4f, lang=en-GB, testphase={phase-III, table, math,
    sec-latex}}` immediately before `\documentclass[final,tagged]{pub-…}`.
  - `patent-paper.tex` left alone — flagged as `note: input file` in
    `meta.yaml`, parent doc carries the metadata.
  - Local veraPDF check on the migrated `whisper-paper` PDF returns
    PASS on `ua2`, `wt1a`, and `4f` flavours (3/3).
  - `.github/workflows/verapdf.yml` EAA-audit step flipped from
    `|| true` WARN-only to **BLOCKing**. Any UA-2 / WTPDF / PDF/A-4f
    regression on a registered artefact now fails the workflow.
  - Build step retains a graceful warning so one malformed fixture
    doesn't deny audit of the others; the authoritative gate is
    `audit --strict` against the produced PDFs.

### Added (earlier in Sprint 5 prep)

- **Sprint 5 prep — coverage + AI-disclosure + audit edges (2026-05-27)**:
  - `ai_disclosure` field accepted at both `meta.ai_disclosure` (project
    default) and `meta.documents.<id>.ai_disclosure` (per-doc override,
    wins on conflict). Propagated to PDF XMP `<dc:description>` so Adobe
    surfaces it in the Description panel — per STM Sept-2025 Generative-AI
    Disclosure classification; portals expected to begin enforcement
    2026-Q4 onward.
  - `tests/test_render_coverage.py` — 26 targeted tests covering
    `_render_cv_markdown` scope_line / subheadline / nested-roles /
    prior_experience / innovation / competencies-as-dict / skills-fallback;
    `_markdown_lines` dict / list / None / scalar paths;
    `_render_cv_text` + `_render_generic_text` branches. Pushes
    `euxis_publisher/cli/render.py` coverage 76% → 96%.
  - `tests/test_audit_edges.py` — 8 edge-case tests for the audit CLI:
    malformed veraPDF output, empty stdout, `_registry_stems` boundary
    YAML shapes, --flavours subset, --timeout propagation, custom
    --json / --markdown paths.
  - `tests/test_ai_disclosure.py` — 7 tests covering both the
    `_build_xmp_xml` `ai_disclosure=` kwarg and the meta / doc-config
    resolution order through `_post_process_pdf`.
  - Coverage threshold in `Makefile` raised back to 95% (was
    temporarily 90 in Sprint 4 to land the operational-hygiene PR).

- **Sprint 4 — operational hygiene (2026-05-27)**:
  - `CITATION.cff` (CFF 1.2.0) with ORCID — engine is now scholarly-citable.
  - `SECURITY.md` — engine-scoped vulnerability disclosure path.
  - `.github/dependabot.yml` — weekly grouped updates for pip / GitHub
    Actions / docker.
  - `.github/workflows/release.yml` — tag-driven release with SLSA L3
    build provenance attestation via `actions/attest-build-provenance`.
  - `.github/workflows/pre-commit-autoupdate.yml` — weekly Monday
    autoupdate, PRs signed via the create-pull-request action.
  - `euxis_publisher/tools/overlay.py` — deep-merge helper for the
    "shared template, overlay data" CV-variant pattern.
  - `tests/test_overlay.py` — 18 tests covering the four documented
    merge rules and the `resolve()` helper.
  - `tests/test_citation.py` — CFF shape + ORCID URI structural check.
  - `cli/render.py --format text` — ATS-safe plain-text shadow for
    Workday / Greenhouse / Taleo pipelines.
  - Python lint job (`ruff`) in `engine-validation.yml`.
  - Signed-commit gate on pull requests.
  - Python matrix: `[3.11, 3.12, 3.13]` (was: 3.12 only).
  - Pinned `tagpdf >= v1.0` (2026-04-24) in `core/cls/pub-base.cls`.
  - `docs/audit-2026-05.md` — May-2026 audit & H2 action plan.
  - `cliff.toml` + this `CHANGELOG.md` generated by git-cliff.

### Changed

- `pyproject.toml`: `requires-python` bumped `>=3.9` → `>=3.11`
  (3.9 EOL'd Oct-2025; 3.10 EOLs Oct-2026). Added `[tool.ruff]` config,
  `[project.urls]`, `[tool.coverage.run]`, classifiers for 3.11-3.13.
- `audit.py --strict`: when `verapdf` is missing on PATH, the gate
  now ERRORs with a clearer message instead of letting SKIP statuses
  silently pass.
- `flake.nix`: bumped `nixos-24.05` → `nixos-25.05` (texlive ships
  `tagpdf >= 1.0`).
- `.editorconfig`: added TeX/YAML/Python/Makefile rules.
- All GitHub Actions migrated to SHA-pinned refs (Dependabot rewrites
  them on the weekly cycle).
- CI Python provisioning switched from `pip install` to
  `astral-sh/setup-uv`; cache key on `pyproject.toml`.

### Fixed

- README badge: removed misleading static `Coverage-100%` shield;
  replaced with live veraPDF audit status, accessibility-standards
  badge, and accurate Python version.

## [Sprint 3] — 2026-05-24

### Added

- `euxis_publisher.cli.audit` — veraPDF runner for PDF/UA-2, WTPDF 1.0
  Accessibility, and PDF/A-4f flavours, with `--strict` CI gate, JSON
  + Markdown reports, and registry-filter mode. Forcing function #1
  (EAA enforcement) closed for private CI.
- `.github/workflows/verapdf.yml` — accessibility gate workflow with
  cached veraPDF installer and Sprint-3 EAA audit step.
- `tests/test_eaa.py` — 17 unit tests covering audit-CLI surface.

## [Sprint 2] — 2026-05-23

### Changed (breaking)

- Per-class tagged-PDF retrofit: all 11 `pub-*.cls` classes now emit
  PDF/A-4f tagged output under the `[tagged]` class option. Authors
  must call `\\DocumentMetadata{...}` before `\\documentclass{...}`;
  see `docs/tagged-pdf.md`.

## [Sprint 1] — 2026-05-22

### Added

- LuaLaTeX hard-require (decision D3 in `docs/strategy-2026.md`).
- Tagged-PDF foundation: `\\IfDocumentMetadataTF` snapshot before
  `pdfx` loads, so the `[tagged]` contract check is reliable.
- Initial Sprint 1 PDF/UA-1 / WTPDF / PDF/A-4 smoke tests.

## [Sprint 0] — 2026-05-09

### Added

- Public engine extracted from `publications` monorepo.
- `euxis_publisher` package (`cli.build`, `cli.render`, `cli.tailor`,
  `cli.sitemap`, `tools.fix_semantic`, `tools.stamp_pdfs`).
- Eleven `pub-*.cls` document classes; five `pub-*.sty` style packages.
- Jinja2 templating with LaTeX-safe delimiters (`<<>>`, `<%%>`, `<##>`).
- `EUXIS_CONTENT_DIR` env var + `--content-dir` flag for split-repo
  workflows.
- Initial test suite (engine smoke + macro contract + assets).

<!-- generated by git-cliff -->
