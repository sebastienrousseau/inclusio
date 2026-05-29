# `templates/` — Jinja2 templates

Public, non-sensitive Jinja2 templates the `inclusio render`
command expands against YAML data.

| Template | Rendered to |
|---|---|
| `cv.tex.j2` | `build/.cache/rendered/cv.tex` (LaTeX for the CV class) |
| `paper.tex.j2` | Paper class LaTeX |
| `faq.tex.j2` | FAQ class LaTeX |
| `guide.tex.j2` | Guide class LaTeX |
| `blog-post.md.j2` | Markdown for the blog renderer |

Brand-specific overrides live in a consumer's own content tree
(override `--content-dir` and ship your own `templates/` directory
alongside `data/` and `src/`).
