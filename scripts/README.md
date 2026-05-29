# `scripts/` — Non-Python helper scripts

Two stand-alone shell scripts the Makefile calls. Everything that
used to be a Python compatibility wrapper here was removed in
v0.0.3 — the canonical entry point is `python -m inclusio.cli.*`.

| Script | What it does |
|---|---|
| `asset-pipeline.sh` | Mermaid (`.mmd`) → SVG → PDF/PNG conversion for figure assets |
| `check-semantic.sh` | Bash linter for forbidden direct-formatting LaTeX commands |

Both are invoked from the Makefile; you rarely need to call them
directly.
