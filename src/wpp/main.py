import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns
from adjustText import adjust_text
from matplotlib.lines import Line2D

from wpp import cache, data, db
from wpp.utils import project_root

ROOT = project_root()
DATA_PATH = ROOT / "data"
DB_PATH = ROOT / "wpp.duckdb"

sns.set_theme(style="ticks")
pl.Config.set_engine_affinity("streaming")

LABEL_CATEGORIES = {
    "Restaurants",
    "Grocery_Stores",
    "Public_Transportation",
    "Museums_Historical",
}

PALETTE = {
    "Other": "#D9D9D9",
    "Restaurants": "#D55E00",
    "Cafes_Coffee": "#E69F00",
    "Bars": "#8C2D62",
    "Grocery_Stores": "#009E73",
    "Specialty_Food": "#66C2A5",
    "Libraries": "#0072B2",
    "Museums_Historical": "#56B4E9",
    "Parks_Forests": "#228833",
    "Schools": "#AA4499",
    "Public_Transportation": "#C99400",
    "Retail": "#5F5F5F",
}


def plot_categories(categories: pl.DataFrame) -> plt.Figure:
    categories = categories.with_columns(
        pl.col("CATEGORY").replace_strict(PALETTE, default="#4C78A8").alias("COLOR"),
        pl.col("CATEGORY").str.replace_all("_", " ").alias("CATEGORY_LABEL"),
    )

    other = categories.filter(pl.col("CATEGORY") == "Other")
    main = categories.filter(pl.col("CATEGORY") != "Other")

    labels = main.filter(pl.col("CATEGORY").is_in(LABEL_CATEGORIES))

    category_legend = (
        main.select("CATEGORY", "CATEGORY_LABEL", "COLOR").unique().sort("CATEGORY")
    )

    # Convert only at the plotting boundary.
    other_pdf = other.to_pandas()
    main_pdf = main.to_pandas()

    plots = [
        ("TOTAL_VISITORS", "Visitors vs Segregation"),
        ("AVG_DIST", "Distance vs Segregation"),
    ]

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(16, 8),
        dpi=400,
        sharey=True,
        constrained_layout=True,
    )

    for ax, (x, title) in zip(axes, plots):
        if not other.is_empty():
            sns.scatterplot(
                data=other_pdf,
                x=x,
                y="SEGREGATION",
                size="NUM_POIS",
                sizes=(30, 350),
                color=PALETTE["Other"],
                alpha=0.20,
                linewidth=0,
                legend=False,
                zorder=1,
                ax=ax,
            )

        sns.scatterplot(
            data=main_pdf,
            x=x,
            y="SEGREGATION",
            hue="CATEGORY",
            size="NUM_POIS",
            sizes=(30, 350),
            palette=PALETTE,
            alpha=0.95,
            edgecolor="white",
            linewidth=1,
            legend=False,
            zorder=5,
            ax=ax,
        )

        texts = [
            ax.text(
                row[x],
                row["SEGREGATION"],
                row["NAICS_TITLE"],
                fontsize=7,
                zorder=20,
            )
            for row in labels.select(
                x,
                "SEGREGATION",
                "NAICS_TITLE",
            ).iter_rows(named=True)
        ]

        adjust_text(
            texts,
            ax=ax,
            arrowprops={
                "arrowstyle": "-",
                "color": "0.3",
                "lw": 0.5,
                "alpha": 0.6,
            },
            expand=(1.15, 1.15),
        )

        ax.set(
            title=title,
            xscale="log",
            ylabel="Segregation",
        )
        ax.grid(alpha=0.15)

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor=row["COLOR"],
            markeredgecolor="white",
            markeredgewidth=0.75,
            markersize=8,
            label=row["CATEGORY_LABEL"],
        )
        for row in category_legend.iter_rows(named=True)
    ]

    fig.legend(
        handles=handles,
        title="Category",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
    )

    sns.despine(fig=fig)
    return fig


def plot_relationships(pois: pl.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, sharey=True, figsize=(8, 4))
    sns.histplot(
        pois.to_pandas(),
        x="TOTAL_VISITORS",
        y="SEGREGATION",
        log_scale=(True, False),
        ax=axes[0],
    )
    sns.histplot(
        pois.to_pandas(),
        x="AVG_DIST",
        y="SEGREGATION",
        log_scale=(True, False),
        ax=axes[1],
    )
    sns.despine()
    fig.tight_layout()
    return fig


def plot_category_counts(categories: pl.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(12, 8))

    categories = categories.with_columns(
        pl.col("CATEGORY")
        .replace_strict(
            PALETTE,
            default="#4C78A8",
        )
        .alias("COLOR")
    )

    pdf_all = categories.sort("NUM_POIS", descending=True).to_pandas()
    pdf_sub = (
        categories.sort("NUM_POIS", descending=True)
        .filter(pl.col("CATEGORY") != "Other")
        .to_pandas()
    )

    sns.barplot(
        pdf_sub,
        y="NAICS_TITLE",
        x="NUM_POIS",
        hue="CATEGORY",
        palette=PALETTE,
        dodge=False,
        legend=False,
        ax=axes[0],
    )

    sns.barplot(
        pdf_all,
        y="CATEGORY",
        x="NUM_POIS",
        hue="CATEGORY",
        palette=PALETTE,
        dodge=False,
        estimator="sum",
        legend=False,
        ax=axes[1],
    )

    sns.despine()
    fig.tight_layout()
    return fig


def plot_poi_visitor_ccdf(pois: pl.DataFrame) -> plt.Figure:
    agg = pois.group_by("ID_STORE").agg(pl.col("TOTAL_VISITORS").sum())
    series = agg["TOTAL_VISITORS"].to_numpy()

    # Sort values ascending
    sorted_vals = np.sort(series)
    n = len(sorted_vals)

    # CCDF: P(X > x) for each sorted value
    # For the i-th smallest value (1-indexed), the fraction of points
    # strictly greater than it is (n - i) / n
    ccdf = 1.0 - (np.arange(1, n + 1) / n)

    fig, ax = plt.subplots()
    ax.plot(sorted_vals, ccdf, marker=".", linestyle="none")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Visitor counts")
    ax.set_ylabel("P(X > x)")
    ax.set_title("CCDF of POI Visitor Counts")

    return fig


def plot_categories_weekly_linechart(categories_weekly: pl.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(2, 2, sharex=True, figsize=(12, 8))
    sns.lineplot(
        categories_weekly.to_pandas(),
        x="DATE_RANGE_START",
        y="SEGREGATION",
        hue="CATEGORY",
        palette=PALETTE,
        ax=axes[0, 0],
        legend=False,
    )
    sns.lineplot(
        categories_weekly.to_pandas(),
        x="DATE_RANGE_START",
        y="AVG_DIST",
        hue="CATEGORY",
        palette=PALETTE,
        ax=axes[1, 0],
        legend=False,
    )

    categories_weekly = categories_weekly.with_columns(
        [
            (
                (pl.col(c) - pl.col(c).mean().over("CATEGORY"))
                / pl.col(c).std().over("CATEGORY")
            ).alias(f"{c}_Z")
            for c in ["SEGREGATION", "AVG_DIST"]
        ]
    )

    sns.lineplot(
        categories_weekly.to_pandas(),
        x="DATE_RANGE_START",
        y="SEGREGATION_Z",
        hue="CATEGORY",
        palette=PALETTE,
        ax=axes[0, 1],
        legend=False,
    )
    sns.lineplot(
        categories_weekly.to_pandas(),
        x="DATE_RANGE_START",
        y="AVG_DIST_Z",
        hue="CATEGORY",
        palette=PALETTE,
        ax=axes[1, 1],
        # legend=False
    )

    sns.despine()
    return fig


if __name__ == "__main__":
    # load data
    con = db.connect(DB_PATH, read_only=True)

    pois_dim = cache.cached_parquet(
        "pois_ny",
        lambda: data.NY.load_pois(con),
    )

    # Static segregation
    poi_visits = cache.cached_parquet(
        "static_poi_segregation_ny",
        lambda: data.NY.load_static_poi_segregation(con),
    )

    pois = pois_dim.join(poi_visits, on="ID_STORE")
    categories = pois.group_by("CATEGORY", "NAICS_TITLE").agg(
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
    )

    print("pois:", pois.head())
    print("categories:", categories.head())

    print()
    print("Individual pois")
    print(
        "TOTAL_VISITORS ~ SEGREGATION",
        pois.select(pl.corr("TOTAL_VISITORS", "SEGREGATION", method="spearman"))[0, 0],
    )
    print(
        "AVG_DIST ~ SEGREGATION",
        pois.select(pl.corr("AVG_DIST", "SEGREGATION", method="spearman"))[0, 0],
    )
    print()
    print("Aggregated categories")
    print(
        "TOTAL_VISITORS ~ SEGREGATION",
        categories.select(pl.corr("TOTAL_VISITORS", "SEGREGATION", method="spearman"))[
            0, 0
        ],
    )
    print(
        "AVG_DIST ~ SEGREGATION",
        categories.select(pl.corr("AVG_DIST", "SEGREGATION", method="spearman"))[0, 0],
    )

    fig = plot_categories(categories)
    figure_path = ROOT / "figures" / "category_segregation.png"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_path, dpi=400, bbox_inches="tight")

    fig = plot_relationships(categories)
    figure_path = ROOT / "figures" / "poi_relationships.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    fig = plot_category_counts(categories)
    figure_path = ROOT / "figures" / "category_counts.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    fig = plot_poi_visitor_ccdf(pois)
    figure_path = ROOT / "figures" / "poi_visitors_ccdf.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    # Weekly segregation
    poi_visits_weekly = cache.cached_parquet(
        "weekly_poi_segregation_ny",
        lambda: data.NY.load_weekly_poi_segregation(con),
    )
    pois_weekly = pois_dim.join(poi_visits_weekly, on="ID_STORE")
    categories_weekly = pois_weekly.group_by("CATEGORY", "DATE_RANGE_START").agg(
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
        pl.col("AVG_TMAX").mean(),
    )

    fig = plot_categories_weekly_linechart(categories_weekly)
    figure_path = ROOT / "figures" / "categories_weekly.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")
