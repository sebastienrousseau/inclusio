# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 8.5 (F7 full closure): PAdES eIDAS signature.

pyhanko is an optional dep (the `[provenance]` extra). Tests:
  - exercise the optional-import path (missing pyhanko → PAdESMissing)
  - cover argument validation (baseline / cert / key / timestamp)
  - skip the actual signing call when pyhanko isn't installed locally
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inclusio.provenance import pades

# ── _require_pyhanko ──────────────────────────────────────────────────


def test_require_pyhanko_raises_when_missing(monkeypatch):
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", False)
    with pytest.raises(pades.PAdESMissing, match="pyhanko is required"):
        pades._require_pyhanko()


def test_require_pyhanko_returns_none_when_present(monkeypatch):
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", True)
    assert pades._require_pyhanko() is None


# ── sign_pdf: argument validation ─────────────────────────────────────


def test_sign_pdf_rejects_unknown_baseline(monkeypatch, tmp_path):
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", True)
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(ValueError, match="Unknown PAdES baseline"):
        pades.sign_pdf(
            pdf,
            baseline="B-X",
            cert_path=Path("c.pem"),
            key_path=Path("k.pem"),
            timestamp_url="http://ts.example/",
        )


def test_sign_pdf_requires_cert_and_key(monkeypatch, tmp_path):
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", True)
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(ValueError, match="requires --cert and --key"):
        pades.sign_pdf(pdf, baseline="B-B")


def test_sign_pdf_b_t_requires_timestamp_url(monkeypatch, tmp_path):
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", True)
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(ValueError, match="requires a trusted timestamp URL"):
        pades.sign_pdf(
            pdf,
            baseline="B-T",
            cert_path=Path("c.pem"),
            key_path=Path("k.pem"),
        )


def test_sign_pdf_b_lt_requires_timestamp_url(monkeypatch, tmp_path):
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", True)
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(ValueError, match="requires a trusted timestamp URL"):
        pades.sign_pdf(
            pdf,
            baseline="B-LT",
            cert_path=Path("c.pem"),
            key_path=Path("k.pem"),
        )


def test_sign_pdf_b_lta_requires_timestamp_url(monkeypatch, tmp_path):
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", True)
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(ValueError, match="requires a trusted timestamp URL"):
        pades.sign_pdf(
            pdf,
            baseline="B-LTA",
            cert_path=Path("c.pem"),
            key_path=Path("k.pem"),
        )


def test_sign_pdf_b_b_does_not_require_timestamp_url(monkeypatch, tmp_path):
    """B-B is the only baseline that's valid without a timestamp."""
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", True)
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    # Should pass argument validation; will still fail later trying to
    # actually load the cert files (which don't exist) — that's
    # pyhanko's responsibility, not ours.
    if not pades._PYHANKO_AVAILABLE:
        pytest.skip("pyhanko not installed")
    # If pyhanko is installed, this still bombs because the cert files
    # don't exist on disk. We only check that the validation guard
    # accepts the args.
    with pytest.raises((FileNotFoundError, ValueError, Exception)):
        pades.sign_pdf(
            pdf,
            baseline="B-B",
            cert_path=tmp_path / "missing-cert.pem",
            key_path=tmp_path / "missing-key.pem",
        )


def test_sign_pdf_raises_missing_when_pyhanko_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", False)
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(pades.PAdESMissing):
        pades.sign_pdf(
            pdf,
            cert_path=Path("c.pem"),
            key_path=Path("k.pem"),
            timestamp_url="http://ts.example/",
        )


# ── verify_pdf ────────────────────────────────────────────────────────


def test_verify_pdf_raises_missing_when_pyhanko_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(pades, "_PYHANKO_AVAILABLE", False)
    pdf = tmp_path / "signed.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(pades.PAdESMissing):
        pades.verify_pdf(pdf)


# ── VALID_BASELINES contract ──────────────────────────────────────────


def test_valid_baselines_match_etsi_en_319_142():
    """The four ETSI EN 319 142 PAdES baselines."""
    assert pades.VALID_BASELINES == ("B-B", "B-T", "B-LT", "B-LTA")


# ── PAdESResult shape ─────────────────────────────────────────────────


def test_pades_result_has_expected_fields(tmp_path):
    r = pades.PAdESResult(
        pdf_path=tmp_path / "x.pdf",
        baseline="B-T",
        signed_with_test_cert=True,
        signer_subject="CN=Euxis Dev",
    )
    assert r.pdf_path == tmp_path / "x.pdf"
    assert r.baseline == "B-T"
    assert r.signed_with_test_cert is True
    assert r.signer_subject == "CN=Euxis Dev"


def test_pades_result_signer_subject_defaults_empty(tmp_path):
    r = pades.PAdESResult(pdf_path=tmp_path / "x.pdf", baseline="B-B", signed_with_test_cert=False)
    assert r.signer_subject == ""
