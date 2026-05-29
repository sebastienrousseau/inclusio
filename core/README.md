# `core/` — LaTeX classes and styles

The LaTeX layer the engine ships. Loaded by every `\documentclass{pub-*}`
invocation in `src/` and in every example.

| Subfolder | What's in it |
|---|---|
| `core/cls/` | Document classes: `pub-base`, `pub-cv`, `pub-paper`, `pub-patent-us`, `pub-faq`, `pub-guide`, `pub-bio`, `pub-arxiv`, `pub-preprint`, `pub-prime` |
| `core/sty/` | Shared style packages: `pub-colors`, `pub-typography`, `pub-buildmodes`, `pub-metadata`, `pub-common` |

These are part of the public engine surface and are exercised on
every CI run via the LaTeX Excellence pipeline. Class-level
changes require a matching update under `core/cls/*.cls` plus a
fixture under `src/` that compiles cleanly with veraPDF.
