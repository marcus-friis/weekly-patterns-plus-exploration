from pathlib import Path

import contextily as cx
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns
from adjustText import adjust_text
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from pyproj import Transformer

from wpp.config import LABEL_CATEGORIES, PALETTE
from wpp.utils import project_root


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

    # Convert only at the  boundary.
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


def plot_poi_metrics_ccdf(pois: pl.DataFrame) -> Figure:
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    visitors = (
        pois.group_by("ID_STORE")
        .agg(pl.col("TOTAL_VISITORS").sum().cast(pl.Float64))["TOTAL_VISITORS"]
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

    for (category,), df in visitor_cat.group_by("CATEGORY"):
        vals = np.sort(df["TOTAL_VISITORS"].to_numpy())

        if len(vals) < 2:
            continue

        ccdf = 1.0 - np.arange(1, len(vals) + 1) / len(vals)

        axes[0, 1].plot(
            vals,
            ccdf,
            alpha=0.7,
            color=PALETTE.get(category, "#4C78A8"),
            label=category.replace("_", " "),
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

    for (category,), df in dist_cat.group_by("CATEGORY"):
        vals = np.sort(df["AVG_DIST"].to_numpy())

        if len(vals) < 2:
            continue

        ccdf = 1.0 - np.arange(1, len(vals) + 1) / len(vals)

        axes[1, 1].plot(
            vals,
            ccdf,
            alpha=0.7,
            color=PALETTE.get(category, "#4C78A8"),
            label=category.replace("_", " "),
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


def plot_weekly_msa_segregation(pois_weekly: pl.DataFrame) -> Figure:
    fig, ax = plt.subplots()
    msas = pois_weekly.group_by("DATE_RANGE_START", "CBSA_NAME").agg(
        pl.col("SEGREGATION").mean().alias("AVG_SEGREGATION"),
        (
            (pl.col("SEGREGATION") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("W_AVG_SEGREGATION"),
    )
    sns.lineplot(
        msas.to_pandas(),
        x="DATE_RANGE_START",
        y="W_AVG_SEGREGATION",
        hue="CBSA_NAME",
        ax=ax,
    )
    return fig


def plot_all(
    pois: pl.DataFrame | None = None,
    categories: pl.DataFrame | None = None,
    pois_weekly: pl.DataFrame | None = None,
    categories_weekly: pl.DataFrame | None = None,
    *,
    base_path: Path | None = None,
):
    if base_path == None:
        base_path = project_root() / "figures"
    base_path.mkdir(parents=True, exist_ok=True)

    if categories is not None:
        fig = plot_categories(categories)
        figure_path = base_path / "category_segregation.png"
        fig.savefig(figure_path, dpi=400, bbox_inches="tight")

        fig = plot_category_counts(categories)
        figure_path = base_path / "category_counts.png"
        fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    if pois is not None:
        fig = plot_poi_map(pois)
        figure_path = base_path / "poi_map.png"
        fig.savefig(figure_path, dpi=400, bbox_inches="tight")

        fig = plot_relationships(pois)
        figure_path = base_path / "poi_relationships.png"
        fig.savefig(figure_path, dpi=200, bbox_inches="tight")

        fig = plot_poi_metrics_ccdf(pois)
        figure_path = base_path / "poi_metrics_ccdf.png"
        fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    if categories_weekly is not None:
        fig = plot_categories_weekly_linechart(categories_weekly)
        figure_path = base_path / "categories_weekly.png"
        fig.savefig(figure_path, dpi=200, bbox_inches="tight")

        fig = plot_categories_weekly_scatter(categories_weekly)
        figure_path = base_path / "categories_weekly_scatter.png"
        fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    if pois_weekly is not None:
        fig = plot_tmax_seg_scatter(pois_weekly)
        figure_path = base_path / "tmax_seg_scatter.png"
        fig.savefig(figure_path, dpi=200, bbox_inches="tight")

        fig = plot_weekly_msa_segregation(pois_weekly)
        figure_path = base_path / "msa_weekly_segregation.pdf"
        fig.savefig(figure_path, dpi=200, bbox_inches="tight")
