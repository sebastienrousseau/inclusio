# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 8 (F7 closure): C2PA Content Credentials.

Tests the subprocess wrapper around `c2patool`. All `c2patool` calls
are mocked so the test suite runs without the binary installed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inclusio.provenance import c2pa

# ── _require_c2patool ──────────────────────────────────────────────────


def test_require_c2patool_raises_when_missing(monkeypatch):
    monkeypatch.setattr(c2pa.shutil, "which", lambda _x: None)
    with pytest.raises(c2pa.C2PAMissing, match="c2patool is required"):
        c2pa._require_c2patool()


def test_require_c2patool_returns_path_when_present(monkeypatch):
    monkeypatch.setattr(c2pa.shutil, "which", lambda _x: "/fake/c2patool")
    assert c2pa._require_c2patool() == "/fake/c2patool"


# ── build_manifest_json ────────────────────────────────────────────────


def test_manifest_includes_claim_generator():
    js = c2pa.build_manifest_json(title="T", author="A")
    payload = json.loads(js)
    assert payload["claim_generator"] == "inclusio/0.1.0"
    assert payload["format"] == "application/pdf"
    assert payload["title"] == "T"


def test_manifest_schema_org_assertion_shape():
    js = c2pa.build_manifest_json(
        title="Whisper Paper", author="Sebastien Rousseau", publisher="Test Pub"
    )
    payload = json.loads(js)
    schema = next(a for a in payload["assertions"] if a["label"] == "stds.schema-org.CreativeWork")
    data = schema["data"]
    assert data["@type"] == "CreativeWork"
    assert data["name"] == "Whisper Paper"
    assert data["author"][0]["name"] == "Sebastien Rousseau"
    assert data["publisher"]["name"] == "Test Pub"


def test_manifest_includes_c2pa_actions_assertion():
    payload = json.loads(c2pa.build_manifest_json(title="T", author="A"))
    actions = next(a for a in payload["assertions"] if a["label"] == "c2pa.actions")
    assert actions["data"]["actions"] == [{"action": "c2pa.created"}]


def test_manifest_date_published_omitted_when_none():
    payload = json.loads(c2pa.build_manifest_json(title="T", author="A"))
    schema = next(a for a in payload["assertions"] if a["label"] == "stds.schema-org.CreativeWork")
    assert "datePublished" not in schema["data"]


def test_manifest_date_published_emitted_when_set():
    payload = json.loads(
        c2pa.build_manifest_json(title="T", author="A", date_published="2026-05-28")
    )
    schema = next(a for a in payload["assertions"] if a["label"] == "stds.schema-org.CreativeWork")
    assert schema["data"]["datePublished"] == "2026-05-28"


def test_manifest_ai_disclosure_appended_when_present():
    payload = json.loads(
        c2pa.build_manifest_json(
            title="T",
            author="A",
            ai_disclosure="Drafted by Llama 3 8B; author edited.",
        )
    )
    training = next(a for a in payload["assertions"] if a["label"] == "c2pa.training-mining")
    assert training["data"]["entries"]["c2pa.ai_inference"]["use"] == "notAllowed"
    assert "Llama 3 8B" in training["data"]["disclosure"]


def test_manifest_no_ai_disclosure_means_no_training_assertion():
    payload = json.loads(c2pa.build_manifest_json(title="T", author="A"))
    labels = [a["label"] for a in payload["assertions"]]
    assert "c2pa.training-mining" not in labels


def test_manifest_extra_assertions_merged():
    extra = [{"label": "stds.exif", "data": {"key": "value"}}]
    payload = json.loads(c2pa.build_manifest_json(title="T", author="A", extra_assertions=extra))
    labels = [a["label"] for a in payload["assertions"]]
    assert "stds.exif" in labels


def test_manifest_claim_generator_version_override():
    payload = json.loads(
        c2pa.build_manifest_json(
            title="T",
            author="A",
            claim_generator="custom-tool",
            claim_generator_version="2.0.0-rc1",
        )
    )
    assert payload["claim_generator"] == "custom-tool/2.0.0-rc1"


# ── embed_manifest ─────────────────────────────────────────────────────


@pytest.fixture
def stub_c2patool(monkeypatch):
    """Stub the subprocess.run call. Records argv + writes a fake output."""
    captured = {"argv": None}

    def fake_which(_x):
        return "/fake/c2patool"

    def fake_run(argv, capture_output=False, text=False, timeout=None, check=False):
        captured["argv"] = list(argv)
        # Emulate --output by writing the input file content + 200 bytes
        # so manifest_bytes is computed deterministically.
        try:
            input_pdf = Path(argv[1])
            out_idx = argv.index("--output") + 1
            out_path = Path(argv[out_idx])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(input_pdf.read_bytes() + b"X" * 200)
        except (ValueError, IndexError):
            pass
        return mock.MagicMock(
            returncode=0,
            stdout="",
            stderr="c2patool 0.x using test_cert (development only)",
        )

    monkeypatch.setattr(c2pa.shutil, "which", fake_which)
    monkeypatch.setattr(c2pa.subprocess, "run", fake_run)
    return captured


def test_embed_manifest_invokes_c2patool_with_expected_argv(stub_c2patool, tmp_path):
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%dummy\n")
    manifest = c2pa.build_manifest_json(title="T", author="A")
    c2pa.embed_manifest(pdf, manifest)
    argv = stub_c2patool["argv"]
    assert argv[0] == "/fake/c2patool"
    assert str(pdf) in argv
    assert "--manifest" in argv
    assert "--output" in argv
    assert "--force" in argv


def test_embed_manifest_writes_manifest_to_temp_file(stub_c2patool, tmp_path):
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%dummy\n")
    manifest = c2pa.build_manifest_json(title="T", author="A")
    c2pa.embed_manifest(pdf, manifest)
    # Manifest file was written next to the output PDF.
    expected = tmp_path / "in.c2pa.manifest.json"
    assert expected.exists()
    assert "claim_generator" in expected.read_text()


def test_embed_manifest_default_output_path(stub_c2patool, tmp_path):
    """Without output_path, signed PDF lands at <stem>.c2pa.pdf."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%dummy\n")
    result = c2pa.embed_manifest(pdf, c2pa.build_manifest_json(title="T", author="A"))
    assert result.pdf_path == tmp_path / "doc.c2pa.pdf"
    assert result.pdf_path.exists()


def test_embed_manifest_custom_output_path(stub_c2patool, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%dummy\n")
    out = tmp_path / "subdir" / "signed.pdf"
    c2pa.embed_manifest(pdf, c2pa.build_manifest_json(title="T", author="A"), output_path=out)
    assert out.exists()


def test_embed_manifest_signed_with_test_cert_when_no_cert(stub_c2patool, tmp_path):
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%dummy\n")
    result = c2pa.embed_manifest(pdf, c2pa.build_manifest_json(title="T", author="A"))
    assert result.signed_with_test_cert is True


def test_embed_manifest_with_cert_and_key_passes_signer_args(stub_c2patool, tmp_path):
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%dummy\n")
    cert = tmp_path / "cert.pem"
    cert.write_text("cert")
    key = tmp_path / "key.pem"
    key.write_text("key")
    c2pa.embed_manifest(
        pdf,
        c2pa.build_manifest_json(title="T", author="A"),
        cert_path=cert,
        key_path=key,
    )
    argv = stub_c2patool["argv"]
    assert "--signer" in argv
    assert str(cert) in argv
    assert "--signer-key" in argv
    assert str(key) in argv


def test_embed_manifest_raises_on_c2patool_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(c2pa.shutil, "which", lambda _x: "/fake/c2patool")

    def fake_run(*_a, **_k):
        return mock.MagicMock(returncode=1, stdout="", stderr="invalid manifest")

    monkeypatch.setattr(c2pa.subprocess, "run", fake_run)
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(subprocess.CalledProcessError):
        c2pa.embed_manifest(pdf, c2pa.build_manifest_json(title="T", author="A"))


def test_embed_manifest_records_manifest_bytes(stub_c2patool, tmp_path):
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%dummy\n")  # 17 bytes
    result = c2pa.embed_manifest(pdf, c2pa.build_manifest_json(title="T", author="A"))
    # Stub adds 200 bytes; manifest_bytes ≈ 200.
    assert result.manifest_bytes == 200


# ── verify_manifest ────────────────────────────────────────────────────


def test_verify_manifest_parses_c2patool_json(monkeypatch, tmp_path):
    monkeypatch.setattr(c2pa.shutil, "which", lambda _x: "/fake/c2patool")
    response = {"active_manifest": "id-1", "manifests": {"id-1": {"title": "T"}}}

    def fake_run(*_a, **_k):
        return mock.MagicMock(returncode=0, stdout=json.dumps(response), stderr="")

    monkeypatch.setattr(c2pa.subprocess, "run", fake_run)
    pdf = tmp_path / "signed.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    out = c2pa.verify_manifest(pdf)
    assert out == response


def test_verify_manifest_returns_empty_when_no_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(c2pa.shutil, "which", lambda _x: "/fake/c2patool")

    def fake_run(*_a, **_k):
        return mock.MagicMock(returncode=1, stdout="", stderr="no manifest")

    monkeypatch.setattr(c2pa.subprocess, "run", fake_run)
    pdf = tmp_path / "unsigned.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    assert c2pa.verify_manifest(pdf) == {}


def test_verify_manifest_handles_invalid_json(monkeypatch, tmp_path):
    monkeypatch.setattr(c2pa.shutil, "which", lambda _x: "/fake/c2patool")

    def fake_run(*_a, **_k):
        return mock.MagicMock(returncode=0, stdout="not json", stderr="")

    monkeypatch.setattr(c2pa.subprocess, "run", fake_run)
    pdf = tmp_path / "bad.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    assert c2pa.verify_manifest(pdf) == {}
