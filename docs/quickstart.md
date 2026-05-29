# Quickstart

Build your first tagged PDF in five minutes.

## 1. Install

```bash
pip install inclusio                 # engine + CLI
inclusio --help                      # confirm it's on PATH
```

Optional extras:

| Extra | Adds | When you need it |
|---|---|---|
| `[mcp]` | FastMCP server + CLI | Driving inclusio from an agent |
| `[provenance]` | pyhanko (PAdES) | Signing PDFs for eIDAS-regulated sectors |
| `[dev]` | pytest, ruff, sphinx, etc. | Contributing or running the full test suite |

You also need a **LuaLaTeX** toolchain (`tlmgr install scheme-medium`
is enough) and, for the audit gate, [veraPDF](https://verapdf.org).

## 2. Build, audit, emit, judge — in one command

```bash
git clone --depth=1 https://github.com/sebastienrousseau/inclusio
cd inclusio/examples/01-hello-world
make
```

You'll see:

```
  BUILD hello [draft] → build
    OK  build/hello.pdf
  AUDIT 1 PDF
    PASS  hello.pdf  ua-2 / wt1a / 4f
```

Inspect the artefact:

```bash
open build/hello.pdf          # macOS
xdg-open build/hello.pdf      # Linux
```

The PDF carries:

- `/StructTreeRoot` for screen readers
- A PDF/A-4f-compliant XMP packet (archival ready)
- A `pdfuaid:part=2` marker the EAA audit gate looks for

## 3. Six examples to grow into

| # | Folder | What it shows |
|---|---|---|
| 1 | [`01-hello-world/`](../examples/01-hello-world/) | This page |
| 2 | [`02-cv-from-jsonresume/`](../examples/02-cv-from-jsonresume/) | JSON Resume → tailored CV + ATS score |
| 3 | [`03-paper-with-citations/`](../examples/03-paper-with-citations/) | Scholarly paper → PDF + HTML + JATS + EPUB + citation judge |
| 4 | [`04-mcp-agent/`](../examples/04-mcp-agent/) | Drive inclusio from Claude Code via MCP |
| 5 | [`05-c2pa-sign/`](../examples/05-c2pa-sign/) | Embed C2PA Content Credentials |
| 6 | [`06-pades-sign/`](../examples/06-pades-sign/) | PAdES B-T (eIDAS) signature |

## 4. From example to your own content

Every example uses the same three knobs:

1. `data/meta.yaml` — registers documents by id and points to source paths.
2. `src/*.tex` — the LaTeX source (must start with `\DocumentMetadata{}` for tagging).
3. `make` — wraps `inclusio` subcommands; replace with direct CLI calls in your own project.

Add a new document by:

```yaml
# data/meta.yaml
documents:
  my-doc:
    class: pub-base               # or pub-paper / pub-patent-us / pub-cv / pub-faq / pub-guide / pub-bio
    src: src/my-doc.tex
    title: My document
```

```latex
% src/my-doc.tex
\DocumentMetadata{pdfversion=2.0, pdfstandard=ua-2, pdfstandard=a-4f, lang=en-GB}
\documentclass[final,tagged]{pub-base}
\begin{document}
…
\end{document}
```

```bash
inclusio build --doc my-doc
inclusio audit --strict
```

## 5. Next steps

- Read the [Tutorials](./tutorials/) for end-to-end walkthroughs of the
  CV, paper, and MCP-agent workflows.
- Read [Architecture](./architecture.md) to understand the public-
  engine ↔ private-content boundary.
- Read [Provenance](./provenance.md) before signing anything you intend
  to publish — the test-cert detection logic exists for good reason.
