from __future__ import annotations

from pathlib import Path

from rsaa_verse.config import ROOT, DEFAULT_SEASON


def test_repo_root_exists() -> None:
    assert ROOT.exists()
    assert (ROOT / "README.md").exists()
    assert (ROOT / "DESCRIPTION").exists()


def test_default_season_is_2025() -> None:
    assert DEFAULT_SEASON == 2025


def test_expected_rsaa_directories_exist() -> None:
    expected = [
        ROOT / "python" / "rsaa_verse",
        ROOT / "warehouse",
        ROOT / "data" / "nfl" / "raw",
        ROOT / "data" / "nfl" / "normalized",
        ROOT / "exports" / "runner_demon",
        ROOT / "reports",
    ]
    for path in expected:
        assert path.exists(), f"missing required path: {path}"
