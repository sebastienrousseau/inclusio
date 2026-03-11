"""test_build_script.py — Full coverage tests for scripts/build.py."""

import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from euxis_publisher.cli import build

sys.modules["build"] = build


# ── load_meta ────────────────────────────────────────────────────────────


class TestLoadMeta:
    def test_loads_valid_meta(self):
        meta = build.load_meta()
        assert "author" in meta
        assert "documents" in meta
        assert "build" in meta

    def test_exits_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(build, "META_FILE", tmp_path / "nonexistent.yaml")
        with pytest.raises(SystemExit):
            build.load_meta()


# ── check_tool / check_tools ─────────────────────────────────────────────


class TestCheckTool:
    def test_finds_known_tool(self):
        # python3 or python should always be available
        assert build.check_tool("python3") or build.check_tool("python")

    def test_returns_false_for_unknown(self):
        assert build.check_tool("totally_nonexistent_tool_xyz") is False


class TestCheckTools:
    def test_passes_when_tools_available(self):
        # Should not raise if pdflatex and bibtex are installed
        build.check_tools()

    def test_exits_when_tools_missing(self, monkeypatch):
        monkeypatch.setattr(build, "check_tool", lambda name: False)
        with pytest.raises(SystemExit):
            build.check_tools()


# ── mode_to_option ───────────────────────────────────────────────────────


class TestModeToOption:
    @pytest.mark.parametrize(
        "mode,expected",
        [
            ("draft", "draft"),
            ("submission", "submission"),
            ("camera-ready", "final"),
            ("final", "final"),
        ],
    )
    def test_known_modes(self, mode, expected):
        assert build.mode_to_option(mode) == expected

    def test_unknown_mode_defaults_to_draft(self):
        assert build.mode_to_option("unknown_mode") == "draft"


# ── texinputs_env ────────────────────────────────────────────────────────


class TestTexinputsEnv:
    def test_contains_required_paths(self):
        result = build.texinputs_env(Path("/test/dir"))
        assert "core/cls" in result
        assert "core/sty" in result
        assert "/test/dir" in result
        assert "assets" in result

    def test_ends_with_separator(self):
        result = build.texinputs_env(Path("/test/dir"))
        sep = ":" if os.name != "nt" else ";"
        assert result.endswith(sep)

    def test_uses_correct_separator(self):
        result = build.texinputs_env(Path("/test"))
        sep = ":" if os.name != "nt" else ";"
        assert sep in result

    def test_split_roots_includes_both_assets(self, tmp_path, monkeypatch):
        """When CONTENT_ROOT != PROJECT_ROOT, both asset dirs appear."""
        content = tmp_path / "content"
        content.mkdir()
        monkeypatch.setattr(build, "CONTENT_ROOT", content)
        # PROJECT_ROOT stays at the real value — they differ
        result = build.texinputs_env(Path("/doc"))
        sep = ":" if os.name != "nt" else ";"
        parts = result.split(sep)
        assert str(content / "assets") in parts
        assert str(build.PROJECT_ROOT / "assets") in parts


# ── _resolve_content_paths ───────────────────────────────────────────────


class TestResolveContentPaths:
    def test_rebinds_all_globals(self, tmp_path, monkeypatch):
        """_resolve_content_paths sets CONTENT_ROOT and all derived paths."""
        # Save originals to restore after test
        orig = {
            attr: getattr(build, attr)
            for attr in ("CONTENT_ROOT", "META_FILE", "BUILD_DIR",
                         "CACHE_DIR", "RENDERED_DIR", "TAILORED_DIR")
        }
        try:
            build._resolve_content_paths(tmp_path)
            assert build.CONTENT_ROOT == tmp_path.resolve()
            assert build.META_FILE == tmp_path.resolve() / "data" / "meta.yaml"
            assert build.BUILD_DIR == tmp_path.resolve() / "build"
            assert build.CACHE_DIR == tmp_path.resolve() / "build" / ".cache"
            assert build.RENDERED_DIR == (
                tmp_path.resolve() / "build" / ".cache" / "rendered"
            )
            assert build.TAILORED_DIR == (
                tmp_path.resolve() / "data" / "tailored"
            )
        finally:
            for attr, val in orig.items():
                setattr(build, attr, val)


# ── build_document ───────────────────────────────────────────────────────


class TestBuildDocument:
    def test_skips_missing_source(self, capsys):
        config = {"src": "nonexistent/path.tex", "class": "pub-paper", "title": "T"}
        meta = {"build": {}}
        result = build.build_document("test-doc", config, "draft", meta)
        assert result is False
        assert "SKIP" in capsys.readouterr().out

    def test_skips_input_files(self, capsys):
        config = {
            "src": "src/papers/patent-paper.tex",
            "class": "pub-paper",
            "title": "T",
            "note": "This is an input file, not standalone",
        }
        meta = {"build": {}}
        result = build.build_document("test-doc", config, "draft", meta)
        assert result is True
        assert "input file" in capsys.readouterr().out

    @patch("build._post_process_pdf")
    @patch("build.shutil.copy2")
    @patch("build.subprocess.run")
    @patch("build.check_tool", return_value=True)
    def test_successful_build(self, mock_check, mock_run, mock_copy, mock_post_process, capsys, tmp_path, monkeypatch):
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "build" / ".cache" / "rendered")
        monkeypatch.setattr(build, "CACHE_DIR", tmp_path / "build" / ".cache")
        meta = {"build": {"compiler": "pdflatex", "max_passes": 1, "bib_engine": "bibtex"}}
        config = {"src": "src/papers/whisper-mps-realtime-asr.tex"}
        build_dir = tmp_path / "build" / ".cache" / "intermediates" / "whisper-paper"

        # Simulate the compiler producing a PDF (created as side effect of run)
        def fake_compile(cmd, **kwargs):
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "whisper-mps-realtime-asr.pdf").write_text("fresh")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = fake_compile
        result = build.build_document("whisper-paper", config, "draft", meta, force=True)
        assert result is True
        assert "OK" in capsys.readouterr().out
        # Verify output-directory points to build/intermediates/
        cmd = mock_run.call_args[0][0]
        output_dir_arg = [a for a in cmd if "-output-directory=" in a][0]
        assert ".cache" in output_dir_arg
        # Verify PDF was copied to build/{mode}/{domain}/
        mock_copy.assert_called_once()
        # Verify post-processing was called
        mock_post_process.assert_called_once()

    @patch("build.subprocess.run")
    @patch("build.check_tool", return_value=True)
    def test_failed_build(self, mock_check, mock_run, capsys, tmp_path, monkeypatch):
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "build" / ".cache" / "rendered")
        monkeypatch.setattr(build, "CACHE_DIR", tmp_path / "build" / ".cache")
        meta = {"build": {"compiler": "pdflatex", "max_passes": 1, "bib_engine": "bibtex"}}
        config = {"src": "src/papers/whisper-mps-realtime-asr.tex"}
        mock_run.return_value = MagicMock(
            returncode=1, stdout="Error on line 1\nBad stuff\n", stderr=""
        )
        result = build.build_document("whisper-paper", config, "draft", meta, force=True)
        assert result is False
        assert "FAIL" in capsys.readouterr().out

    @patch("build._post_process_pdf")
    @patch("build.shutil.copy2")
    @patch("build.subprocess.run")
    @patch("build.check_tool", return_value=False)
    def test_fallback_without_latexmk(self, mock_check, mock_run, mock_copy, mock_post_process, capsys, tmp_path, monkeypatch):
        """When latexmk is unavailable, uses direct compiler."""
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "build" / ".cache" / "rendered")
        monkeypatch.setattr(build, "CACHE_DIR", tmp_path / "build" / ".cache")
        meta = {"build": {"compiler": "pdflatex"}}
        config = {"src": "src/papers/whisper-mps-realtime-asr.tex"}
        build_dir = tmp_path / "build" / ".cache" / "intermediates" / "whisper-paper"

        def fake_compile(cmd, **kwargs):
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "whisper-mps-realtime-asr.pdf").write_text("fresh")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = fake_compile
        result = build.build_document("whisper-paper", config, "draft", meta, force=True)
        assert result is True
        # Verify pdflatex was called directly (not latexmk)
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pdflatex"

    @patch("build.subprocess.run")
    @patch("build.check_tool", return_value=True)
    def test_pdf_not_found_after_compilation(self, mock_check, mock_run, capsys, tmp_path, monkeypatch):
        """Compilation succeeds but no PDF produced."""
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "build" / ".cache" / "rendered")
        monkeypatch.setattr(build, "CACHE_DIR", tmp_path / "build" / ".cache")
        meta = {"build": {"compiler": "pdflatex"}}
        config = {"src": "src/papers/whisper-mps-realtime-asr.tex"}
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        # Don't create a PDF — simulate missing output
        result = build.build_document("whisper-paper", config, "draft", meta, force=True)
        assert result is False
        assert "WARN" in capsys.readouterr().out

    @patch("build.subprocess.run")
    @patch("build.check_tool", return_value=True)
    def test_stale_pdf_deleted_before_build(self, mock_check, mock_run, capsys, tmp_path, monkeypatch):
        """A leftover PDF from a previous build is removed before compilation."""
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "build" / ".cache" / "rendered")
        monkeypatch.setattr(build, "CACHE_DIR", tmp_path / "build" / ".cache")
        meta = {"build": {"compiler": "pdflatex"}}
        config = {"src": "src/papers/whisper-mps-realtime-asr.tex"}
        # Pre-place a stale PDF
        build_dir = tmp_path / "build" / ".cache" / "intermediates" / "whisper-paper"
        build_dir.mkdir(parents=True)
        stale = build_dir / "whisper-mps-realtime-asr.pdf"
        stale.write_text("stale content")
        # Simulate a failed build (returncode != 0)
        mock_run.return_value = MagicMock(
            returncode=1, stdout="Error\n", stderr=""
        )
        result = build.build_document("whisper-paper", config, "draft", meta, force=True)
        assert result is False
        # The stale PDF must have been deleted before compilation
        assert not stale.exists()


# ── cmd_build ────────────────────────────────────────────────────────────


class TestCmdBuild:
    @patch("build.build_document", return_value=True)
    @patch("build.check_tools")
    def test_build_all_documents(self, mock_check, mock_build, capsys):
        meta = build.load_meta()
        args = Namespace(mode="draft", doc=None)
        build.cmd_build(args, meta)
        output = capsys.readouterr().out
        assert "Building" in output
        assert "ok" in output

    @patch("build.build_document", return_value=True)
    @patch("build.check_tools")
    def test_build_single_document(self, mock_check, mock_build, capsys):
        meta = build.load_meta()
        args = Namespace(mode="draft", doc="cv")
        build.cmd_build(args, meta)
        assert mock_build.call_count == 1

    @patch("build.check_tools")
    def test_build_unknown_document_exits(self, mock_check):
        meta = build.load_meta()
        args = Namespace(mode="draft", doc="nonexistent_doc")
        with pytest.raises(SystemExit):
            build.cmd_build(args, meta)

    @patch("build.build_document", return_value=False)
    @patch("build.check_tools")
    def test_build_with_failures_exits(self, mock_check, mock_build):
        meta = build.load_meta()
        args = Namespace(mode="draft", doc="cv")
        with pytest.raises(SystemExit):
            build.cmd_build(args, meta)

    @patch("build.build_document", return_value=None)
    @patch("build.check_tools")
    def test_build_with_skipped(self, mock_check, mock_build, capsys):
        meta = build.load_meta()
        args = Namespace(mode="draft", doc="cv")
        build.cmd_build(args, meta)
        output = capsys.readouterr().out
        assert "skipped" in output


# ── cmd_assets ───────────────────────────────────────────────────────────


class TestCmdAssets:
    @patch("build.subprocess.run")
    def test_runs_asset_pipeline(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        meta = build.load_meta()
        args = Namespace()
        with pytest.raises(SystemExit) as exc:
            build.cmd_assets(args, meta)
        assert exc.value.code == 0

    def test_exits_when_script_missing(self, monkeypatch):
        monkeypatch.setattr(
            build, "PROJECT_ROOT", Path("/nonexistent/path")
        )
        meta = {}
        args = Namespace()
        with pytest.raises(SystemExit):
            build.cmd_assets(args, meta)


# ── cmd_lint ─────────────────────────────────────────────────────────────


class TestCmdLint:
    @patch("build.check_tool", return_value=False)
    @patch("build.subprocess.run")
    def test_lint_passes_with_clean_code(self, mock_run, mock_check, capsys):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        # check_tool returns False for chktex and vale, so they are skipped
        # But check-semantic.sh should run
        meta = build.load_meta()
        args = Namespace()
        build.cmd_lint(args, meta)
        output = capsys.readouterr().out
        assert "all checks passed" in output

    @patch("build.check_tool", return_value=True)
    @patch("build.subprocess.run")
    def test_lint_runs_chktex_when_available(self, mock_run, mock_check, capsys):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        meta = build.load_meta()
        args = Namespace()
        build.cmd_lint(args, meta)
        output = capsys.readouterr().out
        assert "chktex" in output.lower() or "all checks passed" in output

    @patch("build.check_tool", return_value=True)
    @patch("build.subprocess.run")
    def test_lint_reports_chktex_warnings(self, mock_run, mock_check, capsys):
        def side_effect(cmd, **kwargs):
            if isinstance(cmd, list) and "chktex" in cmd[0]:
                return MagicMock(returncode=0, stdout="Warning on line 5", stderr="")
            if isinstance(cmd, list) and "vale" in cmd[0]:
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect
        meta = build.load_meta()
        args = Namespace()
        with pytest.raises(SystemExit):
            build.cmd_lint(args, meta)

    @patch("build.check_tool")
    @patch("build.subprocess.run")
    def test_lint_reports_vale_failure(self, mock_run, mock_check, capsys):
        def tool_check(name):
            return name == "vale"

        mock_check.side_effect = tool_check

        def run_side_effect(cmd, **kwargs):
            if isinstance(cmd, list) and "vale" in cmd:
                return MagicMock(returncode=1, stdout="Vale errors", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = run_side_effect
        meta = build.load_meta()
        args = Namespace()
        with pytest.raises(SystemExit):
            build.cmd_lint(args, meta)

    def test_lint_skips_missing_check_script(self, monkeypatch, capsys):
        monkeypatch.setattr(
            build, "PROJECT_ROOT", Path("/nonexistent/path")
        )
        monkeypatch.setattr(build, "check_tool", lambda name: False)
        meta = {}
        args = Namespace()
        build.cmd_lint(args, meta)
        output = capsys.readouterr().out
        assert "SKIP" in output

    @patch("build.subprocess.run")
    def test_lint_fails_on_semantic_check_error(self, mock_run, monkeypatch, capsys):
        """When check-semantic.sh returns non-zero, lint reports error."""
        monkeypatch.setattr(build, "check_tool", lambda name: False)
        mock_run.return_value = MagicMock(returncode=1)
        meta = build.load_meta()
        args = Namespace()
        with pytest.raises(SystemExit):
            build.cmd_lint(args, meta)


# ── cmd_clean ────────────────────────────────────────────────────────────


class TestCmdClean:
    def test_removes_build_dir(self, tmp_path, monkeypatch, capsys):
        build_d = tmp_path / "build"
        build_d.mkdir()
        (build_d / "intermediates" / "cv").mkdir(parents=True)
        (build_d / "intermediates" / "cv" / "cv.aux").write_text("dummy")
        (build_d / "draft" / "cvs").mkdir(parents=True)
        (build_d / "draft" / "cvs" / "cv.pdf").write_text("dummy")
        monkeypatch.setattr(build, "BUILD_DIR", build_d)
        meta = {}
        args = Namespace()
        build.cmd_clean(args, meta)
        assert not build_d.exists()
        output = capsys.readouterr().out
        assert "Removed" in output

    def test_nothing_to_clean(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "nonexistent_build")
        meta = {}
        args = Namespace()
        build.cmd_clean(args, meta)
        assert "Nothing to clean" in capsys.readouterr().out


# ── cmd_distclean ────────────────────────────────────────────────────────


class TestCmdDistclean:
    def test_removes_dev_artifacts(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "PROJECT_ROOT", tmp_path)
        # Create dev artifacts
        (tmp_path / ".coverage").write_text("data")
        cache_dir = tmp_path / ".pytest_cache"
        cache_dir.mkdir()
        (cache_dir / "v" / "cache").mkdir(parents=True)
        meta = {}
        args = Namespace()
        build.cmd_distclean(args, meta)
        assert not (tmp_path / ".coverage").exists()
        assert not cache_dir.exists()
        output = capsys.readouterr().out
        assert ".coverage" in output
        assert ".pytest_cache" in output

    def test_distclean_without_dev_artifacts(self, tmp_path, monkeypatch, capsys):
        """No crash when dev artifacts don't exist."""
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "nonexistent_build")
        monkeypatch.setattr(build, "PROJECT_ROOT", tmp_path)
        meta = {}
        args = Namespace()
        build.cmd_distclean(args, meta)
        assert "Nothing to clean" in capsys.readouterr().out


# ── cmd_list ─────────────────────────────────────────────────────────────


class TestCmdList:
    def test_lists_documents(self, capsys):
        meta = build.load_meta()
        args = Namespace()
        build.cmd_list(args, meta)
        output = capsys.readouterr().out
        assert "cv" in output
        assert "pub-cv" in output
        assert "ID" in output

    def test_lists_tailored_documents_with_tailored_source(self, capsys):
        meta = {"documents": {}}
        args = Namespace()
        tailored = {
            "tailored-cv": {
                "class": "pub-cv",
                "description": "Tailored CV",
                "tailored": True,
            }
        }
        with patch.object(build, "_discover_tailored", return_value=tailored):
            build.cmd_list(args, meta)
        output = capsys.readouterr().out
        assert "data/tailored/tailored-cv.yaml [tailored]" in output


# ── main ─────────────────────────────────────────────────────────────────


class TestMain:
    def test_no_command_shows_help(self, capsys):
        with patch("sys.argv", ["build.py"]):
            with pytest.raises(SystemExit) as exc:
                build.main()
            assert exc.value.code == 0

    @patch("build.cmd_list")
    def test_list_command(self, mock_list):
        with patch("sys.argv", ["build.py", "list"]):
            build.main()
        mock_list.assert_called_once()

    @patch("build.cmd_clean")
    def test_clean_command(self, mock_clean):
        with patch("sys.argv", ["build.py", "clean"]):
            build.main()
        mock_clean.assert_called_once()

    @patch("build.cmd_distclean")
    def test_distclean_command(self, mock_distclean):
        with patch("sys.argv", ["build.py", "distclean"]):
            build.main()
        mock_distclean.assert_called_once()

    @patch("build.cmd_render")
    def test_render_command(self, mock_render):
        with patch("sys.argv", ["build.py", "render", "--doc", "cv"]):
            build.main()
        mock_render.assert_called_once()

    @patch("build.cmd_fix")
    def test_fix_command(self, mock_fix):
        with patch("sys.argv", ["build.py", "fix"]):
            build.main()
        mock_fix.assert_called_once()

    @patch("build.cmd_sitemap")
    def test_sitemap_command(self, mock_sitemap):
        with patch("sys.argv", ["build.py", "sitemap"]):
            build.main()
        mock_sitemap.assert_called_once()

    @patch("build.cmd_blog")
    def test_blog_command(self, mock_blog):
        with patch("sys.argv", ["build.py", "blog"]):
            build.main()
        mock_blog.assert_called_once()

    @patch("build.cmd_tailor")
    def test_tailor_command(self, mock_tailor):
        with patch("sys.argv", ["build.py", "tailor", "data/jobs/test.txt"]):
            build.main()
        mock_tailor.assert_called_once()

    @patch("build.cmd_list")
    @patch("build._resolve_content_paths")
    def test_content_dir_flag(self, mock_resolve, mock_list, tmp_path):
        """--content-dir calls _resolve_content_paths before dispatching."""
        with patch("sys.argv", ["build.py", "--content-dir",
                                 str(tmp_path), "list"]):
            build.main()
        mock_resolve.assert_called_once_with(str(tmp_path))
        mock_list.assert_called_once()


# ── cmd_render ──────────────────────────────────────────────────────────


class TestCmdRender:
    @patch("build.sys")
    def test_render_imports_and_calls(self, mock_sys, monkeypatch):
        """Verify render subcommand delegates to render module."""
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {"render": mock_render_mod}):
            args = Namespace(doc="cv", format="latex", mode="draft")
            meta = build.load_meta()
            build.cmd_render(args, meta)
            mock_render_mod.render_document.assert_called_once_with(
                "cv", "latex", "draft",
                content_root=build.CONTENT_ROOT,
            )

    def test_render_import_error(self, monkeypatch):
        """Verify error message when jinja2 is not installed."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "render":
                raise ImportError("No module named 'jinja2'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        meta = build.load_meta()
        args = Namespace(doc="cv", format="latex", mode="draft")
        with pytest.raises(SystemExit):
            build.cmd_render(args, meta)

    def test_import_render_module_falls_back_to_package(self, monkeypatch):
        import builtins
        from euxis_publisher.cli import render as package_render

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "render":
                raise ModuleNotFoundError("No module named 'render'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        assert build._import_render_module() is package_render


# ── cmd_fix ─────────────────────────────────────────────────────────────


class TestCmdFix:
    @patch("build.subprocess.run")
    def test_fix_delegates_to_script(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        meta = build.load_meta()
        args = Namespace(dry_run=False, verbose=False)
        with pytest.raises(SystemExit) as exc:
            build.cmd_fix(args, meta)
        assert exc.value.code == 0
        # Verify fix-semantic.py was called
        cmd = mock_run.call_args[0][0]
        assert "fix-semantic.py" in cmd[1]

    @patch("build.subprocess.run")
    def test_fix_dry_run(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        meta = build.load_meta()
        args = Namespace(dry_run=True, verbose=False)
        with pytest.raises(SystemExit):
            build.cmd_fix(args, meta)
        cmd = mock_run.call_args[0][0]
        assert "--dry-run" in cmd

    @patch("build.subprocess.run")
    def test_fix_verbose(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        meta = build.load_meta()
        args = Namespace(dry_run=False, verbose=True)
        with pytest.raises(SystemExit):
            build.cmd_fix(args, meta)
        cmd = mock_run.call_args[0][0]
        assert "--verbose" in cmd

    def test_fix_missing_script_exits(self, monkeypatch):
        monkeypatch.setattr(build, "PROJECT_ROOT", Path("/nonexistent"))
        meta = {}
        args = Namespace(dry_run=False, verbose=False)
        with pytest.raises(SystemExit):
            build.cmd_fix(args, meta)


# ── cmd_sitemap ────────────────────────────────────────────────────────


class TestCmdSitemap:
    @patch("build.subprocess.run")
    def test_sitemap_delegates_to_script(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        meta = build.load_meta()
        args = Namespace(pretty=False, stdout=False)
        with pytest.raises(SystemExit) as exc:
            build.cmd_sitemap(args, meta)
        assert exc.value.code == 0
        cmd = mock_run.call_args[0][0]
        assert "sitemap.py" in cmd[1]

    @patch("build.subprocess.run")
    def test_sitemap_pretty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        meta = build.load_meta()
        args = Namespace(pretty=True, stdout=False)
        with pytest.raises(SystemExit):
            build.cmd_sitemap(args, meta)
        cmd = mock_run.call_args[0][0]
        assert "--pretty" in cmd

    @patch("build.subprocess.run")
    def test_sitemap_stdout(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        meta = build.load_meta()
        args = Namespace(pretty=False, stdout=True)
        with pytest.raises(SystemExit):
            build.cmd_sitemap(args, meta)
        cmd = mock_run.call_args[0][0]
        assert "--stdout" in cmd

    def test_sitemap_missing_script_exits(self, monkeypatch):
        monkeypatch.setattr(build, "PROJECT_ROOT", Path("/nonexistent"))
        meta = {}
        args = Namespace(pretty=False, stdout=False)
        with pytest.raises(SystemExit):
            build.cmd_sitemap(args, meta)


# ── cmd_blog ─────────────────────────────────────────────────────────


class TestCmdBlog:
    @patch("build.sys")
    def test_blog_renders_all(self, mock_sys, monkeypatch):
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {"render": mock_render_mod}):
            meta = build.load_meta()
            args = Namespace(doc=None)
            build.cmd_blog(args, meta)
            assert mock_render_mod.render_blog.call_count >= 1

    @patch("build.sys")
    def test_blog_single_post(self, mock_sys, monkeypatch):
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {"render": mock_render_mod}):
            meta = build.load_meta()
            args = Namespace(doc="whisper-blog")
            build.cmd_blog(args, meta)
            mock_render_mod.render_blog.assert_called_once()

    def test_blog_unknown_exits(self):
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {"render": mock_render_mod}):
            meta = build.load_meta()
            args = Namespace(doc="nonexistent-blog")
            with pytest.raises(SystemExit):
                build.cmd_blog(args, meta)

    @patch("build.check_tool", return_value=False)
    def test_blog_needs_pandoc_for_convert(self, mock_check):
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {"render": mock_render_mod}):
            meta = build.load_meta()
            args = Namespace(doc="security-blog")
            with pytest.raises(SystemExit):
                build.cmd_blog(args, meta)

    def test_blog_import_error(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "render":
                raise ImportError("No module named 'jinja2'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        meta = build.load_meta()
        args = Namespace(doc=None)
        with pytest.raises(SystemExit):
            build.cmd_blog(args, meta)

    def test_blog_no_entries(self, capsys):
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {"render": mock_render_mod}):
            meta = {"blog": {}}
            args = Namespace(doc=None)
            build.cmd_blog(args, meta)
            output = capsys.readouterr().out
            assert "No blog entries" in output


# ── cmd_tailor ──────────────────────────────────────────────────────────


class TestCmdTailor:
    @patch("build.sys")
    def test_tailor_cv(self, mock_sys, tmp_path, monkeypatch, capsys):
        mock_tailor_mod = MagicMock()
        mock_tailor_mod.generate.return_value = tmp_path / "out.yaml"
        with patch.dict("sys.modules", {"tailor": mock_tailor_mod}):
            args = Namespace(
                brief="data/jobs/test.txt", type="cv", id=None,
                base=None, render=False, build=False, mode="draft",
            )
            meta = build.load_meta()
            build.cmd_tailor(args, meta)
            mock_tailor_mod.generate.assert_called_once()
            output = capsys.readouterr().out
            assert "TAILOR" in output

    @patch("build.build_document", return_value=True)
    @patch("build.sys")
    def test_tailor_with_build(self, mock_sys, mock_build_doc, tmp_path,
                                monkeypatch, capsys):
        # Create the tailored YAML file so shutil.copy2 can read it
        yaml_file = tmp_path / "out.yaml"
        yaml_file.write_text("role: Test\n")
        # Redirect PROJECT_ROOT and CONTENT_ROOT so copy target lands in tmp_path
        fake_root = tmp_path / "project"
        (fake_root / "data" / "tailored").mkdir(parents=True)
        monkeypatch.setattr(build, "PROJECT_ROOT", fake_root)
        monkeypatch.setattr(build, "CONTENT_ROOT", fake_root)
        monkeypatch.setattr(build, "BUILD_DIR", fake_root / "build")
        monkeypatch.setattr(build, "CACHE_DIR", fake_root / "build" / ".cache")
        monkeypatch.setattr(build, "RENDERED_DIR",
                            fake_root / "build" / ".cache" / "rendered")
        mock_tailor_mod = MagicMock()
        mock_tailor_mod.generate.return_value = yaml_file
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {
            "tailor": mock_tailor_mod,
            "render": mock_render_mod,
        }):
            args = Namespace(
                brief="data/jobs/test.txt", type="cv", id="my-cv",
                base=None, render=False, build=True, mode="draft",
            )
            meta = build.load_meta()
            build.cmd_tailor(args, meta)
            mock_render_mod.render_document.assert_called_once()
            mock_build_doc.assert_called_once()
            # Verify the copy happened
            assert (fake_root / "data" / "tailored" / "cv.yaml").exists()

    @patch("build.sys")
    def test_tailor_with_render(self, mock_sys, tmp_path, capsys):
        # Create the tailored YAML file so shutil.copy2 can read it
        yaml_file = tmp_path / "out.yaml"
        yaml_file.write_text("title: Test\n")
        # Redirect PROJECT_ROOT so copy target lands in tmp_path
        fake_root = tmp_path / "project"
        (fake_root / "data" / "tailored").mkdir(parents=True)
        # monkeypatch not available as fixture here, use patch
        mock_tailor_mod = MagicMock()
        mock_tailor_mod.generate.return_value = yaml_file
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {
            "tailor": mock_tailor_mod,
            "render": mock_render_mod,
        }), patch.object(build, "PROJECT_ROOT", fake_root), \
             patch.object(build, "CONTENT_ROOT", fake_root), \
             patch.object(build, "BUILD_DIR", fake_root / "build"), \
             patch.object(build, "CACHE_DIR",
                          fake_root / "build" / ".cache"), \
             patch.object(build, "RENDERED_DIR",
                          fake_root / "build" / ".cache" / "rendered"):
            args = Namespace(
                brief="data/jobs/test.txt", type="paper", id=None,
                base=None, render=True, build=False, mode="draft",
            )
            meta = build.load_meta()
            build.cmd_tailor(args, meta)
            mock_render_mod.render_document.assert_called_once()
            # output_id="test", doc_type="paper" → copy should happen
            assert (fake_root / "data" / "tailored" / "paper.yaml").exists()

    @patch("build.build_document", return_value=True)
    @patch("build.sys")
    def test_tailor_build_renames_rendered_tex(self, mock_sys, mock_build_doc,
                                                tmp_path, monkeypatch):
        """Covers line 501: copy rendered {doc_type}.tex → {output_id}.tex."""
        yaml_file = tmp_path / "out.yaml"
        yaml_file.write_text("role: Test\n")
        fake_root = tmp_path / "project"
        (fake_root / "data" / "tailored").mkdir(parents=True)
        rendered_dir = fake_root / "build" / ".cache" / "rendered"
        rendered_dir.mkdir(parents=True)
        # Simulate render having produced cv.tex
        (rendered_dir / "cv.tex").write_text("\\documentclass{pub-cv}\n")
        monkeypatch.setattr(build, "PROJECT_ROOT", fake_root)
        monkeypatch.setattr(build, "BUILD_DIR", fake_root / "build")
        monkeypatch.setattr(build, "CACHE_DIR", fake_root / "build" / ".cache")
        monkeypatch.setattr(build, "RENDERED_DIR", rendered_dir)
        mock_tailor_mod = MagicMock()
        mock_tailor_mod.generate.return_value = yaml_file
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {
            "tailor": mock_tailor_mod,
            "render": mock_render_mod,
        }):
            args = Namespace(
                brief="data/jobs/test.txt", type="cv", id="my-cv",
                base=None, render=False, build=True, mode="draft",
            )
            meta = build.load_meta()
            build.cmd_tailor(args, meta)
            # Rendered tex should be copied to output_id name
            assert (rendered_dir / "my-cv.tex").exists()

    @patch("build.build_document", return_value=True)
    @patch("build.sys")
    def test_tailor_build_unknown_type(self, mock_sys, mock_build_doc,
                                       tmp_path, monkeypatch):
        """Covers line 514: doc_type not in meta documents → fallback src."""
        yaml_file = tmp_path / "out.yaml"
        yaml_file.write_text("title: Test\n")
        fake_root = tmp_path / "project"
        (fake_root / "data" / "tailored").mkdir(parents=True)
        monkeypatch.setattr(build, "PROJECT_ROOT", fake_root)
        monkeypatch.setattr(build, "BUILD_DIR", fake_root / "build")
        monkeypatch.setattr(build, "CACHE_DIR", fake_root / "build" / ".cache")
        monkeypatch.setattr(build, "RENDERED_DIR",
                            fake_root / "build" / ".cache" / "rendered")
        mock_tailor_mod = MagicMock()
        mock_tailor_mod.generate.return_value = yaml_file
        mock_render_mod = MagicMock()
        with patch.dict("sys.modules", {
            "tailor": mock_tailor_mod,
            "render": mock_render_mod,
        }):
            # Use type="guide" which is not in meta documents
            args = Namespace(
                brief="data/jobs/test.txt", type="guide", id=None,
                base=None, render=False, build=True, mode="draft",
            )
            meta = build.load_meta()
            build.cmd_tailor(args, meta)
            # Verify fallback src path was used
            call_args = mock_build_doc.call_args
            doc_config = call_args[0][1]
            assert doc_config["src"] == "build/.cache/rendered/test.tex"

    def test_tailor_import_error(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "tailor":
                raise ImportError("No module named 'tailor'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        meta = build.load_meta()
        args = Namespace(
            brief="data/jobs/test.txt", type="cv", id=None,
            base=None, render=False, build=False, mode="draft",
        )
        with pytest.raises(SystemExit):
            build.cmd_tailor(args, meta)

    def test_import_tailor_module_falls_back_to_package(self, monkeypatch):
        import builtins
        from euxis_publisher.cli import tailor as package_tailor

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "tailor":
                raise ModuleNotFoundError("No module named 'tailor'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        assert build._import_tailor_module() is package_tailor

    def test_tailor_render_import_error(self, monkeypatch, tmp_path):
        # Create the tailored YAML file so copy2 won't fail before the
        # import error is reached.  output_id=brief_stem="test", type="cv"
        # → they differ, so copy happens before import "render".
        yaml_file = tmp_path / "out.yaml"
        yaml_file.write_text("role: Test\n")
        fake_root = tmp_path / "project"
        (fake_root / "data" / "tailored").mkdir(parents=True)
        monkeypatch.setattr(build, "PROJECT_ROOT", fake_root)

        mock_tailor_mod = MagicMock()
        mock_tailor_mod.generate.return_value = yaml_file
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "render":
                raise ImportError("No module named 'jinja2'")
            return real_import(name, *args, **kwargs)

        with patch.dict("sys.modules", {"tailor": mock_tailor_mod}):
            monkeypatch.setattr(builtins, "__import__", mock_import)
            meta = build.load_meta()
            args = Namespace(
                brief="data/jobs/test.txt", type="cv", id=None,
                base=None, render=True, build=False, mode="draft",
            )
            with pytest.raises(SystemExit):
                build.cmd_tailor(args, meta)


# ── Parallel build tests ────────────────────────────────────────────────


class TestParallelBuild:
    @patch("build.build_document", return_value=True)
    @patch("build.check_tools")
    def test_parallel_with_jobs(self, mock_check, mock_build, capsys):
        meta = build.load_meta()
        args = Namespace(mode="draft", doc=None, jobs=2, force=False)
        build.cmd_build(args, meta)
        output = capsys.readouterr().out
        assert "jobs=2" in output
        assert "ok" in output

    @patch("build.build_document", return_value=True)
    @patch("build.check_tools")
    def test_sequential_with_jobs_1(self, mock_check, mock_build, capsys):
        meta = build.load_meta()
        args = Namespace(mode="draft", doc="cv", jobs=1, force=False)
        build.cmd_build(args, meta)
        assert mock_build.call_count == 1

    @patch("build.build_document", return_value=False)
    @patch("build.check_tools")
    def test_parallel_with_failures(self, mock_check, mock_build):
        meta = build.load_meta()
        args = Namespace(mode="draft", doc="cv", jobs=2, force=False)
        with pytest.raises(SystemExit):
            build.cmd_build(args, meta)

    @patch("build.build_document", return_value=None)
    @patch("build.check_tools")
    def test_parallel_with_skipped(self, mock_check, mock_build, capsys):
        meta = build.load_meta()
        args = Namespace(mode="draft", doc="cv", jobs=2, force=False)
        build.cmd_build(args, meta)
        output = capsys.readouterr().out
        assert "skipped" in output


# ── Cache tests ─────────────────────────────────────────────────────────


class TestCache:
    def test_content_hash(self, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text("hello")
        h = build._content_hash(f)
        assert len(h) == 64  # SHA-256 hex digest
        # Same content → same hash
        assert h == build._content_hash(f)

    def test_is_cached_false_when_no_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr(build, "CACHE_DIR", tmp_path / ".cache")
        f = tmp_path / "test.tex"
        f.write_text("content")
        assert build._is_cached("doc", f) is False

    def test_write_and_check_cache(self, tmp_path, monkeypatch):
        cache = tmp_path / ".cache"
        monkeypatch.setattr(build, "CACHE_DIR", cache)
        f = tmp_path / "test.tex"
        f.write_text("content")
        build._write_cache("doc", f)
        assert build._is_cached("doc", f) is True

    def test_cache_invalidated_on_change(self, tmp_path, monkeypatch):
        cache = tmp_path / ".cache"
        monkeypatch.setattr(build, "CACHE_DIR", cache)
        f = tmp_path / "test.tex"
        f.write_text("original")
        build._write_cache("doc", f)
        f.write_text("modified")
        assert build._is_cached("doc", f) is False

    @patch("build._post_process_pdf")
    @patch("build.shutil.copy2")
    @patch("build.subprocess.run")
    @patch("build.check_tool", return_value=True)
    def test_cached_doc_skipped(self, mock_check, mock_run, mock_copy,
                                mock_post_process,
                                capsys, tmp_path, monkeypatch):
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "build" / ".cache" / "rendered")
        cache = tmp_path / "build" / ".cache"
        monkeypatch.setattr(build, "CACHE_DIR", cache)

        meta = {"build": {"compiler": "pdflatex"}}
        config = {"src": "src/papers/whisper-mps-realtime-asr.tex"}

        # Pre-populate cache (hashes/ subdirectory)
        src = build.PROJECT_ROOT / config["src"]
        hash_dir = cache / "hashes"
        hash_dir.mkdir(parents=True)
        (hash_dir / "whisper-paper.sha256").write_text(
            build._content_hash(src)
        )

        result = build.build_document("whisper-paper", config, "draft", meta)
        assert result is True
        output = capsys.readouterr().out
        assert "CACHED" in output
        mock_run.assert_not_called()

    @patch("build._post_process_pdf")
    @patch("build.shutil.copy2")
    @patch("build.subprocess.run")
    @patch("build.check_tool", return_value=True)
    def test_force_bypasses_cache(self, mock_check, mock_run, mock_copy,
                                  mock_post_process,
                                  capsys, tmp_path, monkeypatch):
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "build" / ".cache" / "rendered")
        cache = tmp_path / "build" / ".cache"
        monkeypatch.setattr(build, "CACHE_DIR", cache)

        meta = {"build": {"compiler": "pdflatex"}}
        config = {"src": "src/papers/whisper-mps-realtime-asr.tex"}
        build_dir = tmp_path / "build" / ".cache" / "intermediates" / "whisper-paper"

        # Pre-populate cache (hashes/ subdirectory)
        src = build.PROJECT_ROOT / config["src"]
        hash_dir = cache / "hashes"
        hash_dir.mkdir(parents=True)
        (hash_dir / "whisper-paper.sha256").write_text(
            build._content_hash(src)
        )

        def fake_compile(cmd, **kwargs):
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "whisper-mps-realtime-asr.pdf").write_text("new")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = fake_compile
        result = build.build_document(
            "whisper-paper", config, "draft", meta, force=True
        )
        assert result is True
        output = capsys.readouterr().out
        assert "OK" in output
        assert "CACHED" not in output


# ── New classes existence ────────────────────────────────────────────────


class TestNewClassesExist:
    @pytest.mark.parametrize("cls_name", [
        "pub-preprint",
        "pub-arxiv",
        "pub-patent-us",
        "pub-bio",
        "pub-prime",
    ])
    def test_cls_file_exists(self, cls_name):
        cls_path = build.PROJECT_ROOT / "core" / "cls" / f"{cls_name}.cls"
        assert cls_path.exists(), f"{cls_name}.cls not found"

    @pytest.mark.parametrize("cls_name", [
        "pub-preprint",
        "pub-arxiv",
        "pub-patent-us",
        "pub-bio",
        "pub-prime",
    ])
    def test_cls_has_provides_class(self, cls_name):
        cls_path = build.PROJECT_ROOT / "core" / "cls" / f"{cls_name}.cls"
        content = cls_path.read_text()
        assert r"\ProvidesClass" in content


# ── Rendered path fallback ───────────────────────────────────────────────


class TestRenderedPathFallback:
    @patch("build._post_process_pdf")
    @patch("build.shutil.copy2")
    @patch("build.subprocess.run")
    @patch("build.check_tool", return_value=True)
    def test_uses_rendered_when_available(self, mock_check, mock_run,
                                         mock_copy, mock_post_process,
                                         capsys, tmp_path,
                                         monkeypatch):
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "CACHE_DIR", tmp_path / "build" / ".cache")
        rendered_dir = tmp_path / "build" / ".cache" / "rendered"
        rendered_dir.mkdir(parents=True)
        monkeypatch.setattr(build, "RENDERED_DIR", rendered_dir)

        # Create rendered file
        rendered_tex = rendered_dir / "cv.tex"
        rendered_tex.write_text(r"\documentclass{pub-cv}\begin{document}\end{document}")

        meta = {"build": {"compiler": "pdflatex"}}
        config = {"src": "src/cvs/cv.tex"}
        build_dir = tmp_path / "build" / ".cache" / "intermediates" / "cv"

        def fake_compile(cmd, **kwargs):
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "cv.pdf").write_text("pdf")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = fake_compile
        result = build.build_document("cv", config, "draft", meta, force=True)
        assert result is True
        # Verify cwd was rendered dir, not src/cvs/
        call_kwargs = mock_run.call_args[1]
        assert str(rendered_dir) in call_kwargs["cwd"]

    @patch("build._post_process_pdf")
    @patch("build.shutil.copy2")
    @patch("build.subprocess.run")
    @patch("build.check_tool", return_value=True)
    def test_tailored_skips_rendered_override(self, mock_check, mock_run,
                                              mock_copy, mock_post_process,
                                              capsys, tmp_path,
                                              monkeypatch):
        """Tailored docs use their src/ path, not build/rendered/ override."""
        monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(build, "CACHE_DIR", tmp_path / "build" / ".cache")
        monkeypatch.setattr(build, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(build, "CONTENT_ROOT", tmp_path)
        rendered_dir = tmp_path / "build" / ".cache" / "rendered"
        rendered_dir.mkdir(parents=True)
        monkeypatch.setattr(build, "RENDERED_DIR", rendered_dir)

        # Create both rendered AND src/ file
        (rendered_dir / "my-job.tex").write_text("rendered version")
        src_dir = tmp_path / "src" / "cvs" / "my-job"
        src_dir.mkdir(parents=True)
        src_tex = src_dir / "my-job.tex"
        src_tex.write_text("src version")

        meta = {"build": {"compiler": "pdflatex"}}
        config = {
            "src": "src/cvs/my-job/my-job.tex",
            "tailored": True,
            "figures_src": "src/cvs",
        }
        build_dir = tmp_path / "build" / ".cache" / "intermediates" / "my-job"

        def fake_compile(cmd, **kwargs):
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "my-job.pdf").write_text("pdf")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = fake_compile
        result = build.build_document("my-job", config, "draft", meta, force=True)
        assert result is True
        # Verify cwd was src/ dir, not rendered dir
        call_kwargs = mock_run.call_args[1]
        assert str(src_dir) in call_kwargs["cwd"]
        assert str(rendered_dir) not in call_kwargs["cwd"]
        # Verify figures_src is in TEXINPUTS
        texinputs = call_kwargs["env"]["TEXINPUTS"]
        assert str(tmp_path / "src" / "cvs") in texinputs


# ── _post_process_pdf ─────────────────────────────────────────────────


class TestPostProcessPdf:
    """Comprehensive tests for the consolidated post-processing function."""

    def _make_pdf(self, tmp_path):
        import pikepdf
        pdf_path = tmp_path / "test.pdf"
        pdf = pikepdf.Pdf.new()
        pdf.add_blank_page(page_size=(612, 792))
        pdf.save(pdf_path)
        return pdf_path

    def _meta(self):
        return {
            "author": {
                "name": "Test Author",
                "role": "Lead Engineer",
                "copyright": "\u00a9 2026 Test Author",
                "copyright_url": "https://example.com",
                "publisher": "Test Publisher",
            }
        }

    def _config(self):
        return {
            "title": "Test Title",
            "subject": "Test Subject",
            "description": "A test document",
            "keywords": "key1, key2",
        }

    def test_xmp_metadata_complete(self, tmp_path):
        """All 12 XMP metadata fields + pdfuaid:part must be set."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        build._post_process_pdf(pdf_path, "test-doc", self._config(), self._meta())

        with pikepdf.open(pdf_path) as pdf:
            raw = pdf.Root["/Metadata"].read_bytes().decode("utf-8")
            assert "Test Title" in raw
            assert "Test Author" in raw
            assert "Test Subject" in raw
            assert "A test document" in raw
            assert "\u00a9 2026 Test Author" in raw
            assert "key1, key2" in raw
            assert "<pdf:Producer>Test Publisher</pdf:Producer>" in raw
            assert "LaTeX with hyperref" in raw
            assert "<xmpRights:Marked>True</xmpRights:Marked>" in raw
            assert "https://example.com" in raw
            assert "Lead Engineer" in raw
            assert "<photoshop:CaptionWriter>Test Author" in raw
            assert "<pdfuaid:part>1</pdfuaid:part>" in raw

    def test_document_info_dict(self, tmp_path):
        """The legacy document info dictionary must also be set."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        build._post_process_pdf(pdf_path, "test-doc", self._config(), self._meta())

        with pikepdf.open(pdf_path) as pdf:
            assert str(pdf.docinfo.get("/Title")) == "Test Title"
            assert str(pdf.docinfo.get("/Author")) == "Test Author"
            assert str(pdf.docinfo.get("/Subject")) == "Test Subject"
            assert str(pdf.docinfo.get("/Keywords")) == "key1, key2"
            assert str(pdf.docinfo.get("/Creator")) == "LaTeX with hyperref"
            assert str(pdf.docinfo.get("/Producer")) == "Test Publisher"

    def test_mark_info_and_lang(self, tmp_path):
        """PDF/UA: /MarkInfo and /Lang must be set."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        build._post_process_pdf(pdf_path, "test-doc", self._config(), self._meta())

        with pikepdf.open(pdf_path) as pdf:
            mark_info = pdf.Root.get("/MarkInfo")
            assert mark_info is not None
            assert bool(mark_info.get("/Marked")) is True
            assert str(pdf.Root.get("/Lang")) == "en"

    def test_viewer_preferences(self, tmp_path):
        """/ViewerPreferences with /DisplayDocTitle must be set."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        build._post_process_pdf(pdf_path, "test-doc", self._config(), self._meta())

        with pikepdf.open(pdf_path) as pdf:
            vp = pdf.Root.get("/ViewerPreferences")
            assert vp is not None
            assert bool(vp.get("/DisplayDocTitle")) is True

    def test_encryption_applied(self, tmp_path):
        """PDF must be encrypted with AES-256 and correct permissions."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        build._post_process_pdf(pdf_path, "test-doc", self._config(), self._meta())

        with pikepdf.open(pdf_path) as pdf:
            assert pdf.is_encrypted
            assert pdf.allow.print_highres is True
            assert pdf.allow.extract is False
            assert pdf.allow.modify_other is False
            assert pdf.allow.accessibility is True

    def test_opens_without_password(self, tmp_path):
        """Encrypted PDF must open without a password."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        build._post_process_pdf(pdf_path, "test-doc", self._config(), self._meta())

        # Should not raise PasswordError
        with pikepdf.open(pdf_path) as pdf:
            assert len(pdf.pages) == 1

    def test_copyright_notice_in_dc_rights(self, tmp_path):
        """dc:rights must contain a copyright symbol."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        build._post_process_pdf(pdf_path, "test-doc", self._config(), self._meta())

        with pikepdf.open(pdf_path) as pdf:
            raw = pdf.Root["/Metadata"].read_bytes().decode("utf-8")
            assert "\u00a9" in raw

    def test_skips_when_pikepdf_missing(self, monkeypatch):
        """Silently returns when pikepdf is unavailable."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pikepdf":
                raise ImportError("No module named 'pikepdf'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        build._post_process_pdf(Path("/fake.pdf"), "doc", {}, {})

    def test_handles_empty_metadata(self, tmp_path):
        """Works with minimal empty config/meta without crashing."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        build._post_process_pdf(pdf_path, "doc", {}, {})

        with pikepdf.open(pdf_path) as pdf:
            # Producer falls back to empty author name when no meta
            meta_stream = pdf.Root.get("/Metadata")
            assert meta_stream is not None
            assert pdf.is_encrypted

    def test_no_copyright_url_skips_web_statement(self, tmp_path):
        """When copyright_url is empty, xmpRights:WebStatement is not set."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        meta = {"author": {"name": "A", "role": "R", "copyright": "C"}}
        build._post_process_pdf(pdf_path, "doc", {}, meta)

        with pikepdf.open(pdf_path) as pdf:
            raw = pdf.Root["/Metadata"].read_bytes().decode("utf-8")
            assert "WebStatement" not in raw

    def test_build_xmp_xml_structure(self):
        """_build_xmp_xml produces valid XMP with all namespaces."""
        xml = build._build_xmp_xml(
            "T", "A", "S", "D", "K", "C", "https://u", "R", "P",
        )
        assert '<?xpacket begin=' in xml
        assert '<?xpacket end="w"?>' in xml
        assert 'xmlns:dc=' in xml
        assert 'xmlns:xmpRights=' in xml
        assert 'xmlns:photoshop=' in xml
        assert 'xmlns:pdfuaid=' in xml
        assert '<dc:title>' in xml
        assert '<xmpRights:WebStatement>https://u</xmpRights:WebStatement>' in xml

    def test_producer_uses_publisher(self, tmp_path):
        """pdf:Producer uses author.publisher from meta, not hardcoded."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        meta = {"author": {"name": "Name", "publisher": "My Pub"}}
        build._post_process_pdf(pdf_path, "doc", {}, meta)

        with pikepdf.open(pdf_path) as pdf:
            raw = pdf.Root["/Metadata"].read_bytes().decode("utf-8")
            assert "<pdf:Producer>My Pub</pdf:Producer>" in raw
            assert str(pdf.docinfo.get("/Producer")) == "My Pub"

    def test_producer_falls_back_to_name(self, tmp_path):
        """Without publisher, pdf:Producer falls back to author.name."""
        import pikepdf
        pdf_path = self._make_pdf(tmp_path)
        meta = {"author": {"name": "Fallback Name"}}
        build._post_process_pdf(pdf_path, "doc", {}, meta)

        with pikepdf.open(pdf_path) as pdf:
            raw = pdf.Root["/Metadata"].read_bytes().decode("utf-8")
            assert "<pdf:Producer>Fallback Name</pdf:Producer>" in raw


# ── _artifact_subdir ─────────────────────────────────────────────────────


class TestArtifactSubdir:
    @pytest.mark.parametrize(
        "src,expected",
        [
            ("src/cvs/cv.tex", "cvs"),
            ("src/papers/whisper.tex", "papers"),
            ("src/patents/patent/patent.tex", "patents"),
            ("src/faqs/faqs.tex", "faqs"),
            ("src/guides/user-guide.tex", "guides"),
        ],
    )
    def test_domain_from_src(self, src, expected):
        config = {"src": src}
        assert build._artifact_subdir("doc", config) == expected

    def test_tailored_flag(self):
        config = {"src": "src/cvs/cv.tex", "tailored": True}
        assert build._artifact_subdir("my-cv", config) == "jobs"

    def test_tailored_from_description(self):
        config = {"src": "build/rendered/my-cv.tex", "description": "Tailored cv"}
        assert build._artifact_subdir("my-cv", config) == "jobs"

    def test_tailored_from_rendered_path(self):
        config = {"src": "build/rendered/my-cv.tex"}
        assert build._artifact_subdir("my-cv", config) == "jobs"

    def test_fallback_empty(self):
        config = {"src": "other/path.tex"}
        assert build._artifact_subdir("doc", config) == ""

    def test_empty_src(self):
        config = {}
        assert build._artifact_subdir("doc", config) == ""


class TestDiscoverTailored:
    def test_discovers_tailored_yaml(self, tmp_path, monkeypatch):
        import yaml
        monkeypatch.setattr(build, "TAILORED_DIR", tmp_path / "tailored")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "rendered")
        monkeypatch.setattr(build, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(build, "CONTENT_ROOT", tmp_path)
        (tmp_path / "tailored").mkdir()
        (tmp_path / "rendered").mkdir()

        # Write a tailored CV yaml
        cv_data = {
            "name": {"first": "Jane", "last": "Doe"},
            "role": "PM",
            "summary": "Test",
            "experience": [{"title": "PM", "company": "Co", "dates": "2020",
                            "logo": "", "bullets": ["Did stuff."]}],
            "skills": [],
            "education": [],
            "languages": "English",
            "contact": {"phone": "+1", "email": "j@e.com"},
            "footer_address": "London",
        }
        with open(tmp_path / "tailored" / "test-job.yaml", "w") as f:
            yaml.dump(cv_data, f)

        meta = {"documents": {"cv": {}}, "templates": {
            "cv": {"template": "cv.tex.j2", "data": "cv-data.yaml", "type": "cv"},
        }}

        mock_render = MagicMock(
            render_latex=MagicMock(return_value="\\documentclass{pub-cv}"),
            _generate_xmpdata=MagicMock(),
            TEMPLATE_DIR=tmp_path,
        )
        with patch.dict("sys.modules", {"render": mock_render}):
            result = build._discover_tailored(meta)

        assert "test-job" in result
        assert result["test-job"]["tailored"] is True
        assert result["test-job"]["class"] == "pub-cv"
        assert result["test-job"]["src"] == "src/cvs/test-job/test-job.tex"
        assert result["test-job"]["figures_src"] == "src/cvs"
        # Verify .tex was copied to src/cvs/test-job/
        src_tex = tmp_path / "src" / "cvs" / "test-job" / "test-job.tex"
        assert src_tex.exists()
        assert src_tex.read_text() == "\\documentclass{pub-cv}"

    def test_copies_shared_figures(self, tmp_path, monkeypatch):
        """Covers line 388: shutil.copytree for shared figures directory."""
        import yaml
        monkeypatch.setattr(build, "TAILORED_DIR", tmp_path / "tailored")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "rendered")
        monkeypatch.setattr(build, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(build, "CONTENT_ROOT", tmp_path)
        (tmp_path / "tailored").mkdir()
        (tmp_path / "rendered").mkdir()

        # Create shared figures directory for cvs category
        figures_dir = tmp_path / "src" / "cvs" / "figures"
        figures_dir.mkdir(parents=True)
        (figures_dir / "logo.png").write_bytes(b"\x89PNG")

        cv_data = {
            "name": {"first": "Jane", "last": "Doe"},
            "role": "PM", "summary": "Test",
            "experience": [{"title": "PM", "company": "Co", "dates": "2020",
                            "logo": "", "bullets": ["Did stuff."]}],
            "skills": [], "education": [], "languages": "English",
            "contact": {"phone": "+1", "email": "j@e.com"},
            "footer_address": "London",
        }
        with open(tmp_path / "tailored" / "fig-job.yaml", "w") as f:
            yaml.dump(cv_data, f)

        meta = {"documents": {"cv": {}}, "templates": {
            "cv": {"template": "cv.tex.j2", "data": "cv-data.yaml",
                   "type": "cv"},
        }}
        mock_render = MagicMock(
            render_latex=MagicMock(return_value="\\documentclass{pub-cv}"),
            _generate_xmpdata=MagicMock(),
            TEMPLATE_DIR=tmp_path,
        )
        with patch.dict("sys.modules", {"render": mock_render}):
            result = build._discover_tailored(meta)

        assert "fig-job" in result
        # Verify figures were copied to src/cvs/fig-job/figures/
        target_fig = tmp_path / "src" / "cvs" / "fig-job" / "figures" / "logo.png"
        assert target_fig.exists()
        assert target_fig.read_bytes() == b"\x89PNG"

    def test_copies_rendered_xmpdata(self, tmp_path, monkeypatch):
        import yaml
        monkeypatch.setattr(build, "TAILORED_DIR", tmp_path / "tailored")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "rendered")
        monkeypatch.setattr(build, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(build, "CONTENT_ROOT", tmp_path)
        (tmp_path / "tailored").mkdir()
        (tmp_path / "rendered").mkdir()

        cv_data = {
            "name": {"first": "Jane", "last": "Doe"},
            "role": "PM", "summary": "Test",
            "experience": [{"title": "PM", "company": "Co", "dates": "2020",
                            "logo": "", "bullets": ["Did stuff."]}],
            "skills": [], "education": [], "languages": "English",
            "contact": {"phone": "+1", "email": "j@e.com"},
            "footer_address": "London",
        }
        with open(tmp_path / "tailored" / "xmp-job.yaml", "w") as f:
            yaml.dump(cv_data, f)
        (tmp_path / "rendered" / "xmp-job.xmpdata").write_text("Title: XMP")

        meta = {"documents": {"cv": {}}, "templates": {
            "cv": {"template": "cv.tex.j2", "data": "cv-data.yaml",
                   "type": "cv"},
        }}
        mock_render = MagicMock(
            render_latex=MagicMock(return_value="\\documentclass{pub-cv}"),
            _generate_xmpdata=MagicMock(),
            TEMPLATE_DIR=tmp_path,
        )
        with patch.dict("sys.modules", {"render": mock_render}):
            result = build._discover_tailored(meta)

        assert "xmp-job" in result
        copied = tmp_path / "src" / "cvs" / "xmp-job" / "xmp-job.xmpdata"
        assert copied.exists()

    def test_skips_registered_documents(self, tmp_path, monkeypatch):
        import yaml
        monkeypatch.setattr(build, "TAILORED_DIR", tmp_path / "tailored")
        (tmp_path / "tailored").mkdir()
        # "cv" matches a registered doc ID — should be skipped
        with open(tmp_path / "tailored" / "cv.yaml", "w") as f:
            yaml.dump({"experience": [], "skills": []}, f)

        meta = {"documents": {"cv": {}}, "templates": {}}
        result = build._discover_tailored(meta)
        assert "cv" not in result

    def test_returns_empty_when_no_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(build, "TAILORED_DIR", tmp_path / "nonexistent")
        result = build._discover_tailored({"documents": {}})
        assert result == {}

    def test_skips_empty_yaml(self, tmp_path, monkeypatch):
        monkeypatch.setattr(build, "TAILORED_DIR", tmp_path / "tailored")
        (tmp_path / "tailored").mkdir()
        (tmp_path / "tailored" / "empty.yaml").write_text("")

        meta = {"documents": {}, "templates": {}}
        result = build._discover_tailored(meta)
        assert result == {}

    def test_infers_paper_type(self, tmp_path, monkeypatch):
        import yaml
        monkeypatch.setattr(build, "TAILORED_DIR", tmp_path / "tailored")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "rendered")
        monkeypatch.setattr(build, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(build, "CONTENT_ROOT", tmp_path)
        (tmp_path / "tailored").mkdir()
        (tmp_path / "rendered").mkdir()

        # Data without experience/skills → fallback to paper
        paper_data = {"title": "My Paper", "sections": [{"heading": "Intro"}]}
        with open(tmp_path / "tailored" / "my-paper.yaml", "w") as f:
            yaml.dump(paper_data, f)

        meta = {"documents": {}, "templates": {
            "paper": {"template": "paper.tex.j2"},
        }}

        mock_render = MagicMock(
            render_latex=MagicMock(return_value="\\documentclass{pub-paper}"),
            _generate_xmpdata=MagicMock(),
            TEMPLATE_DIR=tmp_path,
        )
        with patch.dict("sys.modules", {"render": mock_render}):
            result = build._discover_tailored(meta)

        assert "my-paper" in result
        assert result["my-paper"]["class"] == "pub-paper"
        assert result["my-paper"]["src"] == "src/papers/my-paper/my-paper.tex"
        # Verify .tex was copied to src/papers/my-paper/
        src_tex = tmp_path / "src" / "papers" / "my-paper" / "my-paper.tex"
        assert src_tex.exists()

    def test_handles_render_failure(self, tmp_path, monkeypatch):
        import yaml
        monkeypatch.setattr(build, "TAILORED_DIR", tmp_path / "tailored")
        monkeypatch.setattr(build, "RENDERED_DIR", tmp_path / "rendered")
        monkeypatch.setattr(build, "PROJECT_ROOT", tmp_path)
        (tmp_path / "tailored").mkdir()

        cv_data = {"experience": [], "skills": []}
        with open(tmp_path / "tailored" / "broken.yaml", "w") as f:
            yaml.dump(cv_data, f)

        meta = {"documents": {}, "templates": {
            "cv": {"template": "cv.tex.j2"},
        }}

        mock_render = MagicMock(
            render_latex=MagicMock(side_effect=Exception("template error")),
            _generate_xmpdata=MagicMock(),
            TEMPLATE_DIR=tmp_path,
        )
        with patch.dict("sys.modules", {"render": mock_render}):
            result = build._discover_tailored(meta)
        assert result == {}
