###############################################################################
# Root Makefile for Euxis Publisher — Thin wrapper around scripts/build.py
###############################################################################

SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON := python3
BUILD  := $(PYTHON) scripts/build.py

# External content directory (set via EUXIS_CONTENT_DIR env var)
CONTENT_DIR ?= $(EUXIS_CONTENT_DIR)
ifneq ($(CONTENT_DIR),)
  BUILD += --content-dir $(CONTENT_DIR)
  export EUXIS_CONTENT_DIR := $(CONTENT_DIR)
endif

###############################################################################
# Build Targets
###############################################################################

.PHONY: all draft submission final publish assets lint fix render render-md blog tailor sitemap docs setup clean clean-build distclean test coverage validate validate-private list help

all: draft ## Build all documents in draft mode (default)

draft: ## Build all documents in draft mode
	$(BUILD) build --mode draft

submission: ## Build all documents in submission mode
	$(BUILD) build --mode submission

final: ## Build all documents in camera-ready mode (PDF/A-2b)
	$(BUILD) build --mode camera-ready

publish: ## Camera-ready build using external content dir (requires EUXIS_CONTENT_DIR)
ifeq ($(CONTENT_DIR),)
	@echo "ERROR: publish requires EUXIS_CONTENT_DIR or CONTENT_DIR=<path>"
	@exit 1
endif
	$(BUILD) build --mode camera-ready

assets: ## Run asset pipeline (MMD → SVG → PDF/PNG)
	bash scripts/asset-pipeline.sh

lint: ## Run quality checks (semantic, chktex, vale)
	$(BUILD) lint

fix: ## Auto-fix semantic violations in src/
	$(PYTHON) scripts/fix-semantic.py src/

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

coverage: ## Measure Python logic coverage (>=95% required)
	COVERAGE_FILE=/tmp/euxis-publisher.coverage $(PYTHON) -m pytest --cov=scripts --cov-report=term-missing --cov-fail-under=95 tests/

validate: ## Run full local validation (tests, coverage, docs)
	$(MAKE) test PYTHON=$(PYTHON)
	$(MAKE) coverage PYTHON=$(PYTHON)
	$(MAKE) docs PYTHON=$(PYTHON)

validate-private: ## Reminder: run content + British-English validation in private repo
	@echo "Run private validations in ../euxis-publisher-private"
	@echo "Example: python3 ../euxis-publisher/scripts/tailor.py data/jobs/brief.txt --type cv --id be-check --no-ai"

list: ## List all registered documents
	$(BUILD) list

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'
