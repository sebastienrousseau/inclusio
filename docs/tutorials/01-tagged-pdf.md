# Tutorial 1 — Building a tagged PDF

> 15 minutes · Difficulty: easy · Example:
> [`examples/01-hello-world/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/01-hello-world/)

By the end of this tutorial you'll have a PDF that veraPDF marks PASS
on three conformance flavours — PDF/UA-2 (accessibility), WTPDF
(well-tagged), and PDF/A-4f (archival with embedded files) — and you'll
understand how each of those gates works.

## What "tagged PDF" actually means

A *tagged* PDF carries a `/StructTreeRoot` dictionary that describes
the document's logical structure — paragraphs, headings, lists,
figures, table cells — alongside the visual content. Screen readers
walk the structure tree, not the visual layout, which is why an
untagged 200-page PDF is unreadable while a tagged 200-page PDF is
indistinguishable from clean HTML to a JAWS user.

inclusio produces tagged PDFs by delegating structure-tree generation
to the LaTeX kernel's `tagpdf` integration. There are no opaque
post-processing steps — the structure is built during typesetting and
shipped as-is.

## Step 1 — Set up

```bash
pip install inclusio

# A LuaLaTeX toolchain is required.
# macOS:    brew install --cask basictex
# Debian:   apt install texlive-luatex texlive-latex-extra
# veraPDF for the audit step (optional but recommended):
# https://docs.verapdf.org/install/
```

## Step 2 — The minimal source

The minimal inclusio document is **four lines** of preamble plus
content:

```latex
\DocumentMetadata{
  pdfversion = 2.0,
  pdfstandard = ua-2,
  pdfstandard = a-4f,
  lang = en-GB,
}
\documentclass[final,tagged]{pub-base}

\begin{document}
Hello, tagged PDF.
\end{document}
```

The `\DocumentMetadata{}` directive (LaTeX 2024-11 or newer) tells the
kernel to:

1. Emit a PDF 2.0 stream.
2. Write an XMP packet with `pdfaid:part=4` (PDF/A-4) and
   `pdfuaid:part=2` (PDF/UA-2) markers.
3. Set the document language so screen readers pick the right voice.

The `[tagged]` class option enables structure-tree generation. The
`pub-base` class (in [`core/cls/`](https://github.com/sebastienrousseau/inclusio/tree/main/core/cls/)) supplies the
section heading hierarchy, hyperref configuration, and the
ATS-friendly metadata defaults that inclusio expects.

## Step 3 — Register the document

inclusio's discovery layer reads `data/meta.yaml`:

```yaml
author:
  name: Example Author

documents:
  hello:
    class: pub-base
    src: src/hello.tex
    title: Hello, tagged PDF
```

The id (`hello`) is what subsequent CLI calls reference; the `src` is
the LaTeX source.

## Step 4 — Build + audit

```bash
inclusio build --doc hello                 # → build/hello.pdf
inclusio audit --strict                    # → veraPDF report
```

`inclusio build` runs `latexmk -lualatex` over the source. `inclusio
audit --strict` shells out to veraPDF with three profiles enabled:

```text
| `ua2` | 1 | 0 | 0 | 0 |
| `wt1a` | 1 | 0 | 0 | 0 |
| `4f` | 1 | 0 | 0 | 0 |
```

Exit code 0 means all three flavours passed. The `--strict` flag makes
the CLI exit non-zero on any FAIL — the same gate the engine's own CI
uses.

## Step 5 — Verify what's in the PDF

```bash
# Inspect the structure tree with pikepdf
python3 -c "
import pikepdf
with pikepdf.open('build/hello.pdf') as pdf:
    print('Tagged:', '/StructTreeRoot' in pdf.Root)
    print('PDF version:', pdf.pdf_version)
    print('Language:', pdf.Root.get('/Lang'))
"
```

You should see `Tagged: True`, `PDF version: 2.0`, and `Language:
en-GB`.

## What's actually happening — at a glance

```
┌─────────────────┐    LuaLaTeX     ┌─────────────────┐  veraPDF   ┌──────────┐
│  src/hello.tex  │ ──────────────> │ build/hello.pdf │ ─────────> │ Report   │
│  + \DocMeta{}   │   tagpdf-aware  │  /StructTree    │  3 profile │ PASS×3   │
│  + [tagged]     │                 │  XMP packet     │  audit     │          │
└─────────────────┘                 └─────────────────┘            └──────────┘
```

## Common questions

**Do I need to write structure tags by hand?** No. Standard LaTeX
constructs (`\section`, `\begin{itemize}`, `\caption`) emit the right
PDF tags automatically when `\DocumentMetadata{pdfstandard=ua-2}` is
set. You only need manual tagging for non-standard constructs.

**What if I don't want PDF/A-4f?** Drop the `pdfstandard = a-4f` line.
Audit with `--flavours ua-2,wt1a` to skip the PDF/A profile. Note that
PDF 2.0 is required for PDF/UA-2 even without PDF/A.

**Can I use pdflatex or xelatex instead of LuaLaTeX?** No. inclusio
follows decision D3 in the strategy doc: LuaLaTeX is the only engine
that ships reliable tagged-PDF output as of 2026.

**Where does the veraPDF report live?** Under `build/.audit/eaa-*.json`
(machine-readable) and `build/.audit/eaa-*.md` (human-readable). The
`inclusio audit` CLI's stdout is a Markdown summary; the JSON is for
CI pipelines.

## Next steps

- [Tutorial 2 — ATS scoring a CV](./02-judge-cv.md)
- [Tutorial 3 — Driving inclusio from an MCP agent](./03-mcp-agent.md)
- [`docs/tagged-pdf.md`](../tagged-pdf.md) — the reference docs on
  inclusio's tagged-PDF stack.
