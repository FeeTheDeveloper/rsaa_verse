from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

import duckdb
import pyarrow.parquet as pq

from .config import ROOT, NFL_RAW_ROOT, WAREHOUSE_PATH, MANIFEST_PATH


def download_file(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request.urlretrieve(url, str(dest))
    return dest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parquet_stats(path: Path) -> tuple[int, int]:
    table = pq.read_table(path)
    return int(table.num_rows), int(len(table.schema))


def manifest_record(
    *,
    sport: str,
    dataset: str,
    season: int,
    source: str,
    source_locator: str,
    local_path: str,
    format_name: str,
    status: str,
    attempt_count: int = 1,
    error: str | None = None,
    source_version: str = "latest",
    schema_version: str = "v0.1",
    current_season: bool = False,
    row_count: int | None = None,
    column_count: int | None = None,
    file_bytes: int | None = None,
    sha256: str | None = None,
) -> dict[str, Any]:
    path = Path(local_path)
    return {
        "sport": sport,
        "dataset": dataset,
        "season": season,
        "source": source,
        "source_locator": source_locator,
        "source_version": source_version,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "local_path": str(path),
        "format": format_name,
        "bytes": file_bytes if file_bytes is not None else path.stat().st_size,
        "row_count": row_count,
        "column_count": column_count,
        "sha256": sha256 if sha256 is not None else sha256_file(path),
        "status": status,
        "schema_version": schema_version,
        "attempt_count": attempt_count,
        "error": error,
        "current_season": current_season,
    }


def ensure_warehouse() -> None:
    # NOTE: do not pre-create WAREHOUSE_PATH with .touch() here -- duckdb.connect()
    # refuses to open an existing-but-empty file ("not a valid DuckDB database
    # file"), so touching it first breaks first-run ingestion into a warehouse
    # path that doesn't exist yet. duckdb.connect() creates the file itself when
    # the path is absent, so only the parent directory needs to exist.
    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)


def ingest_nfl_pbp_season(season: int = 2025) -> dict[str, Any]:
    ensure_warehouse()
    url = f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"
    dest = NFL_RAW_ROOT / "pbp" / f"season={season}" / f"play_by_play_{season}.parquet"
    download_file(url, dest)
    row_count, column_count = parquet_stats(dest)
    digest = sha256_file(dest)
    record = manifest_record(
        sport="nfl",
        dataset="pbp",
        season=season,
        source="nflverse-data",
        source_locator=url,
        local_path=str(dest),
        format_name="parquet",
        status="completed",
        attempt_count=1,
        source_version="latest",
        current_season=(season == 2025),
        row_count=row_count,
        column_count=column_count,
        file_bytes=dest.stat().st_size,
        sha256=digest,
    )
    manifest_dir = MANIFEST_PATH.parent
    manifest_dir.mkdir(parents=True, exist_ok=True)
    existing = []
    if MANIFEST_PATH.exists():
        existing = json.loads(MANIFEST_PATH.read_text())
    existing.append(record)
    MANIFEST_PATH.write_text(json.dumps(existing, indent=2))

    con = duckdb.connect(str(WAREHOUSE_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(f"CREATE OR REPLACE TABLE raw.pbp_{season} AS SELECT * FROM read_parquet('{dest.as_posix()}')")
    con.execute("CREATE SCHEMA IF NOT EXISTS normalized")
    con.execute(
        f"CREATE OR REPLACE TABLE normalized.pbp_{season} AS SELECT game_id, play_id, season, season_type, week, game_date, home_team, away_team, posteam, defteam, quarter, game_seconds_remaining, half_seconds_remaining, quarter_seconds_remaining, down, ydstogo, yardline_100, yards_gained, play_type, pass, rush, sack, turnover, touchdown, field_goal, punt, kickoff, penalty, first_down, passer, rusher, receiver, air_yards, yards_after_catch, ep, epa, wp, win_probability, expected_points, score, score_differential, drive_id FROM read_parquet('{dest.as_posix()}')"
    )
    con.close()
    return record
