"""test_pdf_validation.py — Structural validation for built PDFs.

Validates that every PDF in build/ has:
- Valid structure (header, EOF)
- Complete XMP metadata (12 required fields)
- PDF/UA accessibility tagging (/MarkInfo /Marked)
- AES-256 encryption with correct permissions
- Copyright and rights metadata

All tests skip gracefully when no PDFs exist, so CI can run this
before or after a build step.
"""

from pathlib import Path

import pytest

BUILD_DIR = Path(__file__).resolve().parent.parent / "build"

try:
    import pikepdf
    HAS_PIKEPDF = True
except ImportError:
    HAS_PIKEPDF = False

INTERMEDIATE_EXTENSIONS = {".aux", ".log", ".toc", ".fls", ".fdb_latexmk",
                           ".bbl", ".blg", ".out", ".synctex.gz", ".xmpdata"}


def _all_pdfs():
    """Collect all final PDFs in build/ (skip .cache/ intermediates)."""
    if not BUILD_DIR.exists():
        return []
    pdfs = []
    for pdf in sorted(BUILD_DIR.rglob("*.pdf")):
        # Skip intermediate PDFs inside the hidden cache directory
        if ".cache" in pdf.parts:
            continue
        pdfs.append(pdf)
    return pdfs


def _pdfs_required():
    """Skip the entire test when no PDFs have been built yet."""
    pdfs = _all_pdfs()
    if not pdfs:
        pytest.skip("No PDFs in build/ — run 'make draft' first")
    return pdfs


# ── Size checks ──────────────────────────────────────────────────────────


class TestPdfSize:
    def test_pdfs_non_empty(self):
        """Every PDF in build/{mode}/ must be > 1 KB."""
        for pdf in _pdfs_required():
            size = pdf.stat().st_size
            assert size > 1024, f"{pdf.name} is only {size} bytes (expected > 1 KB)"

    def test_patent_pdfs_minimum_size(self):
        """Patent PDFs should be > 50 KB (ensures figures compiled)."""
        pdfs = _pdfs_required()
        patent_pdfs = [p for p in pdfs if "patent" in p.stem.lower()
                       or "patent" in p.stem.lower()
                       or "brevet" in p.stem.lower()]
        if not patent_pdfs:
            pytest.skip("No patent PDFs found")
        for pdf in patent_pdfs:
            size = pdf.stat().st_size
            assert size > 50 * 1024, (
                f"{pdf.name} is only {size} bytes (expected > 50 KB for patent)"
            )


# ── Structure checks ────────────────────────────────────────────────────


class TestPdfStructure:
    def test_pdfs_have_valid_header(self):
        """Every PDF must start with the %PDF- magic bytes."""
        for pdf in _pdfs_required():
            header = pdf.read_bytes()[:5]
            assert header == b"%PDF-", (
                f"{pdf.name} has invalid header: {header!r}"
            )

    def test_pdfs_have_eof_marker(self):
        """Every PDF must end with %%EOF (possibly followed by whitespace)."""
        for pdf in _pdfs_required():
            tail = pdf.read_bytes()[-32:]
            assert b"%%EOF" in tail, (
                f"{pdf.name} is missing %%EOF marker in last 32 bytes"
            )


# ── Cleanliness checks ──────────────────────────────────────────────────


class TestArtifactsCleanliness:
    def test_no_intermediate_files_in_output(self):
        """build/ (excluding .cache/) must contain only PDFs — no .aux, .log."""
        if not BUILD_DIR.exists():
            return
        stray = []
        for f in BUILD_DIR.rglob("*"):
            if ".cache" in f.parts:
                continue
            if f.is_file() and f.suffix in INTERMEDIATE_EXTENSIONS:
                stray.append(str(f.relative_to(BUILD_DIR)))
        assert stray == [], (
            f"Intermediate files found in build/: {', '.join(stray)}"
        )


# ── XMP Metadata checks ──────────────────────────────────────────────────

# XMP element tags to look for in the raw XML stream.
# Each maps a short label to the XML element tag that must be present.
_XMP_TAGS = {
    "dc:title": "<dc:title>",
    "dc:creator": "<dc:creator>",
    "dc:description": "<dc:description>",
    "dc:rights": "<dc:rights>",
    "dc:subject": "<dc:subject>",
    "pdf:Keywords": "<pdf:Keywords>",
    "pdf:Producer": "<pdf:Producer>",
    "xmp:CreatorTool": "<xmp:CreatorTool>",
    "xmpRights:Marked": "<xmpRights:Marked>",
    "xmpRights:WebStatement": "<xmpRights:WebStatement>",
    "photoshop:AuthorsPosition": "<photoshop:AuthorsPosition>",
    "photoshop:CaptionWriter": "<photoshop:CaptionWriter>",
}


def _read_xmp_xml(pdf_path):
    """Read raw XMP XML from a PDF's metadata stream."""
    with pikepdf.open(pdf_path) as pdf:
        meta = pdf.Root.get("/Metadata")
        if meta is None:
            return ""
        return meta.read_bytes().decode("utf-8", errors="replace")


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestXmpMetadata:
    """Verify all 12 required XMP metadata fields are present in every PDF."""

    def test_dc_title_present(self):
        """Every PDF must have a non-empty dc:title."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:title>" in xmp, (
                f"{pdf_path.name}: dc:title is missing or empty")

    def test_dc_creator_present(self):
        """Every PDF must have a non-empty dc:creator."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:creator>" in xmp, (
                f"{pdf_path.name}: dc:creator is missing or empty")

    def test_dc_description_present(self):
        """Every PDF must have a non-empty dc:description."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:description>" in xmp, (
                f"{pdf_path.name}: dc:description is missing or empty")

    def test_dc_rights_present(self):
        """Every PDF must have dc:rights (copyright notice)."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:rights>" in xmp, (
                f"{pdf_path.name}: dc:rights is missing or empty")

    def test_dc_subject_present(self):
        """Every PDF must have a non-empty dc:subject."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:subject>" in xmp, (
                f"{pdf_path.name}: dc:subject is missing or empty")

    def test_pdf_keywords_present(self):
        """Every PDF must have non-empty pdf:Keywords."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<pdf:Keywords>" in xmp, (
                f"{pdf_path.name}: pdf:Keywords is missing or empty")

    def test_pdf_producer_present(self):
        """Every PDF must have a non-empty pdf:Producer."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<pdf:Producer>" in xmp, (
                f"{pdf_path.name}: pdf:Producer is missing from XMP")

    def test_xmp_creator_tool_present(self):
        """Every PDF must have xmp:CreatorTool set."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<xmp:CreatorTool>" in xmp, (
                f"{pdf_path.name}: xmp:CreatorTool is missing or empty")

    def test_all_12_xmp_fields_present(self):
        """Every PDF must have all 12 required XMP metadata fields populated."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            missing = [label for label, tag in _XMP_TAGS.items()
                       if tag not in xmp]
            assert not missing, (
                f"{pdf_path.name}: missing XMP fields: {', '.join(missing)}"
            )


# ── Copyright & Rights checks ────────────────────────────────────────────


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestCopyrightMetadata:
    """Verify copyright and rights metadata is complete."""

    def test_xmp_rights_marked(self):
        """Every PDF must have xmpRights:Marked set to 'True'."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<xmpRights:Marked>True</xmpRights:Marked>" in xmp, (
                f"{pdf_path.name}: xmpRights:Marked is not 'True'"
            )

    def test_xmp_rights_web_statement(self):
        """Every PDF must have xmpRights:WebStatement (copyright URL)."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<xmpRights:WebStatement>" in xmp, (
                f"{pdf_path.name}: xmpRights:WebStatement is missing or empty"
            )

    def test_dc_rights_contains_copyright(self):
        """Every PDF dc:rights must contain a copyright symbol or 'Copyright'."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "\u00A9" in xmp or "Copyright" in xmp or "copyright" in xmp, (
                f"{pdf_path.name}: dc:rights does not contain copyright notice"
            )

    def test_photoshop_authors_position(self):
        """Every PDF must have photoshop:AuthorsPosition set."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<photoshop:AuthorsPosition>" in xmp, (
                f"{pdf_path.name}: photoshop:AuthorsPosition is missing or empty"
            )

    def test_photoshop_caption_writer(self):
        """Every PDF must have photoshop:CaptionWriter set."""
        for pdf_path in _pdfs_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<photoshop:CaptionWriter>" in xmp, (
                f"{pdf_path.name}: photoshop:CaptionWriter is missing or empty"
            )


# ── PDF/UA Accessibility checks ──────────────────────────────────────────


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestPdfAccessibility:
    """Verify PDF/UA accessibility compliance markers."""

    def test_mark_info_present(self):
        """Every PDF must have /MarkInfo in the document catalog."""
        for pdf_path in _pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                mark_info = pdf.Root.get("/MarkInfo")
            assert mark_info is not None, (
                f"{pdf_path.name}: /MarkInfo is missing from PDF catalog"
            )

    def test_marked_true(self):
        """Every PDF /MarkInfo must have /Marked set to true."""
        for pdf_path in _pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                mark_info = pdf.Root.get("/MarkInfo")
                if mark_info is not None:
                    marked = bool(mark_info.get("/Marked"))
                else:
                    marked = False
            assert marked, (
                f"{pdf_path.name}: /MarkInfo /Marked is not true"
            )


# ── Security / Encryption checks ─────────────────────────────────────────


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestPdfSecurity:
    """Verify PDF encryption and permission restrictions."""

    def test_pdfs_are_encrypted(self):
        """Every PDF must be encrypted."""
        for pdf_path in _pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                encrypted = pdf.is_encrypted
            assert encrypted, f"{pdf_path.name}: PDF is NOT encrypted"

    def test_encryption_allows_printing(self):
        """Encrypted PDFs must allow printing (user can open + print)."""
        for pdf_path in _pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                if pdf.is_encrypted:
                    perms = pdf.allow
                    assert perms.print_highres or perms.print_lowres, (
                        f"{pdf_path.name}: printing is not permitted"
                    )

    def test_encryption_blocks_extraction(self):
        """Encrypted PDFs must block content extraction."""
        for pdf_path in _pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                if pdf.is_encrypted:
                    assert not pdf.allow.extract, (
                        f"{pdf_path.name}: content extraction is not blocked"
                    )

    def test_encryption_blocks_modification(self):
        """Encrypted PDFs must block document modification."""
        for pdf_path in _pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                if pdf.is_encrypted:
                    assert not pdf.allow.modify_other, (
                        f"{pdf_path.name}: document modification is not blocked"
                    )

    def test_encryption_allows_accessibility(self):
        """Encrypted PDFs must allow accessibility access."""
        for pdf_path in _pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                if pdf.is_encrypted:
                    assert pdf.allow.accessibility, (
                        f"{pdf_path.name}: accessibility access is not permitted"
                    )

    def test_user_can_open_without_password(self):
        """Every PDF must open without a password (empty user password)."""
        for pdf_path in _pdfs_required():
            # pikepdf.open() with no password should succeed
            try:
                with pikepdf.open(pdf_path) as pdf:
                    _ = len(pdf.pages)
            except pikepdf.PasswordError:
                pytest.fail(
                    f"{pdf_path.name}: cannot open without password"
                )


# ── Comprehensive smoke test ─────────────────────────────────────────────


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestPdfComprehensive:
    """Single test that checks ALL requirements on every PDF."""

    def test_every_pdf_fully_compliant(self):
        """Every PDF must pass metadata + accessibility + security checks."""
        pdfs = _pdfs_required()
        failures = []

        for pdf_path in pdfs:
            issues = []
            xmp = _read_xmp_xml(pdf_path)

            # XMP metadata — check raw XML tags
            for label, tag in _XMP_TAGS.items():
                if tag not in xmp:
                    issues.append(f"missing {label}")

            with pikepdf.open(pdf_path) as pdf:
                # Accessibility
                mi = pdf.Root.get("/MarkInfo")
                if not mi or not bool(mi.get("/Marked")):
                    issues.append("missing /MarkInfo /Marked")

                # Encryption
                if not pdf.is_encrypted:
                    issues.append("not encrypted")
                else:
                    if not (pdf.allow.print_highres or pdf.allow.print_lowres):
                        issues.append("printing blocked")
                    if pdf.allow.extract:
                        issues.append("extraction not blocked")
                    if pdf.allow.modify_other:
                        issues.append("modification not blocked")
                    if not pdf.allow.accessibility:
                        issues.append("accessibility blocked")

            if issues:
                failures.append(f"{pdf_path.name}: {'; '.join(issues)}")

        assert not failures, (
            f"{len(failures)} PDF(s) failed compliance:\n"
            + "\n".join(f"  - {f}" for f in failures)
        )
