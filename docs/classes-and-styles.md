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
- `pub-base.cls` keeps optional `tagpdf` activation non-breaking.
- Class-specific `\maketitle` definitions provide role-specific output formats.
- Header geometry is class-specific (`headheight` tuned per class).

For the full macro API, see `docs/macro-reference.md`.
