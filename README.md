<p align="center">
  <img src="https://cloudcdn.pro/inclusio/v1/logos/inclusio.svg" alt="Inclusio logo" width="128" />
</p>

<h1 align="center">Inclusio</h1>

<p align="center">
  <strong>Publishing that includes everyone.</strong>
</p>

<p align="center">
  Accessibility-first publishing engine for LaTeX, packaged as a
  Python CLI. PDF/UA-2 + WTPDF + PDF/A-4f triple-conformance,
  C2PA + PAdES + SLSA provenance, multi-format emission
  (HTML5 / JATS / EPUB3), LLM-augmented judges, and an MCP server
  for agent integration.
</p>

<p align="center">
  <a href="https://github.com/sebastienrousseau/inclusio/actions/workflows/engine-validation.yml"><img src="https://img.shields.io/github/actions/workflow/status/sebastienrousseau/inclusio/engine-validation.yml?style=for-the-badge&logo=github&label=CI" alt="Engine Validation" /></a>
  <a href="https://github.com/sebastienrousseau/inclusio/actions/workflows/verapdf.yml"><img src="https://img.shields.io/github/actions/workflow/status/sebastienrousseau/inclusio/verapdf.yml?style=for-the-badge&logo=github&label=veraPDF" alt="veraPDF Audit" /></a>
  <a href="https://github.com/sebastienrousseau/inclusio"><img src="https://img.shields.io/badge/Python-%3E%3D3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python &gt;= 3.11" /></a>
  <a href="https://github.com/sebastienrousseau/inclusio"><img src="https://img.shields.io/badge/PDF%2FUA--2%20%7C%20WTPDF%20%7C%20PDF%2FA--4f-blue?style=for-the-badge" alt="PDF/UA-2 · WTPDF · PDF/A-4f" /></a>
  <a href="https://github.com/sebastienrousseau/inclusio/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-black?style=for-the-badge" alt="MIT licence" /></a>
</p>

---

## Contents

- [Install](#install) — `pip`, optional extras, source
- [Quick Start](#quick-start) — first tagged PDF in 60 seconds
- [Features](#features) — what the engine ships
- [Usage](#usage) — common Python + CLI recipes
- [Architecture](#architecture) — the engine's package layout
- [Examples](#examples) — six runnable scenarios
- [Documentation](#documentation) — quickstart, tutorials, reference
- [Publishing against an external content tree](#publishing-against-an-external-content-tree)
- [Development](#development) — local validation gate
- [Security](#security) — signed commits, provenance, audit
- [License](#license)

---

## Install

```bash
pip install inclusio                       # engine + CLI
pip install 'inclusio[mcp]'                # + FastMCP server
pip install 'inclusio[provenance]'         # + pyhanko (PAdES)
pip install 'inclusio[dev]'                # + pytest, ruff, sphinx, interrogate
```

**Requires** Python ≥ 3.11 and a LuaLaTeX toolchain on PATH. Linux,
macOS, and WSL are supported (native Windows works for the Python
surface; the LaTeX gate needs WSL or a TeX Live install).

| Optional tool | Adds | Install |
|---|---|---|
| `verapdf` | The strict EAA / accessibility audit gate | [verapdf.org/install](https://docs.verapdf.org/install/) |
| `pandoc` (≥ 3.0) | HTML5 / JATS XML / EPUB3 multi-format emission | `brew install pandoc` · `apt install pandoc` |
| `c2patool` | C2PA Content Credentials | [contentauth/c2patool releases](https://github.com/contentauth/c2patool/releases) |
| `pyhanko` (via `[provenance]`) | PAdES B-T / B-LT / B-LTA signing | Pulled by the extra |

### Build from source

```bash
git clone https://github.com/sebastienrousseau/inclusio.git
cd inclusio
./bin/setup        # check toolchain + install dev extras
make test          # smoke suite
make coverage      # full suite (gate: 97 %)
```

---

## Quick Start

A complete worked example you can paste into a fresh directory:

```bash
pip install inclusio

# Grab the minimal example, build + audit + emit + judge:
git clone --depth=1 https://github.com/sebastienrousseau/inclusio
cd inclusio/examples/01-hello-world && make
```

That single `make` produces `build/hello.pdf` (PDF/UA-2 + WTPDF +
PDF/A-4f triple-conformance), runs veraPDF over it, and exits
non-zero if any flavour fails.

Drive the same surface from Python:

```python
# quickstart.py
import subprocess
from pathlib import Path

# 1. Render + build the bundled "hello" fixture — the CLI is the
#    canonical entry point for the LaTeX step.
subprocess.run(
    ["python", "-m", "inclusio.cli.build", "build", "--doc", "hello"],
    cwd="examples/01-hello-world",
    check=True,
)

# 2. Audit the produced PDF in-process — pure-Python, no subprocess.
from inclusio.cli import audit

pdfs = audit.collect_pdfs(
    target=Path("examples/01-hello-world/build"),
    build_dir=Path("examples/01-hello-world/build"),
    registry_stems={"hello"},
)
report = audit.audit(pdfs)
assert report["summary"]["fail"] == 0, "veraPDF reported a failure"
print(f'  PASS  {report["summary"]["pdfs"]} PDF(s), '
      f'{report["summary"]["pass"]}/{report["summary"]["total"]} checks')
# →   PASS  1 PDF(s), 3/3 checks
```

---

## Features

- **Tagged PDF, by default.** Every build emits a PDF/UA-2 +
  WTPDF + PDF/A-4f triple-conforming artefact via the LaTeX
  kernel's `tagpdf` integration. The veraPDF audit gate is wired
  into CI and exits non-zero on any FAIL.
- **Multi-format emission.** The same LaTeX source produces HTML5
  (WCAG-clean), JATS XML (1.3, JATS4R-ready), and EPUB3 via
  Pandoc.
- **LLM-augmented judges.** ATS (Workday / Greenhouse / Lever
  heuristic), citation grounding, and JD-to-CV fit — local
  `llama.cpp` or BYO-key cloud (Anthropic / OpenAI), with
  heuristic-only fallback when the LLM is unreachable.
- **Content provenance.** C2PA Content Credentials (via
  `c2patool`), PAdES B-T / B-LT / B-LTA signatures (via
  `pyhanko`), and SLSA L3 build attestation (via
  `actions/attest-build-provenance`).
- **MCP server.** `inclusio-mcp` exposes `list_docs`, `audit_pdf`,
  `render`, and `doc_count` so Claude Code, Cursor, Continue, or
  any other MCP client can drive the engine.
- **JSON Resume importer.** `inclusio import-resume` converts a
  jsonresume.org v1 document into the engine's CV YAML schema.
- **Brief-driven CV tailoring.** ATS-clean variants tailored
  against a job description with British-English cleanup and
  consistency lint.

## Usage

### Build, audit, judge a registered document

```bash
inclusio build --doc cv --mode draft        # → build/cv.pdf
inclusio audit --strict                     # → veraPDF, non-zero on FAIL
inclusio judge --doc cv --judge ats         # → grade + findings
```

### Score a CV against a job description

```python
# score_cv.py — fully runnable: drop into a directory with brief.txt + cv.txt
from pathlib import Path
from inclusio.judge import jd_fit

jd_text = Path("brief.txt").read_text(encoding="utf-8")
cv_text = Path("cv.txt").read_text(encoding="utf-8")

report = jd_fit.score_jd_fit(jd_text, cv_text)
print(f"score:   {report.score}/100   grade: {report.grade}")
print(f"missing: {sorted(report.metrics['missing_required'])[:5]}")
# → score:   78/100   grade: B
# → missing: ['opentelemetry', 'rust']
```

### Drive the engine over MCP

```bash
inclusio-mcp                          # stdio (Claude Code default)
inclusio-mcp --http --port 8765       # Streamable HTTP
```

Wire into Claude Code via `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "inclusio": {
      "command": "inclusio-mcp",
      "env": { "INCLUSIO_CONTENT_DIR": "/absolute/path/to/content" }
    }
  }
}
```

### Embed C2PA Content Credentials

```bash
inclusio provenance --doc cv \
  --cert /path/to/cert.pem \
  --key  /path/to/key.pem \
  --output build/cv.c2pa.pdf
```

---

## Architecture

```
inclusio/                  # Python package
  cli/                     # build · audit · render · tailor · judge · emit · provenance · …
  judge/                   # ats · citations · jd_fit · local_llm · cloud_llm
  emit/                    # pandoc (HTML5 / JATS XML / EPUB3)
  provenance/              # c2pa (c2patool) · pades (pyhanko)
  mcp/                     # FastMCP server
  tools/                   # fix_semantic · stamp_pdfs · overlay
core/                      # LaTeX classes (.cls) and styles (.sty)
templates/                 # Jinja2 templates for the template-driven docs
benches/                   # pytest-benchmark micro-benchmarks
examples/                  # Six self-contained runnable scenarios
docs/                      # Sphinx documentation
```

External consumers supply their own content tree (LaTeX sources,
YAML metadata, brand assets) and point the engine at it through
`INCLUSIO_CONTENT_DIR` or `--content-dir`. The repo's own `src/`
and `data/` directories double as the public-engine self-test
fixtures.

## Examples

| # | Folder | What it teaches |
|---|---|---|
| 1 | [`01-hello-world/`](./examples/01-hello-world/) | Tagged-PDF build with the audit gate |
| 2 | [`02-cv-from-jsonresume/`](./examples/02-cv-from-jsonresume/) | JSON Resume → CV → ATS + JD-fit scoring |
| 3 | [`03-paper-with-citations/`](./examples/03-paper-with-citations/) | Paper → PDF + HTML + JATS + EPUB + citation judge |
| 4 | [`04-mcp-agent/`](./examples/04-mcp-agent/) | `inclusio-mcp` + Claude Code skill |
| 5 | [`05-c2pa-sign/`](./examples/05-c2pa-sign/) | C2PA Content Credentials |
| 6 | [`06-pades-sign/`](./examples/06-pades-sign/) | PAdES B-T eIDAS signature |

Each folder has its own `Makefile` (`make help` lists targets) and
a `README.md` with the why + the how.

## Documentation

- **[Quickstart](./docs/quickstart.md)** — five-minute walkthrough.
- **[Tutorials](./docs/tutorials/)** — four end-to-end walkthroughs
  paired 1 : 1 with the examples.
- **[Architecture](./docs/architecture.md)** — public-engine vs
  content-repo boundary, sprint history, decision log.
- **[Tagged PDF](./docs/tagged-pdf.md)** — the conformance stack.
- **[Multi-format](./docs/multi-format.md)** — HTML / JATS / EPUB.
- **[Judges](./docs/judges.md)** — ATS, citations, JD-fit, LLM
  rerank contract.
- **[Provenance](./docs/provenance.md)** — C2PA, PAdES, SLSA.
- **[MCP server](./docs/mcp-server.md)** — tool + resource surface.

## Publishing against an external content tree

```bash
make publish CONTENT_DIR=/absolute/path/to/your-content-repo
```

The content repo supplies its own `data/meta.yaml` (document
registry) and `src/**.tex` (LaTeX sources). The engine reads no
state from outside `INCLUSIO_CONTENT_DIR` once it's set.

## Development

```bash
make test          # smoke (≤ 20 s)
make coverage      # full suite + 97 % gate (~3 min)
make docstrings    # 100 % interrogate gate
make benchmark     # pytest-benchmark micro-budgets
make audit-strict  # veraPDF, exits non-zero on any FAIL
make docs          # Sphinx
```

All commits to `main` are squash-merged via PR. Branch protection
requires `Lint (ruff)` + `Public Engine Checks (py3.11 / 3.12 /
3.13)` + the `Signed-commit gate` to pass. See
[`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Security

- **SSH-signed commits.** Every commit on `main` is GitHub-verified.
- **Signed tags.** Release tags are ED25519-signed.
- **SLSA L3 build provenance** (gated on the repo being public or
  on a paid GitHub plan).
- **PyPI Trusted Publishing** wiring (`pypa/gh-action-pypi-publish`)
  in `release.yml`; flip `vars.PYPI_TRUSTED_PUBLISHING=true` once
  the PyPI publisher is configured.
- **Cloud LLM keys are env-var only** — `inclusio` never auto-
  discovers credentials from disk.

Report vulnerabilities per [`SECURITY.md`](./SECURITY.md).

## License

[MIT](./LICENSE). © 2026 Sebastien Rousseau.
