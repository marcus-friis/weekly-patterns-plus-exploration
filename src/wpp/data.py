from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import polars as pl
from duckdb import DuckDBPyConnection


@dataclass(frozen=True)
class ClimateEvent:
    label: str
    start: datetime
    end: datetime | None = None  # None = single-day / point event

    @property
    def is_range(self) -> bool:
        return self.end is not None and self.end != self.start

    @property
    def last_day(self) -> datetime:
        return self.end or self.start


def get_climate_events() -> list[ClimateEvent]:
    events = [
        ClimateEvent(
            label="Southern California wildfires",
            start=datetime.fromisoformat("2025-01-07"),
            end=datetime.fromisoformat("2025-01-31"),
        ),
        ClimateEvent(
            label="Central Texas floods",
            start=datetime.fromisoformat("2025-07-04"),
            end=datetime.fromisoformat("2025-07-05"),
        ),
        ClimateEvent(
            label="Tampa, Florida heat record",
            start=datetime.fromisoformat("2025-07-27"),
        ),
    ]
    return sorted(events, key=lambda e: e.start)


def load_weekly_patterns_plus_parquet(dir_path: Path | str) -> pl.LazyFrame:
    """Lazily load Weekly Patterns Plus parquet shards into a single LazyFrame."""
    dir_path = Path(dir_path)

    lf = pl.scan_parquet(dir_path / "*.parquet")
    return lf


def get_top_cbsa_block_groups(
    con: DuckDBPyConnection,
    top_k: int = 50,
    *,
    num_income_groups: int = 10,
) -> pl.LazyFrame:
    lf = (
        con.sql(f"""
            SELECT GEOID, CBSAFP, CBSA_NAME, CBSA_POP_RANK, MEDIAN_HH_INCOME
            FROM block_groups_cbsa
            WHERE LSAD = 'M1'
              AND CBSA_POP_RANK <= {top_k}
        """)
        .pl(lazy=True)
        .with_columns(
            pl.col("MEDIAN_HH_INCOME").is_not_null().alias("HAS_INCOME"),
            (pl.col("CBSA_POP_RANK") <= 5).alias("TOP_5"),
            pl.col("MEDIAN_HH_INCOME")
            .qcut(
                num_income_groups,
                labels=[str(i) for i in range(1, num_income_groups + 1)],
                allow_duplicates=True,
            )
            .cast(pl.Utf8)
            .over("CBSAFP")
            .alias("INCOME_DECILE"),
        )
        .with_columns(
            pl.when(pl.col("TOP_5"))
            .then(pl.col("CBSA_NAME"))
            .otherwise(pl.lit("Other"))
            .alias("CBSA_TITLE_TOP")
        )
    )
    return lf
