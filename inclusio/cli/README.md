# `inclusio.cli` — Console entry points

The argparse layer for every `inclusio` command. The console
scripts in `pyproject.toml` (`inclusio`, `inclusio-mcp`) dispatch
here.

## Subcommands

| Subcommand | Module | What it does |
|---|---|---|
| `build` | `inclusio.cli.build` | Compile registered documents into tagged PDFs |
| `render` | `inclusio.cli.render` | Render Jinja2 templates to LaTeX / Markdown / JSON / text |
| `audit` | `inclusio.cli.audit` | Run veraPDF over `build/` (UA-2 + WTPDF + PDF/A-4f) |
| `emit` | (build dispatch) | HTML5 / JATS XML / EPUB3 via Pandoc |
| `judge` | (build dispatch) | ATS / citations / JD-fit judges |
| `provenance` | (build dispatch) | C2PA Content Credentials |
| `tailor` | `inclusio.cli.tailor` | Brief-driven CV / paper / patent tailoring |
| `import-resume` | `inclusio.cli.import_resume` | JSON Resume v1 → inclusio CV YAML |
| `sitemap` | `inclusio.cli.sitemap` | Semantic search metadata (`build/site-map.json`) |
| `blog` | (build dispatch) | Render blog posts to Markdown |
| `lint` | (build dispatch) | Run semantic + chktex + vale checks |
| `fix` | (build dispatch) | Auto-fix semantic violations (`inclusio.tools.fix_semantic`) |
| `clean` / `distclean` / `list` | (build dispatch) | Housekeeping + manifest enumeration |

## Invocation styles

```bash
# Console script (preferred — installed by pip):
inclusio build --doc cv
inclusio audit --strict

# Module form (always works, no PATH dependency):
python -m inclusio.cli.build build --doc cv
python -m inclusio.cli.render --doc cv --format text

# Against an external content tree:
inclusio --content-dir /path/to/content build
INCLUSIO_CONTENT_DIR=/path/to/content inclusio build
```

`inclusio build` and `make publish` scan `data/jobs/` and
auto-generate tailored YAML for supported brief formats before
they compile PDFs.

## Top-level help

```bash
inclusio --help                          # subcommand list
inclusio judge --help                    # judge-specific flags
inclusio provenance --help               # signing flags
```
