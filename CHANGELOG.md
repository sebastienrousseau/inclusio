# Changelog

All notable changes to **Inclusio** (previously *Euxis Publisher*)
are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Conventional Commits](https://www.conventionalcommits.org/).

## [0.0.6] — 2026-07-02

The **MCP-discoverability** cut. Registers `inclusio-mcp` with the
official Model Context Protocol Registry, adds MCP-spec conformance
CI, and ships a Glama directory manifest. No functional changes to
the publishing engine — same accessibility surface as v0.0.5.

### Added

- **Official MCP Registry integration.** The embedded MCP server
  (installed via `pip install 'inclusio[mcp]'`) is now registered
  with the official Model Context Protocol Registry
  (`registry.modelcontextprotocol.io`) as
  `io.github.sebastienrousseau/inclusio-mcp`. A new `server.json`
  at the repo root provides the registry metadata (PyPI package
  identifier `inclusio`, stdio transport), and the README carries
  an `mcp-name: io.github.sebastienrousseau/inclusio-mcp` marker
  used by the registry to verify PyPI package ownership.
  Discoverable in Claude Desktop's built-in "Add server" catalog
  once the registry entry is live.
- **Auto-publish workflow**
  (`.github/workflows/publish-mcp.yml`) — authenticates to the MCP
  Registry via GitHub OIDC (no secrets required) on every
  `v*.*.*` tag push, syncs the tag version into `server.json`,
  and runs `mcp-publisher publish`. Registry metadata now stays
  in lockstep with each PyPI release automatically.
- **Protocol conformance CI**
  (`.github/workflows/mcp-inspect.yml`) — runs
  `@modelcontextprotocol/inspector --cli` against `tools/list`
  on every push and PR that touches the MCP server code
  (`inclusio/mcp/**`). Path-filtered to keep the CI budget bounded.
- **Glama directory manifest** (`glama.json`) — Glama listing under
  the `productivity` category with accessibility, publishing, and
  PDF conformance tags.
- **Suite discoverability.** The README now cross-links sibling
  MCP servers by the same author — `noyalib-mcp`, `rlg-mcp`, and
  the four ISO 20022 banking MCP servers (`pain001-mcp`,
  `bankstatementparser-mcp`, `camt053-mcp`, `acmt001-mcp`) — so
  agents discovering one server surface the others.

### Changed

- **Package version** bumped to `0.0.6` for the MCP registry cut.
- GitHub repository topics extended with `mcp-server` (repo already
  had `mcp` and `model-context-protocol`).

### No functional / API changes

- The accessibility publishing engine is unchanged from `0.0.5`.
  Same `Judge` protocol, same pandoc emitter parameterisation, same
  PDF/UA-2 + WTPDF + PDF/A-4f triple-conformance surface. This
  release is metadata, CI, and discoverability only.

## [0.0.5] — 2026-05-30

Second slice of the deferred Q3.4 refactor. Lands the `Judge`
protocol + pandoc emitter parameterisation. Same pattern as v0.0.4
(extract → preserve back-compat surface → keep tests green).

### Added — `Judge` protocol + `JUDGES` registry

- New `inclusio.judge.Judge` runtime-checkable Protocol documenting
  the shared shape every judge follows: `name`, `score(**inputs)`,
  `score_with_llm(llm, **inputs)`.
- New `inclusio.judge.JUDGES` dict mapping each judge's name to a
  concrete instance — the single source of truth the CLI
  dispatcher resolves through.
- Three private judge classes (`_ATSJudge`, `_CitationsJudge`,
  `_JDFitJudge`) implementing the protocol. Each is a thin
  delegator over the existing module-level `score_*` functions,
  which remain the public API.
- `inclusio.cli.build.cmd_judge` now dispatches via `JUDGES.get(args.judge)`
  instead of the hand-coded `if args.judge == …` ladder.
  Net: ~30 lines saved + a single place to register a new judge.

### Changed — `inclusio.emit.pandoc` parameterisation

- The near-identical `emit_html` / `emit_jats` / `emit_epub`
  functions now delegate to a shared `_emit(spec, ...)` core,
  driven by a `FORMATS` table of `EmitSpec` dataclasses (ext,
  pandoc writer, extra flags, lang toggle, optional postprocess
  hook).
- Public API is unchanged: `emit_html()`, `emit_jats()`,
  `emit_epub()`, `emit_all()` all keep their existing signatures
  and behaviour.
- Adding a new format (Markdown, ODT, Org, …) is now adding one
  row to `FORMATS` + a thin public wrapper.

### Internal

- 890 tests still pass; coverage **98.13 %** (gate 97 %);
  docstrings **100 %** (235/235); ruff clean.

### Deferred to v0.0.6 or v0.0.7

- `cli/build.py` argparse split into per-command modules.
- DAISY ACE EPUB validation.
- Citation-judge retrieval mode (CiteGuard-style RAG).
- `src/+data/ → fixtures/` rename.

## [0.0.4] — 2026-05-29

First slice of the **Q3.4 internal refactor** flagged in v0.0.3.
Small, contained, behaviour-preserving — designed to land cleanly
ahead of the remaining Q3.4 work (cli/build.py split, Judge ABC,
pandoc parameterisation) which ships in subsequent v0.0.4.x
releases.

### Added — `inclusio.pdf` sub-package

- New `inclusio/pdf/` package with `inclusio.pdf.post_process`
  module. Public surface:
  - `build_xmp_xml(...)` — assemble the hand-crafted XMP packet
    (legacy untagged path).
  - `apply_encryption(pdf, pdf_path, content_hash)` — AES-256
    save with accessibility-friendly permission flags.
  - `post_process_pdf(pdf_path, doc_id, doc_config, meta)` — the
    Sprint-5 tagged/untagged dispatch.

### Changed — `inclusio/cli/build.py`

- Removed the three function bodies (≈ 240 lines) from
  `cli/build.py`. The legacy underscore-prefixed names
  (`_build_xmp_xml`, `_post_process_pdf`, `_apply_encryption`)
  are kept as **back-compat aliases** at the top of the module
  so:
  - every existing `@patch("build._post_process_pdf")` decorator
    in the test suite keeps working unchanged;
  - the in-module call site (`build_document` → `_post_process_pdf`)
    resolves through the alias.

### Internal

- 890 tests still pass; coverage **98.18 %** (gate 97 %);
  docstrings **100 %**; ruff clean.

## [0.0.3] — 2026-05-29

First sprint train under the new name. Three of the five planned
Q3 sprints land here; the remaining two (Q3.4 internal refactor,
Q3.5 heavyweight trend response) ship as **v0.0.4** to keep this
release reviewable.

### Added — Q3.1 examples + quickstart

- `examples/` directory with six self-contained scenarios, each
  with a `Makefile` and a README explaining what it teaches:
  1. **`01-hello-world/`** — minimal tagged-PDF build
  2. **`02-cv-from-jsonresume/`** — JSON Resume → CV → ATS + JD-fit scoring
  3. **`03-paper-with-citations/`** — scholarly paper → PDF + HTML + JATS + EPUB + citation judge
  4. **`04-mcp-agent/`** — `inclusio-mcp` + Claude Code skill
  5. **`05-c2pa-sign/`** — embed C2PA Content Credentials
  6. **`06-pades-sign/`** — PAdES B-T eIDAS signature
- `docs/quickstart.md` — 5-minute walkthrough mirroring example 1.
- README "60-second tour" replacing the old install-only intro.

### Added — Q3.3 tutorials

- `docs/tutorials/` with four end-to-end walkthroughs aligned with
  the examples:
  - **`01-tagged-pdf.md`** — what tagged PDFs are + how inclusio
    builds them.
  - **`02-judge-cv.md`** — ATS + JD-fit scoring, with the 2026
    Workday/Paradox context.
  - **`03-mcp-agent.md`** — running `inclusio-mcp` and driving it
    from Claude Code.
  - **`04-camera-ready.md`** — C2PA + PAdES + SLSA layered
    provenance.
- `docs/index.md` reorganised into four sections: Getting started /
  Engine / Project / Historical.

### Changed — Q3.2 directory hygiene

- **New `benches/` directory** — promoted `tests/test_benchmark_hot_paths.py` here.
- **Removed `scripts/{build,render,sitemap,tailor,stamp-pdfs,fix-semantic,__init__}.py`** — 7-line thin shims that duplicated the `inclusio.cli` entry points. `scripts/asset-pipeline.sh` and `scripts/check-semantic.sh` (real shell scripts) stay.
- **Moved historical docs to `docs/audit/`**: `audit-2026-05.md`,
  `strategy-2026.md`, `implementation-plan-2026.md` are time-locked
  records of the project's pre-rename strategy. Surfaced in
  `docs/index.md` under a "Historical" section.
- **Rewrote `CONTRIBUTING.md`** — the old document was pre-inclusio
  and referenced scripts (`generate-cv.sh`, `merge-config.py`) that
  never existed in this codebase. The new doc covers the actual
  contribution flow.
- Updated `Makefile` + `pyproject.toml` to point at the new
  `benches/` location.

**Deferred to a follow-up PR (v0.0.3.1?):** renaming `src/+data/ →
fixtures/`. 184 references to update + the change is a public API
break for content repos that consume inclusio. Needs its own
deprecation cycle.

### Added — Q3.5 trend response (light surface)

- `docs/provenance.md` — added a 2026 eIDAS-2 callout marking PAdES
  B-LTA as the qualified-signature default for regulated EU
  sectors. The inclusio default remains B-T (B-LTA needs CRL/OCSP
  wired up automatically — landing in v0.1).
- `inclusio/emit/pandoc.py` — added a JATS 1.4 (ANSI/NISO
  Z39.96-2024) note to the `emit_jats` docstring. The pandoc
  `jats_archiving` writer still emits JATS 1.3 as of pandoc 3.9;
  the upgrade is backwards-compatible at the document level.

### Deferred to v0.0.4

- **Q3.4 internal refactor** — splitting `inclusio/cli/build.py`
  (1700 lines, 15 subcommands) into per-command modules; extracting
  a `Judge` ABC; parameterising the pandoc emitters; extracting
  `inclusio/pdf/post_process.py`. Each is a non-trivial refactor
  with regression risk; merits its own PR + test pass.
- **Q3.5 (heavyweight items)** — DAISY ACE validation in the EPUB
  emit path; citation-judge retrieval mode (CiteGuard-style RAG).
  Both are new features with new optional deps.

### Internal

- `docs/index.md` reorganised; tutorials added to the Getting
  Started TOC; historical docs gathered under a single section.
- All references to the moved historical docs (in
  `.github/workflows/`, `Makefile`, `docs/**.md`, `README.md`)
  updated to the new paths.

## [0.0.2] — 2026-05-29

### Renamed — euxis-publisher → inclusio

The project has been renamed from `euxis-publisher` to **inclusio**.
The new name comes from Latin *inclusio* (an enclosure / a literary
framing device) and aligns the package with its accessibility-first
mission. Tagline: **"Publishing that includes everyone."**

#### What changed

| Surface | Before | After |
|---|---|---|
| PyPI package | `euxis-publisher` | `inclusio` |
| Python import | `from euxis_publisher.…` | `from inclusio.…` |
| CLI entry point | `euxis-publisher` | `inclusio` |
| MCP CLI | `euxis-mcp` | `inclusio-mcp` |
| Content-dir env var | `EUXIS_CONTENT_DIR` | `INCLUSIO_CONTENT_DIR` |
| Tailor engine env var | `EUXIS_TAILOR_ENGINE` | `INCLUSIO_TAILOR_ENGINE` |
| MCP URI scheme | `euxis://meta` | `inclusio://meta` |
| GitHub repo | `sebastienrousseau/euxis-publisher` | `sebastienrousseau/inclusio` |

#### Compatibility window

- `EUXIS_CONTENT_DIR` is still honoured for one minor cycle
  (until **v0.3**) and emits a `DeprecationWarning`. Content
  repositories should switch to `INCLUSIO_CONTENT_DIR` at their
  earliest convenience.
- All other surfaces have NO compatibility shim — they're a clean
  break. v0.1.0 was tagged but never published to PyPI, so there
  are no installed copies of the old name to migrate.

#### Migration

```bash
# Drop the old package; install the new one.
pip uninstall euxis-publisher
pip install inclusio

# Code changes (sed-replaceable in one pass):
sed -i 's/euxis_publisher/inclusio/g'   your/file.py
sed -i 's/euxis-publisher/inclusio/g'   your/file.md
sed -i 's/euxis-mcp/inclusio-mcp/g'     your/file.toml
sed -i 's|euxis://|inclusio://|g'       your/mcp/config.json
```

#### Historical context

Past CHANGELOG entries, the strategy doc (`docs/strategy-2026.md`),
the audit synthesis (`docs/audit-2026-05.md`), and the
implementation plan (`docs/implementation-plan-2026.md`) are
left unchanged — those are time-locked records of when the
project was called *Euxis Publisher*. The technical content
they describe is unchanged.

## [0.1.0] — 2026-05-28

First public release of the **Euxis Publisher** engine. Production-
ready LaTeX-first publishing pipeline with EAA / WCAG 2.2 AA
accessibility enforcement, multi-format emission, content
authenticity, and an MCP server for agent integration.

### Highlights

- **PDF/UA-2 + WTPDF + PDF/A-4f triple-conformance** via the LaTeX
  kernel's `tagpdf` integration. Every published PDF passes the
  veraPDF gate on all three flavours (27/27 on the current registered
  set: bio, cv, faq, user-guide, 4 papers, 1 patent).
- **CI-enforced quality bar**: 98 % code coverage (gate at 97 %),
  100 % docstring coverage (gate at 100 %), ruff lint + format,
  signed-commits PR gate, EAA strict audit, hot-path benchmark
  surface.
- **Multi-format emission**: HTML5, JATS XML, EPUB3 through Pandoc
  with accessibility metadata.
- **LLM-augmented judges**: ATS (Workday/Greenhouse/Lever heuristic)
  + citation grounding + JD-to-CV fit, with optional local
  (llama.cpp) or cloud (Anthropic / OpenAI BYO-key) rerank that
  falls back to heuristic-only when the LLM is unreachable.
- **Content provenance**: C2PA Content Credentials (c2patool) +
  PAdES eIDAS-aligned signatures (B-B / B-T / B-LT / B-LTA via
  pyhanko) + SLSA L3 build provenance via
  `actions/attest-build-provenance`.
- **MCP server** (FastMCP) exposing the read + audit surface so
  Claude Code / other agents can `list_docs`, `audit_pdf`, `render`,
  and reach the project manifest as a resource.
- **JSON Resume importer** — convert jsonresume.org v1 documents
  to the Euxis CV YAML schema.
- **Brief-driven tailoring** — generate ATS-clean CV variants
  against a job description with deterministic British-English
  cleanup and consistency lint.

### Sprint timeline

This release bundles ten sprints of work:

| Sprint | Theme | Issues |
|---|---|---|
| 0 | Operational hygiene + audit foundation | #1, #2 |
| 1 | Hand-crafted XMP + AES-256 + draft watermark | #3 |
| 2 | Per-class tagged-PDF retrofit (PDF/UA-2 + PDF/A-4f) | #4 |
| 3 | Euxis audit CLI + EAA / accessibility CI gate | #5 |
| 4 | Engine validation + ruff config + SLSA L3 | #5, #9 |
| 5 | Tagged-PDF Sprint-5 metadata refactor + JSON Resume importer | #6 |
| 6 | MCP server + multi-format emitters | #7, #10 |
| 7 | LLM judges (ATS / citations / JD fit) | #8, #12 |
| 8 | C2PA Content Credentials | #11 |
| 8.5 | PAdES eIDAS signatures | #11 |
| Quality | 100 % docstrings + 98 % coverage + benchmarks | — |

### Installation

```bash
pip install euxis-publisher                    # engine + CLI
pip install 'euxis-publisher[mcp]'             # adds FastMCP server
pip install 'euxis-publisher[provenance]'      # adds pyhanko (PAdES)
pip install 'euxis-publisher[dev]'             # adds pytest + ruff + sphinx
```

### Requirements

- Python ≥ 3.11 (tested on 3.11 / 3.12 / 3.13).
- LaTeX toolchain (LuaLaTeX + latexmk) for PDF builds.
- Optional: veraPDF for the audit gate; Pandoc for HTML / JATS /
  EPUB; c2patool for Content Credentials; pyhanko for PAdES.

### Repository layout

The engine ships as a stand-alone Python package; private content
repositories (`euxis-publisher-private` and similar) consume it via
`pip install euxis-publisher` and supply their own `data/meta.yaml`
+ `src/*.tex` overlay through `--content-dir` or
`EUXIS_CONTENT_DIR`. The public engine surface is fully test-covered
without any private content.

## [Unreleased]

### Added

- **Sprint 5 (#6) — JSON Resume importer (2026-05-28)**:
  - `inclusio/cli/import_resume.py` — converts a JSON Resume
    document (jsonresume.org v1 schema) into the Euxis CV YAML
    schema that `templates/cv.tex.j2` consumes.
  - Maps every standard JSON Resume block: `basics` → name/role/
    contact/summary; `work[]` + `volunteer[]` → `experience[]`;
    `education[]` → `education[]`; `skills[]` → `competencies[]`;
    `languages[]` → comma-joined `languages`; `awards[]` +
    `publications[]` → `innovation[]`; `projects[]` passes through
    unchanged; unknown keys preserved under `_jsonresume_extras`.
  - Date ranges normalised ISO `YYYY-MM-DD` → `MM/YYYY – Present`
    so the ATS judge (S7.3) reads them cleanly.
  - Long summaries (>200 chars) promoted to `executive_profile`;
    short ones land in `summary`.
  - CLI: `python -m inclusio.cli.build import-resume
    <resume.json> [-o cv-data.yaml]`. Stdout default; `-` accepted.
  - 38 tests in `tests/test_import_resume.py` covering every
    mapping helper, end-to-end conversion, CLI dispatch, error
    paths.

  Closes #6.

- **Sprint 8.5 (#11) — PAdES eIDAS signature (closes F7 fully) (2026-05-28)**:
  - `inclusio/provenance/pades.py` — pyhanko-based PAdES
    signer supporting all four ETSI EN 319 142 baselines: B-B
    (signer cert), B-T (default, adds RFC 3161 timestamp), B-LT
    (adds revocation data), B-LTA (long-term archival).
  - `pyhanko>=0.22` added as `[provenance]` optional extra so
    `pip install euxis-publisher` stays minimal.
  - `sign_pdf(pdf, cert, key, baseline, timestamp_url, ...)` →
    `PAdESResult` with applied baseline + test-cert detection (CN
    contains "test"/"sample"/"dev"/"demo"/"localhost" → flagged).
  - `verify_pdf(pdf)` wraps pyhanko's verifier; returns intact /
    valid / trusted booleans + a pretty summary.
  - Argument validation up front: unknown baseline → ValueError;
    missing cert/key → ValueError; B-T / B-LT / B-LTA without
    timestamp_url → ValueError with public-TSA recommendations.
  - 13 tests in `tests/test_provenance_pades.py` covering import
    path, baseline validation, cert/key requirements, timestamp-
    URL requirements for B-T/B-LT/B-LTA, B-B no-timestamp path,
    PAdESResult shape, missing-pyhanko detection.
  - Docs (`docs/provenance.md`) expanded with PAdES section: install,
    baseline table, Python API, dev-cert recipe, CI-gate semantics.

  Closes Forcing Function #7 fully. Three layers now in place:
  SLSA L3 build (S4) + C2PA (S8) + PAdES (this commit). 8 of 8
  forcing functions either closed or deferred-by-decision.

- **Sprint 8 — C2PA Content Credentials (F7) (2026-05-28)**:
  - `inclusio/provenance/c2pa.py` — subprocess wrapper over
    the `c2patool` reference implementation. Builds a minimal C2PA
    manifest (schema.org CreativeWork + c2pa.actions + optional
    c2pa.training-mining for AI disclosure) and embeds it into a
    PDF artefact.
  - Same pattern as the Pandoc emitters: shells out to a static
    binary rather than pulling the 12 MB `c2pa-python` native
    wheel — keeps the engine air-gap deployable.
  - `build_manifest_json(...)` composes the manifest; merges
    `ai_disclosure` from F6 (XMP field) into a
    `c2pa.training-mining` assertion so the same disclosure
    surfaces in both XMP and C2PA readers.
  - `embed_manifest(pdf_path, manifest_json, cert_path, key_path,
    ...)` writes the manifest, invokes `c2patool`, and reports
    whether the test-cert fallback was used (CI gate via
    `--strict`).
  - `verify_manifest(pdf_path)` parses an embedded manifest;
    returns an empty dict for unsigned PDFs.
  - CLI: `python -m inclusio.cli.build provenance --doc X
    [--cert C] [--key K] [--strict]`.
  - 22 tests in `tests/test_provenance_c2pa.py` covering the
    binary-missing path, manifest builder (claim generator,
    schema.org assertion shape, c2pa.actions, optional
    date_published, AI-disclosure merge, extra assertions, custom
    claim generator), embed_manifest (argv composition, manifest
    temp-file emission, default + custom output path, test-cert
    flag detection, signer args propagation, failure surfaces,
    manifest-bytes accounting), and verify_manifest (parse,
    missing manifest, invalid JSON).
  - Docs (`docs/provenance.md`): install-c2patool recipe, CLI
    examples, Python API, manifest shape reference, verification
    walkthrough, Sprint 8.5 PAdES roadmap.

  Closes Forcing Function #7 on the C2PA layer. PAdES signature
  (eIDAS-aligned, pyhanko-based) is Sprint 8.5; SLSA L3 attestation
  already shipped in S4.

- **Sprint 7 (S7.5) — cloud LLM adapter (Anthropic + OpenAI BYO-key) (2026-05-28)**:
  - `inclusio/judge/cloud_llm.py` — `CloudLLM` class mirroring
    `LocalLLM`'s interface (`complete()`, `complete_json()`,
    `is_available()`) against:
      - Anthropic Messages API (`/v1/messages`)
      - OpenAI-compatible chat completions (`/v1/chat/completions`)
        — works with OpenAI, xAI, Together, Groq, DeepSeek, Cerebras.
  - Provider detection from base URL (`anthropic.com` → Anthropic;
    everything else → OpenAI-compatible default).
  - BYO-key: constructor `api_key=` arg or env var
    (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`). Missing key →
    `LLMUnavailable`, surfaced as a judge fallback with breadcrumb.
  - HTTP 4xx/5xx (401, 403, 429, 5xx) → `LLMUnavailable` (graceful
    judge fallback); native timeout → `LLMTimeout`.
  - Stdlib-only (urllib.request + json + os). No `anthropic` /
    `openai` / `httpx` package dependency.
  - `from_url(url, **kwargs)` dispatcher: returns the right adapter
    for a URL. Used by the CLI to route `--llm-url` automatically.
  - CLI: `--llm-url https://api.anthropic.com --llm-model
    claude-opus-4-7` on every judge. Same flag works for local
    (`http://localhost:8080`).
  - 29 tests in `tests/test_judge_cloud_llm.py` covering provider
    detection (3 cases), API-key resolution (4 cases: explicit /
    anthropic-env / openai-env / missing), Anthropic request shape
    (endpoint, headers, body, stop sequences, empty content blocks),
    OpenAI-compatible request shape (endpoint, bearer auth, body,
    stop sequences, empty choices), error paths (HTTP error,
    URL error, native timeout, non-JSON body), `complete_json`
    (anthropic parse, fence stripping, parse error), `is_available`
    (true / false on missing key), `from_url` dispatcher (4 cases).
  - Docs (`docs/judges.md`) updated with CloudLLM section, BYO-key
    setup, provider-detection rules, Sprint 7.5 marked done.

  Closes Sprint 7 entirely. 5 of 5 Sprint 7 items shipped. Only F7
  (PAdES + C2PA) remains across all forcing functions.

- **Sprint 7 (S7.4) — JD-to-CV fit judge (2026-05-28)**:
  - `inclusio/judge/jd_fit.py` — third judge in the pipeline.
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
  - `inclusio/judge/citations.py` — heuristic + LLM-backed
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
  - `inclusio/judge/local_llm.py` — stdlib-only HTTP client
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
  - `inclusio/emit/pandoc.py::emit_epub` — Pandoc `--to epub3
    --standalone --mathjax` with BCP-47 language metadata. Closes
    the multi-format triad (HTML + JATS + EPUB), fully closing
    Forcing Function #3.
  - `SUPPORTED_FORMATS` extended to `("html", "jats", "epub")`;
    `emit_all` routes the new format through the same dispatch
    surface.
  - CLI default updated: `python -m inclusio.cli.build emit`
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
  - `inclusio/judge/ats.py` — Workday / Greenhouse / Lever
    heuristic scoring for CV variants. Local, deterministic, sub-ms.
    Closes Forcing Function #5 on the deterministic surface.
  - 9 checks: canonical headings, contact info, length bands,
    bullet density, date consistency, killer phrases (each tunable
    via module-level constants).
  - 0-100 score + A/B/C/D/F grade derivation; `JudgeReport.to_dict()`
    for JSON serialisation.
  - CLI: `python -m inclusio.cli.build judge --doc cv
    --judge ats [--json path] [--strict]`. Renders the CV via
    `render --format text` then scores the plain-text output.
  - `make judge DOC=cv` shortcut.
  - `tests/test_judge_ats.py` — 23 tests covering every check, grade
    boundaries, JSON round-trip, and the score-clamp-to-0 invariant.
  - `docs/judges.md` — heuristic table, CLI examples, Python API,
    Sprint 7.5+ roadmap (llama.cpp, citation grounding).

- **Sprint 7 — emit CLI wiring (2026-05-28)**:
  - `python -m inclusio.cli.build emit [--doc X] [--formats html,jats] [--strict]`
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
  - `inclusio/emit/pandoc.py` — Pandoc-wrapping emitters with
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
  - `inclusio/mcp/server.py` — FastMCP-based MCP server exposing
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
    `inclusio/cli/render.py` coverage 76% → 96%.
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
  - `inclusio/tools/overlay.py` — deep-merge helper for the
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

- `inclusio.cli.audit` — veraPDF runner for PDF/UA-2, WTPDF 1.0
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
- `inclusio` package (`cli.build`, `cli.render`, `cli.tailor`,
  `cli.sitemap`, `tools.fix_semantic`, `tools.stamp_pdfs`).
- Eleven `pub-*.cls` document classes; five `pub-*.sty` style packages.
- Jinja2 templating with LaTeX-safe delimiters (`<<>>`, `<%%>`, `<##>`).
- `EUXIS_CONTENT_DIR` env var + `--content-dir` flag for split-repo
  workflows.
- Initial test suite (engine smoke + macro contract + assets).

<!-- generated by git-cliff -->
