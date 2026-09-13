from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data"
NFL_RAW_ROOT = DATA_ROOT / "nfl" / "raw"
NFL_NORMALIZED_ROOT = DATA_ROOT / "nfl" / "normalized"
WAREHOUSE_PATH = ROOT / "warehouse" / "runner_nfl_history.duckdb"
EXPORTS_ROOT = ROOT / "exports" / "runner_demon"
REPORTS_ROOT = ROOT / "reports"
MANIFEST_PATH = ROOT / "data" / "nfl" / "manifests" / "ingestion_manifest.parquet"
DEFAULT_SEASON = 2025
EARLIEST_SEASON = 1999
LATEST_SEASON = 2026

SEASON_RANGE = list(range(EARLIEST_SEASON, LATEST_SEASON + 1))
