from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns
from adjustText import adjust_text
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from wpp.config import LABEL_CATEGORIES, PALETTE
from wpp.utils import project_root


def _save_figure(fig: Figure, path: Path, *, dpi: int = 200) -> None:
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def plot_categories(categories: pl.DataFrame) -> Figure:
    categories = categories.with_columns(
        pl.col("CATEGORY").replace_strict(PALETTE, default="#4C78A8").alias("COLOR"),
        pl.col("CATEGORY").str.replace_all("_", " ").alias("CATEGORY_LABEL"),
    )
    other = categories.filter(pl.col("CATEGORY") == "Other")
    main = categories.filter(pl.col("CATEGORY") != "Other")
    labels = main.filter(pl.col("CATEGORY").is_in(LABEL_CATEGORIES))
    legend_data = (
        main.select("CATEGORY", "CATEGORY_LABEL", "COLOR").unique().sort("CATEGORY")
    )
    other_pdf, main_pdf = other.to_pandas(), main.to_pandas()

    fig, axes = plt.subplots(
        1, 2, figsize=(16, 8), dpi=400, sharey=True, constrained_layout=True
    )
    for ax, (x, title) in zip(
        axes,
        [
            ("TOTAL_VISITORS", "Visitors vs segregation"),
            ("AVG_DIST", "Distance vs segregation"),
        ],
    ):
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
                row[x], row["SEGREGATION"], row["NAICS_TITLE"], fontsize=7, zorder=20
            )
            for row in labels.select(x, "SEGREGATION", "NAICS_TITLE").iter_rows(
                named=True
            )
        ]
        adjust_text(
            texts,
            ax=ax,
            arrowprops={"arrowstyle": "-", "color": "0.3", "lw": 0.5, "alpha": 0.6},
            expand=(1.15, 1.15),
        )
        ax.set(title=title, xscale="log", ylabel="Segregation")
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
        for row in legend_data.iter_rows(named=True)
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


def plot_categories_weekly_linechart(categories_weekly: pl.DataFrame) -> Figure:
    fig, axes = plt.subplots(
        2, 2, sharex=True, figsize=(12, 8), constrained_layout=True
    )
    raw = categories_weekly.to_pandas()
    sns.lineplot(
        data=raw,
        x="DATE_RANGE_START",
        y="SEGREGATION",
        hue="CATEGORY",
        palette=PALETTE,
        ax=axes[0, 0],
        legend=False,
    )
    sns.lineplot(
        data=raw,
        x="DATE_RANGE_START",
        y="AVG_DIST",
        hue="CATEGORY",
        palette=PALETTE,
        ax=axes[1, 0],
        legend=False,
    )
    standardized = categories_weekly.with_columns(
        [
            (
                (pl.col(c) - pl.col(c).mean().over("CATEGORY"))
                / pl.col(c).std().over("CATEGORY")
            ).alias(f"{c}_Z")
            for c in ["SEGREGATION", "AVG_DIST"]
        ]
    ).to_pandas()
    sns.lineplot(
        data=standardized,
        x="DATE_RANGE_START",
        y="SEGREGATION_Z",
        hue="CATEGORY",
        palette=PALETTE,
        ax=axes[0, 1],
        legend=False,
    )
    sns.lineplot(
        data=standardized,
        x="DATE_RANGE_START",
        y="AVG_DIST_Z",
        hue="CATEGORY",
        palette=PALETTE,
        ax=axes[1, 1],
    )
    sns.despine(fig=fig)
    return fig


def plot_categories_weekly_scatter(categories_weekly: pl.DataFrame) -> Figure:
    fig, ax = plt.subplots(figsize=(10, 10))
    sns.scatterplot(
        data=categories_weekly.to_pandas(),
        x="AVG_DIST",
        y="SEGREGATION",
        hue="CATEGORY",
        palette=PALETTE,
        ax=ax,
    )
    return fig


def plot_relationships(pois: pl.DataFrame) -> Figure:
    fig, axes = plt.subplots(1, 2, sharey=True, figsize=(8, 4), constrained_layout=True)
    pdf = pois.to_pandas()
    sns.histplot(
        data=pdf,
        x="TOTAL_VISITORS",
        y="SEGREGATION",
        log_scale=(True, False),
        ax=axes[0],
    )
    sns.histplot(
        data=pdf, x="AVG_DIST", y="SEGREGATION", log_scale=(True, False), ax=axes[1]
    )
    sns.despine(fig=fig)
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
        c for c in categories if correlations.filter(pl.col("CATEGORY") == c).height
    ]
    if not categories:
        raise ValueError("None of the requested categories are present.")

    fig, axes = plt.subplots(
        len(categories),
        2,
        figsize=(11, max(2 * len(categories), 4)),
        sharex="col",
        squeeze=False,
        constrained_layout=True,
    )
    for row, category in enumerate(categories):
        data = correlations.filter(pl.col("CATEGORY") == category)
        rho, pvalues = data["RHO"].to_numpy(), data["PVALUE"].to_numpy()
        median_rho = np.nanmedian(rho)
        significant_share = data["SIGNIFICANT"].mean()
        color = PALETTE.get(category, "#4C78A8")
        axes[row, 0].hist(
            rho,
            bins=np.linspace(-1, 1, bins + 1),
            color=color,
            alpha=0.85,
            edgecolor="white",
            linewidth=0.4,
        )
        axes[row, 0].axvline(0, color="0.35", linestyle=":", linewidth=0.8)
        axes[row, 0].axvline(median_rho, color="black", linestyle="--", linewidth=1)
        axes[row, 1].hist(
            pvalues,
            bins=np.linspace(0, 1, bins + 1),
            color=color,
            alpha=0.85,
            edgecolor="white",
            linewidth=0.4,
        )
        axes[row, 1].axvline(0.05, color="#D55E00", linestyle="--", linewidth=1)
        axes[row, 0].set_ylabel(
            f"{category.replace('_', ' ')}\n(n={len(rho):,})",
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
    axes[-1, 0].set(
        xlabel=r"Spearman $\rho$: temperature vs. segregation", xlim=(-1, 1)
    )
    axes[-1, 1].set(xlabel="Raw p-value", xlim=(0, 1))
    for ax in axes.flat:
        ax.grid(axis="y", alpha=0.15)
    sns.despine(fig=fig)
    return fig


def plot_tmax_seg_scatter(pois_weekly: pl.DataFrame) -> Figure:
    fig, ax = plt.subplots()
    sns.histplot(data=pois_weekly.to_pandas(), x="AVG_TMAX", y="SEGREGATION", ax=ax)
    sns.despine(fig=fig)
    return fig


def plot_weekly_msa_segregation(pois_weekly: pl.DataFrame) -> Figure:
    msas = pois_weekly.group_by("DATE_RANGE_START", "CBSA_NAME").agg(
        pl.col("SEGREGATION").mean().alias("AVG_SEGREGATION"),
        (
            (pl.col("SEGREGATION") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("W_AVG_SEGREGATION"),
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(
        data=msas.to_pandas(),
        x="DATE_RANGE_START",
        y="W_AVG_SEGREGATION",
        hue="CBSA_NAME",
        ax=ax,
    )
    return fig


def plot_all(
    *,
    pois: pl.DataFrame | None = None,
    categories: pl.DataFrame | None = None,
    pois_weekly: pl.DataFrame | None = None,
    categories_weekly: pl.DataFrame | None = None,
    temperature_correlations: pl.DataFrame | None = None,
    base_path: Path | None = None,
) -> None:
    base_path = base_path or project_root() / "figures" / "analysis"
    base_path.mkdir(parents=True, exist_ok=True)
    if categories is not None:
        _save_figure(
            plot_categories(categories), base_path / "category_segregation.pdf", dpi=400
        )
    if pois is not None:
        _save_figure(plot_relationships(pois), base_path / "poi_relationships.pdf")
    if categories_weekly is not None:
        _save_figure(
            plot_categories_weekly_linechart(categories_weekly),
            base_path / "categories_weekly.pdf",
        )
        _save_figure(
            plot_categories_weekly_scatter(categories_weekly),
            base_path / "categories_weekly_scatter.pdf",
        )
    if pois_weekly is not None:
        _save_figure(
            plot_tmax_seg_scatter(pois_weekly), base_path / "tmax_seg_scatter.pdf"
        )
        _save_figure(
            plot_weekly_msa_segregation(pois_weekly),
            base_path / "msa_weekly_segregation.pdf",
        )
    if temperature_correlations is not None:
        _save_figure(
            plot_poi_temperature_correlations(temperature_correlations),
            base_path / "poi_temperature_correlations.pdf",
        )
