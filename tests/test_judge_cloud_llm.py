# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 7 (S7.5): tests for the cloud LLM adapter.

Mirrors the local-LLM test surface against the two cloud providers:
  - Anthropic Messages API (`/v1/messages`)
  - OpenAI-compatible chat completions (`/v1/chat/completions`)

Mocks `urllib.request.urlopen` so tests are fully deterministic and
require no network / API key.
"""

from __future__ import annotations

import json
import sys
import urllib.error
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inclusio.judge import cloud_llm as cl
from inclusio.judge import local_llm as llm_mod

# ── Helpers ────────────────────────────────────────────────────────────


@contextmanager
def _stub_urlopen(response_json=None, raise_exc=None):
    def fake_urlopen(req, timeout=None):
        fake_urlopen.calls.append(
            {
                "url": req.get_full_url(),
                "method": req.get_method(),
                "headers": dict(req.headers),
                "data": req.data,
                "timeout": timeout,
            }
        )
        if raise_exc is not None:
            raise raise_exc
        body = json.dumps(response_json or {}).encode("utf-8")
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False
        return mock_resp

    fake_urlopen.calls = []
    with mock.patch.object(cl.urllib.request, "urlopen", fake_urlopen):
        yield fake_urlopen


# ── Provider detection ────────────────────────────────────────────────


def test_provider_anthropic_when_url_contains_anthropic():
    assert cl.CloudLLM(base_url="https://api.anthropic.com").provider == "anthropic"


def test_provider_openai_when_url_contains_openai():
    assert cl.CloudLLM(base_url="https://api.openai.com").provider == "openai"


def test_provider_openai_for_unknown_url():
    """Anything else → OpenAI-compatible default (xAI, Together, Groq…)."""
    assert cl.CloudLLM(base_url="https://api.groq.com").provider == "openai"


# ── API-key resolution ────────────────────────────────────────────────


def test_resolves_explicit_api_key():
    llm = cl.CloudLLM(api_key="explicit-key")
    assert llm._resolved_api_key() == "explicit-key"


def test_falls_back_to_anthropic_env_var(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-anthropic-key")
    llm = cl.CloudLLM(base_url="https://api.anthropic.com")
    assert llm._resolved_api_key() == "env-anthropic-key"


def test_falls_back_to_openai_env_var(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    llm = cl.CloudLLM(base_url="https://api.openai.com")
    assert llm._resolved_api_key() == "env-openai-key"


def test_missing_api_key_raises_unavailable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    llm = cl.CloudLLM(base_url="https://api.anthropic.com")
    with pytest.raises(llm_mod.LLMUnavailable, match="ANTHROPIC_API_KEY"):
        llm._resolved_api_key()


# ── Anthropic request shape ───────────────────────────────────────────


def test_anthropic_endpoint_path():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    assert llm._endpoint() == "https://api.anthropic.com/v1/messages"


def test_anthropic_request_includes_required_headers():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    response = {
        "content": [{"type": "text", "text": "ok"}],
        "stop_reason": "end_turn",
        "usage": {"output_tokens": 1},
    }
    with _stub_urlopen(response) as stub:
        result = llm.complete("hello")
    assert result.content == "ok"
    assert result.tokens_predicted == 1
    assert result.stopped_reason == "end_turn"
    headers = stub.calls[0]["headers"]
    assert headers.get("X-api-key") == "k"
    assert headers.get("Anthropic-version") == "2023-06-01"
    body = json.loads(stub.calls[0]["data"].decode("utf-8"))
    assert body["model"] == "claude-opus-4-7"
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    assert body["max_tokens"] == 1024


def test_anthropic_propagates_stop_sequences():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    response = {"content": [{"type": "text", "text": ""}]}
    with _stub_urlopen(response) as stub:
        llm.complete("x", stop=["###"])
    body = json.loads(stub.calls[0]["data"].decode("utf-8"))
    assert body["stop_sequences"] == ["###"]


def test_anthropic_handles_empty_content_blocks():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    response = {"content": [], "stop_reason": "max_tokens"}
    with _stub_urlopen(response):
        result = llm.complete("x")
    assert result.content == ""
    assert result.stopped_reason == "max_tokens"


# ── OpenAI-compatible request shape ───────────────────────────────────


def test_openai_endpoint_path():
    llm = cl.CloudLLM(base_url="https://api.openai.com", api_key="k")
    assert llm._endpoint() == "https://api.openai.com/v1/chat/completions"


def test_openai_request_uses_bearer_auth():
    llm = cl.CloudLLM(base_url="https://api.openai.com", api_key="k", model="gpt-5-pro")
    response = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"completion_tokens": 1},
    }
    with _stub_urlopen(response) as stub:
        result = llm.complete("hello")
    assert result.content == "ok"
    assert result.tokens_predicted == 1
    assert result.stopped_reason == "stop"
    headers = stub.calls[0]["headers"]
    assert headers.get("Authorization") == "Bearer k"
    body = json.loads(stub.calls[0]["data"].decode("utf-8"))
    assert body["model"] == "gpt-5-pro"
    # `stop` should be absent when no stop list was passed.
    assert "stop" not in body


def test_openai_propagates_stop_sequences():
    llm = cl.CloudLLM(base_url="https://api.openai.com", api_key="k")
    response = {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]}
    with _stub_urlopen(response) as stub:
        llm.complete("x", stop=["</end>"])
    body = json.loads(stub.calls[0]["data"].decode("utf-8"))
    assert body["stop"] == ["</end>"]


def test_openai_handles_empty_choices():
    llm = cl.CloudLLM(base_url="https://api.openai.com", api_key="k")
    response = {"choices": []}
    with _stub_urlopen(response):
        result = llm.complete("x")
    assert result.content == ""


# ── Error paths ───────────────────────────────────────────────────────


def test_http_4xx_5xx_raises_unavailable():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    http_err = urllib.error.HTTPError(
        url="https://api.anthropic.com/v1/messages",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=None,
    )
    with _stub_urlopen(raise_exc=http_err):
        with pytest.raises(llm_mod.LLMUnavailable, match="HTTP 429"):
            llm.complete("x")


def test_url_error_raises_unavailable():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    with _stub_urlopen(raise_exc=urllib.error.URLError("DNS failure")):
        with pytest.raises(llm_mod.LLMUnavailable, match="unreachable"):
            llm.complete("x")


def test_native_timeout_raises_timeout():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    with _stub_urlopen(raise_exc=TimeoutError("native")):
        with pytest.raises(llm_mod.LLMTimeout, match="timed out"):
            llm.complete("x")


def test_non_json_body_raises_parse_error():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")

    def fake(req, timeout=None):
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = b"<html>500</html>"
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False
        return mock_resp

    with mock.patch.object(cl.urllib.request, "urlopen", fake):
        with pytest.raises(llm_mod.LLMParseError, match="non-JSON"):
            llm.complete("x")


# ── complete_json ─────────────────────────────────────────────────────


def test_complete_json_parses_anthropic_response():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    response = {
        "content": [{"type": "text", "text": '{"foo": 42}'}],
        "stop_reason": "end_turn",
    }
    with _stub_urlopen(response):
        out = llm.complete_json("x")
    assert out == {"foo": 42}


def test_complete_json_strips_fenced_output():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    response = {"content": [{"type": "text", "text": '```json\n{"bar": 1}\n```'}]}
    with _stub_urlopen(response):
        out = llm.complete_json("x")
    assert out == {"bar": 1}


def test_complete_json_invalid_payload_raises_parse_error():
    llm = cl.CloudLLM(base_url="https://api.anthropic.com", api_key="k")
    response = {"content": [{"type": "text", "text": "not json"}]}
    with _stub_urlopen(response):
        with pytest.raises(llm_mod.LLMParseError):
            llm.complete_json("x")


# ── is_available ──────────────────────────────────────────────────────


def test_is_available_true_when_completion_succeeds(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    response = {"content": [{"type": "text", "text": "ok"}]}
    llm = cl.CloudLLM(base_url="https://api.anthropic.com")
    with _stub_urlopen(response):
        assert llm.is_available() is True


def test_is_available_false_on_missing_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    llm = cl.CloudLLM(base_url="https://api.anthropic.com")
    # Missing key short-circuits to LLMUnavailable inside complete()
    # → is_available() returns False without needing a stub.
    assert llm.is_available() is False


# ── from_url dispatcher ───────────────────────────────────────────────


def test_from_url_routes_anthropic_to_cloud():
    llm = cl.from_url("https://api.anthropic.com")
    assert isinstance(llm, cl.CloudLLM)
    assert llm.provider == "anthropic"


def test_from_url_routes_openai_to_cloud():
    llm = cl.from_url("https://api.openai.com")
    assert isinstance(llm, cl.CloudLLM)
    assert llm.provider == "openai"


def test_from_url_routes_local_for_anything_else():
    llm = cl.from_url("http://localhost:8080")
    assert isinstance(llm, llm_mod.LocalLLM)


def test_from_url_passes_through_timeout():
    llm = cl.from_url("https://api.anthropic.com", timeout=120)
    assert llm.timeout == 120


def test_from_url_filters_unsupported_kwargs():
    """from_url drops unknown kwargs rather than raising."""
    llm = cl.from_url("http://localhost:8080", timeout=30, model="x", api_key="y")
    # LocalLLM has neither model nor api_key — these get filtered out.
    assert isinstance(llm, llm_mod.LocalLLM)
    assert llm.timeout == 30
