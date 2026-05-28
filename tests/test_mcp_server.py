# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Tests for the Sprint 6 (S6.4) MCP server.

The server uses FastMCP (official MCP Python SDK). Tests skip when the
SDK isn't installed — `mcp[cli]` is an optional extra so the engine
remains importable without it.

Coverage focus:
  - `create_server()` returns a configured FastMCP instance
  - Tool functions resolve content from EUXIS_CONTENT_DIR
  - Resource handlers degrade gracefully when files are absent
  - CLI `main()` reports the missing-dep error path
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inclusio.mcp import server as mcp_server

pytestmark = pytest.mark.skipif(
    mcp_server.FastMCP is None,
    reason="MCP optional dep (mcp[cli]) not installed",
)


@pytest.fixture
def content_root(tmp_path, monkeypatch):
    """Stand up a minimal content tree under tmp_path + point env at it."""
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "meta.yaml").write_text(
        "author:\n  name: Test\n"
        "documents:\n"
        "  whisper-paper:\n"
        "    class: pub-paper\n"
        "    src: src/papers/whisper.tex\n"
        "    title: Whisper Paper\n"
        "  cv:\n"
        "    class: pub-cv\n"
        "    src: src/cvs/cv.tex\n"
        "    title: CV\n"
        "    pdf_a: a-4f\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EUXIS_CONTENT_DIR", str(tmp_path))
    return tmp_path


# ── create_server ──────────────────────────────────────────────────────


def test_create_server_returns_fastmcp_instance():
    app = mcp_server.create_server()
    assert app is not None
    assert app.name == "euxis-publisher"


def test_create_server_registers_tools(content_root):
    """The 4 Sprint-6 tools must be registered."""
    app = mcp_server.create_server()
    # FastMCP exposes _tool_manager.list_tools() returning the registered set
    import asyncio

    tools = asyncio.run(app.list_tools())
    names = {t.name for t in tools}
    assert {"list_docs", "audit_pdf", "render", "doc_count"} <= names


def test_create_server_registers_resources(content_root):
    """Three resources: meta, audit/latest, version."""
    app = mcp_server.create_server()
    import asyncio

    resources = asyncio.run(app.list_resources())
    uris = {str(r.uri) for r in resources}
    assert "euxis://meta" in uris
    assert "euxis://audit/latest" in uris
    assert "euxis://version" in uris


# ── _load_meta + _content_root ──────────────────────────────────────────


def test_content_root_honours_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("EUXIS_CONTENT_DIR", str(tmp_path))
    assert mcp_server._content_root() == tmp_path.resolve()


def test_content_root_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("EUXIS_CONTENT_DIR", raising=False)
    from inclusio.cli import build

    assert mcp_server._content_root() == build.CONTENT_ROOT


def test_load_meta_returns_empty_when_no_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("EUXIS_CONTENT_DIR", str(tmp_path))
    assert mcp_server._load_meta() == {}


def test_load_meta_parses_existing_yaml(content_root):
    meta = mcp_server._load_meta()
    assert "documents" in meta
    assert "whisper-paper" in meta["documents"]


# ── Tool: list_docs ────────────────────────────────────────────────────


def test_list_docs_tool_enumerates_manifest(content_root):
    """Invoke list_docs through FastMCP's tool-call surface."""
    app = mcp_server.create_server()
    import asyncio

    result = asyncio.run(app.call_tool("list_docs", {}))
    # FastMCP returns a list of content items; structured result is in
    # result[1] (the second item) when present, else parse result[0].text.
    docs = _extract_structured(result)
    assert isinstance(docs, list)
    ids = {d["id"] for d in docs}
    assert {"whisper-paper", "cv"} <= ids
    cv = next(d for d in docs if d["id"] == "cv")
    assert cv["class"] == "pub-cv"
    assert cv["pdf_a"] == "a-4f"


def test_list_docs_returns_empty_list_when_no_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("EUXIS_CONTENT_DIR", str(tmp_path))
    app = mcp_server.create_server()
    import asyncio

    result = asyncio.run(app.call_tool("list_docs", {}))
    docs = _extract_structured(result)
    assert docs == []


# ── Tool: doc_count ────────────────────────────────────────────────────


def test_doc_count_tool(content_root):
    app = mcp_server.create_server()
    import asyncio

    result = asyncio.run(app.call_tool("doc_count", {}))
    n = _extract_structured(result)
    assert n == 2


# ── Tool: audit_pdf ────────────────────────────────────────────────────


def test_audit_pdf_returns_empty_summary_when_no_pdfs(content_root):
    app = mcp_server.create_server()
    import asyncio

    result = asyncio.run(app.call_tool("audit_pdf", {}))
    rep = _extract_structured(result)
    assert rep["summary"]["pdfs"] == 0


# ── Tool: render ───────────────────────────────────────────────────────


def test_render_tool_invokes_impl(content_root, monkeypatch):
    """Drive the FastMCP-decorated `render` tool through `call_tool`."""
    rendered_dir = content_root / "build" / ".cache" / "rendered"
    rendered_dir.mkdir(parents=True)
    (rendered_dir / "cv.tex").write_text("\\documentclass{pub-cv}")
    monkeypatch.setattr(
        mcp_server.render_mod, "render_document", lambda *a, **k: None
    )
    app = mcp_server.create_server()
    import asyncio

    result = asyncio.run(
        app.call_tool("render", {"doc_id": "cv", "fmt": "latex", "mode": "draft"})
    )
    rep = _extract_structured(result)
    assert rep["doc_id"] == "cv"
    assert rep["format"] == "latex"


# ── Resources ──────────────────────────────────────────────────────────


def test_meta_resource_returns_yaml_text(content_root):
    app = mcp_server.create_server()
    import asyncio

    result = asyncio.run(app.read_resource("euxis://meta"))
    text = _resource_text(result)
    assert "whisper-paper" in text
    assert "pub-cv" in text


def test_meta_resource_returns_empty_when_no_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("EUXIS_CONTENT_DIR", str(tmp_path))
    app = mcp_server.create_server()
    import asyncio

    result = asyncio.run(app.read_resource("euxis://meta"))
    assert _resource_text(result) == ""


def test_audit_latest_resource_returns_empty_object_when_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("EUXIS_CONTENT_DIR", str(tmp_path))
    app = mcp_server.create_server()
    import asyncio

    result = asyncio.run(app.read_resource("euxis://audit/latest"))
    assert _resource_text(result) == "{}"


def test_version_resource_returns_engine_card(content_root):
    app = mcp_server.create_server()
    import asyncio

    result = asyncio.run(app.read_resource("euxis://version"))
    payload = json.loads(_resource_text(result))
    assert payload["name"] == "euxis-publisher"
    assert "version" in payload
    assert "content_root" in payload
    assert payload["mcp_spec"] == "0.1"


# ── _engine_version ────────────────────────────────────────────────────


def test_engine_version_reads_pyproject():
    assert mcp_server._engine_version()  # non-empty string
    assert mcp_server._engine_version() != "unknown"


# ── CLI entrypoint ─────────────────────────────────────────────────────


def test_main_without_mcp_installed_exits_one(monkeypatch, capsys):
    """When FastMCP is not importable, main() reports the missing-dep
    error and exits 1 — exercises the user-facing install hint."""
    monkeypatch.setattr(mcp_server, "FastMCP", None)
    rc = mcp_server.main([])
    assert rc == 1
    captured = capsys.readouterr()
    assert "FastMCP is not installed" in captured.err


def test_create_server_without_mcp_installed_raises(monkeypatch):
    monkeypatch.setattr(mcp_server, "FastMCP", None)
    with pytest.raises(RuntimeError, match="not installed"):
        mcp_server.create_server()


# ── Module-level impls (direct unit tests, FastMCP-free) ──────────────
# The FastMCP-decorated closures dispatch through the SDK runtime in a
# way that coverage doesn't trace. The thin module-level helpers below
# carry the real logic — exercise them directly so coverage stays honest.


def test_list_docs_impl_returns_manifest_records(content_root):
    docs = mcp_server._list_docs_impl()
    ids = {d["id"] for d in docs}
    assert {"whisper-paper", "cv"} <= ids
    cv = next(d for d in docs if d["id"] == "cv")
    assert cv["pdf_a"] == "a-4f"


def test_list_docs_impl_returns_empty_without_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("EUXIS_CONTENT_DIR", str(tmp_path))
    assert mcp_server._list_docs_impl() == []


def test_doc_count_impl(content_root):
    assert mcp_server._doc_count_impl() == 2


def test_audit_pdf_impl_returns_empty_summary_when_no_pdfs(content_root):
    rep = mcp_server._audit_pdf_impl()
    assert rep["summary"]["pdfs"] == 0


def test_meta_resource_impl_returns_yaml_text(content_root):
    text = mcp_server._meta_resource_impl()
    assert "whisper-paper" in text


def test_meta_resource_impl_returns_empty_when_no_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("EUXIS_CONTENT_DIR", str(tmp_path))
    assert mcp_server._meta_resource_impl() == ""


def test_audit_latest_resource_impl_returns_empty_object_when_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("EUXIS_CONTENT_DIR", str(tmp_path))
    assert mcp_server._audit_latest_resource_impl() == "{}"


def test_audit_latest_resource_impl_returns_existing_json(content_root):
    audit_dir = content_root / "build" / ".audit"
    audit_dir.mkdir(parents=True)
    (audit_dir / "latest.json").write_text('{"pdfs": 7}')
    assert mcp_server._audit_latest_resource_impl() == '{"pdfs": 7}'


def test_version_resource_impl(content_root):
    payload = json.loads(mcp_server._version_resource_impl())
    assert payload["name"] == "euxis-publisher"
    assert payload["mcp_spec"] == "0.1"


def test_render_impl_returns_metadata_dict(content_root, monkeypatch):
    """Stub render_document so we don't need a registered template fixture."""
    rendered_dir = content_root / "build" / ".cache" / "rendered"
    rendered_dir.mkdir(parents=True)
    (rendered_dir / "cv.tex").write_text("\\documentclass{pub-cv}")

    def fake_render(doc_id, fmt, build_mode, content_root):
        # No-op: the test pre-creates the output file above.
        pass

    monkeypatch.setattr(mcp_server.render_mod, "render_document", fake_render)
    out = mcp_server._render_impl("cv", fmt="latex", mode="draft")
    assert out["doc_id"] == "cv"
    assert out["format"] == "latex"
    assert out["bytes"] > 0


def test_audit_pdf_impl_with_pdfs_runs_audit(content_root, tmp_path, monkeypatch):
    """Exercise the post-empty-check path with a stub audit."""
    build_dir = content_root / "build"
    build_dir.mkdir()
    pdf_path = build_dir / "x.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n%fake\n")

    monkeypatch.setattr(
        mcp_server.audit_mod, "collect_pdfs", lambda target, build, stems: [pdf_path]
    )
    monkeypatch.setattr(
        mcp_server.audit_mod,
        "audit",
        lambda pdfs: {"summary": {"pdfs": 1, "fail": 0}, "by_pdf": {}, "by_flavour": {}},
    )
    monkeypatch.setattr(mcp_server.audit_mod, "_is_blocking", lambda r: False)
    rep = mcp_server._audit_pdf_impl(strict=True)
    assert rep["summary"]["pdfs"] == 1
    assert rep["blocking_failure"] is False


# ── Helpers ────────────────────────────────────────────────────────────


def _extract_structured(call_tool_result):
    """FastMCP `call_tool` returns (list[Content], structured_dict?)
    in 3.x. The structured payload for primitive / list returns is
    wrapped under {"result": <value>} — unwrap that. For dict returns
    the dict is returned directly. Older FastMCP returns just
    list[Content]; fall back to parsing the first text payload as JSON.
    """
    if isinstance(call_tool_result, tuple) and len(call_tool_result) >= 2:
        payload = call_tool_result[1]
        if isinstance(payload, dict) and set(payload.keys()) == {"result"}:
            return payload["result"]
        return payload
    # Fallback: parse JSON from the first text content.
    items = (
        call_tool_result
        if isinstance(call_tool_result, list)
        else (call_tool_result[0] if isinstance(call_tool_result, tuple) else [])
    )
    for item in items:
        text = getattr(item, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return None


def _resource_text(read_resource_result):
    """`read_resource` returns an iterable of (content, mime_type) or
    Content objects depending on FastMCP version. Extract the text."""
    if isinstance(read_resource_result, (list, tuple)) and read_resource_result:
        first = read_resource_result[0]
        if hasattr(first, "content"):
            return first.content
        if isinstance(first, tuple):
            return first[0] if isinstance(first[0], str) else first[0].decode()
        if hasattr(first, "text"):
            return first.text
    return str(read_resource_result)
