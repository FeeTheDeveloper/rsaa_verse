# RSAA Verse — Runner Sports & Analytics Historical Sports Data Acquisition Layer

RSAA Verse is the historical research and data-engineering layer for Runner Sports & Analytics (RSAA), with an initial focus on the NFL. It sits alongside the live execution intelligence system managed by Runner Demon, while preserving useful historical data acquisition foundations inherited from the original nflverse/PFR workflow.

## Original upstream foundation

This repository originally served as a PFR/nflverse scraper for:

- Pro Football Reference game URL discovery
- PFR advanced season stats
- game-level advanced stat scrapes
- snap-count extraction
- college/combine draft data helpers
- automated GitHub release publishing patterns for historical data

The upstream codebase was built in service of the nflverse ecosystem and remains a valuable historical source and operational reference. RSAA Verse keeps the useful acquisition logic and modernizes it into a source-aware, resumable, warehouse-oriented architecture.

## RSAA modifications

The repository is now being evolved into a research-grade historical sports data system with the following responsibilities:

- source acquisition from structured upstream sources first
- raw archival storage in Parquet partitions
- normalization and validation layers
- feature and research dataset generation
- historical warehouse management in DuckDB
- stable export contracts for Runner Demon consumption

The core design principle is: use current authoritative upstream data when available, and only use PFR scraping as gap-fill/enrichment when no structured dataset already covers the required historical record.

## Data sources

Source hierarchy used by RSAA Verse:

1. NFLverse structured data first
   - nflverse-data release files
   - nflreadr for R-native access patterns
   - nflreadpy / Python-friendly workflows for data engineering
   - Parquet URL access for historical datasets

2. Existing PFR scrapers retained and modernized
   - game URL discovery
   - snap counts
   - advanced stats
   - provider-specific gap fill only where appropriate

3. Other authorized sources when upstream or PFR access is blocked
   - source attribution and failure logging are preserved
   - no intentional rate-limit bypass or abuse path is introduced

## Acquisition philosophy

- Prefer authoritative structured data over scraping HTML when the data exists upstream.
- Respect provider rate limits and robots policies.
- Maintain manifests for every acquisition attempt.
- Use resumable, partitioned storage so a failed season does not require restarting the full archive.
- Preserve raw upstream data and source attribution; do not silently rewrite or discard original identifiers.
- Keep current season refresh logic separate from immutable historical snapshots.

## Warehouse architecture

The repository now targets a DuckDB-based warehouse with schema groups such as:

- raw.*
- normalized.*
- features.*
- research.*
- metadata.*

Large raw and normalized tables are stored as Parquet files in the local data tree. Historical analytical work occurs in DuckDB, while Runner Demon consumes export parquet files rather than directly depending on raw acquisition internals.

## Runner Demon

Runner Demon remains responsible for live analytics and execution intelligence. RSAA Verse is the historical data engine that supplies stable, versioned exports for modeling and research. The export contract is intentionally decoupled from raw ingestion internals.

## Licensing

This repository continues to include inherited code and workflows from the nflverse/PFR ecosystem. The original licensing and attribution remain in place as required. RSAA Verse's added intellectual property consists of the normalization logic, mappings, derived features, research processes, warehouse architecture, and export contracts created for the Runner Sports & Analytics layer.

## Repository layout

- R/: legacy and maintained PFR/nflverse tooling
- python/rsaa_verse/: new acquisition, normalization, validation, and warehouse code
- data/nfl/: raw, normalized, and manifest storage for NFL data
- warehouse/: DuckDB analytical warehouse
- exports/runner_demon/: stable Runner Demon export artifacts
- reports/: coverage and validation reports
- tests/: validation for acquisition, warehouse, and feature logic

## Example commands

```bash
rsaa-verse nfl status
rsaa-verse nfl bootstrap
rsaa-verse nfl ingest pbp --season 2025
rsaa-verse nfl ingest schedules
rsaa-verse nfl ingest all --season 2025
rsaa-verse nfl validate --season 2025
rsaa-verse nfl build-drives --season 2025
rsaa-verse nfl build-features --season 2025
rsaa-verse nfl build-warehouse
rsaa-verse nfl coverage
rsaa-verse nfl export-demon
```

The actual CLI syntax may vary slightly in implementation, but the equivalent functions remain the goal.
