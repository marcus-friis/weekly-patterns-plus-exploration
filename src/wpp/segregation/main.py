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
    # heat = data.get_heat_daily(con, cbsafp="36740")
    # df = data.get_df(con, cbsafp="36740", n_income_groups=N_INCOME_GROUPS)

    # preprocess
    # remove with too few visitors?
    # remove with not all dates?

    daily_segregation = data.get_daily_segregation(
        con,
        n_income_groups=N_INCOME_GROUPS,
        segregation_expression="l1",
    )
    fig, ax = plt.subplots(figsize=(14, 8))

    for (cbsa_name,), group in daily_segregation.group_by(
        "CBSA_NAME",
        maintain_order=True,
    ):
        group = group.sort("DATE_RANGE_START")

        ax.plot(
            group["DATE_RANGE_START"],
            group["AVG_INCOME_SEGREGATION"],
            label=cbsa_name,
            alpha=0.7,
            linewidth=1,
        )

    ax.set(
        xlabel="Date",
        ylabel="Average income segregation",
    )

    sns.despine()
    fig.tight_layout()
    fig.savefig("daily_segregation_by_cbsa.png", dpi=300)
    plt.show()

    largest_cbsas = (
        daily_segregation.group_by("CBSA_NAME")
        .agg(pl.col("AVG_VISITORS").mean().alias("AVG_VISITORS"))
        .top_k(25, by="AVG_VISITORS")
        .get_column("CBSA_NAME")
    )

    plot_data = daily_segregation.filter(pl.col("CBSA_NAME").is_in(largest_cbsas))

    fig, ax = plt.subplots(figsize=(14, 8))

    for (cbsa_name,), group in plot_data.group_by(
        "CBSA_NAME",
        maintain_order=True,
    ):
        group = group.sort("DATE_RANGE_START")

        ax.plot(
            group["DATE_RANGE_START"],
            group["AVG_INCOME_SEGREGATION"],
            label=cbsa_name,
            alpha=0.8,
            linewidth=1.2,
        )

    ax.set(
        xlabel="Date",
        ylabel="Average income segregation",
    )

    ax.legend(
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        frameon=False,
        fontsize=8,
    )

    sns.despine()
    fig.tight_layout()
    fig.savefig("daily_segregation_top_25_cbsas.png", dpi=300)
    plt.show()
