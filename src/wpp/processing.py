import polars as pl
from wpp import data
from wpp.utils import project_root

ROOT = project_root()

if __name__ == "__main__":
    data_path = ROOT / "data" / "2025-weekly-patterns-plus"
    lf = data.load_weekly_patterns_plus_parquet(data_path)
    print(lf.head().collect())

    n_rows = lf.select(pl.len()).collect()[0, 0]
    print(f"Number of rows {n_rows:,}")
    print(
        f"Number of POIs {lf.select(pl.col('ID_STORE').n_unique()).collect()[0, 0]:,}"
    )

    share_with_vhc = (
        lf.filter(pl.col("VISITOR_HOME_CBGS").is_not_null())
        .select(pl.len())
        .collect()[0, 0]
        / n_rows
    )
    print(f"Share with `VISITOR_HOME_CBGS` {share_with_vhc:%}")

    share_with_valid_vhc = (
        lf.filter(pl.col("VISITOR_HOME_CBGS").str.contains(r'":\d'))
        .select(pl.len())
        .collect()[0, 0]
        / n_rows
    )
    print(f"Share with valid `VISITOR_HOME_CBGS` {share_with_valid_vhc:%}")

    share_with_daily_visits_all_days = (
        lf.with_columns(
            pl.col("VISITS_BY_DAY").str.json_decode(pl.List(pl.Int64)).list.to_array(7)
        )
        .filter(pl.col("VISITS_BY_DAY").arr.min() != 0)
        .select(pl.len())
        .collect()[0, 0]
        / n_rows
    )
    print(
        f"Share with no 0 entry in `VISITS_BY_DAY` {share_with_daily_visits_all_days:%}"
    )
