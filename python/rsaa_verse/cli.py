from __future__ import annotations

import click

from .config import DEFAULT_SEASON, EARLIEST_SEASON, LATEST_SEASON


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
@click.option("--season", type=int, default=DEFAULT_SEASON)
@click.option("--from", "from_season", type=int, default=None)
@click.option("--to", "to_season", type=int, default=None)
@click.option("--resume", is_flag=True, default=False)
def ingest(season: int, from_season: int | None, to_season: int | None, resume: bool) -> None:
    if from_season is not None and to_season is not None:
        click.echo(f"Ingest requested for seasons {from_season}-{to_season}; resume={resume}")
    else:
        click.echo(f"Ingest requested for season {season}; resume={resume}")


@cli.command("validate")
@click.option("--season", type=int, default=DEFAULT_SEASON)
def validate(season: int) -> None:
    click.echo(f"Validation requested for season {season}.")


@cli.command("build-drives")
@click.option("--season", type=int, default=DEFAULT_SEASON)
def build_drives(season: int) -> None:
    click.echo(f"Drive build requested for season {season}.")


@cli.command("build-features")
@click.option("--season", type=int, default=DEFAULT_SEASON)
def build_features(season: int) -> None:
    click.echo(f"Feature build requested for season {season}.")


@cli.command("build-warehouse")
def build_warehouse() -> None:
    click.echo("Warehouse build requested.")


@cli.command("coverage")
def coverage() -> None:
    click.echo("Coverage requested.")


@cli.command("export-demon")
def export_demon() -> None:
    click.echo("Demon export requested.")


if __name__ == "__main__":
    cli()
