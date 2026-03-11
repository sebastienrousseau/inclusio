# Euxis Publisher

Public publishing engine for the Euxis framework.

This repository intentionally contains the public engine plus generic
non-sensitive fixtures:
- LaTeX classes and styles (`core/`)
- packaged Python orchestration (`euxis_publisher/`)
- compatibility wrappers (`scripts/`)
- CI and tests for engine behavior
- public sample `data/`, `src/`, and `templates/` fixtures

Private documents and proprietary templates must live in `euxis-publisher-private`.

## Public vs Private Boundary

Public repo (`euxis-publisher`):
- `core/`
- `euxis_publisher/`
- `scripts/` (compatibility wrappers)
- `tests/` (engine-only)
- public non-sensitive fixtures in `data/`, `src/`, `templates/`
- `.github/`, `Makefile`, `flake.nix`, docs

Private repo (`euxis-publisher-private`):
- `data/`
- `src/`
- `templates/`
- content-bearing assets
- content validation tests (metadata schema, patent assets, British-English tailoring validation)

## Validation Status

- This repository does **not** claim 100% logic coverage by default.
- Measure coverage explicitly with:

```bash
make coverage
```

## British-English Tailoring Scope

British-English tailoring behavior is defined by `euxis_publisher/cli/tailor.py` prompt/config and should be validated in `euxis-publisher-private` where real content and briefs live.

Suggested private validation flow:

```bash
# in euxis-publisher-private
python3 -m euxis_publisher.cli.tailor data/jobs/brief.txt --type cv --id be-check --no-ai
python3 -m euxis_publisher.cli.build --content-dir . render --doc cv --mode final
```

## Macro Reference

- See `docs/macro-reference.md` for the canonical macro contract for prompts and templates.

## Documentation

- `docs/README.md`
- `docs/architecture.md`
- `docs/classes-and-styles.md`
- `docs/package-reference.md`
- `docs/macro-reference.md`
- `docs/usage.md`
- `docs/testing-and-ci.md`
- `docs/public-private-boundary.md`

## Folder Guides

- `bin/README.md`
- `core/README.md`
- `data/README.md`
- `euxis_publisher/README.md`
- `euxis_publisher/cli/README.md`
- `euxis_publisher/tools/README.md`
- `scripts/README.md`
- `src/README.md`
- `templates/README.md`
- `tests/README.md`

## Setup

```bash
./bin/setup
```

Install `tagpdf.sty` in TeX Live if you need accessibility tagging.

## Publish With Private Content

`make publish` reads content from the engine repo by default. To publish against
the private content repo, pass the real content path:

```bash
make publish CONTENT_DIR=/home/seb/Code/Private/TeX/euxis-publisher-private
```

Use this form across shells. It avoids shell-specific environment syntax.

Use the shell-specific form only if you need it:

```bash
# Bash / Zsh / POSIX sh
EUXIS_CONTENT_DIR=/home/seb/Code/Private/TeX/euxis-publisher-private make publish

# fish
env EUXIS_CONTENT_DIR=/home/seb/Code/Private/TeX/euxis-publisher-private make publish

# PowerShell
$env:EUXIS_CONTENT_DIR = "/home/seb/Code/Private/TeX/euxis-publisher-private"
make publish
```

## Quick Checks

```bash
# public engine tests
pytest -q tests/test_assets.py tests/test_build.py tests/test_engine_smoke.py

# full content validation runs in euxis-publisher-private
```
