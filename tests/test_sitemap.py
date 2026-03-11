"""test_sitemap.py — Tests for scripts/sitemap.py."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from euxis_publisher.cli import sitemap

sys.modules["sitemap"] = sitemap


# ── load_meta ────────────────────────────────────────────────────────────


class TestLoadMeta:
    def test_loads_real_meta(self):
        meta = sitemap.load_meta()
        assert "documents" in meta
        assert "author" in meta

    def test_exits_when_missing(self, tmp_path):
        with pytest.raises(SystemExit):
            sitemap.load_meta(tmp_path / "nonexistent.yaml")


# ── _classify_domain ─────────────────────────────────────────────────────


class TestClassifyDomain:
    @pytest.mark.parametrize(
        "cls_name,expected",
        [
            ("pub-cv", "cv"),
            ("pub-paper", "paper"),
            ("pub-prime", "paper"),
            ("pub-patent", "patent"),
            ("pub-patent-us", "patent"),
            ("pub-faq", "faq"),
            ("pub-guide", "guide"),
            ("pub-preprint", "paper"),
            ("pub-arxiv", "paper"),
            ("pub-bio", "bio"),
            ("pub-unknown", "other"),
        ],
    )
    def test_classification(self, cls_name, expected):
        assert sitemap._classify_domain(cls_name) == expected


# ── _source_exists ───────────────────────────────────────────────────────


class TestSourceExists:
    def test_existing_source(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "test.tex").write_text("hello")
        assert sitemap._source_exists("src/test.tex", tmp_path) is True

    def test_missing_source(self, tmp_path):
        assert sitemap._source_exists("src/nope.tex", tmp_path) is False


# ── generate_sitemap ────────────────────────────────────────────────────


class TestGenerateSitemap:
    def test_basic_structure(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "doc.tex").write_text("\\documentclass{pub-paper}")
        meta = {
            "author": {"name": "Test Author"},
            "documents": {
                "doc1": {
                    "title": "Test Document",
                    "class": "pub-paper",
                    "src": "src/doc.tex",
                    "version": "1.0",
                    "description": "A test",
                },
            },
        }
        result = sitemap.generate_sitemap(meta, project_root=tmp_path)
        assert result["project"] == "Publications"
        assert result["author"] == "Test Author"
        assert result["document_count"] == 1
        assert "paper" in result["domains"]
        assert len(result["documents"]) == 1

    def test_document_entry_fields(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "cv.tex").write_text("cv")
        meta = {
            "author": {"name": "Author"},
            "documents": {
                "cv": {
                    "title": "CV",
                    "class": "pub-cv",
                    "src": "src/cv.tex",
                    "version": "1.0",
                    "description": "Resume",
                    "pdf_a": "a-1a",
                },
            },
        }
        result = sitemap.generate_sitemap(meta, project_root=tmp_path)
        doc = result["documents"][0]
        assert doc["id"] == "cv"
        assert doc["domain"] == "cv"
        assert doc["source_exists"] is True
        assert doc["pdf_a"] == "a-1a"
        assert doc["standalone"] is True

    def test_optional_fields_included(self, tmp_path):
        meta = {
            "author": {},
            "documents": {
                "patent": {
                    "title": "Patent",
                    "class": "pub-patent",
                    "src": "src/patent.tex",
                    "version": "0.5",
                    "description": "Patent app",
                    "bib": "refs.bib",
                    "docket": "DOCKET-001",
                    "filing_date": "2024-01-01",
                    "options": "twocolumn",
                    "assets": "assets/patent/",
                },
            },
        }
        result = sitemap.generate_sitemap(meta, project_root=tmp_path)
        doc = result["documents"][0]
        assert doc["bib"] == "refs.bib"
        assert doc["docket"] == "DOCKET-001"
        assert doc["filing_date"] == "2024-01-01"
        assert doc["options"] == "twocolumn"
        assert doc["assets"] == "assets/patent/"

    def test_non_standalone_document(self, tmp_path):
        meta = {
            "author": {},
            "documents": {
                "input-doc": {
                    "title": "Input",
                    "class": "pub-paper",
                    "src": "src/input.tex",
                    "version": "1.0",
                    "description": "Input file",
                    "note": "This is an input file used by another",
                },
            },
        }
        result = sitemap.generate_sitemap(meta, project_root=tmp_path)
        doc = result["documents"][0]
        assert doc["standalone"] is False
        assert doc["note"] == "This is an input file used by another"

    def test_empty_documents(self, tmp_path):
        meta = {"author": {"name": "A"}, "documents": {}}
        result = sitemap.generate_sitemap(meta, project_root=tmp_path)
        assert result["document_count"] == 0
        assert result["documents"] == []
        assert result["domains"] == []

    def test_real_meta(self):
        meta = sitemap.load_meta()
        result = sitemap.generate_sitemap(meta)
        # 10 documents + 3 blog entries = 13
        assert result["document_count"] == 13
        assert "cv" in result["domains"]
        assert "paper" in result["domains"]
        assert "patent" in result["domains"]
        assert "blog" in result["domains"]


# ── write_sitemap ───────────────────────────────────────────────────────


class TestWriteSitemap:
    def test_writes_to_file(self, tmp_path):
        output = tmp_path / "site-map.json"
        data = {"documents": [], "generated": "2026-01-01"}
        sitemap.write_sitemap(data, output_path=output)
        assert output.exists()
        loaded = json.loads(output.read_text())
        assert loaded["generated"] == "2026-01-01"

    def test_writes_pretty(self, tmp_path):
        output = tmp_path / "site-map.json"
        data = {"documents": [{"id": "cv"}], "generated": "2026-01-01"}
        sitemap.write_sitemap(data, output_path=output, pretty=True)
        content = output.read_text()
        assert "\n" in content
        assert "  " in content  # indentation

    def test_writes_to_stdout(self, tmp_path, capsys):
        data = {"documents": [], "generated": "2026-01-01"}
        sitemap.write_sitemap(data, stdout=True)
        output = capsys.readouterr().out
        loaded = json.loads(output)
        assert loaded["generated"] == "2026-01-01"

    def test_creates_parent_dirs(self, tmp_path):
        output = tmp_path / "deep" / "nested" / "site-map.json"
        data = {"documents": []}
        sitemap.write_sitemap(data, output_path=output)
        assert output.exists()

    def test_valid_json_output(self, tmp_path):
        output = tmp_path / "site-map.json"
        meta = sitemap.load_meta()
        data = sitemap.generate_sitemap(meta)
        sitemap.write_sitemap(data, output_path=output, pretty=True)
        content = output.read_text()
        parsed = json.loads(content)
        assert isinstance(parsed["documents"], list)
        assert parsed["document_count"] == len(parsed["documents"])


# ── Blog sitemap tests ─────────────────────────────────────────────────


class TestBlogSitemap:
    def test_blog_entries_included(self):
        meta = {
            "author": {"name": "Test"},
            "documents": {},
            "blog": {
                "my-blog": {
                    "title": "Blog Post",
                    "type": "jinja2",
                    "date": "2026-02-17",
                    "description": "A test blog",
                    "data": "blog/test.yaml",
                },
            },
        }
        result = sitemap.generate_sitemap(meta)
        assert result["document_count"] == 1
        assert "blog" in result["domains"]
        doc = result["documents"][0]
        assert doc["id"] == "my-blog"
        assert doc["domain"] == "blog"
        assert doc["title"] == "Blog Post"
        assert doc["slug"] == "blog-post"

    def test_prime_class_maps_to_paper_domain(self):
        assert sitemap._classify_domain("pub-prime") == "paper"

    def test_blog_entries_empty_when_no_blog(self):
        entries = sitemap._blog_entries({"documents": {}})
        assert entries == []

    def test_blog_slug_derived_from_title(self):
        meta = {
            "author": {},
            "documents": {},
            "blog": {
                "b1": {
                    "title": "My Amazing Blog Post!",
                    "type": "jinja2",
                    "date": "2026-01-01",
                    "description": "B",
                    "data": "blog/b.yaml",
                },
            },
        }
        result = sitemap.generate_sitemap(meta)
        doc = result["documents"][0]
        assert doc["slug"] == "my-amazing-blog-post"

    def test_blog_slug_fallback_to_id(self):
        meta = {
            "author": {},
            "documents": {},
            "blog": {
                "my-fallback-id": {
                    "type": "jinja2",
                    "date": "2026-01-01",
                    "description": "B",
                    "data": "blog/b.yaml",
                },
            },
        }
        result = sitemap.generate_sitemap(meta)
        doc = result["documents"][0]
        assert doc["slug"] == "my-fallback-id"

    def test_blog_entries_merged_with_documents(self):
        meta = {
            "author": {"name": "A"},
            "documents": {
                "doc1": {
                    "title": "Doc",
                    "class": "pub-paper",
                    "src": "src/d.tex",
                    "version": "1.0",
                    "description": "D",
                },
            },
            "blog": {
                "b1": {
                    "title": "Blog",
                    "type": "jinja2",
                    "date": "2026-01-01",
                    "description": "B",
                    "data": "blog/b.yaml",
                },
            },
        }
        result = sitemap.generate_sitemap(meta)
        assert result["document_count"] == 2
        domains = result["domains"]
        assert "paper" in domains
        assert "blog" in domains


# ── Sitemap main() ──────────────────────────────────────────────────────


class TestSitemapMain:
    @patch("sys.argv", ["sitemap.py"])
    def test_main_writes_file(self, tmp_path, monkeypatch):
        output = tmp_path / "site-map.json"
        monkeypatch.setattr(sitemap, "OUTPUT_FILE", output)
        sitemap.main()
        assert output.exists()
        data = json.loads(output.read_text())
        assert "documents" in data

    @patch("sys.argv", ["sitemap.py", "--pretty", "--stdout"])
    def test_main_pretty_stdout(self, capsys):
        sitemap.main()
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "documents" in parsed
        assert "  " in output  # pretty-printed

    @patch("sys.argv", ["sitemap.py", "-o", "/tmp/custom-sitemap.json"])
    def test_main_custom_output(self):
        sitemap.main()
        from pathlib import Path

        out = Path("/tmp/custom-sitemap.json")
        assert out.exists()
        data = json.loads(out.read_text())
        assert "documents" in data
        out.unlink()
