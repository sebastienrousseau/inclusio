# `src/` — Public LaTeX fixtures

LaTeX source files that double as the engine's self-test corpus.
Every file here ships through the same build + audit pipeline an
external consumer would use.

| Subfolder | Class |
|---|---|
| `src/bios/` | `pub-bio` |
| `src/cvs/` | `pub-cv` |
| `src/faqs/` | `pub-faq` |
| `src/guides/` | `pub-guide` |
| `src/papers/` | `pub-paper`, `pub-arxiv`, `pub-preprint`, `pub-prime` |
| `src/patents/` | `pub-patent-us` |

These are fixtures, not user content. Your own LaTeX sources live
in an external content directory and are surfaced through
`INCLUSIO_CONTENT_DIR`.
