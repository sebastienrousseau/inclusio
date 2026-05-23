# Classes And Styles

This repository uses a modular class/style architecture.

## Class Layer (`core/cls`)

- `pub-base.cls` - shared base class and common package loading.
- `pub-paper.cls`, `pub-preprint.cls`, `pub-arxiv.cls`, `pub-prime.cls` - research publishing variants.
- `pub-patent.cls`, `pub-patent-us.cls` - legal/patent variants.
- `pub-guide.cls`, `pub-faq.cls` - documentation variants.
- `pub-bio.cls`, `pub-cv.cls` - biography and profile variants.

## Style Layer (`core/sty`)

- `pub-colors.sty` - color tokens and semantic aliases.
- `pub-typography.sty` - typography system and ratios.
- `pub-buildmodes.sty` - mode-specific controls.
- `pub-common.sty` - semantic macro helpers.
- `pub-metadata.sty` - metadata and publication metadata plumbing.

## Notable Implementation Details

- `pub-base.cls` optionally loads `microtype` when available.
- `pub-base.cls` exposes `[tagged]` and `[final-untagged]` options to
  control PDF/UA-2 + PDF/A-4f emission (see `docs/tagged-pdf.md`).
- `pub-base.cls` errors loudly via `\ClassError` if `[tagged]` is set
  without an explicit `\DocumentMetadata{...}` preamble call.
- Class-specific `\maketitle` definitions provide role-specific output formats.
- Header geometry is class-specific (`headheight` tuned per class).

For the full macro API, see `docs/macro-reference.md`.

## Tagged-PDF / PDF/UA-2 / PDF/A-4f conformance matrix

Sprint 2 verified every shipped class emits a tagged PDF that passes
PDF/UA-2 + WTPDF-1.0-Accessibility + PDF/A-4f when compiled with
LuaLaTeX + `\DocumentMetadata` + `[final, tagged]`. Regression coverage
lives in `tests/test_pdf_ua_classes.py` (44 checks: 11 classes × 4
gates).

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

Note on PDF/A-4 vs PDF/A-4f: the kernel tagging project embeds
`latex-list-css.html` + `latex-align-css.html` for HTML export.
PDF/A-4f is the variant explicitly designed to allow non-PDF/A
embedded payloads — use it for any class that engages
`testphase = phase-III` tagging.
