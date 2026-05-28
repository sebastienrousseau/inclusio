# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Local LLM adapter for the judge pipeline (Sprint 7, S7.1).

Wraps the `llama.cpp` HTTP server (default port 8080) as the canonical
local LLM backend for judges. Per decision D4 (docs/strategy-2026.md),
judges are local-first: sensitive content (unpublished CVs, draft
patents, salary signals) must not leave the machine without explicit
opt-in.

Why llama.cpp specifically:
  - Single static binary; no Python ML stack.
  - OpenAI-compatible /v1/chat/completions endpoint AND a native
    /completion endpoint with a smaller request shape.
  - Runs Llama-3-8B-Instruct, Qwen 2.5, Phi-3, Gemma 2, Mistral 7B
    on a 16 GB M-series Mac at >30 tok/s for the quantised builds.

This adapter uses stdlib `urllib.request` only — no `httpx` /
`requests` dependency, so callers don't pull a heavy HTTP stack just
to ask the judge whether their CV reads well.

Usage:

    from euxis_publisher.judge.local_llm import LocalLLM

    llm = LocalLLM(base_url="http://localhost:8080")
    response = llm.complete(
        prompt="Score this CV for ATS compatibility...",
        max_tokens=512,
        temperature=0.2,
    )
    # Or, for JSON-schema-constrained output:
    payload = llm.complete_json(prompt, schema={...})
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


class LLMError(RuntimeError):
    """Base for every local-LLM failure mode."""


class LLMUnavailable(LLMError):
    """llama.cpp server unreachable (ECONNREFUSED / DNS failure)."""


class LLMTimeout(LLMError):
    """Request exceeded the configured timeout."""


class LLMParseError(LLMError):
    """Response body did not match the expected JSON shape."""


@dataclass(frozen=True)
class LLMResponse:
    """One completion result.

    Attributes:
        content: the generated text (`content` field from llama.cpp).
        tokens_predicted: number of tokens the server actually generated.
        stopped_reason: one of `eos`, `limit`, `word`, or empty when
            the server didn't surface a stop reason.
        raw: the full server JSON for callers that need provenance.
    """

    content: str
    tokens_predicted: int = 0
    stopped_reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


# ── Public API ─────────────────────────────────────────────────────────


@dataclass
class LocalLLM:
    """Thin client over the llama.cpp HTTP `/completion` endpoint.

    Attributes:
        base_url: server root, e.g. `http://localhost:8080`. The
            adapter appends `/completion` to this for the native API.
        timeout: per-request timeout in seconds.
        default_max_tokens: cap when callers don't pass one.
        default_temperature: 0.2 is a good "judge" default — focused
            but not deterministic.
    """

    base_url: str = "http://localhost:8080"
    timeout: int = 30
    default_max_tokens: int = 512
    default_temperature: float = 0.2

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST JSON to `<base_url><path>` and decode the response."""
        url = f"{self.base_url.rstrip('/')}{path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = resp.read().decode("utf-8")
        except urllib.error.URLError as exc:
            # ECONNREFUSED, DNS failure, and ssl errors all land here.
            if isinstance(exc.reason, socket.timeout):
                raise LLMTimeout(
                    f"llama.cpp at {self.base_url} timed out after {self.timeout}s"
                ) from exc
            raise LLMUnavailable(f"llama.cpp at {self.base_url} unreachable: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LLMTimeout(
                f"llama.cpp at {self.base_url} timed out after {self.timeout}s"
            ) from exc
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise LLMParseError(f"non-JSON response from {url}: {payload[:200]!r}") from exc

    def complete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Request a single completion. Returns an LLMResponse.

        Args:
            prompt: full prompt text (no chat-template wrapping —
                callers supply the right wrapping for their model).
            max_tokens: hard cap on generated tokens.
            temperature: sampling temperature (0.0 = greedy).
            stop: optional list of stop strings.
        """
        body: dict[str, Any] = {
            "prompt": prompt,
            "n_predict": max_tokens or self.default_max_tokens,
            "temperature": (temperature if temperature is not None else self.default_temperature),
        }
        if stop:
            body["stop"] = stop
        data = self._post("/completion", body)
        return LLMResponse(
            content=data.get("content", ""),
            tokens_predicted=int(data.get("tokens_predicted", 0)),
            stopped_reason=str(data.get("stopped_reason", "")),
            raw=data,
        )

    def complete_json(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Request a completion and parse the response body as JSON.

        Llama.cpp's grammar-constrained JSON output is the recommended
        path here — callers should bake `Respond with valid JSON only.`
        into the prompt and consider running the server with a JSON
        grammar file (`--grammar-file json.gbnf`). This wrapper
        tolerates fenced-code blocks (```json ... ```) by stripping
        them before parsing.
        """
        response = self.complete(prompt, max_tokens=max_tokens, temperature=temperature)
        text = response.content.strip()
        # Strip ```json ... ``` fences if the model emitted them.
        if text.startswith("```"):
            text = text.split("```", 2)[1] if "```" in text[3:] else text[3:]
            text = text.removeprefix("json").strip()
            text = text.rsplit("```", 1)[0].strip() if "```" in text else text
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMParseError(f"completion was not valid JSON: {text[:200]!r}") from exc

    def is_available(self) -> bool:
        """Return True iff the server responds to a small probe.

        Useful as a fast pre-flight check before running an LLM judge
        — avoids the longer error trail from a real `complete()` call.
        """
        try:
            self.complete(prompt="ping", max_tokens=1, temperature=0.0)
            return True
        except LLMError:
            return False


# ── Prompt template helpers ────────────────────────────────────────────


ATS_RERANK_SYSTEM = (
    "You are an ATS-conformance reviewer. The heuristic judge has "
    "already scored the candidate's CV. Read the plain-text CV below "
    "and identify ONE additional concern the heuristic missed — tone "
    "match, role-level mismatch, keyword cluster gaps, or content "
    "ambiguity. Respond with strict JSON only, no prose, no fences."
)


ATS_RERANK_SCHEMA = {
    "score_adjustment": "integer (-15 to +5; negative = penalty)",
    "finding": {
        "check": "string id, e.g. tone_match",
        "severity": "one of warn, block, info",
        "message": "short human-readable note",
        "deduction": "integer 0-15",
    },
}


def build_ats_rerank_prompt(plain_text_cv: str) -> str:
    """Compose the prompt that asks an LLM to rerank an ATS heuristic
    score. Output schema documented in `ATS_RERANK_SCHEMA`."""
    schema_str = json.dumps(ATS_RERANK_SCHEMA, indent=2)
    cv = plain_text_cv.strip()[:6000]  # cap to fit short-context models
    return (
        f"{ATS_RERANK_SYSTEM}\n\n"
        f"Output schema:\n{schema_str}\n\n"
        f"CV (plain text):\n---\n{cv}\n---\n\n"
        f"Respond with valid JSON only:"
    )
