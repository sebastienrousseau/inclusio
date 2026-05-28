---
name: euxis-publisher
description: Build, render, lint, and audit LaTeX-first documents (CVs, papers, patents, FAQs, guides) through the Euxis Publisher engine. Use when the user mentions LaTeX, tagged PDFs, PDF/UA-2, PDF/A-4f, WCAG accessibility, the European Accessibility Act (EAA), or asks about building/auditing documents in a repository that has a `data/meta.yaml` manifest.
---

# Euxis Publisher — Claude skill

Use the Euxis Publisher engine (`inclusio` Python package) to build
camera-ready tagged PDFs, lint LaTeX, and audit accessibility conformance
(PDF/UA-2 + WTPDF + PDF/A-4f). The engine is split across two repos:

- **Engine** (`euxis-publisher`): document classes, build CLI, audit CLI,
  Jinja2 renderer. Open source, MIT-licensed.
- **Content** (`euxis-publisher-private` or any repo with
  `data/meta.yaml`): LaTeX sources, YAML data, templates. Discovered via
  `EUXIS_CONTENT_DIR` or the `--content-dir` flag.

## When to use this skill

Trigger on any of:

- "build the PDFs" / "compile the documents" / "make publish"
- "is this PDF accessible?" / "PDF/UA-2 / PDF/A-4f / WCAG / EAA compliance"
- "render the CV / paper / FAQ template"
- "lint the LaTeX sources" / "chktex" / "vale"
- references to the `pub-cv`, `pub-paper`, `pub-patent`, `pub-faq`,
  `pub-guide`, `pub-arxiv`, `pub-preprint`, `pub-bio`, `pub-prime`,
  `pub-patent-us` document classes.

## Core commands

All commands assume `EUXIS_CONTENT_DIR` points at the content repo (or
the current working directory contains `data/meta.yaml`).

```bash
# List every registered document
python -m inclusio.cli.build list

# Build all docs in camera-ready (tagged PDF/A-4f) mode
python -m inclusio.cli.build build --mode camera-ready

# Build a single doc by id
python -m inclusio.cli.build build --doc whisper-paper --mode camera-ready

# Render a Jinja2 template (latex/markdown/json/text)
python -m inclusio.cli.render --doc cv --format text   # ATS-safe .txt
python -m inclusio.cli.render --doc cv --format markdown  # Workday-friendly

# Run accessibility audit (veraPDF UA-2 / WTPDF / PDF-A-4f)
python -m inclusio.cli.audit              # all PDFs under build/
python -m inclusio.cli.audit --strict     # non-zero exit on FAIL

# Tailor a CV from a job description brief
python -m inclusio.cli.tailor data/jobs/brief.txt --type cv --build
```

`make` shortcuts exist in any repo using the engine: `make publish`,
`make audit`, `make audit-strict`, `make test`, `make coverage`.

## Tagged-PDF authoring conventions

Documents that should emit PDF/UA-2 + PDF/A-4f must start with:

```latex
\DocumentMetadata{
  pdfversion   = 2.0,
  pdfstandard  = ua-2,
  pdfstandard  = a-4f,
  lang         = en-GB,
  testphase    = {phase-III, table, math, sec-latex},
}
\documentclass[final,tagged]{pub-<class>}
```

`\DocumentMetadata` MUST precede `\documentclass`. The `[tagged]` option
engages the LaTeX kernel's tagging project. Omit `[tagged]` for legacy
non-tagged builds (use `[final-untagged]` instead, the explicit escape).

## Avoid these untagged-content traps

veraPDF rule ISO 14289-2 §8.2.2 rejects untagged decorative content.
Known triggers in pub-* classes:

- `\maketitle` on pub-paper / pub-arxiv / pub-preprint emits an untagged
  date rule. Either set `\title{}` to empty or skip `\maketitle`.
- `\titleformat{\section}{…}[\titlerule]` in pub-cv / pub-faq emits an
  untagged horizontal rule. Use the class's semantic macros instead of
  raw `\section{...}` when targeting strict UA-2.
- `\linenumbers` in pub-preprint marginalia is untagged — call
  `\nolinenumbers` for tagged builds.
- `\fancyhf` footers in pub-cv: kernel wraps these correctly only when
  the doc opts into `[tagged]` AND uses Sprint-2+ class versions.

## MCP server

The engine also ships as an MCP server (`euxis-mcp`). When the user is
working through Claude Code or Cursor, prefer calling the MCP tools
(`list_docs`, `audit_pdf`, `render`) over shelling out, because the
results are typed and serialisable. Install via `pip install
'euxis-publisher[mcp]'`.

## Documentation

- `docs/audit-2026-05.md` — 2026-H2 roadmap + audit
- `docs/strategy-2026.md` — eight forcing functions
- `docs/tagged-pdf.md` — full PDF/UA-2 + PDF/A-4f migration guide
- `docs/classes-and-styles.md` — pub-* class reference

## Compliance context

EAA enforcement is **live since 28 June 2025** for EU consumer
audiences. Untagged PDF/A-2u is a regulatory exposure. Camera-ready
artefacts MUST pass the strict `euxis-publisher audit --strict` gate
before publication. Penalties: Germany €100k, France €250k, Italy 5% of
turnover.
