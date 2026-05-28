"""test_pdf_validation.py — Structural validation for built PDFs.

Validates structural correctness of every PDF in `build/`:

- Valid header/EOF, non-empty, no intermediate files leaked.
- /MarkInfo + /Marked tagging (PDF/UA-2 requirement).
- Legacy hand-crafted XMP + AES-256 encryption are validated only on
  PDFs that opted out of the Sprint-5 tagged-PDF path.

Sprint-5 context (decision D2, 2026-05-19): when the LaTeX kernel's
tagpdf project writes /StructTreeRoot, the post-processor STOPS
overwriting the kernel's XMP (the Sprint-1 hand-crafted markers
strip pdfaid:part=4 + pdfuaid:part=2 and break the audit gate). The
veraPDF audit job (.github/workflows/verapdf.yml) is the source of
truth for PDF/UA-2 + PDF/A-4f conformance on tagged PDFs; this test
file covers the legacy untagged path + structural invariants that
hold across both paths.

All tests skip gracefully when no PDFs exist, so CI can run this
before or after a build step.
"""

from pathlib import Path

import pytest
import yaml

BUILD_DIR = Path(__file__).resolve().parent.parent / "build"
META_PATH = Path(__file__).resolve().parent.parent / "data" / "meta.yaml"

try:
    import pikepdf

    HAS_PIKEPDF = True
except ImportError:
    HAS_PIKEPDF = False

INTERMEDIATE_EXTENSIONS = {
    ".aux",
    ".log",
    ".toc",
    ".fls",
    ".fdb_latexmk",
    ".bbl",
    ".blg",
    ".out",
    ".synctex.gz",
    ".xmpdata",
}


def _registered_stems():
    """Stems of PDFs registered in `data/meta.yaml documents:`.

    Orphan PDFs (e.g. one-shot tailored job outputs not in the
    registry) are not part of the published surface and are skipped
    by the strict validation suites.
    """
    if not META_PATH.exists():
        return set()
    try:
        meta = yaml.safe_load(META_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return set()
    stems = set()
    for key, cfg in (meta.get("documents") or {}).items():
        stems.add(key)
        if isinstance(cfg, dict):
            src = cfg.get("src", "")
            if src:
                stems.add(Path(src).stem)
    return stems


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


def _registered_pdfs():
    """Built PDFs that correspond to registered documents only."""
    stems = _registered_stems()
    if not stems:
        return _all_pdfs()
    return [p for p in _all_pdfs() if p.stem in stems]


def _pdfs_required():
    """Skip the entire test when no PDFs have been built yet."""
    pdfs = _all_pdfs()
    if not pdfs:
        pytest.skip("No PDFs in build/ — run 'make draft' first")
    return pdfs


def _registered_pdfs_required():
    """Skip when no registered PDFs are built."""
    pdfs = _registered_pdfs()
    if not pdfs:
        pytest.skip("No registered PDFs in build/ — run 'make draft' first")
    return pdfs


def _is_tagged(pdf_path):
    """True when the PDF carries a /StructTreeRoot (Sprint-5 tagged path)."""
    with pikepdf.open(pdf_path) as pdf:
        return "/StructTreeRoot" in pdf.Root


def _legacy_untagged_pdfs():
    """Registered PDFs that did NOT go through the kernel's tagged-PDF path.

    These are still subject to the Sprint-1 hand-crafted XMP + AES-256
    encryption contract. Tagged PDFs are validated via veraPDF instead.
    """
    if not HAS_PIKEPDF:
        return []
    return [p for p in _registered_pdfs() if not _is_tagged(p)]


# ── Size checks ──────────────────────────────────────────────────────────


class TestPdfSize:
    """Basic size sanity — anything under a couple of KB is a broken build."""

    def test_pdfs_non_empty(self):
        """Every PDF in build/{mode}/ must be > 1 KB."""
        for pdf in _pdfs_required():
            size = pdf.stat().st_size
            assert size > 1024, f"{pdf.name} is only {size} bytes (expected > 1 KB)"

    def test_patent_pdfs_have_figures(self):
        """Patent PDFs ship with at least one figure → typically > 30 KB.

        The old 50 KB threshold was set against a Sprint-1 build; the
        Sprint-5 tagged path produces slightly smaller output for the
        same content. 30 KB is the new floor below which figures are
        almost certainly missing.
        """
        pdfs = _pdfs_required()
        patent_pdfs = [p for p in pdfs if "patent" in p.stem.lower() or "brevet" in p.stem.lower()]
        if not patent_pdfs:
            pytest.skip("No patent PDFs found")
        for pdf in patent_pdfs:
            size = pdf.stat().st_size
            assert size > 30 * 1024, f"{pdf.name} is only {size} bytes — figures likely missing"


# ── Structure checks ────────────────────────────────────────────────────


class TestPdfStructure:
    """Header / EOF sanity — holds across tagged and legacy paths."""

    def test_pdfs_have_valid_header(self):
        """Every PDF must start with the %PDF- magic bytes."""
        for pdf in _pdfs_required():
            header = pdf.read_bytes()[:5]
            assert header == b"%PDF-", f"{pdf.name} has invalid header: {header!r}"

    def test_pdfs_have_eof_marker(self):
        """Every PDF must end with %%EOF (possibly followed by whitespace)."""
        for pdf in _pdfs_required():
            tail = pdf.read_bytes()[-32:]
            assert b"%%EOF" in tail, f"{pdf.name} is missing %%EOF marker in last 32 bytes"


# ── Cleanliness checks ──────────────────────────────────────────────────


class TestArtifactsCleanliness:
    """build/ surface should never carry LaTeX intermediates."""

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
        assert stray == [], f"Intermediate files found in build/: {', '.join(stray)}"


# ── Legacy hand-crafted XMP (untagged path only — Sprint-5 D2) ─────────

# XMP element tags to look for in the raw XML stream. The legacy
# Sprint-1 post-processor wrote all 12; the Sprint-5 tagged-PDF path
# defers to the kernel's XMP, which carries a different subset (see
# the veraPDF audit for the tagged-PDF metadata contract).
_LEGACY_XMP_TAGS = {
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


def _legacy_untagged_required():
    """Skip the legacy-XMP suite when every registered PDF is tagged."""
    pdfs = _legacy_untagged_pdfs()
    if not pdfs:
        pytest.skip(
            "All registered PDFs are tagged (Sprint-5 path) — "
            "legacy XMP fields are owned by the kernel; veraPDF is the "
            "source of truth."
        )
    return pdfs


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestLegacyXmpMetadata:
    """Verify the legacy 12 XMP fields on untagged PDFs.

    Sprint-5 tagged PDFs intentionally defer XMP to the kernel; this
    suite only fires when at least one registered PDF still goes through
    the legacy `\\hypersetup` + hand-crafted XMP path.
    """

    def test_dc_title_present(self):
        """Every untagged PDF must have a non-empty dc:title."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:title>" in xmp, f"{pdf_path.name}: dc:title is missing or empty"

    def test_dc_creator_present(self):
        """Every untagged PDF must have a non-empty dc:creator."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:creator>" in xmp, f"{pdf_path.name}: dc:creator is missing or empty"

    def test_dc_description_present(self):
        """Every untagged PDF must have a non-empty dc:description."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:description>" in xmp, f"{pdf_path.name}: dc:description is missing or empty"

    def test_dc_rights_present(self):
        """Every untagged PDF must have dc:rights (copyright notice)."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:rights>" in xmp, f"{pdf_path.name}: dc:rights is missing or empty"

    def test_dc_subject_present(self):
        """Every untagged PDF must have a non-empty dc:subject."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<dc:subject>" in xmp, f"{pdf_path.name}: dc:subject is missing or empty"

    def test_pdf_keywords_present(self):
        """Every untagged PDF must have non-empty pdf:Keywords."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<pdf:Keywords>" in xmp, f"{pdf_path.name}: pdf:Keywords is missing or empty"

    def test_pdf_producer_present(self):
        """Every untagged PDF must have a non-empty pdf:Producer."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<pdf:Producer>" in xmp, f"{pdf_path.name}: pdf:Producer is missing from XMP"

    def test_xmp_creator_tool_present(self):
        """Every untagged PDF must have xmp:CreatorTool set."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<xmp:CreatorTool>" in xmp, (
                f"{pdf_path.name}: xmp:CreatorTool is missing or empty"
            )

    def test_all_12_xmp_fields_present(self):
        """Every untagged PDF must have all 12 required XMP fields populated."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            missing = [label for label, tag in _LEGACY_XMP_TAGS.items() if tag not in xmp]
            assert not missing, f"{pdf_path.name}: missing XMP fields: {', '.join(missing)}"


# ── Copyright & Rights checks (legacy untagged path) ───────────────────


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestLegacyCopyrightMetadata:
    """Verify copyright and rights metadata on untagged PDFs.

    Tagged PDFs put copyright into the kernel's PDF/A-4f XMP packet
    via `\\DocumentMetadata{rights=…}`; veraPDF validates that.
    """

    def test_xmp_rights_marked(self):
        """Every untagged PDF must have xmpRights:Marked set to 'True'."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<xmpRights:Marked>True</xmpRights:Marked>" in xmp, (
                f"{pdf_path.name}: xmpRights:Marked is not 'True'"
            )

    def test_xmp_rights_web_statement(self):
        """Every untagged PDF must have xmpRights:WebStatement (copyright URL)."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<xmpRights:WebStatement>" in xmp, (
                f"{pdf_path.name}: xmpRights:WebStatement is missing or empty"
            )

    def test_dc_rights_contains_copyright(self):
        """Every untagged PDF dc:rights must contain a copyright symbol or 'Copyright'."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "©" in xmp or "Copyright" in xmp or "copyright" in xmp, (
                f"{pdf_path.name}: dc:rights does not contain copyright notice"
            )

    def test_photoshop_authors_position(self):
        """Every untagged PDF must have photoshop:AuthorsPosition set."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<photoshop:AuthorsPosition>" in xmp, (
                f"{pdf_path.name}: photoshop:AuthorsPosition is missing or empty"
            )

    def test_photoshop_caption_writer(self):
        """Every untagged PDF must have photoshop:CaptionWriter set."""
        for pdf_path in _legacy_untagged_required():
            xmp = _read_xmp_xml(pdf_path)
            assert "<photoshop:CaptionWriter>" in xmp, (
                f"{pdf_path.name}: photoshop:CaptionWriter is missing or empty"
            )


# ── PDF/UA Accessibility checks (both paths) ────────────────────────────


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestPdfAccessibility:
    """Verify PDF/UA accessibility markers across the registered PDF set.

    The tagged path emits /StructTreeRoot + /MarkInfo /Marked via the
    kernel; the legacy path emits /MarkInfo /Marked via the
    post-processor. Both should satisfy these checks — they're a
    structural invariant of the publish gate.
    """

    def test_mark_info_present(self):
        """Every registered PDF must have /MarkInfo in the catalog."""
        for pdf_path in _registered_pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                mark_info = pdf.Root.get("/MarkInfo")
            assert mark_info is not None, f"{pdf_path.name}: /MarkInfo is missing from PDF catalog"

    def test_marked_true(self):
        """Every registered PDF /MarkInfo must have /Marked set to true."""
        for pdf_path in _registered_pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                mark_info = pdf.Root.get("/MarkInfo")
                if mark_info is not None:
                    marked = bool(mark_info.get("/Marked"))
                else:
                    marked = False
            assert marked, f"{pdf_path.name}: /MarkInfo /Marked is not true"


# ── Security / Encryption checks (opt-in path) ─────────────────────────


def _encrypted_registered_pdfs_required():
    """Skip when no registered PDF opted into Sprint-5 secure_pdf=True.

    Sprint-5 (decision D2) made AES-256 encryption opt-in because it is
    incompatible with PDF/A-4f and PDF/UA-2. The encryption-checking
    suite only fires when at least one registered PDF carries an
    /Encrypt dict.
    """
    pdfs = [p for p in _registered_pdfs() if pikepdf.open(p).is_encrypted]
    if not pdfs:
        pytest.skip(
            "No registered PDF is encrypted (Sprint-5 default). "
            "Encryption suite only runs for `secure_pdf: true` docs."
        )
    return pdfs


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestPdfSecurity:
    """Verify PDF encryption and permission restrictions, when present."""

    def test_encryption_allows_printing(self):
        """Encrypted PDFs must allow printing (user can open + print)."""
        for pdf_path in _encrypted_registered_pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                perms = pdf.allow
                assert perms.print_highres or perms.print_lowres, (
                    f"{pdf_path.name}: printing is not permitted"
                )

    def test_encryption_blocks_extraction(self):
        """Encrypted PDFs must block content extraction."""
        for pdf_path in _encrypted_registered_pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                assert not pdf.allow.extract, f"{pdf_path.name}: content extraction is not blocked"

    def test_encryption_blocks_modification(self):
        """Encrypted PDFs must block document modification."""
        for pdf_path in _encrypted_registered_pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                assert not pdf.allow.modify_other, (
                    f"{pdf_path.name}: document modification is not blocked"
                )

    def test_encryption_allows_accessibility(self):
        """Encrypted PDFs must allow accessibility access."""
        for pdf_path in _encrypted_registered_pdfs_required():
            with pikepdf.open(pdf_path) as pdf:
                assert pdf.allow.accessibility, (
                    f"{pdf_path.name}: accessibility access is not permitted"
                )

    def test_user_can_open_without_password(self):
        """Every PDF must open without a password (empty user password)."""
        for pdf_path in _pdfs_required():
            try:
                with pikepdf.open(pdf_path) as pdf:
                    _ = len(pdf.pages)
            except pikepdf.PasswordError:
                pytest.fail(f"{pdf_path.name}: cannot open without password")


# ── Comprehensive smoke test ─────────────────────────────────────────────


@pytest.mark.skipif(not HAS_PIKEPDF, reason="pikepdf not installed")
class TestPdfComprehensive:
    """Single test that checks structural + tagging invariants on every
    registered PDF.

    The strict legacy-XMP / encryption checks live in the dedicated
    classes above (gated to their applicable PDF subsets). This suite
    covers the bar that should hold across both the Sprint-5 tagged
    and the legacy untagged paths.
    """

    def test_every_registered_pdf_is_tagged_and_accessible(self):
        """Every registered PDF must carry /MarkInfo /Marked = true."""
        pdfs = _registered_pdfs_required()
        failures = []
        for pdf_path in pdfs:
            issues = []
            with pikepdf.open(pdf_path) as pdf:
                mi = pdf.Root.get("/MarkInfo")
                if not mi or not bool(mi.get("/Marked")):
                    issues.append("missing /MarkInfo /Marked")
            if issues:
                failures.append(f"{pdf_path.name}: {'; '.join(issues)}")
        assert not failures, f"{len(failures)} PDF(s) failed accessibility:\n" + "\n".join(
            f"  - {f}" for f in failures
        )
