# 01 — Hello, tagged PDF

The minimal happy path: one `.tex` → one PDF that veraPDF marks PASS
on PDF/UA-2, WTPDF, and PDF/A-4f.

**You'll learn:** how `\DocumentMetadata{}` + `[tagged]` class option
delegate XMP + structure-tree generation to the LaTeX kernel, and
how to read the audit report.

## Prereqs

- `inclusio` (`pip install inclusio`)
- A LuaLaTeX toolchain (`tlmgr install scheme-medium` is enough)
- `verapdf` on `PATH` for the audit step (optional)

## Run it

```bash
make            # render → build → audit
```

Outputs land in `build/`:

| File | Meaning |
|---|---|
| `build/hello.pdf` | Tagged PDF/UA-2 + PDF/A-4f |
| `build/.audit/eaa-*.json` | veraPDF report (when veraPDF is installed) |
| `build/.audit/eaa-*.md` | Same report as Markdown |

## What's actually happening

```latex
% src/hello.tex (excerpt)
\DocumentMetadata{
  pdfversion = 2.0,
  pdfstandard = ua-2,
  pdfstandard = a-4f,
  lang = en-GB,
}
\documentclass[final,tagged]{pub-base}
```

The `\DocumentMetadata{}` directive (LaTeX 2024-11 or newer) makes
the kernel:

1. emit a PDF 2.0 stream,
2. write a `pdfaid:part=4` + `pdfuaid:part=2` XMP packet,
3. wrap every text run in a `/StructTreeRoot` tag,
4. and refuse to compile if anything would violate the standards.

`inclusio` adds the `pub-base` class (in `core/cls/`) which provides
the document headers, hyperref configuration, and ATS-friendly
heading hierarchy. After LuaLaTeX finishes, `inclusio audit
--strict` runs veraPDF over the artefact and exits non-zero if any
flavour fails — the same gate the engine's CI uses.

## Next steps

- Add a CV with [`02-cv-from-jsonresume/`](../02-cv-from-jsonresume/)
- Add citations + multi-format emission with
  [`03-paper-with-citations/`](../03-paper-with-citations/)
