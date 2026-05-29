# Examples

Six runnable scenarios that cover the breadth of what **inclusio**
does. Pick whichever matches what you want to ship first; every
folder is self-contained and includes a `Makefile` you can run with
`make`.

## Which one should I run first?

| If you want to … | Start here |
|---|---|
| See what a tagged PDF actually looks like | [`01-hello-world/`](./01-hello-world/) |
| Build a CV, score it, ship it | [`02-cv-from-jsonresume/`](./02-cv-from-jsonresume/) |
| Publish a scholarly paper in four formats | [`03-paper-with-citations/`](./03-paper-with-citations/) |
| Drive inclusio from Claude Code / Cursor | [`04-mcp-agent/`](./04-mcp-agent/) |
| Add a C2PA manifest to a PDF | [`05-c2pa-sign/`](./05-c2pa-sign/) |
| Sign a PDF for eIDAS-regulated use | [`06-pades-sign/`](./06-pades-sign/) |

## Catalog

| # | Folder | What it teaches | Extra toolchain |
|---|---|---|---|
| 1 | [`01-hello-world/`](./01-hello-world/) | Tagged-PDF build + veraPDF audit | LuaLaTeX |
| 2 | [`02-cv-from-jsonresume/`](./02-cv-from-jsonresume/) | JSON Resume → CV → ATS + JD-fit scoring | LuaLaTeX |
| 3 | [`03-paper-with-citations/`](./03-paper-with-citations/) | Paper → PDF + HTML + JATS + EPUB + citation judge | LuaLaTeX, Pandoc |
| 4 | [`04-mcp-agent/`](./04-mcp-agent/) | `inclusio-mcp` + Claude Code skill | `pip install 'inclusio[mcp]'` |
| 5 | [`05-c2pa-sign/`](./05-c2pa-sign/) | C2PA Content Credentials | `c2patool` on PATH |
| 6 | [`06-pades-sign/`](./06-pades-sign/) | PAdES B-T eIDAS signature | `pip install 'inclusio[provenance]'`, a TSA URL |

## Quick Start

```bash
# 1. Engine + every optional extra the examples might want.
pip install 'inclusio[mcp,provenance,dev]'

# 2. Smoke-test the CLI.
inclusio --help

# 3. Run example #1 end-to-end.
cd examples/01-hello-world && make
```

Each example writes its output to a local `build/` directory so you
can inspect the PDF, audit log, and rendered HTML/JATS/EPUB without
touching the engine's own `build/`.

## Cleaning up

```bash
make clean                      # one example's build/
git clean -fdx examples/        # nuke every example's artefacts
```

## Architecture of an example folder

Every example follows the same three-knob structure:

```
01-hello-world/
├── README.md             # the tutorial-style write-up
├── Makefile              # the one-command runner
├── data/
│   └── meta.yaml         # document registry (--content-dir target)
└── src/
    └── hello.tex         # LaTeX source(s)
```

The `Makefile` invokes `python -m inclusio.cli.build --content-dir
$(CURDIR) <command>`, which means the engine treats the example
folder as if it were the full content repo for the duration of the
build. Drop your own `meta.yaml` + `src/*.tex` into a fresh
directory and you have a working content repo.

## Companion tutorials

Each example is paired 1 : 1 with a long-form tutorial in
[`../docs/tutorials/`](../docs/tutorials/). Read the tutorial for
the *why*; run the example for the *how*.
