# Usage

## Setup

```bash
./bin/setup
```

Install the package in editable mode with dev dependencies. On Windows, run the
full TeX toolchain through WSL.

## Common Commands

```bash
make test
make coverage
make render
make sitemap
make publish CONTENT_DIR=/absolute/path/to/inclusio-private
```

Use `make publish` when you want one-step private output. It scans
`data/jobs/`, generates or refreshes tailored YAML for supported briefs, and
then builds the PDFs.

## Build Script

```bash
python3 -m inclusio.cli.build list
python3 -m inclusio.cli.build build --mode draft
python3 -m inclusio.cli.build render --doc cv --mode draft
python3 -m inclusio.cli.build sitemap --pretty
```

## Tailoring Note

British-English tailoring quality checks belong in `inclusio-private` where real briefs and content live.

Supported brief formats for automatic tailoring: `.txt`, `.md`, `.markdown`,
`.rtf`, `.doc`, `.docx`, `.odt`, and `.html`.

## Publishing With Private Content

Use one of the following patterns:

```bash
# Shell-agnostic and recommended
make publish CONTENT_DIR=/absolute/path/to/inclusio-private

# Bash / Zsh / POSIX sh
INCLUSIO_CONTENT_DIR=/absolute/path/to/inclusio-private make publish

# fish
env INCLUSIO_CONTENT_DIR=/absolute/path/to/inclusio-private make publish

# PowerShell
$env:INCLUSIO_CONTENT_DIR = "/absolute/path/to/inclusio-private"
make publish
```

`EUXIS_PUBLISHER_CONTENT_DIR` is not a supported variable name.

Use `make tailor BRIEF=data/jobs/job.txt` when you want to regenerate one brief
explicitly. Use `make publish` when you want the engine to process every
supported brief in `data/jobs/`.
