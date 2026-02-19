"""test_assets.py — Verify asset pipeline configuration and sources."""

import pytest


def test_mmd_files_in_assets(project_root):
    """Verify .mmd diagram sources exist in assets/."""
    assets_dir = project_root / "assets"
    mmd_files = list(assets_dir.rglob("*.mmd"))
    assert len(mmd_files) > 0, "No .mmd files found in assets/"


def test_qaas_diagrams_present(project_root):
    """Verify QAAS patent diagrams are in assets/patents/qaas/."""
    qaas_dir = project_root / "assets" / "patents" / "qaas"
    mmd_files = list(qaas_dir.glob("*.mmd"))
    assert len(mmd_files) >= 10, (
        f"Expected >= 10 QAAS diagrams, found {len(mmd_files)}"
    )


def test_qeap_diagrams_present(project_root):
    """Verify QEAP patent diagrams are in assets/patents/qeap/."""
    qeap_dir = project_root / "assets" / "patents" / "qeap"
    mmd_files = list(qeap_dir.glob("*.mmd"))
    assert len(mmd_files) >= 5, (
        f"Expected >= 5 QEAP diagrams, found {len(mmd_files)}"
    )


def test_asset_pipeline_exists(project_root):
    """Verify asset pipeline script exists and is executable."""
    script = project_root / "scripts" / "asset-pipeline.sh"
    assert script.exists(), "scripts/asset-pipeline.sh not found"
    assert script.stat().st_mode & 0o111, "asset-pipeline.sh is not executable"
