# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""PDF post-processing utilities.

This sub-package owns the pikepdf-driven manipulations the engine
applies after LaTeX hands off a compiled PDF: XMP-metadata writes,
AES-256 encryption when opted in, and the Sprint-5 (S5.4) tagged
vs. untagged dispatch that protects the kernel-written XMP packet on
PDF/UA-2 + PDF/A-4f conforming artefacts.

Extracted from `inclusio.cli.build` in v0.0.4 so the function set can
be unit-tested and reused (e.g. by a future "stamp a built PDF
without re-running LaTeX" CLI) without dragging in the build
orchestrator's 1700-line argparse + dispatch surface.
"""

from inclusio.pdf.post_process import (
    apply_encryption,
    build_xmp_xml,
    post_process_pdf,
)

__all__ = [
    "apply_encryption",
    "build_xmp_xml",
    "post_process_pdf",
]
