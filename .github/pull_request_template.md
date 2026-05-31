<!--
  Thanks for the PR. Keep this template; replace the comments.
  See CONTRIBUTING.md for the full contribution flow.
-->

## Summary

<!-- 2-3 sentences: what changed and why. -->

## Changes

<!-- Bulleted, concrete. Highlight any public-API surface change. -->

## Local validation

| Gate | Result |
|---|---|
| `make test` | <!-- e.g. 9 passed, 1 skipped --> |
| `make coverage` | <!-- 9?.??% --> |
| `make docstrings` | <!-- 100% (X/X) --> |
| `ruff check` + `format --check` | <!-- All checks passed --> |

## Test plan

- [ ] Engine Validation green on 3.11 / 3.12 / 3.13
- [ ] Signed-commit gate green (every commit ED25519-signed)
- [ ] CHANGELOG entry added under `## [Unreleased]` (if user-visible)
- [ ] Documentation updated (if behaviour or surface changed)

## Linked issues

<!-- "Closes #N" / "Refs #M". Required for non-trivial changes. -->
