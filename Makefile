###############################################################################
# Root Makefile for Euxis Publisher — Thin wrapper around the packaged build CLI
###############################################################################

.DEFAULT_GOAL := help

PYTHON := $(shell command -v mise >/dev/null 2>&1 && mise which python3 2>/dev/null || echo python3)
BUILD  := $(PYTHON) -m inclusio.cli.build

# External content directory (set via INCLUSIO_CONTENT_DIR env var)
CONTENT_DIR ?= $(INCLUSIO_CONTENT_DIR)
ifneq ($(CONTENT_DIR),)
  BUILD += --content-dir $(CONTENT_DIR)
  export INCLUSIO_CONTENT_DIR := $(CONTENT_DIR)
endif

###############################################################################
# Build Targets
###############################################################################

.PHONY: all draft submission final publish publish-jobs assets lint fix render render-md blog tailor sitemap audit audit-strict docs setup clean clean-build distclean test coverage benchmark docstrings validate validate-private list help

all: draft ## Build all documents in draft mode (default)

draft: ## Build all documents in draft mode
	$(BUILD) build --mode draft

submission: ## Build all documents in submission mode
	$(BUILD) build --mode submission

final: ## Build all documents in camera-ready mode (PDF/A-2b)
	$(BUILD) build --mode camera-ready

publish: ## Camera-ready build using external content dir (requires INCLUSIO_CONTENT_DIR)
ifeq ($(CONTENT_DIR),)
	@echo "ERROR: publish requires INCLUSIO_CONTENT_DIR or CONTENT_DIR=<path>"
	@exit 1
endif
	$(BUILD) build --mode camera-ready

publish-jobs: ## Camera-ready build for tailored/job documents only
ifeq ($(CONTENT_DIR),)
	@echo "ERROR: publish-jobs requires INCLUSIO_CONTENT_DIR or CONTENT_DIR=<path>"
	@exit 1
endif
	$(BUILD) build --mode camera-ready --jobs-only

assets: ## Run asset pipeline (MMD → SVG → PDF/PNG)
	bash scripts/asset-pipeline.sh

lint: ## Run quality checks (semantic, chktex, vale)
	$(BUILD) lint

fix: ## Auto-fix semantic violations in src/
	$(PYTHON) -m inclusio.tools.fix_semantic src/

render: ## Render Jinja2 templates to LaTeX
	$(BUILD) render

render-md: ## Render all templates to Markdown
	$(BUILD) render --format markdown

blog: ## Render blog posts to Markdown
	$(BUILD) blog

tailor: ## Generate tailored document from a brief
	@echo "Usage: make tailor BRIEF=data/jobs/job.txt [TYPE=cv] [ID=my-cv]"
	$(BUILD) tailor $(BRIEF) --type $(or $(TYPE),cv) $(if $(ID),--id $(ID)) --build

sitemap: ## Generate semantic search metadata (build/site-map.json)
	$(BUILD) sitemap --pretty

judge: ## Score a CV against the ATS judge — `make judge DOC=cv`
	@if [ -z "$(DOC)" ]; then echo "ERROR: make judge DOC=<cv-id>"; exit 2; fi
	$(BUILD) judge --doc $(DOC) --judge ats

emit: ## Emit HTML5 + JATS XML for every registered document (Sprint 6/7)
	$(BUILD) emit

emit-html: ## Emit HTML5 only
	$(BUILD) emit --formats html

emit-jats: ## Emit JATS XML only
	$(BUILD) emit --formats jats

audit: ## Run EAA / accessibility audit (veraPDF UA-2 + WTPDF + PDF/A-4f) on build/
	$(PYTHON) -m inclusio.cli.audit

audit-strict: ## Audit in CI-strict mode (non-zero exit on blocking FAIL/ERROR)
	$(PYTHON) -m inclusio.cli.audit --strict

docs: ## Build Sphinx documentation (HTML)
	@$(PYTHON) -c "import importlib.util,sys;mods=['sphinx','myst_parser','furo'];missing=[m for m in mods if importlib.util.find_spec(m) is None];print('Missing docs deps: ' + ', '.join(missing) + '. Install with: ' + '$(PYTHON) -m pip install --user sphinx myst-parser furo') if missing else None;sys.exit(1 if missing else 0)"
	$(PYTHON) -m sphinx -b html docs docs/_build/html

setup: ## Show dependency setup guidance
	./bin/setup

clean: ## Remove build/ directory
	$(BUILD) clean

clean-build: ## Remove only build cache (keep final PDFs)
	rm -rf build/.cache/

distclean: ## Remove build output + dev artifacts (.coverage, .pytest_cache)
	$(BUILD) distclean

test: ## Run public engine tests
	$(PYTHON) -m pytest -q tests/test_assets.py tests/test_build.py tests/test_engine_smoke.py tests/test_macro_contract.py

coverage: ## Measure Python logic coverage (>=97% required)
	COVERAGE_FILE=/tmp/inclusio.coverage $(PYTHON) -m pytest --cov=inclusio --cov-report=term-missing --cov-fail-under=97 tests/ --ignore=tests/test_pdf_validation.py

benchmark: ## Run hot-path micro-benchmarks (pytest-benchmark)
	$(PYTHON) -m pytest tests/test_benchmark_hot_paths.py --benchmark-only --benchmark-min-rounds=10 --benchmark-columns=min,mean,median,stddev,ops,rounds

docstrings: ## Verify 100% docstring coverage (interrogate)
	$(PYTHON) -m interrogate --fail-under=100 -v inclusio/

validate: ## Run full local validation (tests, coverage, docstrings, docs)
	$(MAKE) test PYTHON=$(PYTHON)
	$(MAKE) coverage PYTHON=$(PYTHON)
	$(MAKE) docstrings PYTHON=$(PYTHON)
	$(MAKE) docs PYTHON=$(PYTHON)

validate-private: ## Reminder: run content + British-English validation in private repo
	@echo "Run private validations in ../inclusio-private"
	@echo "Example: python3 -m inclusio.cli.tailor data/jobs/brief.txt --type cv --id be-check --no-ai"

list: ## List all registered documents
	$(BUILD) list

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'
