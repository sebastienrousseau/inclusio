# Contributing to Inclusio

Thank you for considering a contribution. This document covers what
the project is, how to get set up, what changes are welcome, and the
gates a PR has to pass.

## What this repository is

- **`inclusio/`** — the Python publishing engine. Builds tagged PDFs
  (PDF/UA-2 + WTPDF + PDF/A-4f), emits HTML5 / JATS / EPUB3, runs
  LLM-augmented judges, embeds C2PA + PAdES + SLSA provenance, and
  exposes itself over MCP.
- **`examples/`** — six runnable scenarios (start here if you want to
  see what it does).
- **`docs/`** — long-form Sphinx documentation.
- **`tests/`**, **`benches/`** — pytest + pytest-benchmark suites.
- **`core/`**, **`templates/`** — LaTeX classes and Jinja2 templates.
- **`src/`**, **`data/`** — showcase content that the engine builds
  as its own self-test (also the canonical example of the
  consumer-side layout an external content repo would use).

The public engine surface is fully test-covered without any private
content; the showcase under `src/` and `data/` doubles as a
regression fixture.

## Quick-start for contributors

```bash
# 1. Fork + clone
git clone git@github.com:your-name/inclusio.git
cd inclusio

# 2. Install the dev extras
pip install -e '.[dev,mcp,provenance]'

# 3. Validate that the engine works
make test            # smoke suite (~20 s)
make coverage        # full suite + coverage gate (~3 min)
make docstrings      # 100 % docstring gate
make benchmark       # hot-path microbenchmarks

# 4. Try an example
cd examples/01-hello-world && make
```

You also need a **LuaLaTeX** toolchain for the PDF build steps. On
macOS: `brew install --cask mactex` (or `basictex`). On Debian/Ubuntu:
`apt install texlive-luatex texlive-latex-extra`. For the audit gate
install [veraPDF](https://verapdf.org).

## What changes are welcome

| Welcome | Discuss first |
|---|---|
| Bug fixes with a test that reproduces | Public API changes |
| New examples under `examples/` | New top-level directories |
| Documentation improvements / tutorials | Adding a heavy dependency |
| Additional LLM-judge backends | Changing the audit gate criteria |
| Performance work backed by benchmark deltas | Renaming an env var or CLI flag |
| Per-class tagged-PDF retrofit for new classes | LaTeX class layout overhaul |
| Per-format emit improvements | Switching the templating engine |

For "discuss first" items, open an issue before the PR. The strategy
tracker ([#14](https://github.com/sebastienrousseau/inclusio/issues/14))
is the best place to see what's already planned.

## Quality bar — what every PR must pass

Branch protection requires:

- **Lint (ruff)** — `ruff check .` and `ruff format --check` on
  `inclusio/` + the post-Sprint-4 tests.
- **Public Engine Checks (py3.11 / 3.12 / 3.13)** — full pytest
  matrix; coverage ≥ 97 %, docstrings = 100 %.
- **Signed-commit gate** — every commit in the PR must show as
  "Verified" by GitHub. See [SSH commit signing
  docs](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification#ssh-commit-signature-verification).

Strongly encouraged (will run on PR, won't gate):

- **veraPDF tagged-PDF audit** — when your change touches the
  build/post-process path.
- **LaTeX Excellence Pipeline** — when your change touches `.tex`,
  `.cls`, `.bib`, or any Makefile.
- **Hot-path benchmarks** — run `make benchmark` locally if your
  change touches `inclusio/judge/`, `inclusio/cli/render.py`, or
  `inclusio/emit/`.

## Commit style

Conventional Commits.

```
<type>(<scope>): <imperative-mood subject>

<body — what + why, not how>

<footer — Closes #N, Fixes #M>
```

| Type | Use for |
|---|---|
| `feat` | New capability |
| `fix` | Bug fix |
| `refactor` | Internal restructure with no behaviour change |
| `docs` | README / docs / docstrings |
| `test` | Test-only changes |
| `bench` | Benchmark-only changes |
| `chore` | Tooling, dependencies, release prep |
| `ci` | CI workflow / config |
| `build` | Build system / pip extras |
| `style` | Formatting only |

Sign your commits with SSH (preferred — same as inclusio itself) or
GPG. Unsigned commits fail the gate.

## Submitting a change

```bash
# Branch off main
git checkout -b feat/your-thing main

# Stage + commit + push
git commit -m "feat(scope): your imperative description"
git push -u origin feat/your-thing

# Open the PR
gh pr create --base main --head feat/your-thing
```

Before merging:

- [ ] All required checks green
- [ ] CHANGELOG entry added under `## [Unreleased]`
- [ ] Doc updates landed (if the change is user-visible)
- [ ] Example updated (if the change affects an `examples/` flow)

The maintainer squash-merges most PRs; if you want a different
strategy, say so in the PR description.

## Local testing recipes

```bash
# Run a single test
pytest tests/test_judge_ats.py -v

# Run the suite with coverage reporting (the gate)
make coverage

# Run only the benchmarks
make benchmark

# Build the docs (Sphinx) — needs the [dev] extras
make docs

# Run the EAA audit (needs veraPDF on PATH)
make audit-strict
```

## Code of conduct

This project follows the [Contributor
Covenant](https://www.contributor-covenant.org/). By participating
you agree to abide by its terms.

## License

Inclusio is MIT-licensed (see [`LICENSE`](./LICENSE)). By submitting
a contribution you agree it will be released under that licence.

## Getting help

- **Bugs / feature requests:** open an issue.
- **Strategy / roadmap:** see issue
  [#14](https://github.com/sebastienrousseau/inclusio/issues/14).
- **Security:** see [`SECURITY.md`](./SECURITY.md).
