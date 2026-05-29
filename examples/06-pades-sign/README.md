# 06 — PAdES eIDAS signature

Apply a PAdES (PDF Advanced Electronic Signature) signature to a
built PDF using the [`pyhanko`](https://pyhanko.readthedocs.io/)
library. Defaults to **B-T** — basic + RFC 3161 trusted timestamp —
which is the eIDAS-aligned baseline accepted across EU regulated
sectors.

**You'll learn:** the four PAdES baselines (B-B, B-T, B-LT, B-LTA),
when to pick each, and how `inclusio` produces them.

## Prereqs

- `inclusio[provenance]`: `pip install 'inclusio[provenance]'`
- A signing certificate + private key (PEM or DER). Generate a
  dev cert in 30 s:

  ```bash
  openssl req -x509 -newkey rsa:4096 \
    -keyout key.pem -out cert.pem \
    -days 365 -nodes -subj '/CN=Inclusio Dev'
  ```

- A timestamp authority URL for B-T / B-LT / B-LTA. Public TSAs:
  - `http://timestamp.digicert.com`
  - `http://timestamp.sectigo.com`

## Sign

```bash
make sign \
  CERT=cert.pem KEY=key.pem \
  TSA=http://timestamp.digicert.com
```

## Verify

```bash
make verify
```

## Baselines at a glance

| Baseline | Adds | When to pick |
|---|---|---|
| **B-B** | Signature + cert | Cheapest. Valid until cert expires. |
| **B-T** *(default)* | + Trusted timestamp | Survives cert expiration as long as the TSA is trusted. **Default.** |
| **B-LT** | + Revocation data (CRL/OCSP) embedded | Archival-grade. Verifier doesn't need internet. |
| **B-LTA** | + Document timestamp re-signing | True long-term archival. Required for some regulated sectors under eIDAS 2. |

## Production warning

`pyhanko` flags certs whose CN contains `test`, `sample`, `dev`,
`demo`, or `localhost` as test certificates. The `inclusio
provenance` CLI surfaces this with a `WARN:` line. **Never publish
a PDF signed with a test cert** — auditors and downstream verifiers
will refuse it.
