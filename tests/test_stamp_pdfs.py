"""test_stamp_pdfs.py — Tests for scripts/stamp-pdfs.py PDF stamping."""

import importlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pikepdf
import pytest

# Import module with hyphenated filename and register in sys.modules
_scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
sys.path.insert(0, _scripts_dir)
_spec = importlib.util.spec_from_file_location(
    "stamp_pdfs",
    Path(_scripts_dir) / "stamp-pdfs.py",
)
stamp_pdfs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stamp_pdfs)
sys.modules["stamp_pdfs"] = stamp_pdfs


def _create_pdf(path, pages=1):
    """Create a minimal valid PDF for testing."""
    pdf = pikepdf.Pdf.new()
    for _ in range(pages):
        pdf.add_blank_page(page_size=(612, 792))
    pdf.save(path)


# ── get_git_hash ────────────────────────────────────────────────────────


class TestGetGitHash:
    def test_returns_hash_in_repo(self):
        result = stamp_pdfs.get_git_hash()
        assert result != "unknown"
        assert len(result) >= 7

    @patch("stamp_pdfs.subprocess.run")
    def test_returns_unknown_on_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        assert stamp_pdfs.get_git_hash() == "unknown"

    @patch("stamp_pdfs.subprocess.run")
    def test_returns_unknown_on_missing_git(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        assert stamp_pdfs.get_git_hash() == "unknown"


# ── get_git_branch ──────────────────────────────────────────────────────


class TestGetGitBranch:
    def test_returns_branch_in_repo(self):
        result = stamp_pdfs.get_git_branch()
        assert result != "detached"
        assert len(result) > 0

    @patch("stamp_pdfs.subprocess.run")
    def test_returns_detached_on_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        assert stamp_pdfs.get_git_branch() == "detached"

    @patch("stamp_pdfs.subprocess.run")
    def test_returns_detached_on_missing_git(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        assert stamp_pdfs.get_git_branch() == "detached"


# ── _build_watermark_xobject ────────────────────────────────────────────


class TestBuildWatermarkXobject:
    def test_returns_xobject(self):
        pdf = pikepdf.Pdf.new()
        xobj = stamp_pdfs._build_watermark_xobject(pdf, "DRAFT", 612, 792)
        assert xobj["/Type"] == pikepdf.Name("/XObject")
        assert xobj["/Subtype"] == pikepdf.Name("/Form")

    def test_bbox_matches_page_dimensions(self):
        pdf = pikepdf.Pdf.new()
        xobj = stamp_pdfs._build_watermark_xobject(pdf, "TEST", 800, 600)
        bbox = xobj["/BBox"]
        assert float(bbox[2]) == 800
        assert float(bbox[3]) == 600

    def test_handles_special_chars_in_text(self):
        pdf = pikepdf.Pdf.new()
        xobj = stamp_pdfs._build_watermark_xobject(
            pdf, "DRAFT (v1)", 612, 792
        )
        stream = xobj.read_bytes().decode()
        assert "\\(" in stream
        assert "\\)" in stream

    def test_has_transparency_resources(self):
        pdf = pikepdf.Pdf.new()
        xobj = stamp_pdfs._build_watermark_xobject(pdf, "DRAFT", 612, 792)
        resources = xobj["/Resources"]
        assert "/ExtGState" in resources
        assert "/Font" in resources


# ── stamp_pdf ───────────────────────────────────────────────────────────


class TestStampPdf:
    def test_writes_provenance_metadata(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _create_pdf(pdf_path)

        stamp_pdfs.stamp_pdf(pdf_path, "abc1234", "2026-02-17T12:00:00Z")

        with pikepdf.open(pdf_path) as pdf:
            with pdf.open_metadata() as meta:
                desc = meta.get("dc:description", "")
                producer = meta.get("pdf:Producer", "")
        assert "abc1234" in desc
        assert "2026-02-17" in desc
        assert "abc1234" in producer


# ── watermark_pdf ───────────────────────────────────────────────────────


class TestWatermarkPdf:
    def test_adds_watermark_to_single_page(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _create_pdf(pdf_path)

        stamp_pdfs.watermark_pdf(pdf_path, "DRAFT")

        with pikepdf.open(pdf_path) as pdf:
            page = pdf.pages[0]
            resources = page["/Resources"]
            assert "/XObject" in resources
            assert "/Watermark0" in resources["/XObject"]

    def test_adds_watermark_to_multi_page(self, tmp_path):
        pdf_path = tmp_path / "multi.pdf"
        _create_pdf(pdf_path, pages=3)

        stamp_pdfs.watermark_pdf(pdf_path, "CONFIDENTIAL")

        with pikepdf.open(pdf_path) as pdf:
            for page in pdf.pages:
                assert "/Watermark0" in page["/Resources"]["/XObject"]

    def test_page_without_resources(self, tmp_path):
        """Pages with no /Resources key get one created."""
        pdf_path = tmp_path / "bare.pdf"
        # Create PDF, then strip /Resources from the page
        _create_pdf(pdf_path)
        with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
            del pdf.pages[0]["/Resources"]
            pdf.save(pdf_path)

        stamp_pdfs.watermark_pdf(pdf_path, "DRAFT")

        with pikepdf.open(pdf_path) as pdf:
            page = pdf.pages[0]
            assert "/Resources" in page
            assert "/Watermark0" in page["/Resources"]["/XObject"]

    def test_page_without_xobject(self, tmp_path):
        """Pages with /Resources but no /XObject get one created."""
        pdf_path = tmp_path / "noxobj.pdf"
        _create_pdf(pdf_path)
        # Ensure Resources exists but XObject does not
        with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
            page = pdf.pages[0]
            if "/Resources" not in page:
                page["/Resources"] = pikepdf.Dictionary()
            res = page["/Resources"]
            if "/XObject" in res:
                del res["/XObject"]
            pdf.save(pdf_path)

        stamp_pdfs.watermark_pdf(pdf_path, "DRAFT")

        with pikepdf.open(pdf_path) as pdf:
            page = pdf.pages[0]
            assert "/Watermark0" in page["/Resources"]["/XObject"]

    def test_contents_array_appended(self, tmp_path):
        """When /Contents is already an Array, overlay is appended."""
        pdf_path = tmp_path / "array.pdf"
        _create_pdf(pdf_path)
        # Convert Contents to an Array
        with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
            page = pdf.pages[0]
            original = page["/Contents"]
            page["/Contents"] = pikepdf.Array([original])
            pdf.save(pdf_path)

        stamp_pdfs.watermark_pdf(pdf_path, "DRAFT")

        with pikepdf.open(pdf_path) as pdf:
            page = pdf.pages[0]
            assert isinstance(page["/Contents"], pikepdf.Array)
            assert len(page["/Contents"]) == 2


# ── main() ──────────────────────────────────────────────────────────────


# ── secure_pdf ─────────────────────────────────────────────────────────


class TestSecurePdfStamp:
    def test_secure_pdf_applies_encryption(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _create_pdf(pdf_path)

        stamp_pdfs.secure_pdf(pdf_path)

        with pikepdf.open(pdf_path) as pdf:
            assert pdf.is_encrypted

    def test_secure_pdf_custom_password(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _create_pdf(pdf_path)

        stamp_pdfs.secure_pdf(pdf_path, owner_password="my-secret")

        # Should still be openable (no user password)
        with pikepdf.open(pdf_path) as pdf:
            assert pdf.is_encrypted

    def test_secure_pdf_permissions(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _create_pdf(pdf_path)

        stamp_pdfs.secure_pdf(pdf_path, owner_password="owner123")

        # Open with owner password to check permissions
        with pikepdf.open(pdf_path, password="owner123") as pdf:
            assert pdf.is_encrypted


# ── main() ──────────────────────────────────────────────────────────────


class TestStampPdfsMain:
    def test_main_stamps_pdfs(self, tmp_path, capsys):
        _create_pdf(tmp_path / "doc.pdf")
        with patch("sys.argv", ["stamp-pdfs.py", str(tmp_path)]):
            stamp_pdfs.main()
        output = capsys.readouterr().out
        assert "STAMP" in output
        assert "doc.pdf" in output
        assert "Done." in output

    def test_main_with_watermark(self, tmp_path, capsys):
        _create_pdf(tmp_path / "doc.pdf")
        with patch(
            "sys.argv",
            ["stamp-pdfs.py", str(tmp_path), "--watermark", "DRAFT"],
        ):
            stamp_pdfs.main()
        output = capsys.readouterr().out
        assert "STAMP+WM" in output
        assert "doc.pdf" in output

    def test_main_not_a_directory_exits(self, tmp_path):
        with patch("sys.argv", ["stamp-pdfs.py", str(tmp_path / "nope")]):
            with pytest.raises(SystemExit) as exc_info:
                stamp_pdfs.main()
            assert exc_info.value.code == 1

    def test_main_no_pdfs_found(self, tmp_path, capsys):
        (tmp_path / "readme.txt").write_text("nothing")
        with patch("sys.argv", ["stamp-pdfs.py", str(tmp_path)]):
            stamp_pdfs.main()
        output = capsys.readouterr().out
        assert "No PDFs found" in output

    def test_main_multiple_pdfs(self, tmp_path, capsys):
        _create_pdf(tmp_path / "a.pdf")
        _create_pdf(tmp_path / "b.pdf")
        with patch("sys.argv", ["stamp-pdfs.py", str(tmp_path)]):
            stamp_pdfs.main()
        output = capsys.readouterr().out
        assert "a.pdf" in output
        assert "b.pdf" in output
        assert "Stamping 2 PDF(s)" in output

    def test_main_with_secure(self, tmp_path, capsys):
        _create_pdf(tmp_path / "doc.pdf")
        with patch(
            "sys.argv",
            ["stamp-pdfs.py", str(tmp_path), "--secure"],
        ):
            stamp_pdfs.main()
        output = capsys.readouterr().out
        assert "SEC" in output
        assert "doc.pdf" in output
        # Verify encryption was applied
        with pikepdf.open(tmp_path / "doc.pdf") as pdf:
            assert pdf.is_encrypted

    def test_main_with_secure_and_watermark(self, tmp_path, capsys):
        _create_pdf(tmp_path / "doc.pdf")
        with patch(
            "sys.argv",
            ["stamp-pdfs.py", str(tmp_path), "--watermark", "DRAFT", "--secure"],
        ):
            stamp_pdfs.main()
        output = capsys.readouterr().out
        assert "WM" in output
        assert "SEC" in output

    def test_main_with_owner_password(self, tmp_path, capsys):
        _create_pdf(tmp_path / "doc.pdf")
        with patch(
            "sys.argv",
            ["stamp-pdfs.py", str(tmp_path), "--secure",
             "--owner-password", "mysecret"],
        ):
            stamp_pdfs.main()
        output = capsys.readouterr().out
        assert "SEC" in output
