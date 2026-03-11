# Testing And CI

## Local Test Targets

- `make test` runs public engine smoke/tests.
- `make coverage` runs full tests with strict coverage gate.

## Coverage Policy

`make coverage` enforces:

- `--cov=scripts`
- `--cov=euxis_publisher`
- `--cov-fail-under=95`

Coverage output is written with `COVERAGE_FILE=/tmp/euxis-publisher.coverage` to avoid local permission collisions.

## CI Workflow

`engine-validation.yml` runs:

1. Python setup
2. Python interpreter visibility step (`which` + `--version`)
3. dependency install
4. `./bin/setup`
5. `make test`
6. `make coverage`

## Macro Contract Guard

`tests/test_macro_contract.py` prevents accidental removal/rename of public LaTeX macro APIs used by templates and prompts.
