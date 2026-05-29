"""test_fix_semantic.py — Tests for scripts/fix-semantic.py auto-fixer."""

import sys
from unittest.mock import patch

import pytest

from inclusio.tools import fix_semantic

sys.modules["fix_semantic"] = fix_semantic
fix_file = fix_semantic.fix_file
fix_line = fix_semantic.fix_line


# ── fix_line unit tests ──────────────────────────────────────────────────


class TestFixLine:
    def test_textbf_to_keyterm(self):
        line = r"This is \textbf{important} text."
        result, count = fix_line(line)
        assert r"\keyterm{important}" in result
        assert r"\textbf" not in result
        assert count == 1

    def test_textit_to_emph(self):
        line = r"Some \textit{emphasis} here."
        result, count = fix_line(line)
        assert r"\emph{emphasis}" in result
        assert count == 1

    def test_vspace_removal(self):
        line = r"\vspace{1em}"
        result, count = fix_line(line)
        assert result.strip() == ""
        assert count == 1

    def test_hspace_removal(self):
        line = r"text\hspace{2em}more"
        result, count = fix_line(line)
        assert r"\hspace" not in result
        assert count == 1

    def test_fontsize_removal(self):
        line = r"\fontsize{12}{14} text"
        result, count = fix_line(line)
        assert r"\fontsize" not in result
        assert count == 1

    def test_color_content_kept(self):
        line = r"\color{red}{important text}"
        result, count = fix_line(line)
        assert "important text" in result
        assert r"\color" not in result
        assert count == 1

    def test_centering_removal(self):
        line = r"\centering"
        result, count = fix_line(line)
        assert result.strip() == ""
        assert count == 1

    def test_no_false_positive_centering(self):
        """Should not match \\centeringextra (non-word-boundary)."""
        line = r"\centeringextra"
        result, count = fix_line(line)
        # \centering\b should not match \centeringextra
        assert count == 0

    def test_nested_braces(self):
        line = r"\textbf{\emph{text}}"
        result, count = fix_line(line)
        assert r"\keyterm{\emph{text}}" in result
        assert count >= 1

    def test_multiple_replacements(self):
        line = r"\textbf{a} and \textit{b}"
        result, count = fix_line(line)
        assert r"\keyterm{a}" in result
        assert r"\emph{b}" in result
        assert count == 2

    def test_clean_line_unchanged(self):
        line = r"\keyterm{already semantic}"
        result, count = fix_line(line)
        assert result == line
        assert count == 0


# ── fix_file tests ───────────────────────────────────────────────────────


class TestFixFile:
    def test_textbf_replaced_in_file(self, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(r"\textbf{hello}")
        count = fix_file(f)
        assert count == 1
        assert r"\keyterm{hello}" in f.read_text()

    def test_vspace_line_removed(self, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text("line1\n\\vspace{1em}\nline2\n")
        count = fix_file(f)
        assert count == 1
        content = f.read_text()
        assert r"\vspace" not in content
        assert "line1" in content
        assert "line2" in content

    def test_dry_run_no_modification(self, tmp_path):
        f = tmp_path / "test.tex"
        original = r"\textbf{test}"
        f.write_text(original)
        count = fix_file(f, dry_run=True)
        assert count == 1
        assert f.read_text() == original  # File unchanged

    def test_clean_file_zero_count(self, tmp_path):
        f = tmp_path / "clean.tex"
        f.write_text(r"\keyterm{already clean}")
        count = fix_file(f)
        assert count == 0

    def test_verbose_line_change(self, tmp_path, capsys):
        f = tmp_path / "test.tex"
        f.write_text(r"\textbf{hello}")
        fix_file(f, verbose=True)
        output = capsys.readouterr().out
        assert r"\textbf{hello}" in output
        assert "→" in output

    def test_verbose_line_removed(self, tmp_path, capsys):
        f = tmp_path / "test.tex"
        f.write_text("\\vspace{1em}")
        fix_file(f, verbose=True)
        output = capsys.readouterr().out
        assert "removed empty line" in output


# ── main() tests ────────────────────────────────────────────────────────


class TestFixSemanticMain:
    def test_main_fixes_directory(self, tmp_path):
        (tmp_path / "a.tex").write_text(r"\textbf{x}")
        (tmp_path / "b.tex").write_text(r"\textit{y}")
        with patch("sys.argv", ["fix-semantic.py", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                fix_semantic.main()
            assert exc_info.value.code == 2  # 2 files modified

    def test_main_fixes_single_file(self, tmp_path):
        f = tmp_path / "single.tex"
        f.write_text(r"\textbf{z}")
        with patch("sys.argv", ["fix-semantic.py", str(f)]):
            with pytest.raises(SystemExit) as exc_info:
                fix_semantic.main()
            assert exc_info.value.code == 1
        assert r"\keyterm{z}" in f.read_text()

    def test_main_dry_run(self, tmp_path):
        f = tmp_path / "test.tex"
        original = r"\textbf{dry}"
        f.write_text(original)
        with patch("sys.argv", ["fix-semantic.py", str(tmp_path), "--dry-run"]):
            with pytest.raises(SystemExit) as exc_info:
                fix_semantic.main()
            assert exc_info.value.code == 1
        assert f.read_text() == original  # unchanged

    def test_main_verbose(self, tmp_path, capsys):
        f = tmp_path / "test.tex"
        f.write_text(r"\textbf{v}")
        with patch("sys.argv", ["fix-semantic.py", str(tmp_path), "--verbose"]):
            with pytest.raises(SystemExit):
                fix_semantic.main()
        output = capsys.readouterr().out
        assert "→" in output

    def test_main_missing_path_exits(self):
        with patch("sys.argv", ["fix-semantic.py", "/nonexistent/path"]):
            with pytest.raises(SystemExit) as exc_info:
                fix_semantic.main()
            assert exc_info.value.code == 1

    def test_main_no_tex_files(self, tmp_path):
        (tmp_path / "readme.md").write_text("nothing here")
        with patch("sys.argv", ["fix-semantic.py", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                fix_semantic.main()
            assert exc_info.value.code == 0

    def test_main_clean_files_exit_zero(self, tmp_path):
        (tmp_path / "clean.tex").write_text(r"\keyterm{ok}")
        with patch("sys.argv", ["fix-semantic.py", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                fix_semantic.main()
            assert exc_info.value.code == 0
