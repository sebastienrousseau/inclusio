# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Cloud LLM adapter for the judge pipeline (Sprint 7, S7.5).

Mirrors the `LocalLLM` (S7.1) interface against Anthropic's Messages API
and any OpenAI-compatible /v1/chat/completions endpoint (OpenAI itself,
xAI, Together, Groq, DeepSeek, Cerebras, etc.). Per decision D4
(docs/strategy-2026.md), cloud is opt-in: API keys come from env vars
or explicit constructor args — never auto-detected from disk.

When to use cloud vs local:
  - `LocalLLM` (S7.1): default. Sensitive content (unpublished CVs,
    draft patents, salary signals). Zero data leakage.
  - `CloudLLM` (S7.5): use when the LLM-rerank quality matters more
    than data residency — e.g. ad-hoc CV reviews, public papers,
    citation grounding at scale.

The two adapters expose the same `complete(prompt)` and
`complete_json(prompt)` methods so every judge in this package
(ATS, citations, JD-fit) routes through either backend by simple
substitution.

Provider detection from the base URL:
  - contains `anthropic.com` → Anthropic Messages API
  - else → OpenAI-compatible /v1/chat/completions

Both are stdlib-only (urllib.request + json). No `httpx` / `anthropic` /
`openai` SDK dependency — keeps the engine deployable in air-gapped
environments without an opt-in pip extra.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .local_llm import LLMError, LLMParseError, LLMResponse, LLMTimeout, LLMUnavailable

_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


@dataclass
class CloudLLM:
    """Cloud LLM client — Anthropic Messages or OpenAI-compatible chat.

    Attributes:
        base_url: provider root. Defaults to Anthropic.
        model: model id. For Anthropic, e.g. `claude-opus-4-7`; for
            OpenAI-compatible, e.g. `gpt-5-pro` or any model the
            endpoint accepts.
        api_key: explicit key. When None, falls back to the env var
            for the detected provider (ANTHROPIC_API_KEY /
            OPENAI_API_KEY). Missing key → `LLMUnavailable`.
        timeout: per-request timeout in seconds.
        default_max_tokens: cap when callers don't pass one.
        default_temperature: 0.2 = focused judge default.
    """

    base_url: str = "https://api.anthropic.com"
    model: str = "claude-opus-4-7"
    api_key: str | None = None
    timeout: int = 60
    default_max_tokens: int = 1024
    default_temperature: float = 0.2

    @property
    def provider(self) -> str:
        """Detected provider name (`anthropic` / `openai`)."""
        if "anthropic" in self.base_url:
            return "anthropic"
        return "openai"

    def _resolved_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        env_key = _ENV_KEYS[self.provider]
        key = os.environ.get(env_key)
        if not key:
            raise LLMUnavailable(f"Missing API key — set {env_key} or pass api_key= explicitly.")
        return key

    def _endpoint(self) -> str:
        if self.provider == "anthropic":
            return f"{self.base_url.rstrip('/')}/v1/messages"
        return f"{self.base_url.rstrip('/')}/v1/chat/completions"

    def _headers(self, api_key: str) -> dict[str, str]:
        if self.provider == "anthropic":
            return {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "accept": "application/json",
            }
        return {
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
            "accept": "application/json",
        }

    def _build_body(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: list[str] | None,
    ) -> dict[str, Any]:
        if self.provider == "anthropic":
            body: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if stop:
                body["stop_sequences"] = stop
            return body
        # OpenAI-compatible
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if stop:
            body["stop"] = stop
        return body

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        """Normalise the provider response into an LLMResponse."""
        if self.provider == "anthropic":
            # Anthropic: content is a list of content blocks; take the
            # first text block.
            content_blocks = data.get("content", []) or []
            text = ""
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    break
            usage = data.get("usage", {}) or {}
            return LLMResponse(
                content=text,
                tokens_predicted=int(usage.get("output_tokens", 0)),
                stopped_reason=str(data.get("stop_reason", "")),
                raw=data,
            )
        # OpenAI-compatible
        choices = data.get("choices", []) or []
        text = ""
        finish_reason = ""
        if choices:
            first = choices[0] or {}
            message = first.get("message", {}) or {}
            text = message.get("content", "") or ""
            finish_reason = str(first.get("finish_reason", ""))
        usage = data.get("usage", {}) or {}
        return LLMResponse(
            content=text,
            tokens_predicted=int(usage.get("completion_tokens", 0)),
            stopped_reason=finish_reason,
            raw=data,
        )

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        url = self._endpoint()
        api_key = self._resolved_api_key()
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(api_key),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # 401/403/429/5xx — surface as Unavailable so the judge
            # falls back to heuristic-only with a clear breadcrumb.
            raise LLMUnavailable(f"{self.provider} HTTP {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, socket.timeout):
                raise LLMTimeout(
                    f"{self.provider} at {url} timed out after {self.timeout}s"
                ) from exc
            raise LLMUnavailable(f"{self.provider} unreachable: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LLMTimeout(f"{self.provider} at {url} timed out after {self.timeout}s") from exc
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
        """Single completion request. Returns LLMResponse."""
        body = self._build_body(
            prompt=prompt,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=(temperature if temperature is not None else self.default_temperature),
            stop=stop,
        )
        data = self._post(body)
        return self._parse_response(data)

    def complete_json(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Completion + JSON parse. Tolerates ```json fenced output."""
        response = self.complete(prompt, max_tokens=max_tokens, temperature=temperature)
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1] if "```" in text[3:] else text[3:]
            text = text.removeprefix("json").strip()
            text = text.rsplit("```", 1)[0].strip() if "```" in text else text
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMParseError(f"completion was not valid JSON: {text[:200]!r}") from exc

    def is_available(self) -> bool:
        """True iff a small probe completes without raising LLMError."""
        try:
            self.complete(prompt="ping", max_tokens=1, temperature=0.0)
            return True
        except LLMError:
            return False


def from_url(url: str, **kwargs: Any):
    """Detect Local vs Cloud from *url* and return the right adapter.

    Cloud is keyed off `anthropic.com` or `openai.com` in the URL;
    everything else is treated as a local llama.cpp instance.
    """
    # Avoid a circular import when this module is loaded standalone.
    from .local_llm import LocalLLM

    if "anthropic.com" in url or "openai.com" in url:
        # Drop kwargs that don't apply to CloudLLM (e.g. `timeout`
        # is shared, but local-only flags would error).
        cloud_kwargs = {k: v for k, v in kwargs.items() if k in {"timeout", "model", "api_key"}}
        return CloudLLM(base_url=url, **cloud_kwargs)
    local_kwargs = {k: v for k, v in kwargs.items() if k in {"timeout"}}
    return LocalLLM(base_url=url, **local_kwargs)
