#!/usr/bin/env python3
"""Build a small, lineage-preserving NFL history warehouse from nflverse PBP."""
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


def build(input_path: Path, warehouse: Path, season: int) -> dict[str, object]:
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256(input_path)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    connection = duckdb.connect(str(warehouse))
    source = str(input_path.resolve()).replace("\\", "/").replace("'", "''")
    connection.execute("create schema if not exists normalized")
    connection.execute("create schema if not exists features")
    connection.execute("create schema if not exists research")
    connection.execute("create schema if not exists metadata")
    connection.execute("drop table if exists normalized.plays")
    connection.execute("drop table if exists normalized.games")
    connection.execute("drop table if exists normalized.drives")
    connection.execute("drop table if exists features.period")
    connection.execute("drop table if exists research.game_state_samples")
    connection.execute(f"""
      create table normalized.plays as
      select game_id, play_id, season, week, game_date, home_team, away_team,
        posteam as offense, defteam as defense, qtr as quarter,
        game_seconds_remaining, half_seconds_remaining, time, down, ydstogo,
        yardline_100, ydsnet, play_type, play_type_nfl, yards_gained,
        first_down, third_down_converted, fourth_down_converted, interception,
        fumble_lost, sack, penalty, touchdown, pass_touchdown, rush_touchdown,
        return_touchdown, field_goal_result, td_team, total_home_score,
        total_away_score, score_differential, epa, success, qb_epa,
        total, spread_line, stadium,
        drive as drive_id, fixed_drive, drive_play_count, drive_time_of_possession,
        game_date as source_timestamp,
        '{retrieved_at}' as received_timestamp,
        '{retrieved_at}' as processed_timestamp
      from read_parquet('{source}')
    """)
    connection.execute(f"""
      create table normalized.games as
      select game_id, any_value(season) season, any_value(game_date) game_date,
        any_value(home_team) home_team, any_value(away_team) away_team,
        max(total_home_score) home_score, max(total_away_score) away_score,
        any_value(total) closing_total, any_value(spread_line) closing_spread,
        any_value(stadium) venue, count(*) play_count,
        min(game_seconds_remaining) seconds_remaining_at_end
      from normalized.plays
      group by game_id
    """)
    connection.execute("""
      create table normalized.drives as
      select game_id, fixed_drive as drive_id, any_value(offense) offense,
        any_value(defense) defense, min(quarter) start_quarter, max(quarter) end_quarter,
        min(yardline_100) start_yardline_100, max(yardline_100) end_yardline_100,
        count(*) plays, sum(coalesce(yards_gained, 0)) yards,
        sum(coalesce(first_down, 0)) first_downs, sum(coalesce(penalty, 0)) penalties,
        sum(coalesce(sack, 0)) sacks, sum(coalesce(interception, 0)) interceptions,
        sum(coalesce(fumble_lost, 0)) fumbles_lost, sum(coalesce(touchdown, 0)) touchdowns,
        sum(coalesce(pass_touchdown, 0) + coalesce(rush_touchdown, 0) + coalesce(return_touchdown, 0)) scoring_events,
        max(coalesce(epa, 0)) max_play_epa, sum(coalesce(epa, 0)) epa,
        max(drive_play_count) source_play_count,
        any_value(drive_time_of_possession) source_time_of_possession
      from normalized.plays
      where fixed_drive is not null and offense is not null
      group by game_id, fixed_drive
    """)
    connection.execute("""
      create table features.period as
      select game_id, offense as team, quarter,
        sum(coalesce(total_home_score, 0)) as observed_home_score_last,
        sum(coalesce(total_away_score, 0)) as observed_away_score_last,
        count(*) plays, sum(coalesce(yards_gained, 0)) yards,
        avg(epa) average_epa, avg(case when success then 1.0 else 0.0 end) success_rate,
        sum(coalesce(touchdown, 0)) touchdowns, sum(coalesce(interception, 0)) interceptions,
        sum(coalesce(fumble_lost, 0)) fumbles_lost
      from normalized.plays
      where quarter between 1 and 5 and offense is not null
      group by game_id, offense, quarter
    """)
    connection.execute("""
      create table research.game_state_samples as
      select game_id, play_id, quarter, game_seconds_remaining,
        score_differential, offense as possession, yardline_100, down, ydstogo,
        fixed_drive as completed_drive_id, total_home_score, total_away_score,
        epa, success, yards_gained,
        total_home_score - lag(total_home_score) over (partition by game_id order by play_id) as home_points_delta,
        total_away_score - lag(total_away_score) over (partition by game_id order by play_id) as away_points_delta
      from normalized.plays
      where quarter between 1 and 5 and game_seconds_remaining is not null
    """)
    counts = {table: connection.execute(f"select count(*) from {table}").fetchone()[0] for table in ["normalized.games", "normalized.plays", "normalized.drives", "features.period", "research.game_state_samples"]}
    invalid = connection.execute("select count(*) from normalized.drives where plays <= 0 or offense is null").fetchone()[0]
    connection.execute("drop table if exists metadata.ingestion_manifest")
    connection.execute("create table metadata.ingestion_manifest (schema_version varchar, source_id varchar, source_path varchar, season integer, retrieved_at varchar, sha256 varchar, validation_status varchar, row_counts varchar)")
    connection.execute("insert into metadata.ingestion_manifest values (?, ?, ?, ?, ?, ?, ?, ?)", ["runner.verse-export.v1", "nflverse_pbp", str(input_path), season, retrieved_at, digest, "passed" if invalid == 0 and counts["normalized.plays"] > 0 else "failed", json.dumps(counts, sort_keys=True)])
    connection.close()
    return {"warehouse": str(warehouse), "source": str(input_path), "sha256": digest, "season": season, "row_counts": counts, "validation_status": "passed" if invalid == 0 and counts["normalized.plays"] > 0 else "failed"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/nfl/play_by_play/season=2025/play_by_play_2025.parquet")
    parser.add_argument("--warehouse", default="warehouse/runner_nfl_history.duckdb")
    parser.add_argument("--season", type=int, default=2025)
    args = parser.parse_args()
    result = build(Path(args.input), Path(args.warehouse), args.season)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
