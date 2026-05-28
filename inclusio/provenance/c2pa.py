# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""C2PA Content Credentials for the Euxis Publisher pipeline (S8.x).

C2PA (Coalition for Content Provenance and Authenticity) is the
industry-standard cryptographic chain-of-custody manifest for digital
artefacts. Adobe, Microsoft, Truepic, BBC, and the major model
vendors have shipped C2PA writers / readers since 2024-2025; PDF
support landed in C2PA 2.0 (early 2026) and is now the de-facto signal
for "this PDF wasn't tampered with after creation".

This module wraps the `c2patool` binary (Truepic's reference
implementation) as a subprocess — same pattern the Pandoc emitters
use. The wrapper:

  1. Builds a minimal C2PA manifest from a document's metadata
     (title, author, publisher, AI disclosure from F6, build
     provenance).
  2. Invokes `c2patool` to embed the manifest into the PDF.
  3. Optionally re-verifies an embedded manifest.

Why shell out instead of using `c2pa-python`:

  - `c2pa-python` pulls in a 12 MB native binary wheel; the engine
    aims to stay air-gap deployable without binary deps.
  - `c2patool` is a single static binary distributed by Truepic;
    can be installed system-wide or vendored alongside the engine.
  - The subprocess boundary makes the manifest payload easy to
    audit — we ship the JSON, the tool signs it; no opaque library
    state.

Production signing requires an X.509 cert + key. Without them,
`c2patool` uses its built-in test cert and emits a warning — fine
for development, NOT fine for camera-ready artefacts.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class C2PAMissing(RuntimeError):
    """Raised when `c2patool` is required but not installed on PATH."""


@dataclass(frozen=True)
class C2PAResult:
    """Outcome of one `embed_manifest` call.

    Attributes:
        pdf_path: where the signed PDF landed.
        manifest_bytes: size of the embedded manifest in bytes.
        signed_with_test_cert: True when `c2patool` fell back to its
            built-in test cert (no production cert was provided);
            signals that the artefact is NOT publication-ready.
        stderr: c2patool's stderr (warnings, version banner, etc).
    """

    pdf_path: Path
    manifest_bytes: int
    signed_with_test_cert: bool
    stderr: str = ""


# ── Tool resolution ────────────────────────────────────────────────────


def _require_c2patool() -> str:
    """Return the path to `c2patool`, or raise `C2PAMissing`."""
    path = shutil.which("c2patool")
    if not path:
        raise C2PAMissing(
            "c2patool is required for C2PA Content Credentials. "
            "Install from https://github.com/contentauth/c2patool/releases "
            "(single static binary) or via `cargo install c2patool` if you "
            "have a Rust toolchain."
        )
    return path


# ── Manifest builder ───────────────────────────────────────────────────


def build_manifest_json(
    title: str,
    author: str,
    publisher: str = "Euxis Publisher",
    claim_generator: str = "euxis-publisher",
    claim_generator_version: str = "0.1.0",
    date_published: str | None = None,
    ai_disclosure: str = "",
    extra_assertions: list[dict[str, Any]] | None = None,
) -> str:
    """Compose a minimal C2PA manifest JSON for a publisher PDF.

    Args:
        title: document title (`dc:title` equivalent).
        author: human-readable author name.
        publisher: organisation that produced the PDF.
        claim_generator / claim_generator_version: signal the tool
            chain. Recorded as `claim_generator: "<name>/<version>"`
            per C2PA convention.
        date_published: ISO-8601 date (e.g. `2026-05-28`). When None,
            the assertion is omitted so callers can leave timestamping
            to c2patool itself.
        ai_disclosure: free-text AI-disclosure label (matches the
            STM Sept-2025 classification — see S5.1's XMP field).
            When non-empty, embedded as a `c2pa.training-mining`
            assertion so downstream readers can surface it.
        extra_assertions: optional list of additional C2PA assertion
            dicts merged into the manifest's `assertions` array.

    Returns:
        Pretty-printed JSON string ready to write to a temp file
        and pass to `c2patool --manifest`.
    """
    assertions: list[dict[str, Any]] = [
        {
            "label": "stds.schema-org.CreativeWork",
            "data": {
                "@context": "https://schema.org",
                "@type": "CreativeWork",
                "name": title,
                "author": [{"@type": "Person", "name": author}],
                "publisher": {"@type": "Organization", "name": publisher},
                **({"datePublished": date_published} if date_published else {}),
            },
        },
        {
            "label": "c2pa.actions",
            "data": {"actions": [{"action": "c2pa.created"}]},
        },
    ]
    if ai_disclosure:
        assertions.append(
            {
                "label": "c2pa.training-mining",
                "data": {
                    "entries": {
                        "c2pa.ai_inference": {"use": "notAllowed"},
                        "c2pa.ai_training": {"use": "notAllowed"},
                    },
                    "disclosure": ai_disclosure,
                },
            }
        )
    if extra_assertions:
        assertions.extend(extra_assertions)

    manifest = {
        "claim_generator": f"{claim_generator}/{claim_generator_version}",
        "title": title,
        "format": "application/pdf",
        "assertions": assertions,
    }
    return json.dumps(manifest, indent=2)


# ── Embed / verify ─────────────────────────────────────────────────────


def embed_manifest(
    pdf_path: Path,
    manifest_json: str,
    output_path: Path | None = None,
    cert_path: Path | None = None,
    key_path: Path | None = None,
    timeout: int = 120,
) -> C2PAResult:
    """Embed *manifest_json* into *pdf_path* via `c2patool`.

    Args:
        pdf_path: input PDF.
        manifest_json: manifest body as JSON string (output of
            `build_manifest_json`). Written to a temp file alongside
            the PDF and passed via `c2patool --manifest`.
        output_path: where the signed PDF goes. Defaults to a
            sibling `<stem>.c2pa.pdf` so the input is preserved.
        cert_path / key_path: PEM-encoded X.509 cert + private key.
            When None, `c2patool` falls back to its built-in test
            cert; the result's `signed_with_test_cert` flag is set
            so callers can refuse to publish.
        timeout: subprocess timeout in seconds. 120 is the default
            because PDF re-serialisation on a large doc is not free.

    Returns:
        C2PAResult with the signed PDF path + manifest size +
        test-cert flag.

    Raises:
        C2PAMissing: if `c2patool` is not installed.
        subprocess.CalledProcessError: if c2patool fails.
    """
    tool = _require_c2patool()
    out = output_path if output_path else pdf_path.with_suffix(".c2pa.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = out.with_suffix(".manifest.json")
    manifest_path.write_text(manifest_json, encoding="utf-8")

    cmd: list[str] = [
        tool,
        str(pdf_path),
        "--manifest",
        str(manifest_path),
        "--output",
        str(out),
        "--force",  # overwrite if the output exists
    ]
    if cert_path and key_path:
        cmd += ["--signer", str(cert_path), "--signer-key", str(key_path)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )

    # c2patool warns to stderr when falling back to the dev test cert.
    used_test_cert = (
        cert_path is None or key_path is None or "test_cert" in (result.stderr or "").lower()
    )
    return C2PAResult(
        pdf_path=out,
        manifest_bytes=out.stat().st_size - pdf_path.stat().st_size if out.exists() else 0,
        signed_with_test_cert=used_test_cert,
        stderr=result.stderr or "",
    )


def verify_manifest(pdf_path: Path, timeout: int = 60) -> dict[str, Any]:
    """Read the embedded C2PA manifest from *pdf_path*.

    Returns the parsed manifest dict (the `manifests` array entry
    that matches the PDF's active manifest). Empty dict when no
    manifest is embedded; raises `C2PAMissing` when `c2patool` is
    not installed.
    """
    tool = _require_c2patool()
    result = subprocess.run(
        [tool, "--detailed", str(pdf_path)],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        # c2patool's exit code is non-zero when no manifest is
        # present; return empty dict rather than raising.
        return {}
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {}
