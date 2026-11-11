from itertools import product
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import pyfixest as pf
import seaborn as sns
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

from wpp import cache, correlations, data, db, plotting
from wpp.config import PALETTE
from wpp.utils import project_root

ROOT = project_root()
FIGURE_PATH = ROOT / "lolfigures2"
DB_PATH = ROOT / "wpp.duckdb"

sns.set_theme(style="ticks")
pl.Config.set_engine_affinity("streaming")


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

    # segregation
    msas = pois.group_by("CBSA_NAME").agg(
        pl.col("SEGREGATION").mean().alias("AVG_SEGREGATION"),
        (
            (pl.col("SEGREGATION") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("W_AVG_SEGREGATION"),
    )
    print("Segregation by MSA")
    print(msas.sort("CBSA_NAME"))

    correlations.print_segregation_summary(pois, categories, categories_weekly)

    # plots
    plotting.plot_all(
        pois,
        categories,
        pois_weekly,
        categories_weekly,
        base_path=FIGURE_PATH,
    )

    # modeling
    OUTCOME = "SEGREGATION"

    naive_model = pf.feols(
        f"{OUTCOME} ~ AVG_TMAX",
        data=pois_weekly.select("SEGREGATION", "AVG_TMAX"),
    )
    naive_model.summary()

    model = pf.feols(
        f"{OUTCOME} ~ AVG_TMAX | ID_STORE + DATE_RANGE_START",
        data=pois_weekly.select(
            "ID_STORE", "DATE_RANGE_START", "SEGREGATION", "AVG_TMAX", "CELL_ID"
        ),
        vcov={"CRV1": "ID_STORE + CELL_ID"},
    )
    model.summary()

    model_poly = pf.feols(
        f"{OUTCOME} ~ AVG_TMAX + I(AVG_TMAX**2) | ID_STORE + DATE_RANGE_START",
        data=pois_weekly.select(
            "ID_STORE", "DATE_RANGE_START", "SEGREGATION", "AVG_TMAX", "CELL_ID"
        ),
        vcov={"CRV1": "ID_STORE + CELL_ID"},
    )
    model_poly.summary()

    bins = [-float("inf"), 0, 5, 10, 15, 20, 25, 30, 35, float("inf")]
    labels = ["<0", "0-5", "5-10", "10-15", "15-20", "20-25", "25-30", "30-35", "35+"]

    pois_weekly = pois_weekly.with_columns(
        pl.col("AVG_TMAX").bin_intervals(bins[1:-1], labels=labels).alias("TMAX_BIN")
    )
    model_bins = pf.feols(
        f"{OUTCOME} ~ C(TMAX_BIN, contr.treatment(base='15-20')) | ID_STORE + DATE_RANGE_START",
        data=pois_weekly.select(
            "ID_STORE", "DATE_RANGE_START", "SEGREGATION", "TMAX_BIN", "CELL_ID"
        ),
        vcov={"CRV1": "ID_STORE + CELL_ID"},
    )
    model_bins.summary()

    # MSA x CATEGORY
    cats = sorted(pois_weekly["CATEGORY"].unique().to_list())
    msas = sorted(pois_weekly["CBSA_NAME"].unique().to_list())

    results: dict[tuple[str, str], tuple[Any, int]] = {}
    combinations = product(cats + ["All"], msas + ["All"])
    for pool in combinations:
        cat, msa = pool
        msa_expr = pl.col("CBSA_NAME") == msa if msa != "All" else pl.lit(True)
        cat_expr = pl.col("CATEGORY") == cat if cat != "All" else pl.lit(True)
        df = pois_weekly.filter(msa_expr, cat_expr).select(
            "ID_STORE", "DATE_RANGE_START", "SEGREGATION", "TMAX_BIN", "CELL_ID"
        )
        if df.height < 100:
            continue

        model_p = pf.feols(
            f"{OUTCOME} ~ C(TMAX_BIN, contr.treatment(base='15-20')) | ID_STORE + DATE_RANGE_START",
            data=df,
            vcov={"CRV1": "ID_STORE + CELL_ID"},
        )
        results[pool] = (model_p, df.height)

    def plot_model(m, ax, cat, title=None):
        t = m.tidy()
        t.index = t.index.str.extract(r"\[T\.(.+)\]", expand=False)
        t.loc["15-20"] = 0  # reference bin
        t = t.reindex(labels)  # correct order, gaps if bin is empty
        color = PALETTE.get(cat, "#4C78A8")
        ax.axhline(0, color="grey", ls="--", lw=0.8)
        ax.errorbar(
            labels,
            t["Estimate"],
            yerr=[t["Estimate"] - t["2.5%"], t["97.5%"] - t["Estimate"]],
            fmt="o-",
            ms=3,
            capsize=2,
            color=color,
        )
        ax.set_title(title, fontsize=8)
        ax.tick_params(axis="x", rotation=45, labelsize=7)

    # Individual plots
    subfigure_path = FIGURE_PATH / "asdf"
    subfigure_path.mkdir(parents=True, exist_ok=True)
    for (cat, msa), (m, h) in results.items():
        fig, ax = plt.subplots(figsize=(5, 3.5))
        plot_model(m, ax, cat, f"{cat} | {msa} | n = ${h:,}$")
        fig.tight_layout()
        figure_path = subfigure_path / f"bins_{cat}_{msa}.png"
        fig.savefig(figure_path, dpi=200)
        plt.close(fig)

    # Grid: rows = category (+All), cols = CBSA (+All)
    rows, cols = cats + ["All"], msas + ["All"]
    fig, axes = plt.subplots(
        len(rows),
        len(cols),
        sharex=True,
        sharey=True,
        figsize=(2.5 * len(cols), 2.2 * len(rows)),
        squeeze=False,
    )
    for i, cat in enumerate(rows):
        for j, msa in enumerate(cols):
            ax = axes[i, j]
            if (cat, msa) in results:
                r = results[(cat, msa)]
                m, h = r
                plot_model(m, ax, cat, f"n = ${h:,}$")
            else:
                ax.set_axis_off()
            ax.set_ylim(-0.1, 0.1)
            ax.grid()
            sns.despine(ax=ax)

            if i == len(rows) - 1:
                ax.set_xlabel(msa)
            if j == 0:
                ax.set_ylabel(cat)
    fig.tight_layout()
    figure_path = FIGURE_PATH / "grid.pdf"
    fig.savefig(figure_path, format="pdf")
