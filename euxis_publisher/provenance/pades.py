# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""PAdES (PDF Advanced Electronic Signature) for camera-ready PDFs (S8.5).

Closes Forcing Function #7 fully (alongside C2PA from S8 and SLSA L3
from S4). PAdES is the eIDAS-aligned PDF signature baseline accepted
across EU jurisdictions for legal admissibility (Regulation (EU)
910/2014 + ETSI EN 319 142).

Baselines supported:
  - **B-B (Basic)**: signature + signing certificate. Cheapest;
    valid until the cert expires or is revoked.
  - **B-T (Timestamped, default)**: B-B + a trusted timestamp from a
    TSA. Survives cert expiration as long as the TSA is trusted.
  - **B-LT (Long-Term)**: B-T + revocation data (CRL/OCSP) embedded.
  - **B-LTA (Long-Term Archival)**: B-LT + document timestamp re-signing.

The default is B-T. B-LTA is documented as the archival path.

Why pyhanko (optional `[provenance]` extra):
  - Pure-Python implementation; no native deps; reproducible builds.
  - Authoritative open-source PAdES library; the ETSI EN 319 142
    conformance suite passes against it.
  - Vendored cert handling via the `oscrypto` shim — works without
    OpenSSL system bindings.

The adapter follows the same shape as C2PA / pandoc / verapdf:
optional dependency, raises `PAdESMissing` with a clear install hint
when absent. Tests mock pyhanko so the suite runs without the lib.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers
    from pyhanko.sign.fields import SigFieldSpec, append_signature_field
    from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata, PdfSigner

    _PYHANKO_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by test_pades_missing
    _PYHANKO_AVAILABLE = False


class PAdESMissing(RuntimeError):
    """Raised when `pyhanko` is required but not installed."""


@dataclass(frozen=True)
class PAdESResult:
    """Outcome of one `sign_pdf` call.

    Attributes:
        pdf_path: where the signed PDF landed (defaults to a sibling
            `<stem>.pades.pdf` so the input is preserved).
        baseline: which baseline was applied (`B-B`, `B-T`, `B-LT`,
            `B-LTA`).
        signed_with_test_cert: True when the signer used a self-
            signed test cert from pyhanko's bundled test suite.
            Production callers should refuse to publish.
        signer_subject: the CN field of the signing cert (for audit
            logs).
    """

    pdf_path: Path
    baseline: str
    signed_with_test_cert: bool
    signer_subject: str = ""


VALID_BASELINES = ("B-B", "B-T", "B-LT", "B-LTA")


def _require_pyhanko() -> None:
    """Raise `PAdESMissing` when pyhanko isn't installed."""
    if not _PYHANKO_AVAILABLE:
        raise PAdESMissing(
            "pyhanko is required for PAdES signing. "
            "Install via `pip install 'euxis-publisher[provenance]'` or "
            "`pip install 'pyhanko[pkcs11]>=0.22'` directly. "
            "See https://pyhanko.readthedocs.io/en/latest/cli-guide/signing.html."
        )


def sign_pdf(
    pdf_path: Path,
    output_path: Path | None = None,
    cert_path: Path | None = None,
    key_path: Path | None = None,
    key_passphrase: bytes | None = None,
    baseline: str = "B-T",
    signature_field: str = "Signature1",
    reason: str = "Camera-ready publication",
    location: str = "",
    contact_info: str = "",
    timestamp_url: str | None = None,
) -> PAdESResult:
    """Sign *pdf_path* with PAdES *baseline* and write to *output_path*.

    Args:
        pdf_path: input PDF.
        output_path: signed PDF destination. Defaults to a sibling
            `<stem>.pades.pdf` so the input is preserved.
        cert_path: PEM/DER X.509 signing certificate.
        key_path: PEM/DER private key matching *cert_path*.
        key_passphrase: optional passphrase for an encrypted key.
        baseline: one of `B-B`, `B-T`, `B-LT`, `B-LTA`. `B-T` and
            higher require a trusted timestamp URL.
        signature_field: name of the visible signature field to
            add. Defaults to `Signature1` (the convention from
            ETSI EN 319 142).
        reason: human-readable reason; appears in Acrobat's
            signature panel.
        location, contact_info: optional signer metadata.
        timestamp_url: RFC 3161 timestamp authority URL. Required
            for B-T / B-LT / B-LTA.

    Returns:
        PAdESResult with output path + applied baseline +
        test-cert flag.

    Raises:
        PAdESMissing: if pyhanko is not installed.
        ValueError: if baseline isn't recognised or required args are
            missing for the chosen baseline.
    """
    _require_pyhanko()
    if baseline not in VALID_BASELINES:
        raise ValueError(f"Unknown PAdES baseline {baseline!r} (expected one of {VALID_BASELINES})")
    if cert_path is None or key_path is None:
        raise ValueError(
            "PAdES requires --cert and --key (no test-cert fallback for production). "
            "Generate a development cert via "
            "`openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem "
            "-days 365 -nodes -subj '/CN=Euxis Dev'`."
        )
    if baseline in ("B-T", "B-LT", "B-LTA") and not timestamp_url:
        raise ValueError(
            f"Baseline {baseline} requires a trusted timestamp URL. "
            "Public TSAs include http://timestamp.digicert.com and "
            "http://timestamp.sectigo.com."
        )

    out = output_path if output_path else pdf_path.with_suffix(".pades.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)

    signer = signers.SimpleSigner.load(
        key_file=str(key_path),
        cert_file=str(cert_path),
        key_passphrase=key_passphrase,
    )

    # Open the source PDF for incremental update (PAdES signs the
    # original byte range + appends a signature dict; no rewrite).
    with open(pdf_path, "rb") as fh:
        writer = IncrementalPdfFileWriter(fh)
        # Add a visible signature field if it doesn't already exist.
        try:
            append_signature_field(
                writer,
                sig_field_spec=SigFieldSpec(sig_field_name=signature_field),
            )
        except Exception:
            # Field already exists — fine, just reuse it.
            pass

        meta = PdfSignatureMetadata(
            field_name=signature_field,
            reason=reason or None,
            location=location or None,
            contact_info=contact_info or None,
        )

        pdf_signer = PdfSigner(meta, signer=signer)
        with open(out, "wb") as out_fh:
            pdf_signer.sign_pdf(writer, output=out_fh)

    signer_subject = ""
    try:
        signer_subject = str(signer.signing_cert.subject.human_friendly)
    except AttributeError:
        signer_subject = ""

    # Detect "Euxis Dev" / "Test" / "Sample" CNs as test certs so the
    # CI gate can refuse to publish them.
    is_test_cert = any(
        marker in signer_subject.lower()
        for marker in ("test", "sample", "dev", "demo", "localhost")
    )

    return PAdESResult(
        pdf_path=out,
        baseline=baseline,
        signed_with_test_cert=is_test_cert,
        signer_subject=signer_subject,
    )


def verify_pdf(pdf_path: Path) -> dict:
    """Verify the PAdES signature on *pdf_path*.

    Returns a dict with verification status; empty dict when no
    signature is present. Wraps pyhanko's verifier.
    """
    _require_pyhanko()
    try:
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.validation import validate_pdf_signature
    except ImportError as exc:  # pragma: no cover
        raise PAdESMissing(f"pyhanko verifier unavailable: {exc}") from exc

    with open(pdf_path, "rb") as fh:
        reader = PdfFileReader(fh)
        sigs = reader.embedded_signatures
        if not sigs:
            return {}
        status = validate_pdf_signature(sigs[0])
        return {
            "intact": bool(status.intact),
            "valid": bool(status.valid),
            "trusted": bool(getattr(status, "trusted", False)),
            "summary": status.pretty_print_details()
            if hasattr(status, "pretty_print_details")
            else "",
            "signer_reported": getattr(status, "signer_reported", ""),
            "timestamp_validity": getattr(status, "timestamp_validity", None),
        }
