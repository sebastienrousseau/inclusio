# `inclusio/` — Python package

The library code that backs the `inclusio` CLI, the
`inclusio-mcp` server, and every public API in the engine. Import
directly when you want to drive parts of the pipeline from Python
without shelling out to the CLI.

## At a glance

```python
# Programmatic access to every major surface.
from inclusio.cli      import audit, build, render
from inclusio.judge    import ats, citations, jd_fit
from inclusio.emit     import pandoc as emit       # HTML / JATS / EPUB
from inclusio.provenance import c2pa, pades        # signing layers
from inclusio.mcp      import server as mcp        # FastMCP factory
from inclusio.tools    import overlay              # CV/paper/patent overlays
```

## Layout

| Sub-package | Responsibility |
|---|---|
| `inclusio/cli/` | Argparse entry points for `build`, `render`, `audit`, `emit`, `judge`, `tailor`, `provenance`, `sitemap`, `import_resume`. The console scripts in `pyproject.toml` route here. |
| `inclusio/judge/` | The three judges (`ats`, `citations`, `jd_fit`) and their LLM backends (`local_llm`, `cloud_llm`). Heuristic-first; LLM rerank is opt-in. |
| `inclusio/emit/` | Pandoc wrappers for HTML5, JATS XML 1.3, and EPUB3. |
| `inclusio/provenance/` | `c2pa` (Content Credentials via `c2patool`) and `pades` (PAdES B-B/B-T/B-LT/B-LTA via `pyhanko`). Both layers are optional and import-guarded. |
| `inclusio/mcp/` | FastMCP server (`inclusio-mcp`) with four tools and three resources. Optional; pulled by the `[mcp]` extra. |
| `inclusio/tools/` | `fix_semantic` (LaTeX auto-fixer), `stamp_pdfs` (pikepdf-based watermark + metadata stamper), `overlay` (CV/paper/patent variant overlays). |

## Calling the CLI vs. the library

Most users call the CLI:

```bash
python -m inclusio.cli.build build --doc cv
python -m inclusio.cli.audit  --strict
python -m inclusio.cli.render --doc cv --format text
```

When you want to compose the engine into a larger Python program,
import the sub-package directly:

```python
from pathlib import Path
from inclusio.cli import audit

# Run veraPDF over every registered PDF under build/, in-process.
report = audit.audit(
    audit.collect_pdfs(
        target=Path("build"),
        build_dir=Path("build"),
        registry_stems={"cv", "paper"},
    )
)
print(report["summary"])
# → {'pdfs': 2, 'pass': 6, 'fail': 0, 'skip': 0, 'error': 0}
```

## Optional extras

| Extra | Adds | Required for |
|---|---|---|
| `[mcp]` | `mcp[cli]` | The `inclusio-mcp` server + the `inclusio.mcp` import path |
| `[provenance]` | `pyhanko` | `inclusio.provenance.pades` signing |
| `[dev]` | `pytest`, `pytest-cov`, `pytest-benchmark`, `ruff`, `interrogate`, `sphinx`, `myst-parser`, `furo` | Running the test suite + building the docs |

External binaries (`pandoc`, `c2patool`, `verapdf`, `latexmk`) are
runtime deps invoked via `subprocess`. The optional-import guards
raise `PandocMissing` / `C2PAMissing` / `PAdESMissing` with a
specific install hint when the binary or library isn't on PATH.

## Stability

The CLI surface (`inclusio.cli.*` argparse flags + exit codes) is
the public contract; treat module-level Python imports as
semi-stable until v0.1. Coverage gate is **97 %** (currently
98 %); docstring gate is **100 %**.
