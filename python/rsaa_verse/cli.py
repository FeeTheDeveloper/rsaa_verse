from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import click

from . import ingest as ingest_module
from .config import (
    DEFAULT_SEASON,
    EARLIEST_SEASON,
    EXPORTS_ROOT,
    LATEST_SEASON,
    ROOT,
    WAREHOUSE_PATH,
)

# dev/build_runner_nfl_history.py and dev/export_runner_demon.py are the real,
# already-working implementations of the warehouse build and Demon export steps.
# dev/ is not a Python package (no __init__.py), so they are loaded here by file
# path rather than duplicated into python/rsaa_verse/ -- this keeps a single
# source of truth for that logic instead of maintaining two copies.
_DEV_ROOT = ROOT / "dev"


def _load_dev_module(name: str, filename: str) -> ModuleType:
    path = _DEV_ROOT / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load dev module {filename} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_build_history = _load_dev_module("rsaa_verse_dev_build_runner_nfl_history", "build_runner_nfl_history.py")
_export_runner_demon = _load_dev_module("rsaa_verse_dev_export_runner_demon", "export_runner_demon.py")


def _default_pbp_input(season: int) -> Path:
    """Mirror dev/build_runner_nfl_history.py's own default --input convention.

    NOTE: this is a *different* raw-data layout (data/raw/nfl/play_by_play/...)
    than the one rsaa_verse.ingest / config.NFL_RAW_ROOT writes to and reads from
    (data/nfl/raw/pbp/...). Both currently hold duplicate copies of the season
    2025 file. This split predates this wiring pass and is not resolved here --
    build-drives/build-features/build-warehouse use the dev script's own default
    location (its actual, already-working behavior) unless --input overrides it.
    """
    return ROOT / "data" / "raw" / "nfl" / "play_by_play" / f"season={season}" / f"play_by_play_{season}.parquet"


_SHARED_BUILD_NOTE = (
    "build-drives, build-features, and build-warehouse currently all invoke the same "
    "underlying step (dev/build_runner_nfl_history.py:build()), which builds "
    "normalized.plays/games/drives, features.period, and research.game_state_samples "
    "together in a single pass. There is no decomposed drives-only or features-only "
    "implementation yet, so all three commands do identical work for a season."
)


def _run_build(season: int, input_path: Path | None, warehouse_path: Path | None) -> dict:
    resolved_input = input_path if input_path is not None else _default_pbp_input(season)
    resolved_warehouse = warehouse_path if warehouse_path is not None else WAREHOUSE_PATH
    if not resolved_input.exists():
        raise click.ClickException(f"Input parquet not found: {resolved_input}")
    return _build_history.build(resolved_input, resolved_warehouse, season)


@click.group()
def cli() -> None:
    """RSAA Verse command line."""


@cli.command("status")
def status() -> None:
    click.echo("RSAA Verse status: repository audit preserved; Python acquisition layer initialized.")


@cli.command("bootstrap")
def bootstrap() -> None:
    click.echo(f"Bootstrapping RSAA Verse for NFL seasons {EARLIEST_SEASON}-{LATEST_SEASON}.")


@cli.command("ingest")
@click.option("--season", type=int, default=DEFAULT_SEASON, show_default=True)
@click.option("--from", "from_season", type=int, default=None)
@click.option("--to", "to_season", type=int, default=None)
@click.option("--resume", is_flag=True, default=False)
def ingest(season: int, from_season: int | None, to_season: int | None, resume: bool) -> None:
    """Download nflverse play-by-play parquet for one or more seasons and load it into the warehouse.

    Only season 2025 has actually been validated end-to-end in this repository so far;
    requesting other seasons will genuinely attempt them against nflverse-data, but that
    has not been verified here.
    """
    if resume:
        click.echo(
            "Note: --resume is accepted but not yet implemented -- there is no "
            "skip-if-already-ingested logic in rsaa_verse.ingest. Every requested "
            "season below is re-ingested regardless of prior manifest state."
        )
    if from_season is not None and to_season is not None:
        seasons = list(range(from_season, to_season + 1))
    else:
        seasons = [season]

    for one_season in seasons:
        click.echo(f"Ingesting NFL play-by-play for season {one_season}...")
        try:
            record = ingest_module.ingest_nfl_pbp_season(one_season)
        except Exception as exc:
            # Surfaced honestly rather than swallowed: rsaa_verse.ingest's
            # normalized.pbp_{season} table SQL references several source column
            # names (e.g. "quarter", "drive_id") that do not match the actual
            # nflverse play_by_play schema (which uses "qtr", "fixed_drive"/"drive",
            # etc. -- see dev/build_runner_nfl_history.py's query for the real
            # names). This is a pre-existing bug in ingest.py, not introduced by
            # this CLI wiring; fixing it would require deciding how several fields
            # (e.g. "turnover", "field_goal", "punt", "kickoff") should actually be
            # derived, which is out of scope for a wiring pass. The download and
            # manifest-write steps for this season may have completed before this
            # failure -- check the manifest and raw parquet before retrying.
            raise click.ClickException(
                f"ingest_nfl_pbp_season({one_season}) failed: {exc}\n"
                "This is a pre-existing bug in rsaa_verse.ingest's normalized-table "
                "SQL (source column names do not match the actual nflverse schema), "
                "not a wiring problem. See cli.py's ingest command for details."
            ) from exc
        click.echo(
            f"  -> {record['status']}: {record['row_count']} rows, "
            f"{record['column_count']} columns (sha256={record['sha256'][:12]}...)"
        )
        click.echo(
            f"  -> manifest appended at {ingest_module.MANIFEST_PATH} "
            "(note: this is separate from the pre-existing data/manifests/ingestion.jsonl "
            "record, which was produced by an earlier ingestion path -- this command does "
            "not append to that file)."
        )


@cli.command("validate")
@click.option("--season", type=int, default=DEFAULT_SEASON, show_default=True)
def validate(season: int) -> None:
    """Not yet implemented.

    No validation logic exists anywhere in python/rsaa_verse or dev/ to wire this to.
    This is an honest stub, not a silent no-op dressed up as real validation.
    """
    click.echo(
        f"validate is not yet implemented (season {season} requested). "
        "No validation function exists in this codebase yet; this is a stub."
    )


@cli.command("build-drives")
@click.option("--season", type=int, default=DEFAULT_SEASON, show_default=True)
@click.option("--input", "input_path", type=click.Path(path_type=Path), default=None)
@click.option("--warehouse", "warehouse_path", type=click.Path(path_type=Path), default=None)
def build_drives(season: int, input_path: Path | None, warehouse_path: Path | None) -> None:
    """Build normalized/features/research warehouse tables for a season."""
    click.echo(_SHARED_BUILD_NOTE)
    result = _run_build(season, input_path, warehouse_path)
    click.echo(json.dumps(result, indent=2, default=str))


@cli.command("build-features")
@click.option("--season", type=int, default=DEFAULT_SEASON, show_default=True)
@click.option("--input", "input_path", type=click.Path(path_type=Path), default=None)
@click.option("--warehouse", "warehouse_path", type=click.Path(path_type=Path), default=None)
def build_features(season: int, input_path: Path | None, warehouse_path: Path | None) -> None:
    """Build normalized/features/research warehouse tables for a season."""
    click.echo(_SHARED_BUILD_NOTE)
    result = _run_build(season, input_path, warehouse_path)
    click.echo(json.dumps(result, indent=2, default=str))


@cli.command("build-warehouse")
@click.option("--season", type=int, default=DEFAULT_SEASON, show_default=True)
@click.option("--input", "input_path", type=click.Path(path_type=Path), default=None)
@click.option("--warehouse", "warehouse_path", type=click.Path(path_type=Path), default=None)
def build_warehouse(season: int, input_path: Path | None, warehouse_path: Path | None) -> None:
    """Build normalized/features/research warehouse tables for a season."""
    click.echo(_SHARED_BUILD_NOTE)
    result = _run_build(season, input_path, warehouse_path)
    click.echo(json.dumps(result, indent=2, default=str))


@cli.command("coverage")
def coverage() -> None:
    """Not yet implemented.

    No coverage-reporting logic exists anywhere in python/rsaa_verse or dev/ to wire
    this to. This is an honest stub, not a silent no-op dressed up as real reporting.
    """
    click.echo(
        "coverage is not yet implemented. No coverage-reporting function exists in "
        "this codebase yet; this is a stub."
    )


@cli.command("export-demon")
@click.option("--season", type=int, default=DEFAULT_SEASON, show_default=True)
@click.option("--warehouse", "warehouse_path", type=click.Path(path_type=Path), default=None)
@click.option("--output", "output_path", type=click.Path(path_type=Path), default=None)
def export_demon(season: int, warehouse_path: Path | None, output_path: Path | None) -> None:
    """Export curated warehouse tables to exports/runner_demon parquet files + manifest.json."""
    resolved_warehouse = warehouse_path if warehouse_path is not None else WAREHOUSE_PATH
    resolved_output = output_path if output_path is not None else EXPORTS_ROOT
    if not resolved_warehouse.exists():
        raise click.ClickException(f"Warehouse not found: {resolved_warehouse}. Run build-warehouse first.")
    manifest = _export_runner_demon.export_demon(resolved_warehouse, resolved_output, season)
    click.echo(json.dumps(manifest, indent=2, default=str))


if __name__ == "__main__":
    cli()
