from pathlib import Path

import polars as pl


def load_weekly_patterns_plus_parquet(dir_path: Path | str) -> pl.LazyFrame:
    """Lazily load Weekly Patterns Plus parquet shards into a single LazyFrame."""
    dir_path = Path(dir_path)

    lf = pl.scan_parquet(dir_path / "*.parquet")
    return lf
