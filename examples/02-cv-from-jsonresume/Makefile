.PHONY: all import render build audit ats jd-fit clean help

PYTHON ?= python3
INCLUSIO := $(PYTHON) -m inclusio.cli.build --content-dir $(CURDIR)

all: import build audit ats ## Full chain (default)

import: ## Convert resume.json → data/cv-data.yaml
	$(INCLUSIO) import-resume resume.json -o data/cv-data.yaml

build: import ## Render Jinja2 → LaTeX → PDF
	$(INCLUSIO) build --doc cv --mode draft

audit: ## veraPDF audit
	$(INCLUSIO) audit --strict || true

ats: ## ATS heuristic score
	$(INCLUSIO) judge --doc cv --judge ats

jd-fit: ## Score CV against brief.txt
	$(INCLUSIO) judge --doc cv --judge jd_fit --brief brief.txt

clean: ## Remove build/ + generated YAML
	rm -rf build data/cv-data.yaml

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
