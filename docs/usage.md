# Usage

## Setup

```bash
./bin/setup
```

This script installs the Python package in editable mode with dev
dependencies. On Windows, use WSL for the full TeX toolchain.

## Common Commands

```bash
make test
make coverage
make render
make sitemap
make publish CONTENT_DIR=/absolute/path/to/euxis-publisher-private
```

## Build Script

```bash
python3 -m euxis_publisher.cli.build list
python3 -m euxis_publisher.cli.build build --mode draft
python3 -m euxis_publisher.cli.build render --doc cv --mode draft
python3 -m euxis_publisher.cli.build sitemap --pretty
```

## Tailoring Note

British-English tailoring quality checks belong in `euxis-publisher-private` where real briefs and content live.

## Publishing With Private Content

Use one of the following patterns:

```bash
# Shell-agnostic and recommended
make publish CONTENT_DIR=/absolute/path/to/euxis-publisher-private

# Bash / Zsh / POSIX sh
EUXIS_CONTENT_DIR=/absolute/path/to/euxis-publisher-private make publish

# fish
env EUXIS_CONTENT_DIR=/absolute/path/to/euxis-publisher-private make publish

# PowerShell
$env:EUXIS_CONTENT_DIR = "/absolute/path/to/euxis-publisher-private"
make publish
```

`EUXIS_PUBLISHER_CONTENT_DIR` is not a supported variable name.
