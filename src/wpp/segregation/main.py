from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

import matplotlib.pyplot as plt
import polars as pl
import seaborn as sns
from matplotlib.lines import Line2D

from wpp import db
from wpp.segregation import data
from wpp.utils import project_root

ROOT = project_root()
DATA_PATH = ROOT / "data"
DB_PATH = ROOT / "wpp.duckdb"
N_INCOME_GROUPS = 4

sns.set_theme(style="ticks")


def entropy_segregation(n_groups: int) -> pl.Expr:
    return (
        1 - pl.col("TAU").entropy(normalize=False) / pl.lit(float(n_groups)).log()
    ).alias("INCOME_SEGREGATION")


def l1_segregation(n_groups: int) -> pl.Expr:
    expected_share = 1 / n_groups
    normalization = n_groups / (2 * (n_groups - 1))

    return (normalization * (pl.col("TAU") - expected_share).abs().sum()).alias(
        "INCOME_SEGREGATION"
    )


def compute_segregation_by(
    df: pl.DataFrame,
    by: list[str],
    segregation_expr: pl.Expr,
) -> pl.DataFrame:
    expected_cols = {
        *by,
        "HOME_INCOME_GROUP",
        "VISITOR_COUNTS",
        "DIST",
    }

    missing = expected_cols - set(df.columns)
    assert not missing, f"Missing columns: {missing}"

    visitor_distribution = (
        df.filter(
            pl.col("HOME_INCOME_GROUP").is_not_null()
            & pl.col("VISITOR_COUNTS").is_not_null()
            & (pl.col("VISITOR_COUNTS") > 0)
        )
        .group_by([*by, "HOME_INCOME_GROUP"])
        .agg(pl.col("VISITOR_COUNTS").sum().alias("QUARTILE_VISITORS"))
        .with_columns(
            pl.col("QUARTILE_VISITORS").sum().over(by).alias("TOTAL_VISITORS")
        )
        .with_columns(
            (pl.col("QUARTILE_VISITORS") / pl.col("TOTAL_VISITORS")).alias("TAU")
        )
    )

    segregation = (
        visitor_distribution.group_by(by)
        .agg(
            pl.col("TOTAL_VISITORS").first(),
            segregation_expr,
        )
        .join(
            df.group_by(by).agg(
                (
                    (pl.col("DIST") * pl.col("VISITOR_COUNTS")).sum()
                    / pl.col("VISITOR_COUNTS").sum()
                ).alias("DIST")
            ),
            on=by,
            how="left",
        )
    )

    return segregation


if __name__ == "__main__":
    con = db.connect(DB_PATH)
    pois = data.get_pois(con)
    heat = data.get_heat_daily(con, cbsafp="36740")
    df = data.get_df(con, cbsafp="36740", n_income_groups=N_INCOME_GROUPS)

    # preprocess
    # remove with too few visitors?
    # remove with not all dates?

    poi_daily_segregation = compute_segregation_by(
        df, ["ID_STORE", "DATE_RANGE_START"], entropy_segregation(N_INCOME_GROUPS)
    )
    daily_segregation = (
        poi_daily_segregation.group_by("DATE_RANGE_START")
        .agg(
            pl.col("TOTAL_VISITORS").mean().alias("AVG_VISITORS"),
            pl.col("INCOME_SEGREGATION").mean().alias("AVG_INCOME_SEGREGATION"),
            (
                (pl.col("INCOME_SEGREGATION") * pl.col("TOTAL_VISITORS")).sum()
                / pl.col("TOTAL_VISITORS").sum()
            ).alias("W_AVG_INCOME_SEGREGATION"),
            pl.col("DIST").mean().alias("AVG_DIST"),
            (
                (pl.col("DIST") * pl.col("TOTAL_VISITORS")).sum()
                / pl.col("TOTAL_VISITORS").sum()
            ).alias("W_AVG_DIST"),
        )
        .sort("DATE_RANGE_START")
    )

    fig, axes = plt.subplots(2, sharex=True)
    axes[0].plot(
        daily_segregation["DATE_RANGE_START"],
        daily_segregation["AVG_INCOME_SEGREGATION"],
    )
    axes[1].plot(
        heat["DATE"],
        heat["AVG_TMEAN"],
    )
    fig.savefig("lel.png")
    plt.show()

    fig, ax = plt.subplots()
    x = daily_segregation.with_columns(
        pl.col("DATE_RANGE_START").dt.date().alias("DATE")
    ).join(heat, on="DATE")
    ax.scatter(x["AVG_TMEAN"], x["AVG_INCOME_SEGREGATION"])
    fig.savefig("leeeel.png")
    plt.show()
