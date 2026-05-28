# Provenance + signing — `euxis_publisher.provenance`

Sprint 8 closes [Forcing Function #7](strategy-2026.md) on the artefact
side. The engine already ships **SLSA L3 build provenance** for the
wheel + sdist via `actions/attest-build-provenance` (see
`.github/workflows/release.yml`); Sprint 8 adds the per-PDF signal:

| Layer | Status | What it proves |
|---|---|---|
| SLSA L3 build provenance | ✅ shipped (S4) | Wheel + sdist were built by *this* GitHub workflow from *this* commit. |
| **C2PA Content Credentials** | ✅ **shipped (S8)** | Per-PDF chain of custody: who, when, with which tools, AI disclosure. |
| **PAdES signature (eIDAS)** | ✅ **shipped (S8.5)** | Cryptographic signature over the PDF for legal admissibility in EU jurisdictions. B-B / B-T / B-LT / B-LTA baselines via pyhanko. |

## C2PA — `euxis_publisher.provenance.c2pa`

### Install `c2patool`

The engine wraps the [`c2patool` reference implementation](https://github.com/contentauth/c2patool)
as a subprocess (same pattern as the Pandoc emitters). Install the
static binary:

```bash
# macOS
brew install c2patool  # or: cargo install c2patool

# Debian / Ubuntu
curl -L -o c2patool.tar.gz \
  https://github.com/contentauth/c2patool/releases/latest/download/c2patool-linux-x86_64.tar.gz
tar xf c2patool.tar.gz && sudo mv c2patool /usr/local/bin/
```

### CLI

```bash
# Embed a C2PA manifest in a registered document
python -m euxis_publisher.cli.build provenance --doc whisper-paper

# Production: sign with your own cert + key
python -m euxis_publisher.cli.build provenance \
    --doc whisper-paper \
    --cert /path/to/cert.pem \
    --key  /path/to/key.pem \
    --strict     # exit 1 if test-cert fallback was used
```

The output PDF lands at `build/<type>/<doc-stem>.c2pa.pdf`. The
original PDF is preserved.

### Python API

```python
from euxis_publisher.provenance.c2pa import build_manifest_json, embed_manifest
from pathlib import Path

manifest = build_manifest_json(
    title="Whisper Paper",
    author="Sebastien Rousseau",
    publisher="Euxis Publisher",
    date_published="2026-05-28",
    ai_disclosure="Drafted by Llama 3 8B; author edited.",
)

result = embed_manifest(
    pdf_path=Path("build/papers/whisper.pdf"),
    manifest_json=manifest,
    cert_path=Path("certs/euxis-prod.crt"),
    key_path=Path("certs/euxis-prod.key"),
)
print(result.pdf_path, result.manifest_bytes, "bytes")
```

### Manifest shape

The minimal manifest the engine emits:

```json
{
  "claim_generator": "euxis-publisher/0.1.0",
  "title": "Whisper Paper",
  "format": "application/pdf",
  "assertions": [
    {
      "label": "stds.schema-org.CreativeWork",
      "data": {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": "Whisper Paper",
        "author": [{"@type": "Person", "name": "Sebastien Rousseau"}],
        "publisher": {"@type": "Organization", "name": "Euxis Publisher"},
        "datePublished": "2026-05-28"
      }
    },
    {
      "label": "c2pa.actions",
      "data": {"actions": [{"action": "c2pa.created"}]}
    },
    {
      "label": "c2pa.training-mining",
      "data": {
        "entries": {
          "c2pa.ai_inference": {"use": "notAllowed"},
          "c2pa.ai_training":  {"use": "notAllowed"}
        },
        "disclosure": "Drafted by Llama 3 8B; author edited."
      }
    }
  ]
}
```

Callers can add their own assertions via the `extra_assertions=`
parameter — e.g. a Crossref DOI, an arXiv id, or an ORCID identifier.

### Verification

```bash
# Inspect the embedded manifest
c2patool --detailed build/papers/whisper.c2pa.pdf

# Or via the Python API
from euxis_publisher.provenance.c2pa import verify_manifest
verify_manifest(Path("build/papers/whisper.c2pa.pdf"))
# → {"active_manifest": "...", "manifests": {...}}
```

### Why shell out

[`c2pa-python`](https://pypi.org/project/c2pa/) exists but ships a
12 MB native wheel. The engine aims to stay air-gap deployable
without binary Python deps — `c2patool` is a single static binary
that the operator can install at their own pace.

## PAdES — `euxis_publisher.provenance.pades` (Sprint 8.5)

eIDAS-aligned PDF signature for legal admissibility in EU
jurisdictions (Regulation EU 910/2014 + ETSI EN 319 142). Wraps
[`pyhanko`](https://pyhanko.readthedocs.io/) as an optional
`[provenance]` extra.

### Install

```bash
pip install 'euxis-publisher[provenance]'   # adds pyhanko>=0.22
```

### Baselines

| Baseline | What it includes | Use when |
|---|---|---|
| `B-B` | Signature + signer cert | Quick proof-of-author |
| `B-T` (default) | B-B + RFC 3161 trusted timestamp | Survives cert expiration; tier-1 publications |
| `B-LT` | B-T + revocation data (CRL/OCSP) | Long-term archival |
| `B-LTA` | B-LT + document timestamp re-signing | Decades-long archival; legal records |

### Python API

```python
from pathlib import Path
from euxis_publisher.provenance.pades import sign_pdf

result = sign_pdf(
    pdf_path=Path("build/papers/whisper.pdf"),
    cert_path=Path("certs/euxis-prod.crt"),
    key_path=Path("certs/euxis-prod.key"),
    baseline="B-T",
    timestamp_url="http://timestamp.digicert.com",
    reason="Camera-ready publication",
    location="London, UK",
)
print(result.pdf_path, result.baseline, result.signed_with_test_cert)
```

### Verify

```python
from euxis_publisher.provenance.pades import verify_pdf
status = verify_pdf(Path("build/papers/whisper.pades.pdf"))
print(status["intact"], status["valid"], status["trusted"])
```

### Generating a development cert

```bash
openssl req -x509 -newkey rsa:4096 -days 365 -nodes \
    -keyout key.pem -out cert.pem \
    -subj "/CN=Euxis Dev/O=Acme/C=GB"
```

The wrapper sets `signed_with_test_cert: true` when the CN contains
`test`, `sample`, `dev`, `demo`, or `localhost` — so CI gates with
`--strict` refuse to publish a dev-signed artefact.

## Reference

- [C2PA spec 2.0](https://c2pa.org/specifications/specifications/2.0/index.html)
- [c2patool docs](https://github.com/contentauth/c2patool)
- [eIDAS / PAdES](https://www.iso.org/standard/76376.html)
