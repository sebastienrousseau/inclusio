<!-- SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com> -->
<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# AGENTS.md

Invariants for AI-assisted contributions to `inclusio`. Read this before changing anything.

Everything here applies equally to humans and automated agents. It is addressed to agents because agents can make breaking changes across multiple files before anyone notices.

## 1. Core Invariants

1. **Strict SemVer sequencing policy**: Public releases stay on the `0.0.x` line and increment strictly by `0.0.1`. Never manually edit version numbers outside the active release branch `feat/v<next-version>`. `v0.1.0` is forbidden until `v0.0.999` exists.
2. **Single Active Release PR Invariant**: Across all repositories, there MUST be at most ONE active pull request targeting `main`, which MUST be the release iteration branch `feat/v<next-version>`.
3. **Dual licensing**: The repository is dual-licensed under Apache-2.0 OR MIT. All files must declare an SPDX license header.
4. **Single source of truth**: The version in `pyproject.toml` (`[project] version`) is the single source of truth. It must agree with `glama.json`, `server.json`, `CITATION.cff`, and `CHANGELOG.md` (verified by `scripts/verify_versions.py`).
5. **Deterministic accessibility**: All MCP and engine tools (`list_docs`, `audit_pdf`, `render`, `doc_count`) must preserve accessibility conformance standards (PDF/UA-2, WTPDF, PDF/A-4f) and remain side-effect-safe.

## 2. Before You Claim To Be Done (Verification Gates)

Before concluding any task or preparing a commit, run:

```console
pytest tests/test_mcp_server.py tests/test_adapters.py
ruff check inclusio/
python3 scripts/verify_versions.py
```

## 3. Things That Look Like Bugs and Are Not

- **MCP extra is optional**: `inclusio` works as a standalone CLI without `mcp`. `create_server()` raises a clear `RuntimeError` prompting the caller to install `inclusio[mcp]`.
- **Framework adapters are lazy**: `inclusio.mcp.adapters` exports tools for LangChain, CrewAI, and LlamaIndex without making those heavy packages mandatory dependencies.
