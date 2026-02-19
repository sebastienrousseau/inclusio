# Euxis Publisher

Public publishing engine for the Euxis framework.

This repository intentionally contains engine code only:
- LaTeX classes and styles (`core/`)
- build/render/sitemap orchestration (`scripts/`)
- CI and tests for engine behavior

Private documents and proprietary templates must live in `euxis-publisher-private`.

## Public vs Private Boundary

Public repo (`euxis-publisher`):
- `core/`
- `scripts/`
- `tests/` (engine-only)
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

British-English tailoring behavior is defined by `scripts/tailor.py` prompt/config and should be validated in `euxis-publisher-private` where real content and briefs live.

Suggested private validation flow:

```bash
# in euxis-publisher-private
python3 ../euxis-publisher/scripts/tailor.py data/jobs/brief.txt --type cv --id be-check --no-ai
python3 ../euxis-publisher/scripts/build.py --content-dir . render --doc cv --mode final
```

## Macro Reference

- See `docs/macro-reference.md` for the canonical macro contract for prompts and templates.

## Documentation

- `docs/README.md`
- `docs/architecture.md`
- `docs/classes-and-styles.md`
- `docs/macro-reference.md`
- `docs/usage.md`
- `docs/testing-and-ci.md`
- `docs/public-private-boundary.md`

## Setup

```bash
./bin/setup
```

For accessibility tagging support, ensure TeX Live provides `tagpdf.sty`.

## Quick Checks

```bash
# public engine tests
pytest -q tests/test_assets.py tests/test_build.py tests/test_engine_smoke.py

# full content validation runs in euxis-publisher-private
```
