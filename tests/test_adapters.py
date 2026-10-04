# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Mock-verified tests for the framework adapters.

The agent frameworks (LangChain, CrewAI, LlamaIndex) are heavy and
conflict-prone, so they are NOT installed in the test environment. Instead
each adapter is exercised against a FAKE framework tool factory injected into
``sys.modules``; the fake records exactly what the adapter passes so we can
assert one framework tool per inclusio MCP tool, with the right name,
description, JSON input schema and a working callable. The missing-extra
``ImportError`` branch is covered by forcing the lazy import to fail.

This verifies the adapter LOGIC only; it is mock-verified, not live-verified
against the real frameworks. The ``[mcp]`` extra (FastMCP) IS required so
``create_server()`` can build the server the adapters introspect — the tests
skip when it is absent, matching the existing MCP-server test module.
"""

import sys
import types

import pytest

pytest.importorskip("mcp")

import inclusio.mcp.adapters as adapters  # noqa: E402
from inclusio.mcp.server import create_server  # noqa: E402

EXPECTED_TOOLS = {
    "list_docs",
    "audit_pdf",
    "render",
    "doc_count",
}


def _mcp_tool_map() -> dict:
    """Return the inclusio MCP tools keyed by name for cross-checking."""
    app = create_server()
    return {t.name: t for t in app._tool_manager.list_tools()}


class _Recorder:
    """A fake framework tool factory that records the adapter's call kwargs.

    A single class doubles as every framework's tool type: its classmethods
    (``from_function`` / ``from_defaults``) capture the callable, name,
    description and schema the adapter passes and return a lightweight object
    exposing them for assertions.
    """

    def __init__(self, *, func, name, description, schema):
        """Store the recorded attributes of one wrapped tool."""
        self.func = func
        self.name = name
        self.description = description
        self.schema = schema

    @classmethod
    def from_function(cls, *, func, name, description, args_schema):
        """Record a LangChain/CrewAI-style ``from_function`` construction."""
        return cls(func=func, name=name, description=description, schema=args_schema)

    @classmethod
    def from_defaults(cls, *, fn, name, description, fn_schema):
        """Record a LlamaIndex-style ``from_defaults`` construction."""
        return cls(func=fn, name=name, description=description, schema=fn_schema)


class _FakeToolException(Exception):
    """Stand-in for ``langchain_core.tools.ToolException``."""


def _inject(monkeypatch, dotted_names, **attrs):
    """Inject fake modules for a dotted import path into ``sys.modules``.

    Each name in ``dotted_names`` becomes an empty module; the attributes in
    ``attrs`` are set on the deepest (last) module so ``from <last> import X``
    resolves them.
    """
    modules = []
    for dotted in dotted_names:
        mod = types.ModuleType(dotted)
        monkeypatch.setitem(sys.modules, dotted, mod)
        modules.append(mod)
    for key, value in attrs.items():
        setattr(modules[-1], key, value)


def _assert_wrapped_all_tools(built):
    """Assert a built adapter list mirrors the MCP tools one-for-one."""
    mcp_tools = _mcp_tool_map()
    assert {item.name for item in built} == EXPECTED_TOOLS
    assert len(built) == len(mcp_tools)
    for item in built:
        source = mcp_tools[item.name]
        assert item.description == source.description
        assert item.schema == source.parameters
        assert item.schema["type"] == "object"


# ---------------------------------------------------------------------------
# _mcp_tools introspection
# ---------------------------------------------------------------------------
def test_mcp_tools_returns_all_registered_tools():
    """The introspection helper returns every registered MCP tool."""
    names = {t.name for t in adapters._mcp_tools()}
    assert names == EXPECTED_TOOLS


# ---------------------------------------------------------------------------
# _wrap_with_tool_exception: both branches (success + error mapping)
# ---------------------------------------------------------------------------
def test_wrap_with_tool_exception_passes_through_result():
    """A successful call passes its keyword args and result straight through."""
    wrapped = adapters._wrap_with_tool_exception(lambda **kw: {"echo": kw}, _FakeToolException)
    assert wrapped(query="x") == {"echo": {"query": "x"}}


def test_wrap_with_tool_exception_maps_raised_error():
    """A raised error is remapped to the framework's tool-exception type."""

    def _boom(**kwargs):
        """Raise to exercise the error-mapping branch."""
        raise ValueError("backend blew up")

    wrapped = adapters._wrap_with_tool_exception(_boom, _FakeToolException)
    try:
        wrapped()
        raised = False
    except _FakeToolException as exc:
        raised = True
        assert "backend blew up" in str(exc)
    assert raised is True


# ---------------------------------------------------------------------------
# LangChain adapter
# ---------------------------------------------------------------------------
def test_as_langchain_tools_wraps_every_tool(monkeypatch, tmp_path):
    """Each MCP tool becomes a StructuredTool with a live wrapped callable."""
    _inject(
        monkeypatch,
        ["langchain_core", "langchain_core.tools"],
        StructuredTool=_Recorder,
        ToolException=_FakeToolException,
    )
    built = adapters.as_langchain_tools()
    _assert_wrapped_all_tools(built)

    # The recorded callable is the ToolException-wrapping closure; calling it
    # runs the real MCP tool and returns its payload. `doc_count` reads the
    # (absent) manifest under an empty content dir and returns 0.
    monkeypatch.setenv("INCLUSIO_CONTENT_DIR", str(tmp_path))
    doc_count_tool = next(i for i in built if i.name == "doc_count")
    assert doc_count_tool.func() == 0


def test_as_langchain_tools_missing_extra_raises(monkeypatch):
    """Absent langchain-core surfaces an ImportError naming the extra."""
    monkeypatch.setitem(sys.modules, "langchain_core", None)
    try:
        adapters.as_langchain_tools()
        raised = False
    except ImportError as exc:
        raised = True
        assert "inclusio[langchain]" in str(exc)
    assert raised is True


# ---------------------------------------------------------------------------
# CrewAI adapter
# ---------------------------------------------------------------------------
def test_as_crewai_tools_wraps_every_tool(monkeypatch):
    """Each MCP tool becomes a CrewStructuredTool carrying the raw callable."""
    _inject(
        monkeypatch,
        ["crewai", "crewai.tools"],
        CrewStructuredTool=_Recorder,
    )
    built = adapters.as_crewai_tools()
    _assert_wrapped_all_tools(built)

    # CrewAI receives the raw MCP callable unchanged.
    mcp_tools = _mcp_tool_map()
    for item in built:
        assert item.func.__name__ == mcp_tools[item.name].fn.__name__


def test_as_crewai_tools_missing_extra_raises(monkeypatch):
    """Absent crewai surfaces an ImportError naming the extra."""
    monkeypatch.setitem(sys.modules, "crewai", None)
    try:
        adapters.as_crewai_tools()
        raised = False
    except ImportError as exc:
        raised = True
        assert "inclusio[crewai]" in str(exc)
    assert raised is True


# ---------------------------------------------------------------------------
# LlamaIndex adapter
# ---------------------------------------------------------------------------
def test_as_llamaindex_tools_wraps_every_tool(monkeypatch):
    """Each MCP tool becomes a FunctionTool carrying the raw callable."""
    _inject(
        monkeypatch,
        ["llama_index", "llama_index.core", "llama_index.core.tools"],
        FunctionTool=_Recorder,
    )
    built = adapters.as_llamaindex_tools()
    _assert_wrapped_all_tools(built)

    # LlamaIndex receives the raw MCP callable unchanged.
    mcp_tools = _mcp_tool_map()
    for item in built:
        assert item.func.__name__ == mcp_tools[item.name].fn.__name__


def test_as_llamaindex_tools_missing_extra_raises(monkeypatch):
    """Absent llama-index-core surfaces an ImportError naming the extra."""
    monkeypatch.setitem(sys.modules, "llama_index", None)
    try:
        adapters.as_llamaindex_tools()
        raised = False
    except ImportError as exc:
        raised = True
        assert "inclusio[llamaindex]" in str(exc)
    assert raised is True


# ---------------------------------------------------------------------------
# The adapters are plain module functions, not @app.tool: building/using them
# must not change the MCP server's advertised tool-set.
# ---------------------------------------------------------------------------
def test_adapters_do_not_alter_registered_toolset():
    """Using the adapters leaves the server's advertised tool-set unchanged."""
    names = set(_mcp_tool_map())
    assert names == EXPECTED_TOOLS
