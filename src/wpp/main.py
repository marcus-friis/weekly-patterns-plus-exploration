import contextily as cx
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import pyfixest as pf
import seaborn as sns
from adjustText import adjust_text
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from pyproj import Transformer
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

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


def plot_categories(categories: pl.DataFrame) -> Figure:
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


def plot_poi_map(pois: pl.DataFrame) -> Figure:
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12, 6),
        constrained_layout=True,
    )

    # ------------------------------------------------------------------
    # Project WGS84 -> Web Mercator
    # ------------------------------------------------------------------

    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:3857",
        always_xy=True,
    )

    x, y = transformer.transform(
        pois["LONGITUDE"].to_numpy(),
        pois["LATITUDE"].to_numpy(),
    )

    hb_density = axes[0].hexbin(
        x,
        y,
        gridsize=80,
        mincnt=5,
        bins="log",
        cmap="viridis",
    )

    axes[0].set_title(f"POI density (n={len(pois):,})")

    cax = inset_axes(
        axes[0],
        width="40%",
        height="3%",
        loc="lower right",
        borderpad=1,
    )

    cbar = fig.colorbar(
        hb_density,
        cax=cax,
        orientation="horizontal",
    )

    cbar.set_label("Log POI count", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    hb_seg = axes[1].hexbin(
        x,
        y,
        C=pois["SEGREGATION"].to_numpy(),
        reduce_C_function=np.mean,
        gridsize=80,
        mincnt=5,
        cmap="coolwarm",
        vmin=0,
        vmax=1,
    )

    axes[1].set_title("Mean segregation")

    cax = inset_axes(
        axes[1],
        width="40%",
        height="3%",
        loc="lower right",
        borderpad=1,
    )

    cbar = fig.colorbar(
        hb_seg,
        cax=cax,
        orientation="horizontal",
    )

    cbar.set_label("Segregation", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    for ax in axes:
        cx.add_basemap(ax)

        ax.set_axis_off()

    return fig


def plot_relationships(pois: pl.DataFrame) -> Figure:
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


def plot_category_counts(categories: pl.DataFrame) -> Figure:
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


def plot_poi_metrics_ccdf(pois: pl.DataFrame) -> Figure:
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    visitors = (
        pois.group_by("ID_STORE")
        .agg(pl.col("TOTAL_VISITORS").sum())["TOTAL_VISITORS"]
        .to_numpy()
    )

    vals = np.sort(visitors)
    vals = vals[np.isfinite(vals) & (vals > 0)]
    ccdf = (len(vals) - np.arange(len(vals))) / len(vals)

    axes[0, 0].plot(vals, ccdf, ".", alpha=0.7)
    axes[0, 0].set_title("Visitor Counts (All POIs)")

    visitor_cat = pois.group_by(["CATEGORY", "ID_STORE"]).agg(
        pl.col("TOTAL_VISITORS").sum()
    )

    for category, df in visitor_cat.group_by("CATEGORY"):
        vals = np.sort(df["TOTAL_VISITORS"].to_numpy())

        if len(vals) < 2:
            continue

        ccdf = 1.0 - np.arange(1, len(vals) + 1) / len(vals)

        axes[0, 1].plot(
            vals,
            ccdf,
            alpha=0.7,
            label=category[0] if isinstance(category, tuple) else category,
        )

    axes[0, 1].set_title("Visitor Counts (By Category)")
    axes[0, 1].legend(fontsize=8)

    avg_dist = (
        pois.group_by("ID_STORE").agg(pl.col("AVG_DIST").mean())["AVG_DIST"].to_numpy()
    )

    vals = np.sort(avg_dist)
    ccdf = 1.0 - np.arange(1, len(vals) + 1) / len(vals)

    axes[1, 0].plot(vals, ccdf, ".", alpha=0.7)
    axes[1, 0].set_title("Average Travel Distance (All POIs)")

    dist_cat = pois.group_by(["CATEGORY", "ID_STORE"]).agg(pl.col("AVG_DIST").mean())

    for category, df in dist_cat.group_by("CATEGORY"):
        vals = np.sort(df["AVG_DIST"].to_numpy())

        if len(vals) < 2:
            continue

        ccdf = 1.0 - np.arange(1, len(vals) + 1) / len(vals)

        axes[1, 1].plot(
            vals,
            ccdf,
            alpha=0.7,
            label=category[0] if isinstance(category, tuple) else category,
        )

    axes[1, 1].set_title("Average Travel Distance (By Category)")
    axes[1, 1].legend(fontsize=8)

    for ax in axes.flat:
        ax.set(
            xscale="log",
            yscale="log",
            ylabel="P(X > x)",
        )

    axes[0, 0].set_xlabel("Visitors")
    axes[0, 1].set_xlabel("Visitors")
    axes[1, 0].set_xlabel("Average distance (m)")
    axes[1, 1].set_xlabel("Average distance (m)")

    fig.tight_layout()

    return fig


def plot_categories_weekly_linechart(categories_weekly: pl.DataFrame) -> Figure:
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


def plot_categories_weekly_scatter(categories_weekly: pl.DataFrame) -> Figure:
    fig, ax = plt.subplots(figsize=(10, 10))
    sns.scatterplot(
        categories_weekly.to_pandas(),
        x="AVG_DIST",
        y="SEGREGATION",
        hue="CATEGORY",
        palette=PALETTE,
        ax=ax,
    )
    return fig


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
                "RHO": float(result.statistic),
                "PVALUE": float(result.pvalue),
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


def plot_poi_temperature_correlations(
    correlations: pl.DataFrame,
    *,
    categories: list[str] | None = None,
    bins: int = 30,
) -> Figure:
    if correlations.is_empty():
        raise ValueError("No valid POI-level correlations to plot.")

    if categories is None:
        categories = (
            correlations.group_by("CATEGORY")
            .agg(pl.len().alias("NUM_POIS"))
            .sort("NUM_POIS", descending=True)["CATEGORY"]
            .to_list()
        )

    categories = [
        category
        for category in categories
        if correlations.filter(pl.col("CATEGORY") == category).height > 0
    ]

    n_categories = len(categories)

    fig, axes = plt.subplots(
        n_categories,
        2,
        figsize=(11, max(2.0 * n_categories, 4)),
        sharex="col",
        squeeze=False,
        constrained_layout=True,
    )

    rho_bins = np.linspace(-1, 1, bins + 1)
    pvalue_bins = np.linspace(0, 1, bins + 1)

    for row, category in enumerate(categories):
        category_data = correlations.filter(pl.col("CATEGORY") == category)

        rho = category_data["RHO"].to_numpy()
        pvalues = category_data["PVALUE"].to_numpy()

        median_rho = np.median(rho)
        significant_share = category_data["SIGNIFICANT"].mean()

        axes[row, 0].hist(
            rho,
            bins=rho_bins,
            color=PALETTE.get(category, "#4C78A8"),
            alpha=0.85,
            edgecolor="white",
            linewidth=0.4,
        )

        axes[row, 0].axvline(
            0,
            color="0.35",
            linestyle=":",
            linewidth=0.8,
        )
        axes[row, 0].axvline(
            median_rho,
            color="black",
            linestyle="--",
            linewidth=1,
        )

        axes[row, 1].hist(
            pvalues,
            bins=pvalue_bins,
            color=PALETTE.get(category, "#4C78A8"),
            alpha=0.85,
            edgecolor="white",
            linewidth=0.4,
        )

        axes[row, 1].axvline(
            0.05,
            color="#D55E00",
            linestyle="--",
            linewidth=1,
        )

        category_label = category.replace("_", " ")

        axes[row, 0].set_ylabel(
            f"{category_label}\n(n={len(rho):,})",
            rotation=0,
            ha="right",
            va="center",
        )

        axes[row, 0].text(
            0.98,
            0.88,
            rf"median $\rho$ = {median_rho:.2f}",
            transform=axes[row, 0].transAxes,
            ha="right",
            va="top",
            fontsize=8,
        )

        axes[row, 1].text(
            0.98,
            0.88,
            f"FDR significant = {significant_share:.1%}",
            transform=axes[row, 1].transAxes,
            ha="right",
            va="top",
            fontsize=8,
        )

    axes[0, 0].set_title("POI-level Spearman correlations")
    axes[0, 1].set_title("Raw p-value distributions")

    axes[-1, 0].set_xlabel(r"Spearman $\rho$: temperature vs. segregation")
    axes[-1, 1].set_xlabel("Raw p-value")

    axes[-1, 0].set_xlim(-1, 1)
    axes[-1, 1].set_xlim(0, 1)

    for ax in axes.flat:
        ax.grid(axis="y", alpha=0.15)

    sns.despine(fig=fig)

    return fig


def plot_tmax_seg_scatter(pois_weekly: pl.DataFrame) -> Figure:
    fig, ax = plt.subplots()
    sns.histplot(pois_weekly.to_pandas(), x="AVG_TMAX", y="SEGREGATION", ax=ax)
    sns.despine()
    return fig


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

    poi_visits_weekly = cache.cached_parquet(
        "weekly_poi_segregation",
        lambda: data.load_weekly_poi_segregation(con),
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

    # Static segregation
    # print("Individual pois")
    # print(
    #     "TOTAL_VISITORS ~ SEGREGATION",
    #     pois.select(pl.corr("TOTAL_VISITORS", "SEGREGATION", method="spearman"))[0, 0],
    # )
    # print(
    #     "AVG_DIST ~ SEGREGATION",
    #     pois.select(pl.corr("AVG_DIST", "SEGREGATION", method="spearman"))[0, 0],
    # )
    # print()
    # print("Aggregated categories")
    # print(
    #     "TOTAL_VISITORS ~ SEGREGATION",
    #     categories.select(pl.corr("TOTAL_VISITORS", "SEGREGATION", method="spearman"))[
    #         0, 0
    #     ],
    # )
    # print(
    #     "AVG_DIST ~ SEGREGATION",
    #     categories.select(pl.corr("AVG_DIST", "SEGREGATION", method="spearman"))[0, 0],
    # )
    #
    # fig = plot_categories(categories)
    # figure_path = ROOT / "figures" / "category_segregation.png"
    # figure_path.parent.mkdir(parents=True, exist_ok=True)
    # fig.savefig(figure_path, dpi=400, bbox_inches="tight")
    #
    # fig = plot_poi_map(pois)
    # figure_path = ROOT / "figures" / "poi_map.png"
    # fig.savefig(figure_path, dpi=400, bbox_inches="tight")
    #
    # fig = plot_relationships(pois)
    # figure_path = ROOT / "figures" / "poi_relationships.png"
    # fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    #
    # fig = plot_category_counts(categories)
    # figure_path = ROOT / "figures" / "category_counts.png"
    # fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    #
    # fig = plot_poi_metrics_ccdf(pois)
    # figure_path = ROOT / "figures" / "poi_metrics_ccdf.png"
    # fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    #
    # # Weekly segregation
    # rows = []
    # for cat in categories_weekly["CATEGORY"].unique():
    #     X = categories_weekly.filter(pl.col("CATEGORY") == cat)
    #     corr = spearmanr(X["AVG_TMAX"], X["SEGREGATION"])
    #     rows.append(
    #         {
    #             "CATEGORY": cat,
    #             "statistic": corr.statistic,  # pyright: ignore[reportAttributeAccessIssue]
    #             "pvalue": corr.pvalue,  # pyright: ignore[reportAttributeAccessIssue]
    #         }
    #     )
    # corrs = pl.DataFrame(rows)
    # print(corrs)
    #
    # poi_correlations = compute_poi_temperature_correlations(
    #     pois_weekly,
    #     min_observations=10,
    # )
    #
    # print(
    #     poi_correlations.group_by("CATEGORY")
    #     .agg(
    #         pl.len().alias("NUM_POIS"),
    #         pl.col("N").median().alias("MEDIAN_WEEKS"),
    #         pl.col("RHO").median().alias("MEDIAN_RHO"),
    #         pl.col("RHO").mean().alias("MEAN_RHO"),
    #         pl.col("SIGNIFICANT").mean().alias("SHARE_FDR_SIGNIFICANT"),
    #     )
    #     .sort("MEDIAN_RHO")
    # )
    #
    # fig = plot_poi_temperature_correlations(poi_correlations)
    # figure_path = ROOT / "figures" / "poi_temperature_correlations.png"
    # figure_path.parent.mkdir(parents=True, exist_ok=True)
    #
    # fig.savefig(
    #     figure_path,
    #     dpi=300,
    #     bbox_inches="tight",
    # )
    #
    # fig = plot_categories_weekly_linechart(categories_weekly)
    # figure_path = ROOT / "figures" / "categories_weekly.png"
    # fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    #
    # fig = plot_categories_weekly_scatter(categories_weekly)
    # figure_path = ROOT / "figures" / "categories_weekly_scatter.png"
    # fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    #
    # fig = plot_tmax_seg_scatter(pois_weekly)
    # figure_path = ROOT / "figures" / "tmax_seg_scatter.png"
    # fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    # Segregation modeling

    pdf = (
        pois_weekly.select(
            "ID_STORE",
            "SEGREGATION",
            "AVG_DIST",
            "AVG_TMAX",
            "DATE_RANGE_START",
            "CELL_ID",
        )
        .filter(
            pl.col("ID_STORE").is_not_null(),
            pl.col("SEGREGATION").is_not_null(),
            pl.col("DATE_RANGE_START").is_not_null(),
            pl.col("AVG_DIST").is_finite(),
            pl.col("AVG_TMAX").is_finite(),
        )
        .with_columns(
            (pl.col("AVG_TMAX") / 2).floor().mul(2).cast(pl.Int32).alias("TMAX_BIN")
        )
        .to_pandas()
    )
    reference_bin = int(pdf["TMAX_BIN"].value_counts().idxmax())
    print(f"Reference: {reference_bin} to {reference_bin + 2} degrees")

    print(f"Fitting model on {len(pdf):,} observations...", flush=True)

    model = pf.feols(
        f"SEGREGATION ~ i(TMAX_BIN, ref={reference_bin}) | ID_STORE + DATE_RANGE_START",
        data=pdf,
        vcov={"CRV1": "ID_STORE + CELL_ID"},
    )

    model.summary()

    coef = model.coef()
    se = model.se()

    effects = (
        pl.DataFrame(
            {
                "TERM": coef.index.tolist(),
                "ESTIMATE": coef.to_numpy(),
                "SE": se.to_numpy(),
            }
        )
        .with_columns(
            pl.col("TERM")
            .str.extract(r"TMAX_BIN::(-?\d+)", 1)
            .cast(pl.Int32)
            .alias("TMAX_BIN")
        )
        .drop_nulls("TMAX_BIN")
        .with_columns(
            (pl.col("ESTIMATE") - 1.96 * pl.col("SE")).alias("CI_LOW"),
            (pl.col("ESTIMATE") + 1.96 * pl.col("SE")).alias("CI_HIGH"),
        )
    )

    reference_effect = pl.DataFrame(
        {
            "TERM": [f"TMAX_BIN::{reference_bin}"],
            "ESTIMATE": [0.0],
            "SE": [0.0],
            "TMAX_BIN": [reference_bin],
            "CI_LOW": [0.0],
            "CI_HIGH": [0.0],
        },
        schema={
            "TERM": pl.String,
            "ESTIMATE": pl.Float64,
            "SE": pl.Float64,
            "TMAX_BIN": pl.Int32,
            "CI_LOW": pl.Float64,
            "CI_HIGH": pl.Float64,
        },
    )

    effects = (
        pl.concat(
            [effects, reference_effect],
            how="vertical",
        )
        .sort("TMAX_BIN")
        .with_columns((pl.col("TMAX_BIN") + 1).alias("BIN_MIDPOINT"))
    )

    effects_pdf = effects.to_pandas()

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.errorbar(
        effects_pdf["BIN_MIDPOINT"],
        effects_pdf["ESTIMATE"],
        yerr=[
            effects_pdf["ESTIMATE"] - effects_pdf["CI_LOW"],
            effects_pdf["CI_HIGH"] - effects_pdf["ESTIMATE"],
        ],
        fmt="o-",
        color="#0072B2",
        markerfacecolor="white",
        markeredgecolor="#0072B2",
        markersize=5,
        linewidth=1.25,
        elinewidth=0.8,
        capsize=3,
        label="Estimate and 95% CI",
    )

    ax.axhline(
        0,
        color="black",
        linewidth=0.8,
        linestyle="--",
    )

    ax.axvspan(
        reference_bin,
        reference_bin + 2,
        color="0.85",
        alpha=0.7,
        label=f"Reference: {reference_bin}–{reference_bin + 2}°",
    )

    ax.set(
        xlabel="Average maximum temperature, 2° bin midpoint",
        ylabel="Difference in average travel distance (m)",
        title="Temperature and average visitor travel distance",
    )

    ax.set_xticks(effects_pdf["BIN_MIDPOINT"])
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.15)

    ax.legend(
        frameon=False,
        loc="best",
    )

    sns.despine(ax=ax)
    fig.tight_layout()

    figure_path = ROOT / "figures" / "temperature_distance_binned.png"
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(
        figure_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    for cat in categories["CATEGORY"].unique():
        pdf = (
            pois_weekly.select(
                "ID_STORE",
                "CATEGORY",
                "SEGREGATION",
                "AVG_DIST",
                "AVG_TMAX",
                "DATE_RANGE_START",
                "CELL_ID",
            )
            .filter(pl.col("CATEGORY") == cat)
            .filter(
                pl.col("ID_STORE").is_not_null(),
                pl.col("SEGREGATION").is_not_null(),
                pl.col("DATE_RANGE_START").is_not_null(),
                pl.col("AVG_DIST").is_finite(),
                pl.col("AVG_TMAX").is_finite(),
            )
            .with_columns(
                (pl.col("AVG_TMAX") / 2).floor().mul(2).cast(pl.Int32).alias("TMAX_BIN")
            )
            .to_pandas()
        )
        reference_bin = int(pdf["TMAX_BIN"].value_counts().idxmax())
        print(f"Reference: {reference_bin} to {reference_bin + 2} degrees")

        print(f"Fitting model on {len(pdf):,} observations...", flush=True)

        model = pf.feols(
            f"SEGREGATION ~ i(TMAX_BIN, ref={reference_bin}) | ID_STORE + DATE_RANGE_START",
            data=pdf,
            vcov={"CRV1": "ID_STORE + CELL_ID"},
        )

        print(cat)
        model.summary()

        coef = model.coef()
        se = model.se()

        effects = (
            pl.DataFrame(
                {
                    "TERM": coef.index.tolist(),
                    "ESTIMATE": coef.to_numpy(),
                    "SE": se.to_numpy(),
                }
            )
            .with_columns(
                pl.col("TERM")
                .str.extract(r"TMAX_BIN::(-?\d+)", 1)
                .cast(pl.Int32)
                .alias("TMAX_BIN")
            )
            .drop_nulls("TMAX_BIN")
            .with_columns(
                (pl.col("ESTIMATE") - 1.96 * pl.col("SE")).alias("CI_LOW"),
                (pl.col("ESTIMATE") + 1.96 * pl.col("SE")).alias("CI_HIGH"),
            )
        )

        reference_effect = pl.DataFrame(
            {
                "TERM": [f"TMAX_BIN::{reference_bin}"],
                "ESTIMATE": [0.0],
                "SE": [0.0],
                "TMAX_BIN": [reference_bin],
                "CI_LOW": [0.0],
                "CI_HIGH": [0.0],
            },
            schema={
                "TERM": pl.String,
                "ESTIMATE": pl.Float64,
                "SE": pl.Float64,
                "TMAX_BIN": pl.Int32,
                "CI_LOW": pl.Float64,
                "CI_HIGH": pl.Float64,
            },
        )

        effects = (
            pl.concat(
                [effects, reference_effect],
                how="vertical",
            )
            .sort("TMAX_BIN")
            .with_columns((pl.col("TMAX_BIN") + 1).alias("BIN_MIDPOINT"))
        )

        effects_pdf = effects.to_pandas()

        fig, ax = plt.subplots(figsize=(9, 5))

        ax.errorbar(
            effects_pdf["BIN_MIDPOINT"],
            effects_pdf["ESTIMATE"],
            yerr=[
                effects_pdf["ESTIMATE"] - effects_pdf["CI_LOW"],
                effects_pdf["CI_HIGH"] - effects_pdf["ESTIMATE"],
            ],
            fmt="o-",
            color="#0072B2",
            markerfacecolor="white",
            markeredgecolor="#0072B2",
            markersize=5,
            linewidth=1.25,
            elinewidth=0.8,
            capsize=3,
            label="Estimate and 95% CI",
        )

        ax.axhline(
            0,
            color="black",
            linewidth=0.8,
            linestyle="--",
        )

        ax.axvspan(
            reference_bin,
            reference_bin + 2,
            color="0.85",
            alpha=0.7,
            label=f"Reference: {reference_bin}–{reference_bin + 2}°",
        )

        ax.set(
            xlabel="Average maximum temperature, 2° bin midpoint",
            ylabel="Difference in average travel distance (m)",
            title="Temperature and average visitor travel distance",
        )

        ax.set_xticks(effects_pdf["BIN_MIDPOINT"])
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=0.15)

        ax.legend(
            frameon=False,
            loc="best",
        )

        sns.despine(ax=ax)
        fig.tight_layout()

        figure_path = ROOT / "figures" / f"temperature_distance_binned_{cat}.png"
        figure_path.parent.mkdir(parents=True, exist_ok=True)

        fig.savefig(
            figure_path,
            dpi=300,
            bbox_inches="tight",
        )

        plt.close(fig)
