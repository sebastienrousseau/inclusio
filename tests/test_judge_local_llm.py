# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 7 (S7.1): tests for the llama.cpp HTTP adapter.

The adapter is stdlib-only (urllib.request + json). Tests mock
`urllib.request.urlopen` to:
  - validate the request payload shape (prompt, n_predict,
    temperature, optional stop array).
  - exercise every documented error path (LLMUnavailable on
    ECONNREFUSED, LLMTimeout on socket timeout, LLMParseError on
    non-JSON body / non-JSON completion).
  - verify the `complete_json` fence-stripping path.
  - test `score_cv_with_llm` rerank merge + clamp + fallback.

Zero network calls — fully deterministic, fast.
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

from euxis_publisher.judge import ats as ats_judge
from euxis_publisher.judge import local_llm as llm_mod

# ── Helpers ────────────────────────────────────────────────────────────


@contextmanager
def _stub_urlopen(response_json=None, raise_exc=None):
    """Patch urllib.request.urlopen to return canned JSON or raise."""

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
    with mock.patch.object(llm_mod.urllib.request, "urlopen", fake_urlopen):
        yield fake_urlopen


# ── complete: argv composition ────────────────────────────────────────


def test_complete_posts_to_completion_endpoint():
    with _stub_urlopen({"content": "ok", "tokens_predicted": 1}) as stub:
        llm = llm_mod.LocalLLM(base_url="http://localhost:8080")
        result = llm.complete("test", max_tokens=10, temperature=0.0)
    assert result.content == "ok"
    assert result.tokens_predicted == 1
    call = stub.calls[0]
    assert call["url"] == "http://localhost:8080/completion"
    assert call["method"] == "POST"
    # urllib lowercases header keys when echoing on .headers dict
    assert call["headers"].get("Content-type") == "application/json"
    body = json.loads(call["data"].decode("utf-8"))
    assert body["prompt"] == "test"
    assert body["n_predict"] == 10
    assert body["temperature"] == 0.0


def test_complete_uses_default_max_tokens_and_temperature():
    with _stub_urlopen({"content": "ok"}) as stub:
        llm = llm_mod.LocalLLM()
        llm.complete("test")
    body = json.loads(stub.calls[0]["data"].decode("utf-8"))
    assert body["n_predict"] == llm_mod.LocalLLM().default_max_tokens
    assert body["temperature"] == llm_mod.LocalLLM().default_temperature


def test_complete_propagates_stop_sequences():
    with _stub_urlopen({"content": "ok"}) as stub:
        llm_mod.LocalLLM().complete("test", stop=["</end>", "###"])
    body = json.loads(stub.calls[0]["data"].decode("utf-8"))
    assert body["stop"] == ["</end>", "###"]


def test_complete_strips_trailing_slash_in_base_url():
    with _stub_urlopen({"content": "ok"}) as stub:
        llm = llm_mod.LocalLLM(base_url="http://localhost:8080/")
        llm.complete("test")
    assert stub.calls[0]["url"] == "http://localhost:8080/completion"


def test_complete_returns_full_raw_payload():
    payload = {"content": "x", "tokens_predicted": 5, "stopped_reason": "eos", "extra": 42}
    with _stub_urlopen(payload):
        result = llm_mod.LocalLLM().complete("test")
    assert result.raw == payload
    assert result.stopped_reason == "eos"


# ── Error paths ────────────────────────────────────────────────────────


def test_complete_raises_unavailable_on_connection_refused():
    exc = urllib.error.URLError("Connection refused")
    with _stub_urlopen(raise_exc=exc):
        with pytest.raises(llm_mod.LLMUnavailable, match="unreachable"):
            llm_mod.LocalLLM().complete("test")


def test_complete_raises_timeout_on_socket_timeout():
    exc = urllib.error.URLError(TimeoutError("timed out"))
    with _stub_urlopen(raise_exc=exc):
        with pytest.raises(llm_mod.LLMTimeout, match="timed out"):
            llm_mod.LocalLLM().complete("test")


def test_complete_raises_timeout_on_python_timeout_error():
    with _stub_urlopen(raise_exc=TimeoutError("native")):
        with pytest.raises(llm_mod.LLMTimeout, match="timed out"):
            llm_mod.LocalLLM().complete("test")


def test_complete_raises_parse_error_on_non_json_body():
    def fake(req, timeout=None):
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = b"<html>500</html>"
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False
        return mock_resp

    with mock.patch.object(llm_mod.urllib.request, "urlopen", fake):
        with pytest.raises(llm_mod.LLMParseError, match="non-JSON"):
            llm_mod.LocalLLM().complete("test")


# ── complete_json: fence stripping + parse errors ─────────────────────


def test_complete_json_parses_plain_json():
    with _stub_urlopen({"content": '{"foo": 42}'}):
        out = llm_mod.LocalLLM().complete_json("test")
    assert out == {"foo": 42}


def test_complete_json_strips_fenced_code_block():
    with _stub_urlopen({"content": '```json\n{"bar": 1}\n```'}):
        out = llm_mod.LocalLLM().complete_json("test")
    assert out == {"bar": 1}


def test_complete_json_strips_unlabeled_fence():
    with _stub_urlopen({"content": '```\n{"baz": 2}\n```'}):
        out = llm_mod.LocalLLM().complete_json("test")
    assert out == {"baz": 2}


def test_complete_json_raises_parse_error_on_invalid_payload():
    with _stub_urlopen({"content": "not even close to json"}):
        with pytest.raises(llm_mod.LLMParseError, match="not valid JSON"):
            llm_mod.LocalLLM().complete_json("test")


# ── is_available ──────────────────────────────────────────────────────


def test_is_available_true_when_completion_succeeds():
    with _stub_urlopen({"content": "ok"}):
        assert llm_mod.LocalLLM().is_available() is True


def test_is_available_false_when_unreachable():
    with _stub_urlopen(raise_exc=urllib.error.URLError("Connection refused")):
        assert llm_mod.LocalLLM().is_available() is False


# ── build_ats_rerank_prompt ───────────────────────────────────────────


def test_build_ats_rerank_prompt_includes_cv_and_schema():
    cv = "Jane Doe\nSummary\n-------\nBuilds things."
    prompt = llm_mod.build_ats_rerank_prompt(cv)
    assert "ATS-conformance reviewer" in prompt
    assert "Jane Doe" in prompt
    assert '"score_adjustment"' in prompt
    assert "JSON only" in prompt


def test_build_ats_rerank_prompt_truncates_long_cv():
    long_cv = "x" * 10_000
    prompt = llm_mod.build_ats_rerank_prompt(long_cv)
    assert "x" * 6000 in prompt
    # Truncated — beyond 6 KB the CV is dropped.
    assert "x" * 7000 not in prompt


# ── score_cv_with_llm ─────────────────────────────────────────────────


CLEAN_CV = """Jane Doe

Director of Engineering

+44 7000 000000 | jane@example.com

Summary
-------
Builds payments rails for tier-1 banks.

Experience
----------
Acme Engineer (01/2020) Remote
  - Built prototype that became flagship product

Skills
------
API strategy · Payments

Education
---------
- MSc Computer Science | Imperial College | London | 09/2010
"""


def test_score_cv_with_llm_merges_llm_finding():
    """LLM returns a tone-match finding + a -5 score adjustment."""
    llm_payload = {
        "score_adjustment": -5,
        "finding": {
            "check": "tone_match",
            "severity": "warn",
            "message": "Director-level language mismatched mid-level role keywords.",
            "deduction": 5,
        },
    }
    with _stub_urlopen({"content": json.dumps(llm_payload)}):
        llm = llm_mod.LocalLLM()
        report = ats_judge.score_cv_with_llm(CLEAN_CV, llm)
    tone = next(f for f in report.findings if f.check == "tone_match")
    assert tone.severity == "warn"
    assert tone.deduction == 5
    assert report.metrics["llm_adjustment"] == -5


def test_score_cv_with_llm_clamps_adjustment_lower_bound():
    """Even if the LLM tries to take 50 points, we cap at -15."""
    llm_payload = {"score_adjustment": -50, "finding": {"message": "x"}}
    with _stub_urlopen({"content": json.dumps(llm_payload)}):
        report = ats_judge.score_cv_with_llm(CLEAN_CV, llm_mod.LocalLLM())
    assert report.metrics["llm_adjustment"] == -15


def test_score_cv_with_llm_clamps_adjustment_upper_bound():
    """Positive LLM adjustments capped at +5."""
    llm_payload = {"score_adjustment": 30, "finding": {"message": "great cv"}}
    with _stub_urlopen({"content": json.dumps(llm_payload)}):
        report = ats_judge.score_cv_with_llm(CLEAN_CV, llm_mod.LocalLLM())
    assert report.metrics["llm_adjustment"] == 5


def test_score_cv_with_llm_unavailable_falls_back_to_heuristic():
    """ECONNREFUSED → return heuristic-only report with an info finding."""
    with _stub_urlopen(raise_exc=urllib.error.URLError("Connection refused")):
        report = ats_judge.score_cv_with_llm(CLEAN_CV, llm_mod.LocalLLM())
    # The heuristic-only A grade is preserved.
    assert report.score >= 90
    # And an info-level breadcrumb documents the fallback.
    info = next(f for f in report.findings if f.check == "llm_rerank")
    assert info.severity == "info"
    assert "unavailable" in info.message.lower()


def test_score_cv_with_llm_handles_empty_finding():
    """LLM returns adjustment without a finding — adjustment still applies."""
    llm_payload = {"score_adjustment": -3, "finding": {}}
    with _stub_urlopen({"content": json.dumps(llm_payload)}):
        report = ats_judge.score_cv_with_llm(CLEAN_CV, llm_mod.LocalLLM())
    # No tone_match finding added (empty message), but score adjusted.
    assert report.metrics["llm_adjustment"] == -3
    assert not any(f.check == "tone_match" for f in report.findings)


def test_score_cv_with_llm_handles_parse_error_gracefully():
    """LLM emits garbage JSON — fall back, don't crash."""
    with _stub_urlopen({"content": "not json"}):
        report = ats_judge.score_cv_with_llm(CLEAN_CV, llm_mod.LocalLLM())
    info = next(f for f in report.findings if f.check == "llm_rerank")
    assert info.severity == "info"
