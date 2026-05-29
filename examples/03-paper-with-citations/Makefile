.PHONY: all build emit audit citations clean help

PYTHON ?= python3
INCLUSIO := $(PYTHON) -m inclusio.cli.build --content-dir $(CURDIR)

all: build emit audit citations ## Full pipeline (default)

build: ## Compile src/paper.tex → build/paper.pdf
	$(INCLUSIO) build --doc paper --mode draft

emit: ## Emit HTML5 + JATS XML + EPUB3
	$(INCLUSIO) emit --doc paper --formats html,jats,epub

audit: ## veraPDF audit
	$(INCLUSIO) audit --strict || true

citations: ## Citation-grounding judge
	$(INCLUSIO) judge --doc paper --judge citations

clean: ## Remove build/
	rm -rf build

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
