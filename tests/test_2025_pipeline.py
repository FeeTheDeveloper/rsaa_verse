from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

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


def test_season_2025_pbp_parquet_has_rows() -> None:
    # Content-level check (not just existence): the only season actually ingested
    # so far -- 2025 -- must have a non-empty, well-formed play-by-play table.
    # Deliberately does not assert anything about any other season.
    path = ROOT / "data" / "nfl" / "raw" / "pbp" / f"season={DEFAULT_SEASON}" / f"play_by_play_{DEFAULT_SEASON}.parquet"
    assert path.exists(), f"missing tracked season {DEFAULT_SEASON} play-by-play parquet: {path}"
    table = pq.read_table(path)
    assert table.num_rows > 0
    assert "game_id" in table.schema.names
