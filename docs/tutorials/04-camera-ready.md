# Tutorial 4 — Camera-ready chain (C2PA + PAdES + SLSA)

> 30 minutes · Difficulty: medium-hard · Examples:
> [`05-c2pa-sign/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/05-c2pa-sign/),
> [`06-pades-sign/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/06-pades-sign/)

By the end of this tutorial you'll have a PDF carrying three
independent provenance layers — C2PA Content Credentials, a PAdES
B-T eIDAS signature, and a SLSA L3 build attestation — and you'll
understand when to use each.

## Why three layers

The three layers answer different questions:

| Layer | Question it answers | Verifier needs |
|---|---|---|
| **C2PA** | What is this artefact + who made it + with what tools? | C2PA-aware reader (Acrobat, Photoshop, Bing, `c2patool`) |
| **PAdES** | Is the signer who they claim, was the PDF unchanged since signing? | Adobe Acrobat or any PAdES-aware verifier |
| **SLSA** | Was this artefact built by a trusted pipeline? | `gh attestation verify` or any SLSA verifier |

The three are complementary. C2PA tells a journalist "this was created
by an Inclusio pipeline on the named author's machine". PAdES tells
a court "this signer was authenticated by a recognised CA and the
file is intact". SLSA tells a procurement officer "this binary came
from a GitHub Actions workflow I can audit".

> **2026 regulatory context:** PAdES B-LTA is mandatory under eIDAS 2
> for qualified e-signatures in EU finance, health, and public-
> procurement archival. SLSA L3 will be required by the EU CRA from
> Dec 2027 for "important" products. Plan accordingly.

## Prereqs

- `inclusio[provenance]`: `pip install 'inclusio[provenance]'`
- `c2patool` on PATH — install from
  [contentauth/c2patool releases](https://github.com/contentauth/c2patool/releases).
- A signing certificate + private key (PEM/DER). A dev pair:

  ```bash
  openssl req -x509 -newkey rsa:4096 \
    -keyout key.pem -out cert.pem \
    -days 365 -nodes -subj '/CN=Inclusio Tutorial'
  ```

## Step 1 — Start with a tagged PDF

You need a built PDF before you can sign it. Reuse
[Tutorial 1](./01-tagged-pdf.md)'s output, or build any registered
document:

```bash
cd examples/01-hello-world && make
```

You should have `build/hello.pdf`.

## Step 2 — Embed C2PA Content Credentials

```bash
inclusio provenance --doc hello \
  --cert /path/to/cert.pem \
  --key  /path/to/key.pem \
  --output build/hello.c2pa.pdf
```

The default manifest contains:

```json
{
  "claim_generator": "inclusio/0.0.3",
  "assertions": [
    {
      "label": "stds.schema-org.CreativeWork",
      "data": {
        "@type": "CreativeWork",
        "name": "Hello, tagged PDF",
        "author": [{"@type": "Person", "name": "Example Author"}],
        "publisher": {"@type": "Organization",
                      "name": "Inclusio Examples"}
      }
    },
    { "label": "c2pa.actions",
      "data": { "actions": [{"action": "c2pa.created"}] } }
  ]
}
```

If you set `--ai-disclosure ai-edits-only`, a third
`c2pa.training-mining` assertion is added — the STM Sept-2025
classification.

**Test-cert warning:** if your cert's CN contains `test`, `sample`,
`dev`, `demo`, or `localhost`, inclusio flags the result with a
`WARN:` line and the CLI exits 0 only without `--strict`. Never
publish a C2PA-signed PDF with a dev cert; verifiers will refuse it.

Verify:

```bash
c2patool build/hello.c2pa.pdf
```

You'll see the walk of the manifest, including the schema.org
assertion and the c2pa.actions chain.

## Step 3 — Add a PAdES B-T signature

PAdES is layered ON TOP of C2PA. The order is significant —
sign-last is the convention so the signature covers the C2PA
manifest too.

```bash
python3 -c "
from inclusio.provenance.pades import sign_pdf
from pathlib import Path

result = sign_pdf(
    pdf_path     = Path('build/hello.c2pa.pdf'),
    output_path  = Path('build/hello.signed.pdf'),
    cert_path    = Path('cert.pem'),
    key_path     = Path('key.pem'),
    baseline     = 'B-T',                                   # default
    timestamp_url= 'http://timestamp.digicert.com',         # public TSA
    reason       = 'Camera-ready publication',
    location     = 'London',
)
print(f'  signed: {result.pdf_path}')
print(f'  baseline: {result.baseline}')
print(f'  test cert: {result.signed_with_test_cert}')
print(f'  signer: {result.signer_subject}')
"
```

## Step 4 — Verify the PAdES signature

```bash
python3 -c "
from inclusio.provenance.pades import verify_pdf
from pathlib import Path
import json
print(json.dumps(verify_pdf(Path('build/hello.signed.pdf')), indent=2))
"
```

You should see `"intact": true` and `"valid": true`. `"trusted"`
depends on whether your verifier knows your CA — for a self-signed
dev cert this is False; for a CA-issued cert it should be True.

## Step 5 — Pick the right PAdES baseline

| Baseline | Adds | When to use |
|---|---|---|
| **B-B** | Signature + signing cert | Cheapest. Valid until cert expires. |
| **B-T** *(default)* | + RFC 3161 timestamp | Survives cert expiration. **Default.** |
| **B-LT** | + Revocation data (CRL/OCSP) | Archival; verifier doesn't need internet. |
| **B-LTA** | + Document timestamp re-signing | True long-term archival. eIDAS 2 requirement. |

For research papers + reports — **B-T**. For legal contracts +
regulated-sector archival — **B-LTA**.

## Step 6 — SLSA L3 build provenance (CI)

SLSA attestation happens at *build* time, not sign time. The engine's
Release workflow already produces SLSA L3 attestations via
[`actions/attest-build-provenance`](
https://github.com/actions/attest-build-provenance) when the repo
variable `SLSA_ATTESTATION_ENABLED=true` is set.

After a tagged release, verify with:

```bash
gh attestation verify dist/inclusio-0.0.3-py3-none-any.whl \
  --repo sebastienrousseau/inclusio
```

You'll see the signed in-toto attestation linking the artefact to
the workflow run, commit SHA, and runner identity.

## The complete chain — what verifiers see

```
hello.signed.pdf
├── C2PA manifest
│   ├── stds.schema-org.CreativeWork  (author, publisher, name)
│   ├── c2pa.actions                  (created)
│   └── [c2pa.training-mining]        (AI disclosure if set)
├── PAdES B-T signature
│   ├── Signing certificate
│   ├── Signed byte range (covers PDF + C2PA manifest)
│   └── RFC 3161 timestamp from a trusted TSA
└── SLSA L3 attestation (separate file, not embedded)
    └── in-toto statement linking artefact ← workflow ← commit
```

A C2PA verifier reads `hello.signed.pdf` and shows the schema.org
assertion. Adobe Acrobat shows the PAdES signature in its Signature
Panel. `gh attestation verify` validates the SLSA chain.

## Common questions

**Can I sign without a real cert in CI?** No — never. Use a real CA
or an internal organisation CA. The test-cert flag exists exactly to
catch this slip in CI.

**Does C2PA's signing cert have to match the PAdES one?** No. C2PA
signs the manifest; PAdES signs the byte range. Different keys for
different purposes is acceptable (and common at large publishers).

**What if I only have one cert?** Use it for PAdES; skip the
`--cert/--key` on the C2PA step and accept the test-cert warning IF
the artefact is internal only. For external publication, get a
separate C2PA cert.

**How big does the signed PDF get?** A B-T signature adds ~30 KB.
B-LTA adds ~80 KB. The C2PA manifest adds ~5 KB. Negligible for most
documents.

## Next steps

- [`docs/provenance.md`](../provenance.md) — the full provenance
  reference, including the manifest schema and the verification
  algorithms.
- The [C2PA specification](https://spec.c2pa.org/) and
  [ETSI EN 319 142](https://www.etsi.org/standard/319142) for PAdES.
- [SLSA specification](https://slsa.dev/) for SLSA L3.
