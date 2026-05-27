"""test_semantic_edges.py — Edge-case tests for semantic enforcement error paths."""

import pytest
from test_semantic import (
    find_tex_files,
    test_all_documents_have_source,
    test_all_documents_use_pub_class,
    test_no_forbidden_commands,
)


class TestFindTexFilesEdges:
    def test_returns_empty_when_no_src_dir(self, tmp_path):
        """Cover line 27: return [] when src/ doesn't exist."""
        result = find_tex_files(tmp_path)
        assert result == []


class TestForbiddenCommandsEdges:
    def test_fails_on_raw_textbf(self, tmp_path):
        """Cover lines 46-47, 50-51: violations detected and reported."""
        src = tmp_path / "src"
        src.mkdir()
        tex = src / "test.tex"
        tex.write_text(r"\textbf{forbidden}")
        with pytest.raises(pytest.fail.Exception, match="raw formatting"):
            test_no_forbidden_commands(tmp_path)


class TestDocumentsHaveSourceEdges:
    def test_fails_on_missing_source(self, tmp_path):
        """Cover lines 62, 65: missing source file reported."""
        documents = {"test-doc": {"src": "src/nonexistent.tex"}}
        with pytest.raises(pytest.fail.Exception, match="Missing source"):
            test_all_documents_have_source(tmp_path, documents)


class TestDocumentsUsePubClassEdges:
    def test_fails_on_old_class(self, tmp_path):
        """Cover lines 83, 86: old class reference detected."""
        src = tmp_path / "src"
        src.mkdir()
        tex = src / "test.tex"
        tex.write_text(r"\documentclass{cv}")
        documents = {"test-doc": {"src": "src/test.tex"}}
        with pytest.raises(pytest.fail.Exception, match="old classes"):
            test_all_documents_use_pub_class(tmp_path, documents)

    def test_skips_missing_source(self, tmp_path):
        """Cover line 76: continue when source file doesn't exist."""
        documents = {"test-doc": {"src": "src/nonexistent.tex"}}
        # Should not raise — just skips missing files
        test_all_documents_use_pub_class(tmp_path, documents)
