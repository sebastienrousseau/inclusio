.PHONY: all build audit clean help

PYTHON ?= python3
BUILD := $(PYTHON) -m inclusio.cli.build --content-dir $(CURDIR)

all: build audit ## Build + audit (default)

build: ## Compile src/hello.tex to build/hello.pdf
	$(BUILD) build --mode draft

audit: ## Run veraPDF over build/*.pdf
	$(BUILD) audit --strict || true

clean: ## Remove build/
	rm -rf build

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
