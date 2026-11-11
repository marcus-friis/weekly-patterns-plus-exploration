import numpy as np
import polars as pl
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

from wpp import cache, data, db, plotting
from wpp.utils import project_root

ROOT = project_root()
DB_PATH = ROOT / "wpp.duckdb"


def compute_poi_temperature_correlations(
    pois_weekly: pl.DataFrame,
    *,
    min_observations: int = 10,
) -> pl.DataFrame:
    rows = []

    data = (
        pois_weekly.select(
            "CATEGORY",
            "ID_STORE",
            "AVG_TMAX",
            "SEGREGATION",
        )
        .drop_nulls()
        .filter(
            pl.col("AVG_TMAX").is_finite(),
            pl.col("SEGREGATION").is_finite(),
        )
        .sort("CATEGORY", "ID_STORE")
    )

    for (category, id_store), group in data.group_by(
        "CATEGORY",
        "ID_STORE",
        maintain_order=True,
    ):
        n = group.height

        if n < min_observations:
            continue

        temperature = group["AVG_TMAX"].to_numpy()
        segregation = group["SEGREGATION"].to_numpy()

        # Spearman correlation is undefined for constant series.
        if np.unique(temperature).size < 2 or np.unique(segregation).size < 2:
            continue

        result = spearmanr(
            temperature,
            segregation,
            nan_policy="omit",
        )

        if not np.isfinite(result.statistic):
            continue

        rows.append(
            {
                "CATEGORY": category,
                "ID_STORE": id_store,
                "N": n,
                "RHO": float(result.statistic),  # pyright: ignore[reportAttributeAccessIssue]
                "PVALUE": float(result.pvalue),  # pyright: ignore[reportAttributeAccessIssue]
            }
        )

    correlations = pl.DataFrame(
        rows,
        schema={
            "CATEGORY": pl.String,
            "ID_STORE": pl.String,
            "N": pl.Int64,
            "RHO": pl.Float64,
            "PVALUE": pl.Float64,
        },
    )

    if correlations.is_empty():
        return correlations.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("QVALUE"),
            pl.lit(False).alias("SIGNIFICANT"),
        )

    # Control the false-discovery rate across all tested POIs.
    _, qvalues, _, _ = multipletests(
        correlations["PVALUE"].to_numpy(),
        alpha=0.05,
        method="fdr_bh",
    )

    return correlations.with_columns(
        pl.Series("QVALUE", qvalues),
    ).with_columns(
        (pl.col("QVALUE") < 0.05).alias("SIGNIFICANT"),
    )


def print_segregation_summary(
    pois: pl.DataFrame, categories: pl.DataFrame, categories_weekly: pl.DataFrame
):
    print("Individual pois")
    res = spearmanr(
        pois["TOTAL_VISITORS"].to_numpy(),
        pois["SEGREGATION"].to_numpy(),
    )
    print("TOTAL_VISITORS ~ SEGREGATION", res.statistic, res.pvalue)  # pyright: ignore[reportAttributeAccessIssue]
    res = spearmanr(pois["AVG_DIST"].to_numpy(), pois["SEGREGATION"].to_numpy())
    print("AVG_DIST ~ SEGREGATION", res.statistic, res.pvalue)  # pyright: ignore[reportAttributeAccessIssue]
    print()

    print("Aggregated categories")
    res = spearmanr(
        categories["TOTAL_VISITORS"].to_numpy(), categories["SEGREGATION"].to_numpy()
    )
    print("TOTAL_VISITORS ~ SEGREGATION", res.statistic, res.pvalue)  # pyright: ignore[reportAttributeAccessIssue]
    res = spearmanr(
        categories["AVG_DIST"].to_numpy(), categories["SEGREGATION"].to_numpy()
    )
    print("AVG_DIST ~ SEGREGATION", res.statistic, res.pvalue)  # pyright: ignore[reportAttributeAccessIssue]

    rows = []
    for cat in categories_weekly["CATEGORY"].unique():
        X = categories_weekly.filter(pl.col("CATEGORY") == cat)
        corr = spearmanr(X["AVG_TMAX"], X["SEGREGATION"])
        rows.append(
            {
                "CATEGORY": cat,
                "statistic": corr.statistic,  # pyright: ignore[reportAttributeAccessIssue]
                "pvalue": corr.pvalue,  # pyright: ignore[reportAttributeAccessIssue]
            }
        )
    corrs = pl.DataFrame(rows)
    print()
    print("Categories ~ heat weekly")
    print(corrs)


def agg_categories(df: pl.DataFrame, by: str | list[str]) -> pl.DataFrame:
    aggs = [
        pl.len().alias("NUM_POIS"),
        pl.col("SEGREGATION").mean(),
        (
            (pl.col("SEGREGATION") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("W_SEGREGATION"),
        pl.col("TOTAL_VISITORS").sum(),
        pl.col("TOTAL_VISITORS").mean().alias("AVG_VISITORS"),
        (
            (pl.col("AVG_DIST") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("AVG_DIST"),
    ]

    if "AVG_TMAX" in df.columns:
        aggs.append(pl.col("AVG_TMAX").mean())

    return df.group_by(by).agg(aggs)


if __name__ == "__main__":
    # load and prepare data
    con = db.connect(DB_PATH, read_only=True)

    pois_dim = cache.cached_parquet(
        "pois",
        lambda: data.load_pois(con),
    )
    poi_visits = cache.cached_parquet(
        "static_poi_segregation",
        lambda: data.load_static_poi_segregation(con),
    ).with_columns(pl.col("TOTAL_VISITORS").cast(pl.Float64))
    pois = pois_dim.join(poi_visits, on="ID_STORE")
    categories = agg_categories(pois, ["CATEGORY", "NAICS_TITLE"])

    poi_visits_weekly = cache.cached_parquet(
        "weekly_poi_segregation",
        lambda: data.load_weekly_poi_segregation(con),
    )
    pois_weekly = pois_dim.join(poi_visits_weekly, on="ID_STORE")
    categories_weekly = agg_categories(pois_weekly, ["CATEGORY", "DATE_RANGE_START"])

    poi_correlations = compute_poi_temperature_correlations(
        pois_weekly,
        min_observations=10,
    )

    print_segregation_summary(pois, categories, categories_weekly)

    print(
        poi_correlations.group_by("CATEGORY")
        .agg(
            pl.len().alias("NUM_POIS"),
            pl.col("N").median().alias("MEDIAN_WEEKS"),
            pl.col("RHO").median().alias("MEDIAN_RHO"),
            pl.col("RHO").mean().alias("MEAN_RHO"),
            pl.col("SIGNIFICANT").mean().alias("SHARE_FDR_SIGNIFICANT"),
        )
        .sort("MEDIAN_RHO")
    )

    fig = plotting.plot_poi_temperature_correlations(poi_correlations)
    figure_path = "poi_temperature_correlations.png"
    fig.savefig(
        figure_path,
        dpi=300,
        bbox_inches="tight",
    )

    con.close()
