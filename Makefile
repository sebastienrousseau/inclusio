###############################################################################
# Root Makefile for Publications — Thin wrapper around scripts/build.py
###############################################################################

SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON := python3
BUILD  := $(PYTHON) scripts/build.py

###############################################################################
# Build Targets
###############################################################################

.PHONY: all draft submission final assets lint fix render render-md blog tailor sitemap setup clean clean-build distclean test list help

all: draft ## Build all documents in draft mode (default)

draft: ## Build all documents in draft mode
	$(BUILD) build --mode draft

submission: ## Build all documents in submission mode
	$(BUILD) build --mode submission

final: ## Build all documents in camera-ready mode (PDF/A-2b)
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

blog: ## Render blog posts to Shokunin-compatible Markdown
	$(BUILD) blog

tailor: ## Generate tailored document from a brief
	@echo "Usage: make tailor BRIEF=data/jobs/job.txt [TYPE=cv] [ID=my-cv]"
	$(BUILD) tailor $(BRIEF) --type $(or $(TYPE),cv) $(if $(ID),--id $(ID)) --build

sitemap: ## Generate semantic search metadata (build/site-map.json)
	$(BUILD) sitemap --pretty

setup: ## Install dependencies (auto-detects nix/brew/apt)
	./bin/setup

clean: ## Remove build/ directory
	$(BUILD) clean

clean-build: ## Remove only build cache (keep final PDFs)
	rm -rf build/.cache/

distclean: ## Remove build output + dev artifacts (.coverage, .pytest_cache)
	$(BUILD) distclean

test: ## Run test suite
	$(PYTHON) -m pytest tests/ -v

list: ## List all registered documents
	$(BUILD) list

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
