# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Framework adapters: expose the inclusio MCP tools to agent frameworks.

The inclusio MCP server registers its tools (``list_docs``, ``audit_pdf``,
``render``, ``doc_count``) with FastMCP inside the :func:`create_server`
factory in :mod:`inclusio.mcp.server`. Agent frameworks such as LangChain,
CrewAI and LlamaIndex each have their own tool object; this module builds a
fresh server via ``create_server()``, introspects its FastMCP tool registry,
and wraps every registered tool into the requested framework's native tool
type — one framework tool per MCP tool.

Two dependency layers are optional here. The MCP server itself lives behind
the ``[mcp]`` extra (FastMCP); if it is absent, ``create_server()`` raises a
clear ``RuntimeError`` naming ``pip install 'inclusio[mcp]'``. Each
``as_*_tools`` function additionally pulls in its agent framework lazily, so
importing this module never depends on any framework. A framework is only
needed when its adapter is actually called; if it is absent the adapter
raises :class:`ImportError` naming the extra to install (e.g.
``pip install 'inclusio[langchain]'``).

The tool metadata (name, description and the JSON ``parameters`` schema) and
the underlying callable are read from the FastMCP tool registry via
:func:`_mcp_tools`. The introspected JSON input schema is passed straight
through to each framework's schema argument.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from inclusio.mcp.server import create_server


def _mcp_tools() -> list[Any]:
    """Return the inclusio MCP server's registered FastMCP tools.

    Builds the server through :func:`create_server` (which raises a clear
    ``RuntimeError`` naming the ``[mcp]`` extra when FastMCP is not
    installed) and reads its tool manager's registry, so each entry carries
    the tool's ``name``, ``description``, JSON input schema (``parameters``)
    and the underlying callable (``fn``).
    """
    app = create_server()
    return list(app._tool_manager.list_tools())


def _wrap_with_tool_exception(
    fn: Callable[..., Any], tool_exception: type[Exception]
) -> Callable[..., Any]:
    """Wrap an MCP callable so raised errors become ``tool_exception``.

    LangChain signals a recoverable tool failure by raising
    ``ToolException``; the inclusio tools normally return their result
    payload rather than raising, but any unexpected error is mapped to the
    framework's convention here.
    """

    def _call(**kwargs: Any) -> Any:
        """Invoke the wrapped tool, mapping failures to ``tool_exception``."""
        try:
            return fn(**kwargs)
        except Exception as exc:
            raise tool_exception(str(exc)) from exc

    return _call


def as_langchain_tools() -> list[Any]:
    """Wrap every inclusio MCP tool as a LangChain ``StructuredTool``.

    Returns one :class:`langchain_core.tools.StructuredTool` per registered
    MCP tool, carrying its name, description and JSON input schema; the
    callable is wrapped so raised errors surface as ``ToolException``.

    Raises:
        ImportError: if ``langchain-core`` is not installed
            (``pip install 'inclusio[langchain]'``).
        RuntimeError: if the ``[mcp]`` extra (FastMCP) is not installed.
    """
    try:
        from langchain_core.tools import StructuredTool, ToolException
    except ImportError as exc:
        raise ImportError(
            "LangChain is not installed. Install it with "
            "`pip install 'inclusio[langchain]'`."
        ) from exc

    return [
        StructuredTool.from_function(
            func=_wrap_with_tool_exception(tool.fn, ToolException),
            name=tool.name,
            description=tool.description,
            args_schema=tool.parameters,
        )
        for tool in _mcp_tools()
    ]


def as_crewai_tools() -> list[Any]:
    """Wrap every inclusio MCP tool as a CrewAI ``CrewStructuredTool``.

    Returns one ``crewai.tools.CrewStructuredTool`` per registered MCP tool,
    carrying its name, description, JSON input schema and callable.

    Raises:
        ImportError: if CrewAI is not installed
            (``pip install 'inclusio[crewai]'``).
        RuntimeError: if the ``[mcp]`` extra (FastMCP) is not installed.
    """
    try:
        from crewai.tools import CrewStructuredTool
    except ImportError as exc:
        raise ImportError(
            "CrewAI is not installed. Install it with "
            "`pip install 'inclusio[crewai]'`."
        ) from exc

    return [
        CrewStructuredTool.from_function(
            func=tool.fn,
            name=tool.name,
            description=tool.description,
            args_schema=tool.parameters,
        )
        for tool in _mcp_tools()
    ]


def as_llamaindex_tools() -> list[Any]:
    """Wrap every inclusio MCP tool as a LlamaIndex ``FunctionTool``.

    Returns one ``llama_index.core.tools.FunctionTool`` per registered MCP
    tool, carrying its name, description, JSON input schema and callable.

    Raises:
        ImportError: if ``llama-index-core`` is not installed
            (``pip install 'inclusio[llamaindex]'``).
        RuntimeError: if the ``[mcp]`` extra (FastMCP) is not installed.
    """
    try:
        from llama_index.core.tools import FunctionTool
    except ImportError as exc:
        raise ImportError(
            "LlamaIndex is not installed. Install it with "
            "`pip install 'inclusio[llamaindex]'`."
        ) from exc

    return [
        FunctionTool.from_defaults(
            fn=tool.fn,
            name=tool.name,
            description=tool.description,
            fn_schema=tool.parameters,
        )
        for tool in _mcp_tools()
    ]
