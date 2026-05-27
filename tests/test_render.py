"""test_render.py — Tests for scripts/render.py Jinja2 rendering engine."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from euxis_publisher.cli import render

sys.modules["render"] = render


# ── TestCreateJinjaEnv ───────────────────────────────────────────────────


class TestCreateJinjaEnv:
    def test_custom_delimiters(self):
        env = render.create_jinja_env()
        assert env.block_start_string == "<%"
        assert env.block_end_string == "%>"
        assert env.variable_start_string == "<<"
        assert env.variable_end_string == ">>"
        assert env.comment_start_string == "<#"
        assert env.comment_end_string == "#>"

    def test_strict_undefined(self):
        from jinja2 import StrictUndefined

        env = render.create_jinja_env()
        assert env.undefined is StrictUndefined

    def test_custom_template_dir(self, tmp_path):
        env = render.create_jinja_env(tmp_path)
        assert env.loader is not None


# ── TestRenderLatex ──────────────────────────────────────────────────────


class TestRenderLatex:
    def test_basic_substitution(self, tmp_path):
        (tmp_path / "test.tex.j2").write_text(
            r"\title{<< title >>}" + "\n"
        )
        result = render.render_latex("test.tex.j2", {"title": "Hello"}, tmp_path)
        assert r"\title{Hello}" in result

    def test_loop_rendering(self, tmp_path):
        template = (
            "<% for item in items %>\\item << item >>\n<% endfor %>"
        )
        (tmp_path / "loop.j2").write_text(template)
        result = render.render_latex(
            "loop.j2", {"items": ["A", "B"]}, tmp_path
        )
        assert r"\item A" in result
        assert r"\item B" in result

    def test_missing_variable_raises(self, tmp_path):
        from jinja2 import UndefinedError

        (tmp_path / "missing.j2").write_text("<< missing_var >>")
        with pytest.raises(UndefinedError):
            render.render_latex("missing.j2", {}, tmp_path)


# ── TestRenderMarkdown ───────────────────────────────────────────────────


class TestRenderMarkdown:
    def _make_cv_data(self):
        return {
            "name": {"first": "Jane", "last": "Doe"},
            "role": "Engineer",
            "contact": {"phone": "+1234", "email": "jane@example.com"},
            "summary": "A summary.",
            "experience": [
                {
                    "title": "Dev",
                    "company": "Corp",
                    "dates": "2020-2024",
                    "logo": "",
                    "bullets": ["Did things"],
                }
            ],
            "prior_experience": [
                {
                    "title": "Intern",
                    "company": "Startup",
                    "dates": "2019",
                    "logo": "",
                    "location": "",
                }
            ],
            "skills": [
                {"title": "Coding", "description": "Writes code."}
            ],
            "education": [
                {
                    "year": "2020",
                    "degree": "BSc CS",
                    "institution": "Uni,",
                    "location": "City",
                }
            ],
            "languages": "English",
        }

    def test_cv_output_structure(self):
        data = self._make_cv_data()
        result = render.render_markdown(data, "cv")
        assert "# Jane Doe" in result
        assert "## Summary" in result
        assert "## Professional Experience" in result
        assert "## Education" in result
        assert "## Languages" in result

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown document type"):
            render.render_markdown({}, "unknown_type")

    def test_blog_type_delegates(self, tmp_path):
        (tmp_path / "blog-post.md.j2").write_text(
            "---\ntitle: \"<< title | default('') >>\"\n---\n<< body | default('') >>\n"
        )
        with patch.object(render, "TEMPLATE_DIR", tmp_path):
            result = render.render_markdown(
                {"title": "Test", "body": "Content"}, "blog"
            )
        assert "Test" in result


# ── TestRenderJson ───────────────────────────────────────────────────────


class TestRenderJson:
    def test_valid_json_output(self):
        data = {"name": "Test", "items": [1, 2, 3]}
        result = render.render_json(data)
        parsed = json.loads(result)
        assert parsed["name"] == "Test"
        assert parsed["items"] == [1, 2, 3]


# ── TestRenderDocument ───────────────────────────────────────────────────


class TestRenderDocument:
    def test_unknown_doc_exits(self, monkeypatch):
        monkeypatch.setattr(render, "META_FILE", render.META_FILE)
        with pytest.raises(SystemExit):
            render.render_document("nonexistent_doc_xyz")

    def test_registered_template_renders(self, monkeypatch, tmp_path):
        # Create minimal meta, data, and template
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "meta.yaml").write_text(
            "templates:\n"
            "  testdoc:\n"
            "    template: test.tex.j2\n"
            "    data: test-data.yaml\n"
            "    type: cv\n"
        )
        (data_dir / "test-data.yaml").write_text("title: Hello\n")
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.tex.j2").write_text("<< title >>")
        build_rendered = tmp_path / "build" / ".cache" / "rendered"

        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)

        result = render.render_document("testdoc", "latex", "draft")
        assert "Hello" in result
        assert (build_rendered / "testdoc.tex").exists()

    def test_missing_meta_exits(self, monkeypatch, tmp_path):
        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)
        with pytest.raises(SystemExit):
            render.render_document("cv")

    def test_missing_data_file_exits(self, monkeypatch, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "meta.yaml").write_text(
            "templates:\n"
            "  bad:\n"
            "    template: t.j2\n"
            "    data: missing.yaml\n"
        )
        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)
        with pytest.raises(SystemExit):
            render.render_document("bad")

    def test_markdown_format(self, monkeypatch, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "meta.yaml").write_text(
            "templates:\n"
            "  cvtest:\n"
            "    template: cv.tex.j2\n"
            "    data: cv.yaml\n"
            "    type: cv\n"
        )
        (data_dir / "cv.yaml").write_text(
            "name:\n  first: A\n  last: B\n"
            "role: R\n"
            "contact:\n  phone: '1'\n  email: e@e\n"
            "summary: S\n"
            "experience: []\n"
            "prior_experience: []\n"
            "skills: []\n"
            "education: []\n"
            "languages: L\n"
        )
        build_rendered = tmp_path / "build" / ".cache" / "rendered"
        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)

        result = render.render_document("cvtest", "markdown", "draft")
        assert "# A B" in result
        assert (build_rendered / "cvtest.md").exists()

    def test_json_format(self, monkeypatch, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "meta.yaml").write_text(
            "templates:\n"
            "  jtest:\n"
            "    template: t.j2\n"
            "    data: d.yaml\n"
        )
        (data_dir / "d.yaml").write_text("key: value\n")
        build_rendered = tmp_path / "build" / ".cache" / "rendered"
        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)

        result = render.render_document("jtest", "json", "draft")
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert (build_rendered / "jtest.json").exists()

    def test_tailored_data_override(self, monkeypatch, tmp_path):
        """When data/tailored/{doc_id}.yaml exists, use it instead of base."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "meta.yaml").write_text(
            "templates:\n"
            "  testdoc:\n"
            "    template: test.tex.j2\n"
            "    data: test-data.yaml\n"
            "    type: cv\n"
        )
        (data_dir / "test-data.yaml").write_text("title: Original\n")
        # Create tailored override
        tailored_dir = data_dir / "tailored"
        tailored_dir.mkdir()
        (tailored_dir / "testdoc.yaml").write_text("title: Tailored\n")
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.tex.j2").write_text("<< title >>")

        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)

        result = render.render_document("testdoc", "latex", "draft")
        assert "Tailored" in result
        assert "Original" not in result

    def test_can_disable_tailored_data_override(self, monkeypatch, tmp_path):
        """Explicit docs can opt out of data/tailored shadowing."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "meta.yaml").write_text(
            "templates:\n"
            "  testdoc:\n"
            "    template: test.tex.j2\n"
            "    data: test-data.yaml\n"
            "    type: cv\n"
            "    allow_tailored_override: false\n"
        )
        (data_dir / "test-data.yaml").write_text("title: Dedicated\n")
        tailored_dir = data_dir / "tailored"
        tailored_dir.mkdir()
        (tailored_dir / "testdoc.yaml").write_text("title: Tailored\n")
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.tex.j2").write_text("<< title >>")

        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)

        result = render.render_document("testdoc", "latex", "draft")
        assert "Dedicated" in result
        assert "Tailored" not in result

    def test_unknown_format_exits(self, monkeypatch, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "meta.yaml").write_text(
            "templates:\n"
            "  doc:\n"
            "    template: t.j2\n"
            "    data: d.yaml\n"
        )
        (data_dir / "d.yaml").write_text("key: value\n")
        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)
        with pytest.raises(SystemExit):
            render.render_document("doc", "xml", "draft")


# ── TestRenderMain ──────────────────────────────────────────────────────


class TestRenderMain:
    @patch("sys.argv", ["render.py", "--doc", "cv"])
    @patch("render.render_document")
    def test_main_defaults(self, mock_rd):
        render.main()
        mock_rd.assert_called_once_with("cv", "latex", "draft")

    @patch("sys.argv", ["render.py", "--doc", "cv", "--format", "markdown",
                         "--mode", "submission"])
    @patch("render.render_document")
    def test_main_with_options(self, mock_rd):
        render.main()
        mock_rd.assert_called_once_with("cv", "markdown", "submission")

    @patch("sys.argv", ["render.py"])
    def test_main_no_args_exits(self):
        with pytest.raises(SystemExit):
            render.main()


# ── TestCVRegression ─────────────────────────────────────────────────────


class TestCVRegression:
    def test_rendered_cv_matches_source(self):
        """Rendered CV from YAML+template matches src/cvs/cv.tex
        after whitespace normalization."""
        import yaml as pyyaml

        data_path = render.PROJECT_ROOT / "data" / "cv-data.yaml"
        if not data_path.exists():
            pytest.skip("cv-data.yaml not found")

        with open(data_path) as f:
            data = pyyaml.safe_load(f)

        rendered = render.render_latex("cv.tex.j2", data)
        source = (render.PROJECT_ROOT / "src" / "cvs" / "cv.tex").read_text()

        def normalize(text):
            """Normalize whitespace for comparison."""
            lines = [line.rstrip() for line in text.strip().splitlines()]
            return "\n".join(line for line in lines if line)

        assert normalize(rendered) == normalize(source)


# ── TestSlugify ────────────────────────────────────────────────────────


class TestSlugify:
    @pytest.mark.parametrize(
        "title,expected",
        [
            (
                "Bug Discovered in Quantum Algorithm for Lattice-Based Crypto",
                "bug-discovered-in-quantum-algorithm-for-lattice-based-crypto",
            ),
            ("Simple Title", "simple-title"),
            ("Title With!  Special@#  Chars", "title-with-special-chars"),
            ("already-slugified", "already-slugified"),
            ("Multiple   Spaces", "multiple-spaces"),
            ("Under_scores_too", "under-scores-too"),
            ("  Leading & Trailing  ", "leading-trailing"),
            (
                "Quantum-Safe API Authentication",
                "quantum-safe-api-authentication",
            ),
        ],
    )
    def test_slugify(self, title, expected):
        assert render.slugify(title) == expected


# ── TestRenderBlogMarkdown ──────────────────────────────────────────────


class TestRenderBlogMarkdown:
    def test_jinja2_blog_renders(self, tmp_path):
        (tmp_path / "blog.md.j2").write_text(
            "---\ntitle: \"<< title | default('') >>\"\n---\n<< body | default('') >>\n"
        )
        result = render.render_blog_markdown(
            {"title": "Test Post", "body": "Hello world"},
            "blog.md.j2",
            tmp_path,
        )
        assert "Test Post" in result
        assert "Hello world" in result

    def test_blog_frontmatter_complete(self, tmp_path):
        (tmp_path / "blog.md.j2").write_text(
            "---\n"
            "title: \"<< title | default('') >>\"\n"
            "author: \"<< author | default('') >>\"\n"
            "date: \"<< date | default('') >>\"\n"
            "---\n"
            "<< body | default('') >>\n"
        )
        result = render.render_blog_markdown(
            {
                "title": "My Post",
                "author": "Author",
                "date": "2026-02-17",
                "body": "Content",
            },
            "blog.md.j2",
            tmp_path,
        )
        assert "---" in result
        assert 'title: "My Post"' in result
        assert 'author: "Author"' in result
        assert "2026-02-17" in result

    def test_blog_with_tags(self, tmp_path):
        (tmp_path / "blog.md.j2").write_text(
            "tags: \"<< tags | default([]) | join(', ') >>\"\n"
        )
        result = render.render_blog_markdown(
            {"tags": ["ml", "asr"]},
            "blog.md.j2",
            tmp_path,
        )
        assert "ml, asr" in result


# ── TestConvertLatexToBlog ──────────────────────────────────────────────


class TestConvertLatexToBlog:
    @patch("render.subprocess.run")
    def test_pandoc_conversion(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="# Converted\n\nBody text\n", stderr=""
        )
        meta_entry = {
            "title": "Test",
            "date": "2026-02-17",
            "author": "Author",
            "description": "Desc",
            "tags": ["a", "b"],
        }
        result = render.convert_latex_to_blog(
            "src/test.tex", meta_entry, "/tmp"
        )
        assert "---" in result
        assert 'title: "Test"' in result
        assert "Body text" in result

    @patch("render.subprocess.run")
    def test_pandoc_failure_raises(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="pandoc error"
        )
        with pytest.raises(RuntimeError, match="pandoc conversion failed"):
            render.convert_latex_to_blog(
                "src/test.tex",
                {"title": "T", "date": "D", "author": "A", "description": "D"},
                "/tmp",
            )


# ── TestRenderBlog ──────────────────────────────────────────────────────


class TestRenderBlog:
    def test_jinja2_type_writes_artifact(self, tmp_path):
        # Set up template
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "blog.md.j2").write_text(
            "---\ntitle: \"<< title | default('') >>\"\n---\n<< body | default('') >>\n"
        )
        # Set up data
        data_dir = tmp_path / "data" / "blog"
        data_dir.mkdir(parents=True)
        (data_dir / "test.yaml").write_text("title: Hello\nbody: World\n")

        config = {
            "type": "jinja2",
            "data": "blog/test.yaml",
            "template": "blog.md.j2",
            "title": "Test Post",
            "date": "2026-02-17",
        }
        result = render.render_blog("test", config, tmp_path)
        assert "Hello" in result
        out_file = tmp_path / "build" / "blog" / "2026-02-17-test-post.md"
        assert out_file.exists()

    @patch("render.subprocess.run")
    def test_convert_type_calls_pandoc(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Converted body\n", stderr=""
        )
        config = {
            "type": "convert",
            "src": "src/test.tex",
            "date": "2026-02-17",
            "title": "Conv Post",
            "author": "A",
            "description": "D",
            "tags": [],
        }
        result = render.render_blog("conv", config, tmp_path)
        assert "Converted body" in result
        out_file = tmp_path / "build" / "blog" / "2026-02-17-conv-post.md"
        assert out_file.exists()

    def test_unknown_type_raises(self, tmp_path):
        config = {
            "type": "unknown",
            "title": "Bad Post",
            "date": "2026-02-17",
        }
        with pytest.raises(ValueError, match="Unknown blog type"):
            render.render_blog("bad", config, tmp_path)

    def test_default_date_when_missing(self, tmp_path):
        """When date is not in config, uses today's date."""
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "blog.md.j2").write_text("<< body | default('') >>")
        data_dir = tmp_path / "data" / "blog"
        data_dir.mkdir(parents=True)
        (data_dir / "d.yaml").write_text("body: hi\n")

        config = {
            "type": "jinja2",
            "data": "blog/d.yaml",
            "template": "blog.md.j2",
            "title": "No Date Post",
        }
        render.render_blog("x", config, tmp_path)
        from datetime import date

        today = date.today().isoformat()
        out_file = tmp_path / "build" / "blog" / f"{today}-no-date-post.md"
        assert out_file.exists()

    def test_slug_derived_from_title(self, tmp_path):
        """Slug is derived from title via slugify()."""
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "blog.md.j2").write_text("<< body | default('') >>")
        data_dir = tmp_path / "data" / "blog"
        data_dir.mkdir(parents=True)
        (data_dir / "d.yaml").write_text("body: hi\n")

        config = {
            "type": "jinja2",
            "data": "blog/d.yaml",
            "template": "blog.md.j2",
            "title": "My Amazing Blog Post!",
            "date": "2026-01-01",
        }
        render.render_blog("x", config, tmp_path)
        out_file = tmp_path / "build" / "blog" / "2026-01-01-my-amazing-blog-post.md"
        assert out_file.exists()

    def test_title_fallback_to_blog_id(self, tmp_path):
        """When title is not in config, falls back to blog_id."""
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "blog.md.j2").write_text("<< body | default('') >>")
        data_dir = tmp_path / "data" / "blog"
        data_dir.mkdir(parents=True)
        (data_dir / "d.yaml").write_text("body: hi\n")

        config = {
            "type": "jinja2",
            "data": "blog/d.yaml",
            "template": "blog.md.j2",
            "date": "2026-01-01",
        }
        render.render_blog("my-blog-id", config, tmp_path)
        out_file = tmp_path / "build" / "blog" / "2026-01-01-my-blog-id.md"
        assert out_file.exists()

    def test_convert_default_project_root(self):
        """convert_latex_to_blog uses PROJECT_ROOT when project_root is None."""
        with patch("render.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="body\n", stderr=""
            )
            result = render.convert_latex_to_blog(
                "src/test.tex",
                {"title": "T", "date": "D", "author": "A", "description": "D"},
            )
            assert "---" in result

    def test_render_blog_default_project_root(self, tmp_path):
        """render_blog uses CONTENT_ROOT when content_root is None."""
        with patch.object(render, "CONTENT_ROOT", tmp_path):
            templates = tmp_path / "templates"
            templates.mkdir()
            (templates / "blog-post.md.j2").write_text("<< body | default('') >>")
            data_dir = tmp_path / "data" / "blog"
            data_dir.mkdir(parents=True)
            (data_dir / "d.yaml").write_text("body: hi\n")

            config = {
                "type": "jinja2",
                "data": "blog/d.yaml",
                "title": "Test",
                "date": "2026-01-01",
            }
            result = render.render_blog("x", config)
            assert "hi" in result

    def test_date_stamped_filename(self, tmp_path):
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "blog.md.j2").write_text("<< body | default('') >>")
        data_dir = tmp_path / "data" / "blog"
        data_dir.mkdir(parents=True)
        (data_dir / "d.yaml").write_text("body: text\n")

        config = {
            "type": "jinja2",
            "data": "blog/d.yaml",
            "template": "blog.md.j2",
            "title": "My Slug",
            "date": "2026-03-15",
        }
        render.render_blog("x", config, tmp_path)
        out_file = tmp_path / "build" / "blog" / "2026-03-15-my-slug.md"
        assert out_file.exists()


# ── Shokunin SSG Blog Regression Test ────────────────────────────────────


class TestShokuninBlogRegression:
    """Verify the blog bridge reproduces a known Shokunin SSG blog post
    byte-for-byte.

    Reference: sebastienrousseau/sebastienrousseau.github.io
    _posts/2024-04-22-bug-discovered-in-quantum-algorithm-for-lattice-based-crypto.md
    """

    REFERENCE_PATH = (
        render.PROJECT_ROOT
        / "data"
        / "blog"
        / "security-bug-blog.yaml"
    )

    @pytest.fixture()
    def reference_content(self):
        """Load the expected output by rendering the reference YAML through
        the real project template and returning the result."""
        import subprocess

        result = subprocess.run(
            [
                "gh", "api",
                "repos/sebastienrousseau/sebastienrousseau.github.io"
                "/contents/_posts/2024-04-22-bug-discovered-in-quantum-"
                "algorithm-for-lattice-based-crypto.md",
                "--jq", ".content",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip("gh CLI not available or API rate-limited")

        import base64

        return base64.b64decode(result.stdout.strip()).decode("utf-8")

    def _render(self):
        import yaml as pyyaml

        with open(self.REFERENCE_PATH) as f:
            data = pyyaml.safe_load(f)
        template_dir = render.PROJECT_ROOT / "templates"
        return render.render_blog_markdown(
            data, "blog-post.md.j2", template_dir
        )

    def test_renders_without_error(self):
        result = self._render()
        assert "---" in result
        assert "Bug Discovered" in result

    def test_frontmatter_fields_present(self):
        result = self._render()
        assert 'author: "contact@sebastienrousseau.com' in result
        assert 'banner_alt: "Image generated using MidJourney' in result
        assert "changefreq: \"weekly\"" in result
        assert 'charset: "UTF-8"' in result
        assert "Apr 22, 2024" in result
        assert "post-quantum cryptography" in result
        assert 'layout: "report"' in result
        assert 'locale: "en_GB"' in result
        assert 'news_genres: "Blog"' in result
        assert "twitter_card: \"summary\"" in result
        assert 'twitter_creator: "@wwdseb"' in result
        assert "Shokunin SSG" in result
        assert "apple-mobile-web-app-capable" in result
        assert "msapplication-navbutton-color" in result
        assert 'site_software: "Shokunin, Rust"' in result

    def test_body_content_present(self):
        result = self._render()
        assert "The Quantum Conundrum" in result
        assert "Yilei Chen" in result
        assert "Nigel Smart" in result
        assert "CRYSTALS-KYBER" in result
        assert "CRYSTALS-Dilithium" in result
        assert "37 CFR" not in result  # should NOT be in this post
        assert "[00]:" in result
        assert "[07]:" in result

    def test_exact_match_with_github(self, reference_content):
        """Byte-for-byte comparison with GitHub reference (opt-in in public engine)."""
        import os
        if os.getenv("EUXIS_STRICT_GOLDEN") != "1":
            pytest.skip("Strict golden comparison is opt-in for public engine")
        rendered = self._render()
        assert rendered == reference_content


# ── TestXmpDataGeneration ─────────────────────────────────────────────


class TestXmpDataGeneration:
    def test_generates_xmpdata(self, monkeypatch, tmp_path):
        rendered_dir = tmp_path / "build" / "rendered"
        monkeypatch.setattr(render, "RENDERED_DIR", rendered_dir)

        data = {"title": "My Title", "subject": "Test", "keywords": "a, b"}
        meta = {"author": {"name": "Author Name"}}
        result = render._generate_xmpdata("testdoc", data, meta)
        assert result.exists()
        assert result.name == "testdoc.xmpdata"

    def test_xmpdata_fields(self, monkeypatch, tmp_path):
        rendered_dir = tmp_path / "build" / "rendered"
        monkeypatch.setattr(render, "RENDERED_DIR", rendered_dir)

        data = {
            "title": "PDF Title",
            "subject": "PDF Subject",
            "description": "A test PDF document",
            "keywords": "kw1, kw2",
            "copyright": "\u00a9 2026 Test",
        }
        meta = {"author": {"name": "Test Author"}}
        xmp_path = render._generate_xmpdata("doc", data, meta)
        content = xmp_path.read_text()
        assert "\\Title{PDF Title}" in content
        assert "\\Author{Test Author}" in content
        assert "\\Subject{PDF Subject}" in content
        assert "\\Description{A test PDF document}" in content
        assert "\\Keywords{kw1, kw2}" in content
        assert "\\Copyright{\u00a9 2026 Test}" in content
        assert "\\Creator{LaTeX with hyperref}" in content
        assert "\\CreatorTool{Publications Build System}" in content
        assert "\\Language{en}" in content

    def test_xmpdata_defaults(self, monkeypatch, tmp_path):
        rendered_dir = tmp_path / "build" / "rendered"
        monkeypatch.setattr(render, "RENDERED_DIR", rendered_dir)

        data = {}
        meta = {}
        xmp_path = render._generate_xmpdata("fallback-doc", data, meta)
        content = xmp_path.read_text()
        # Title falls back to doc_id
        assert "\\Title{fallback-doc}" in content
        # Author falls back to empty
        assert "\\Author{}" in content
        # Subject/Description/Keywords/Copyright fall back to empty
        assert "\\Subject{}" in content
        assert "\\Description{}" in content
        assert "\\Keywords{}" in content
        assert "\\Copyright{}" in content

    def test_xmpdata_generated_on_latex_render(self, monkeypatch, tmp_path):
        """render_document() generates .xmpdata when format is latex."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "meta.yaml").write_text(
            "author:\n  name: Author\n"
            "templates:\n"
            "  testdoc:\n"
            "    template: test.tex.j2\n"
            "    data: test-data.yaml\n"
            "    type: cv\n"
        )
        (data_dir / "test-data.yaml").write_text(
            "title: Hello\nsubject: S\nkeywords: K\n"
        )
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.tex.j2").write_text("<< title >>")
        build_rendered = tmp_path / "build" / ".cache" / "rendered"

        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)

        render.render_document("testdoc", "latex", "draft")
        xmp_path = build_rendered / "testdoc.xmpdata"
        assert xmp_path.exists()
        content = xmp_path.read_text()
        assert "\\Title{Hello}" in content

    def test_xmpdata_not_generated_for_markdown(self, monkeypatch, tmp_path):
        """render_document() does NOT generate .xmpdata for markdown format."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "meta.yaml").write_text(
            "author:\n  name: Author\n"
            "templates:\n"
            "  cvtest:\n"
            "    template: cv.tex.j2\n"
            "    data: cv.yaml\n"
            "    type: cv\n"
        )
        (data_dir / "cv.yaml").write_text(
            "name:\n  first: A\n  last: B\n"
            "role: R\n"
            "contact:\n  phone: '1'\n  email: e@e\n"
            "summary: S\n"
            "experience: []\n"
            "prior_experience: []\n"
            "skills: []\n"
            "education: []\n"
            "languages: L\n"
        )
        build_rendered = tmp_path / "build" / ".cache" / "rendered"
        monkeypatch.setattr(render, "CONTENT_ROOT", tmp_path)

        render.render_document("cvtest", "markdown", "draft")
        xmp_path = build_rendered / "cvtest.xmpdata"
        assert not xmp_path.exists()
