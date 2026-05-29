# 05 — C2PA Content Credentials

Embed a [C2PA](https://c2pa.org/) manifest into a built PDF so
downstream readers (Adobe Acrobat, Photoshop, c2patool itself) can
verify the artefact's provenance.

**You'll learn:** how `inclusio provenance` shells out to
`c2patool`, what assertions the default manifest carries, and what
a verifier sees.

## Prereqs

- A registered document already built (run `examples/01-hello-world/
  make` first, or point at any PDF you have).
- `c2patool` on `PATH` — install from
  [contentauth/c2patool releases](https://github.com/contentauth/c2patool/releases).
- (Optional) A real X.509 cert + key pair for production signing.
  Without them, inclusio uses c2patool's test cert and flags the
  result.

## Sign with the test cert (development only)

```bash
make sign-test       # → build/hello.c2pa.pdf with a test-cert manifest
```

## Sign with a real cert

```bash
make sign \
  CERT=/path/to/signing-cert.pem \
  KEY=/path/to/signing-key.pem
```

## Verify

```bash
c2patool build/hello.c2pa.pdf   # walks the manifest
inclusio provenance --doc hello --verify   # via the engine
```

## What's in the manifest

```jsonc
{
  "claim_generator": "inclusio/0.0.3",
  "assertions": [
    {
      "label": "stds.schema-org.CreativeWork",
      "data": { "@type": "CreativeWork", "name": "...", ... }
    },
    { "label": "c2pa.actions",
      "data": { "actions": [{ "action": "c2pa.created" }] } },
    // If --ai-disclosure is set, an extra c2pa.training-mining
    // assertion declaring AI involvement.
  ]
}
```

The manifest is composed by `inclusio.provenance.c2pa.
build_manifest_json` — see the source for the full schema.
