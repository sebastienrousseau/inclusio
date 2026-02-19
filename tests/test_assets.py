"""test_assets.py — Verify engine asset pipeline wiring."""


def test_asset_pipeline_exists(project_root):
    """Verify asset pipeline script exists and is executable."""
    script = project_root / "scripts" / "asset-pipeline.sh"
    assert script.exists(), "scripts/asset-pipeline.sh not found"
    assert script.stat().st_mode & 0o111, "asset-pipeline.sh is not executable"
