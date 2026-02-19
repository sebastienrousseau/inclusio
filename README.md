# Publications

A collection of LaTeX-based publications organized as 5 independent projects.

## Projects

| Project | Description |
|---------|-------------|
| [cvs/](cvs/) | Curriculum vitae with ATS-optimized multi-format output |
| [papers/](papers/) | Research papers and whitepapers |
| [patents/](patents/) | USPTO-compliant patent applications |
| [faqs/](faqs/) | Frequently asked questions documentation |
| [guides/](guides/) | User guides and documentation |

Each project is self-contained with its own build system, configuration, templates, scripts, and tests.

## Prerequisites

- TeX Live (pdflatex, bibtex, latexmk)
- Ghostscript (PDF optimization)
- Pandoc (multi-format conversion)
- Python 3 + pytest (testing)

## Quick Start

```bash
# Build everything
make all

# Build a single project
make -C cvs all
make -C papers all
make -C patents all

# Clean everything
make clean

# Run all tests
make test
```

## Repository Structure

```
Publications/
├── cvs/          # Independent CV project
├── papers/       # Independent papers project
├── patents/      # Independent patents project
├── faqs/         # Independent FAQs project
├── guides/       # Independent guides project
├── Makefile      # Thin orchestrator
├── build/        # Collected PDFs from all projects
└── .github/      # CI workflows
```

## Testing

Each project has its own test suite in `tests/`:

```bash
pytest cvs/tests/ -v
pytest papers/tests/ -v
pytest patents/tests/ -v
pytest faqs/tests/ -v
pytest guides/tests/ -v
```

Or run all tests at once:

```bash
make test
```
