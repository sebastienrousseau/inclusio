.PHONY: sign sign-test verify clean help

PYTHON ?= python3
INCLUSIO := $(PYTHON) -m inclusio.cli.build --content-dir $(CURDIR)

PDF_IN  ?= ../01-hello-world/build/hello.pdf
PDF_OUT ?= build/hello.c2pa.pdf

sign-test: ## Sign with c2patool's bundled test cert (dev only)
	@mkdir -p build
	$(INCLUSIO) provenance --doc hello --output $(PDF_OUT)

sign: ## Sign with --cert / --key (production)
	@test -n "$(CERT)" && test -n "$(KEY)" || { \
	  echo "Usage: make sign CERT=/path/to/cert.pem KEY=/path/to/key.pem"; exit 2; }
	@mkdir -p build
	$(INCLUSIO) provenance --doc hello \
	  --cert $(CERT) --key $(KEY) \
	  --output $(PDF_OUT)

verify: ## Verify the embedded manifest
	$(INCLUSIO) provenance --doc hello --verify

clean: ## Remove build/
	rm -rf build

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
