.PHONY: sign verify clean help

PYTHON ?= python3

PDF_IN ?= ../01-hello-world/build/hello.pdf
PDF_OUT ?= build/hello.pades.pdf

BASELINE ?= B-T

sign: ## Sign PDF_IN → PDF_OUT (set CERT, KEY, TSA)
	@test -n "$(CERT)" && test -n "$(KEY)" && test -n "$(TSA)" || { \
	  echo "Usage: make sign CERT=cert.pem KEY=key.pem TSA=https://..."; \
	  exit 2; }
	@mkdir -p build
	$(PYTHON) -c "from inclusio.provenance.pades import sign_pdf; \
	  import pathlib; \
	  r = sign_pdf( \
	    pdf_path=pathlib.Path('$(PDF_IN)'), \
	    output_path=pathlib.Path('$(PDF_OUT)'), \
	    cert_path=pathlib.Path('$(CERT)'), \
	    key_path=pathlib.Path('$(KEY)'), \
	    baseline='$(BASELINE)', \
	    timestamp_url='$(TSA)'); \
	  print(f'  signed {r.pdf_path} (baseline={r.baseline}, test_cert={r.signed_with_test_cert})')"

verify: ## Verify embedded signature
	$(PYTHON) -c "from inclusio.provenance.pades import verify_pdf; \
	  import pathlib, json; \
	  print(json.dumps(verify_pdf(pathlib.Path('$(PDF_OUT)')), indent=2))"

clean: ## Remove build/
	rm -rf build

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
