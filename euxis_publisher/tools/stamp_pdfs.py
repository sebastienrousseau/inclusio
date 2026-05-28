#!/usr/bin/env python3
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""stamp-pdfs.py — Inject git provenance metadata into built PDFs.

Writes the Git commit hash and build timestamp into each PDF's document
info dictionary, enabling any printed copy to be traced back to the
exact source revision.

Optionally overlays a semi-transparent diagonal watermark (e.g. "DRAFT")
on every page to prevent accidental distribution of non-final documents.

Usage (CI):
    python3 -m euxis_publisher.tools.stamp_pdfs artifacts/draft/ --watermark "DRAFT"
    python3 -m euxis_publisher.tools.stamp_pdfs artifacts/camera-ready/

Requires: pikepdf  (pip install pikepdf)
"""

import argparse
import datetime
import hashlib
import math
import subprocess
import sys
from pathlib import Path

DEFAULT_SUBPROCESS_TIMEOUT = 30


def get_git_hash():
    """Return the short git commit hash, or 'unknown' outside a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=DEFAULT_SUBPROCESS_TIMEOUT,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def get_git_branch():
    """Return the current git branch name, or 'detached' outside a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=DEFAULT_SUBPROCESS_TIMEOUT,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "detached"


def _build_watermark_xobject(pdf, text, page_width, page_height):
    """Build a Form XObject that renders diagonal watermark text.

    Uses Helvetica-Bold (a standard PDF Type1 font — no embedding needed)
    with 15% opacity, rotated 45° across the page diagonal.
    """
    import pikepdf

    # Font size scales with page diagonal so the stamp fills the page
    diagonal = math.sqrt(page_width**2 + page_height**2)
    font_size = min(diagonal / max(len(text), 1) * 1.2, 120)
    angle_rad = math.atan2(page_height, page_width)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Approximate text width (Helvetica-Bold avg char width ≈ 0.6 × font_size)
    text_width = len(text) * 0.6 * font_size
    # Centre the text on the page diagonal
    offset_x = (page_width - text_width * cos_a) / 2
    offset_y = (page_height - text_width * sin_a) / 2

    # Escape any parentheses in the text for the PDF string
    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # Build the content stream:
    #   - Push graphics state
    #   - Set extended graphics state for transparency (ca = 0.15)
    #   - Set fill colour to medium grey
    #   - Position + rotate via text matrix
    #   - Render the string
    #   - Pop graphics state
    stream = (
        f"q "
        f"/GS1 gs "
        f"0.7 0.7 0.7 rg "
        f"BT "
        f"/F1 {font_size:.1f} Tf "
        f"{cos_a:.4f} {sin_a:.4f} {-sin_a:.4f} {cos_a:.4f} "
        f"{offset_x:.1f} {offset_y:.1f} Tm "
        f"({safe_text}) Tj "
        f"ET "
        f"Q"
    )

    # Create the transparency graphics state
    gs = pikepdf.Dictionary(
        {
            "/Type": pikepdf.Name("/ExtGState"),
            "/ca": 0.15,  # fill opacity
            "/CA": 0.15,  # stroke opacity
        }
    )

    # Create the Helvetica-Bold font reference (standard Type1 — no embed)
    font = pikepdf.Dictionary(
        {
            "/Type": pikepdf.Name("/Font"),
            "/Subtype": pikepdf.Name("/Type1"),
            "/BaseFont": pikepdf.Name("/Helvetica-Bold"),
        }
    )

    # Wrap as a Form XObject so we can overlay without touching page content
    resources = pikepdf.Dictionary(
        {
            "/ExtGState": pikepdf.Dictionary({"/GS1": pdf.make_indirect(gs)}),
            "/Font": pikepdf.Dictionary({"/F1": pdf.make_indirect(font)}),
        }
    )

    xobj = pikepdf.Stream(pdf, stream.encode())
    xobj["/Type"] = pikepdf.Name("/XObject")
    xobj["/Subtype"] = pikepdf.Name("/Form")
    xobj["/BBox"] = pikepdf.Array([0, 0, page_width, page_height])
    xobj["/Resources"] = resources

    return pdf.make_indirect(xobj)


def watermark_pdf(pdf_path, text):
    """Overlay a diagonal watermark on every page of the PDF."""
    import pikepdf

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        for page in pdf.pages:
            # Determine page dimensions from MediaBox
            mbox = page.get("/MediaBox", pikepdf.Array([0, 0, 612, 792]))
            pw = float(mbox[2]) - float(mbox[0])
            ph = float(mbox[3]) - float(mbox[1])

            xobj = _build_watermark_xobject(pdf, text, pw, ph)

            # Register the XObject in the page's resources
            if "/Resources" not in page:
                page["/Resources"] = pikepdf.Dictionary()
            resources = page["/Resources"]
            if "/XObject" not in resources:
                resources["/XObject"] = pikepdf.Dictionary()
            wm_name = "/Watermark0"
            resources["/XObject"][wm_name] = xobj

            # Append a Do command to the page's content stream
            overlay = pikepdf.Stream(pdf, f"q {wm_name} Do Q".encode())
            if isinstance(page["/Contents"], pikepdf.Array):
                page["/Contents"].append(pdf.make_indirect(overlay))
            else:
                page["/Contents"] = pikepdf.Array(
                    [
                        page["/Contents"],
                        pdf.make_indirect(overlay),
                    ]
                )

        pdf.save(pdf_path)


def secure_pdf(pdf_path, owner_password=None):
    """Apply encryption and permission restrictions to a PDF.

    Uses AES-256 encryption (R=6). The PDF remains openable without a
    password, but modification, extraction, and assembly are blocked.
    """
    import pikepdf

    if owner_password is None:
        content_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]
        owner_password = content_hash

    perms = pikepdf.Permissions(
        print_highres=True,
        print_lowres=True,
        extract=False,
        modify_annotation=False,
        modify_form=False,
        modify_assembly=False,
        modify_other=False,
        accessibility=True,
    )

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        pdf.save(
            pdf_path,
            encryption=pikepdf.Encryption(
                owner=owner_password,
                user="",
                R=6,
                allow=perms,
            ),
        )


def stamp_pdf(pdf_path, commit_hash, build_date):
    """Write provenance metadata into a single PDF."""
    import pikepdf

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            # Dublin Core description — visible in "Properties" dialog
            meta["dc:description"] = f"Built from commit {commit_hash} on {build_date}"
            # Custom XMP field for machine-readable provenance
            meta["pdf:Producer"] = f"Publications build.py | {commit_hash} | {build_date}"
        pdf.save(pdf_path)


def main(argv=None):
    """Entry point for `python -m euxis_publisher.tools.stamp_pdfs`.

    Walks the requested build directory, embeds git provenance (commit
    SHA, branch, dirty flag, build timestamp) into each PDF's XMP
    metadata, and optionally overlays a draft watermark across pages.
    """
    parser = argparse.ArgumentParser(
        description="Stamp PDFs with git provenance and optional watermark",
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing PDFs to stamp",
    )
    parser.add_argument(
        "--watermark",
        metavar="TEXT",
        help="Overlay a semi-transparent diagonal watermark on every page",
    )
    parser.add_argument(
        "--secure",
        action="store_true",
        help="Apply encryption and content protection",
    )
    parser.add_argument(
        "--owner-password",
        metavar="PASS",
        help="Owner password (default: auto-generated from content hash)",
    )
    args = parser.parse_args(argv)

    if not args.directory.is_dir():
        print(f"ERROR: {args.directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    commit_hash = get_git_hash()
    build_date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    pdfs = sorted(args.directory.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {args.directory}")
        return

    print(f"Stamping {len(pdfs)} PDF(s) with {commit_hash} @ {build_date}")

    for pdf in pdfs:
        stamp_pdf(pdf, commit_hash, build_date)
        if args.watermark:
            watermark_pdf(pdf, args.watermark)
        if args.secure:
            secure_pdf(pdf, args.owner_password)
        label = "STAMP"
        if args.watermark:
            label += "+WM"
        if args.secure:
            label += "+SEC"
        print(f"  {label:10s} {pdf.name}")

    print("Done.")


if __name__ == "__main__":  # pragma: no cover
    main()
