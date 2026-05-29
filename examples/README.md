# Examples

Six runnable scenarios that cover the breadth of what `inclusio` does.
Pick whichever matches what you want to ship first; every folder is
self-contained and includes a `Makefile` you can run with `make`.

| # | Folder | What it teaches | Toolchain dep |
|---|---|---|---|
| 1 | [`01-hello-world/`](./01-hello-world/) | Build a single `.tex` into a tagged, audit-clean PDF | LuaLaTeX |
| 2 | [`02-cv-from-jsonresume/`](./02-cv-from-jsonresume/) | Import a JSON Resume → render → ATS-judge → tagged-PDF CV | LuaLaTeX, Pandoc (optional for emit) |
| 3 | [`03-paper-with-citations/`](./03-paper-with-citations/) | Compile a scholarly paper → multi-format (PDF + HTML + JATS + EPUB) + citation judge | LuaLaTeX + Pandoc |
| 4 | [`04-mcp-agent/`](./04-mcp-agent/) | Run the MCP server and drive it from Claude Code | `pip install 'inclusio[mcp]'` |
| 5 | [`05-c2pa-sign/`](./05-c2pa-sign/) | Embed C2PA Content Credentials into a built PDF | `c2patool` on PATH |
| 6 | [`06-pades-sign/`](./06-pades-sign/) | PAdES B-T (eIDAS) signature on a built PDF | `pip install 'inclusio[provenance]'`, a TSA URL |

## Common entry points

```bash
# Install with everything the examples need.
pip install 'inclusio[mcp,provenance,dev]'

# Smoke test that the engine is on PATH.
inclusio --help

# Run an example.
cd examples/01-hello-world
make
```

Each example writes its output to a local `build/` directory so you
can inspect the PDF, audit log, and rendered HTML/JATS/EPUB without
touching the engine's own `build/`.

## Cleaning up

```bash
make clean              # remove a single example's build/
git clean -fdx examples/ # nuke every example's artefacts
```
