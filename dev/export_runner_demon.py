#!/usr/bin/env python3
"""Export validated curated Verse tables for Demon consumption."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", default="warehouse/runner_nfl_history.duckdb")
    parser.add_argument("--output", default="exports/runner_demon")
    parser.add_argument("--season", type=int, default=2025)
    args = parser.parse_args()
    warehouse = Path(args.warehouse)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(warehouse), read_only=True)
    definitions = {
        "team_profiles.parquet": "select offense as team, count(*) drives, avg(yards) avg_drive_yards, avg(plays) avg_drive_plays, avg(epa) avg_drive_epa from normalized.drives group by offense",
        "game_baselines.parquet": "select * from normalized.games",
        "drive_baselines.parquet": "select * from normalized.drives",
        "period_baselines.parquet": "select * from features.period",
        "game_state_baselines.parquet": "select * from research.game_state_samples",
        "market_history.parquet": "select * from normalized.games where closing_total is not null or closing_spread is not null",
    }
    artifacts = []
    for filename, query in definitions.items():
        target = output / filename
        connection.execute(f"copy ({query}) to ? (format parquet, compression zstd)", [str(target)])
        artifacts.append({"path": filename, "rows": connection.execute(f"select count(*) from read_parquet(?)", [str(target)]).fetchone()[0], "sha256": sha256(target)})
    validation = connection.execute("select validation_status from metadata.ingestion_manifest order by retrieved_at desc limit 1").fetchone()[0]
    connection.close()
    manifest = {
        "schema_version": "runner.verse-export.v1",
        "feature_version": "runner_nfl_history.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seasons": [args.season],
        "sources": ["nflverse_pbp"],
        "artifacts": artifacts,
        "validation": {"status": "passed" if validation == "passed" else "failed", "report": "DuckDB normalized games, plays, drives, periods, and state samples validated."},
        "producer_version": "rsaa_verse.runner-export.v1",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0 if manifest["validation"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
