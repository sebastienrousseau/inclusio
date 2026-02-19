# Usage

## Setup

```bash
./bin/setup
```

## Common Commands

```bash
make test
make coverage
make render
make sitemap
```

## Build Script

```bash
python3 scripts/build.py list
python3 scripts/build.py build --mode draft
python3 scripts/build.py render --doc cv --mode draft
python3 scripts/build.py sitemap --pretty
```

## Tailoring Note

British-English tailoring quality checks belong in `euxis-publisher-private` where real briefs and content live.
