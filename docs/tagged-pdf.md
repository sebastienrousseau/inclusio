# Tagged PDF: Migrating to PDF/UA-2 + WTPDF + PDF/A-4

> Sprint 1 deliverable (2026-05-23). Status: foundation landed; per-class
> retrofit is Sprint 2.

## Why

The European Accessibility Act (EAA) became enforceable on **28 June 2025**.
It references EN 301 549 which incorporates WCAG 2.1/2.2 AA. PDFs served
to EU consumers need **structural tagging** (headings, lists, captions,
reading order, language tags) or they fail conformance and risk penalties
up to **€100,000 or 4% of revenue**.

The old Euxis output (PDF/A-2u) was archival-quality but **untagged** —
screen readers couldn't recover structure. PDF/UA-2 (ISO 14289-2:2024)
plus PDF/A-4 (ISO 19005-4:2020) is the 2026 accessibility floor for new
PDF producers.

## The new contract

Two preamble lines, in this order, turn on tagged + PDF/UA-2 + PDF/A-4:

```latex
\DocumentMetadata{
  pdfversion   = 2.0,
  pdfstandard  = ua-2,
  pdfstandard  = a-4f,
  lang         = en-GB,
  testphase    = {phase-III, table, math, sec-latex},
}
\documentclass[final,tagged]{pub-paper}
```

What each piece does:

| Line | Meaning |
|---|---|
| `\DocumentMetadata{...}` (must precede `\documentclass`) | Engages the LaTeX kernel's tagging project. Replaces the old `pdfx` package for PDF/A and contributes the XMP metadata stream natively. |
| `pdfversion = 2.0` | Required for PDF/UA-2 (which lives only in PDF 2.0). |
| `pdfstandard = ua-2` | Asserts PDF/UA-2 conformance — the accessibility standard. |
| `pdfstandard = a-4` | Asserts PDF/A-4 archival conformance — supersedes pdfx's PDF/A-2u target. |
| `lang = en-GB` | Document language; flows into `/Lang` in the catalog. |
| `testphase = {phase-III, table, math, sec-latex}` | Enables current kernel tagging hooks: structure, tables, maths, native LaTeX sectioning. |
| `[tagged]` class option | Contract assertion: the class **errors loudly** if `\DocumentMetadata` was not called. Prevents silently producing an untagged PDF. |

## Compiler requirement

**LuaLaTeX is hard-required** (decision D3, 2026-05-23). `tagpdf`'s
phase-III hooks rely on Lua callbacks; pdfTeX and XeTeX paths have been
removed from the engine. Use TeX Live 2024 or later.

## Validation

Build and validate any document with:

```bash
# Build camera-ready (engages tagging via \DocumentMetadata)
python -m inclusio.cli.build build --doc my-paper --mode camera-ready

# Check structure tagging is present
pdfinfo build/papers/my-paper.pdf | grep Tagged   # expect: Tagged: yes

# Validate against PDF/UA-2 (full accessibility)
verapdf --format text --flavour ua2 build/papers/my-paper.pdf

# Validate against WTPDF 1.0 Accessibility profile
verapdf --format text --flavour wt1a build/papers/my-paper.pdf

# Validate against PDF/A-4 archival
verapdf --format text --flavour 4 build/papers/my-paper.pdf
```

A successful run prints `PASS <path> <flavour>` on a single line.

## Migration: existing untagged documents

If you can't migrate immediately, use the explicit escape hatch:

```latex
\documentclass[final-untagged]{pub-paper}
```

This produces a valid PDF/A-2u output via the legacy `pdfx` path. It is
**not WCAG-compliant**. Use only during the Sprint 2 retrofit window;
mark such documents in `meta.yaml` with a `migration_due:` field so they
don't drift to permanent-untagged.

## Verified results (Sprint 1 + 2)

Sprint 2 resolved the one PDF/A-4 rule that failed in Sprint 1 (ISO
19005-4 §6.9 #3 "all embedded files shall be PDF/A-compliant"). The
root cause was the LaTeX kernel embedding `latex-list-css.html` and
`latex-align-css.html` for HTML export of tagged PDFs — these are
CSS, not PDF/A. The fix is to target **PDF/A-4f** (the "with embedded
files" variant) instead of plain PDF/A-4. PDF/A-4f explicitly allows
non-conformant embedded payloads and is the correct archival target
for accessibility-tagged documents that also carry HTML export hints.

Every shipped `pub-*.cls` now passes the four-check matrix:

| Class | Compile | PDF/UA-2 | WTPDF-Accessibility | PDF/A-4f |
|---|:---:|:---:|:---:|:---:|
| `pub-base` | ✓ | ✓ | ✓ | ✓ |
| `pub-paper` | ✓ | ✓ | ✓ | ✓ |
| `pub-arxiv` | ✓ | ✓ | ✓ | ✓ |
| `pub-preprint` | ✓ | ✓ | ✓ | ✓ |
| `pub-prime` | ✓ | ✓ | ✓ | ✓ |
| `pub-bio` | ✓ | ✓ | ✓ | ✓ |
| `pub-cv` | ✓ | ✓ | ✓ | ✓ |
| `pub-faq` | ✓ | ✓ | ✓ | ✓ |
| `pub-guide` | ✓ | ✓ | ✓ | ✓ |
| `pub-patent` | ✓ | ✓ | ✓ | ✓ |
| `pub-patent-us` | ✓ | ✓ | ✓ | ✓ |

44/44 PASS. Regression covered by `tests/test_pdf_ua_classes.py`.

## CI

The `verapdf.yml` workflow runs three layers of gates on every push:

1. **Per-class smoke matrix** (`tests/test_pdf_ua_classes.py`) —
   compiles a minimal document per `pub-*.cls` with `[tagged]` and
   asserts veraPDF `ua2 + wt1a + 4f` PASS. **BLOCKing** since Sprint 2.
2. **Sprint-1 foundation tests** (`tests/test_pdf_ua.py`) — assert the
   `[tagged]` / `[final-untagged]` contract on `pub-base`. BLOCKing.
3. **Sprint-3 audit CLI tests** (`tests/test_eaa.py`) — unit tests for
   the `euxis audit` command (mocked veraPDF; no runner deps). BLOCKing.
4. **Audit step** (`euxis audit --strict`) — runs the real audit
   against any built public fixtures. WARN-only on public side because
   public fixtures haven't all migrated to `\DocumentMetadata` yet;
   the private repo runs the same command **BLOCKing** in its own CI.

## EAA audit CLI

Sprint 3 ships `euxis audit` as a first-class tool. It runs veraPDF
against every registered document's PDF and produces both JSON and
Markdown reports under `build/.audit/eaa-<timestamp>.{json,md}`.

```bash
# audit every registered document
make audit

# fail the shell on any PDF/UA-2 / WTPDF / PDF/A-4f failure
make audit-strict

# audit a specific PDF
python -m inclusio.cli.audit build/papers/foo.pdf

# audit every PDF, including non-registered (e.g. recruiter inputs)
python -m inclusio.cli.audit --all

# choose flavours
python -m inclusio.cli.audit --flavours ua2,4f
```

By default the audit applies a **registry filter**: only PDFs whose
filename stem matches a `documents:` key in `meta.yaml` are audited.
This skips input briefs and other PDFs that live in `build/` but
aren't Euxis-built artefacts. Pass `--all` to bypass.

## References

- ISO 14289-2:2024 — PDF/UA-2: https://www.iso.org/standard/82278.html
- WTPDF 1.0 — PDF Association: https://pdfa.org/wp-content/uploads/2024/02/Well-Tagged-PDF-WTPDF-1.0.pdf
- ISO 19005-4:2020 — PDF/A-4: https://pdfa.org/resource/iso-19005-4-pdf-a-4/
- European Accessibility Act: https://commission.europa.eu/strategy-and-policy/policies/justice-and-fundamental-rights/disability/european-accessibility-act-eaa_en
- LaTeX `\DocumentMetadata` — LaTeX news August 2022: https://www.latex-project.org/news/latex2e-news/ltnews36.pdf
- `tagpdf` package: https://ctan.org/pkg/tagpdf
- veraPDF: https://verapdf.org/
- Euxis strategy: [`strategy-2026.md`](strategy-2026.md)
- Sprint plan: [`implementation-plan-2026.md`](implementation-plan-2026.md)
