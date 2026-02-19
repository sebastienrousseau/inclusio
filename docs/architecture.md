# Architecture

`euxis-publisher` is the public engine layer of the Euxis publishing stack.

## Goals

- Provide reusable LaTeX classes and style packages.
- Provide deterministic build/render/sitemap tooling.
- Keep private content and sensitive templates out of the public repository.

## Repository Layout

- `core/cls/` - document classes (`pub-*`)
- `core/sty/` - shared style system packages
- `scripts/` - build/render/tailor/sitemap automation
- `tests/` - public engine validation tests
- `.github/workflows/` - CI checks

## Design Principles

- Engine-content separation: logic in public repo, proprietary content in private repo.
- Stable semantic interfaces: macro contract enforced by tests.
- Build-mode lifecycle: draft/submission/final behavior controlled centrally.
- Cross-platform consistency: deterministic scripts and CI checks.
