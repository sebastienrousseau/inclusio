"""Provenance + signing for camera-ready PDFs (Sprint 8).

Closes Forcing Function #7 (PAdES / C2PA / SLSA) in
docs/strategy-2026.md. The engine already ships SLSA L3 build
provenance for the wheel + sdist via `actions/attest-build-provenance`
(see `.github/workflows/release.yml`); this module adds the per-PDF
signal:

  - `c2pa` — C2PA Content Credentials manifest (provenance for the
    artefact lifecycle: who created it, when, with which tools, and
    any AI-disclosure metadata from F6). Wraps `c2patool` via
    subprocess so we don't pull a heavy native dep.

  - `pades` — eIDAS-aligned PAdES signature (Sprint 8.5 scaffold —
    not yet implemented; pyhanko optional dep planned).
"""

from __future__ import annotations

from .c2pa import (
    C2PAMissing,
    C2PAResult,
    build_manifest_json,
    embed_manifest,
    verify_manifest,
)

__all__ = [
    "C2PAMissing",
    "C2PAResult",
    "build_manifest_json",
    "embed_manifest",
    "verify_manifest",
]
