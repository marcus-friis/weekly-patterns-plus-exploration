from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns
from matplotlib.figure import Figure

from wpp.config import PALETTE
from wpp.utils import project_root


def _require_columns(df: pl.DataFrame, columns: list[str]) -> None:
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def _save_figure(fig: Figure, path: Path, *, dpi: int = 200) -> None:
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def plot_category_counts(categories: pl.DataFrame) -> Figure:
    _require_columns(categories, ["CATEGORY", "NAICS_TITLE", "NUM_POIS"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 8), constrained_layout=True)

    pdf_all = categories.sort("NUM_POIS", descending=True).to_pandas()
    pdf_sub = (
        categories.filter(pl.col("CATEGORY") != "Other")
        .sort("NUM_POIS", descending=True)
        .to_pandas()
    )

    sns.barplot(
        data=pdf_sub,
        y="NAICS_TITLE",
        x="NUM_POIS",
        hue="CATEGORY",
        palette=PALETTE,
        dodge=False,
        legend=False,
        ax=axes[0],
    )
    sns.barplot(
        data=pdf_all,
        y="CATEGORY",
        x="NUM_POIS",
        hue="CATEGORY",
        palette=PALETTE,
        dodge=False,
        estimator="sum",
        legend=False,
        ax=axes[1],
    )
    axes[0].set_title("POIs by NAICS title")
    axes[1].set_title("POIs by category")
    sns.despine(fig=fig)
    return fig


def plot_pois_weekly(pois_weekly: pl.DataFrame) -> Figure:
    """Plot row count, unique POIs, total visitors, and median visitors by week."""
    _require_columns(
        pois_weekly,
        [
            "DATE_RANGE_START",
            "ID_STORE",
            "TOTAL_VISITORS",
            "AVG_DIST",
            "SEGREGATION",
        ],
    )
    agg = (
        pois_weekly.group_by("DATE_RANGE_START")
        .agg(
            pl.len().alias("NUM_ROWS"),
            pl.col("ID_STORE").n_unique().alias("NUM_POIS"),
            pl.col("TOTAL_VISITORS").sum().alias("TOTAL_VISITORS"),
            pl.col("TOTAL_VISITORS").median().alias("MEDIAN_VISITORS"),
            pl.col("AVG_DIST").mean().alias("MEAN_DIST"),
            pl.col("SEGREGATION").mean().alias("MEAN_SEGREGATION"),
        )
        .sort("DATE_RANGE_START")
    )

    fig, axes = plt.subplots(
        3,
        2,
        figsize=(12, 10),
        sharex=True,
        constrained_layout=True,
    )

    plots = [
        ("NUM_ROWS", "Rows"),
        ("NUM_POIS", "Unique POIs"),
        ("TOTAL_VISITORS", "Total visitors"),
        ("MEDIAN_VISITORS", "Median visitors per row"),
        ("MEAN_DIST", "Mean distance"),
        ("MEAN_SEGREGATION", "Mean segregation"),
    ]

    for ax, (column, title) in zip(axes.flat, plots):
        ax.plot(
            agg["DATE_RANGE_START"],
            agg[column],
        )
        ax.set_title(title)
        ax.grid(alpha=0.15)

    axes[2, 0].set_ylabel("Distance")
    axes[2, 1].set_ylabel("Segregation")

    sns.despine(fig=fig)
    return fig


def plot_weekly_coverage(pois_weekly: pl.DataFrame) -> Figure:
    """Plot POI coverage and week-to-week retention/churn."""
    _require_columns(pois_weekly, ["DATE_RANGE_START", "ID_STORE"])
    presence = pois_weekly.select("DATE_RANGE_START", "ID_STORE").unique()
    dates = presence["DATE_RANGE_START"].unique().sort().to_list()

    records: list[dict[str, object]] = []
    previous: set[object] | None = None
    for date in dates:
        current = set(
            presence.filter(pl.col("DATE_RANGE_START") == date)["ID_STORE"].to_list()
        )
        records.append(
            {
                "DATE_RANGE_START": date,
                "NUM_POIS": len(current),
                "NEW_POIS": 0 if previous is None else len(current - previous),
                "LOST_POIS": 0 if previous is None else len(previous - current),
                "RETENTION": None
                if not previous
                else len(current & previous) / len(previous),
            }
        )
        previous = current

    coverage = pl.DataFrame(records)
    fig, axes = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True, constrained_layout=True
    )
    axes[0].plot(
        coverage["DATE_RANGE_START"], coverage["NUM_POIS"], label="Observed POIs"
    )
    axes[0].plot(coverage["DATE_RANGE_START"], coverage["NEW_POIS"], label="New POIs")
    axes[0].plot(coverage["DATE_RANGE_START"], coverage["LOST_POIS"], label="Lost POIs")
    axes[0].set_ylabel("POIs")
    axes[0].legend(frameon=False, ncol=3)
    axes[1].plot(coverage["DATE_RANGE_START"], coverage["RETENTION"])
    axes[1].set(ylabel="Retention", ylim=(0, 1.02))
    for ax in axes:
        ax.grid(alpha=0.15)
    sns.despine(fig=fig)
    return fig


def plot_poi_week_coverage(pois_weekly: pl.DataFrame) -> Figure:
    """Show how many of the available weeks each POI is observed."""
    _require_columns(pois_weekly, ["DATE_RANGE_START", "ID_STORE"])
    total_weeks = pois_weekly["DATE_RANGE_START"].n_unique()
    coverage = (
        pois_weekly.group_by("ID_STORE")
        .agg(pl.col("DATE_RANGE_START").n_unique().alias("OBSERVED_WEEKS"))
        .with_columns((pl.col("OBSERVED_WEEKS") / total_weeks).alias("COVERAGE_SHARE"))
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    sns.histplot(
        data=coverage.to_pandas(), x="OBSERVED_WEEKS", discrete=True, ax=axes[0]
    )
    sns.histplot(data=coverage.to_pandas(), x="COVERAGE_SHARE", bins=20, ax=axes[1])
    axes[0].set_title(f"Observed weeks per POI (available={total_weeks})")
    axes[1].set(title="POI panel coverage", xlim=(0, 1))
    sns.despine(fig=fig)
    return fig


def plot_weekly_distribution(
    pois_weekly: pl.DataFrame,
    column: str,
    *,
    ylabel: str | None = None,
    log_scale: bool = False,
) -> Figure:
    """Plot weekly median and 10/25/75/90 percentiles for a numeric column."""
    _require_columns(pois_weekly, ["DATE_RANGE_START", column])
    summary = (
        pois_weekly.group_by("DATE_RANGE_START")
        .agg(
            pl.col(column).quantile(0.10).alias("P10"),
            pl.col(column).quantile(0.25).alias("P25"),
            pl.col(column).median().alias("P50"),
            pl.col(column).quantile(0.75).alias("P75"),
            pl.col(column).quantile(0.90).alias("P90"),
        )
        .sort("DATE_RANGE_START")
    )
    x = summary["DATE_RANGE_START"].to_numpy()
    fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)
    ax.fill_between(
        x, summary["P10"], summary["P90"], alpha=0.15, label="10th–90th percentile"
    )
    ax.fill_between(
        x, summary["P25"], summary["P75"], alpha=0.30, label="25th–75th percentile"
    )
    ax.plot(x, summary["P50"], color="black", linewidth=1.5, label="Median")
    ax.set(ylabel=ylabel or column, yscale="log" if log_scale else "linear")
    ax.grid(alpha=0.15)
    ax.legend(frameon=False)
    sns.despine(fig=fig)
    return fig


def plot_week_of_month_distributions(
    pois_weekly: pl.DataFrame,
) -> Figure:
    """Compare POI-level distance and home-group distributions by week of month."""
    _require_columns(
        pois_weekly,
        ["DATE_RANGE_START", "AVG_DIST", "NUM_HOME_GROUPS"],
    )
    data = pois_weekly.with_columns(
        (((pl.col("DATE_RANGE_START").dt.day() - 1) // 7) + 1)
        .cast(pl.Int8)
        .alias("WEEK_OF_MONTH")
    ).to_pandas()

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), constrained_layout=True)
    sns.boxplot(
        data=data,
        x="WEEK_OF_MONTH",
        y="AVG_DIST",
        showfliers=False,
        color="#4C78A8",
        ax=axes[0],
    )
    sns.boxplot(
        data=data,
        x="WEEK_OF_MONTH",
        y="NUM_HOME_GROUPS",
        showfliers=False,
        color="#F58518",
        ax=axes[1],
    )
    axes[0].set(
        title="Distance distribution by week of month", ylabel="Average distance"
    )
    axes[1].set(
        title="Home-group distribution by week of month", ylabel="Number of home groups"
    )
    for ax in axes:
        ax.set_xlabel("Week of month")
        ax.grid(axis="y", alpha=0.15)
    sns.despine(fig=fig)
    return fig


def plot_weekly_missingness(
    pois_weekly: pl.DataFrame,
    *,
    columns: list[str] | None = None,
) -> Figure:
    """Heatmap of weekly null shares for selected fields."""
    if columns is None:
        candidates = [
            "SEGREGATION",
            "AVG_DIST",
            "TOTAL_VISITORS",
            "AVG_TMAX",
            "NUM_HOME_GROUPS",
            "CATEGORY",
            "CBSA_NAME",
        ]
        columns = [column for column in candidates if column in pois_weekly.columns]
    _require_columns(pois_weekly, ["DATE_RANGE_START", *columns])
    if not columns:
        raise ValueError("No columns available for the missingness plot.")

    summary = (
        pois_weekly.group_by("DATE_RANGE_START")
        .agg([pl.col(column).is_null().mean().alias(column) for column in columns])
        .sort("DATE_RANGE_START")
    )
    matrix = summary.select(columns).to_numpy().T
    fig, ax = plt.subplots(
        figsize=(max(10, summary.height * 0.22), 1.2 + 0.55 * len(columns))
    )
    sns.heatmap(
        matrix,
        cmap="mako",
        vmin=0,
        vmax=1,
        yticklabels=columns,
        ax=ax,
        cbar_kws={"label": "Null share"},
    )
    ticks = np.arange(summary.height)[:: max(1, summary.height // 12)]
    ax.set_xticks(ticks + 0.5)
    ax.set_xticklabels(
        [str(summary["DATE_RANGE_START"][int(i)]) for i in ticks],
        rotation=45,
        ha="right",
    )
    ax.set(xlabel="Week", ylabel="")
    fig.tight_layout()
    return fig


def plot_poi_metrics_ccdf(pois: pl.DataFrame) -> Figure:
    _require_columns(pois, ["ID_STORE", "CATEGORY", "TOTAL_VISITORS", "AVG_DIST"])
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), constrained_layout=True)

    def draw_ccdf(ax, values: np.ndarray, **kwargs: object) -> None:
        values = np.asarray(values, dtype=float)
        values = np.sort(values[np.isfinite(values) & (values > 0)])
        if len(values) < 2:
            return
        ccdf = (len(values) - np.arange(len(values))) / len(values)
        ax.plot(values, ccdf, **kwargs)

    visitors = (
        pois.group_by("ID_STORE")
        .agg(pl.col("TOTAL_VISITORS").sum())["TOTAL_VISITORS"]
        .to_numpy()
    )
    draw_ccdf(axes[0, 0], visitors, marker=".", linestyle="", alpha=0.7)
    for (category,), df in (
        pois.group_by(["CATEGORY", "ID_STORE"])
        .agg(pl.col("TOTAL_VISITORS").sum())
        .group_by("CATEGORY")
    ):
        draw_ccdf(
            axes[0, 1],
            df["TOTAL_VISITORS"].to_numpy(),
            alpha=0.7,
            color=PALETTE.get(category, "#4C78A8"),
            label=category.replace("_", " "),
        )

    distances = (
        pois.group_by("ID_STORE").agg(pl.col("AVG_DIST").mean())["AVG_DIST"].to_numpy()
    )
    draw_ccdf(axes[1, 0], distances, marker=".", linestyle="", alpha=0.7)
    for (category,), df in (
        pois.group_by(["CATEGORY", "ID_STORE"])
        .agg(pl.col("AVG_DIST").mean())
        .group_by("CATEGORY")
    ):
        draw_ccdf(
            axes[1, 1],
            df["AVG_DIST"].to_numpy(),
            alpha=0.7,
            color=PALETTE.get(category, "#4C78A8"),
            label=category.replace("_", " "),
        )

    titles = [
        "Visitor counts (all POIs)",
        "Visitor counts (by category)",
        "Average distance (all POIs)",
        "Average distance (by category)",
    ]
    for ax, title in zip(axes.flat, titles):
        ax.set(title=title, xscale="log", yscale="log", ylabel="P(X ≥ x)")
    axes[0, 0].set_xlabel("Visitors")
    axes[0, 1].set_xlabel("Visitors")
    axes[1, 0].set_xlabel("Average distance (m)")
    axes[1, 1].set_xlabel("Average distance (m)")
    axes[0, 1].legend(fontsize=8)
    axes[1, 1].legend(fontsize=8)
    sns.despine(fig=fig)
    return fig


def plot_week_of_month_distance_home_groups(
    pois_weekly: pl.DataFrame,
    *,
    home_groups_column: str = "NUM_HOME_GROUPS",
) -> Figure:
    """
    Plot POI-week distributions of AVG_DIST and home block-group counts
    by the ordinal weekly observation within each calendar month.
    """

    _require_columns(
        pois_weekly,
        [
            "DATE_RANGE_START",
            "AVG_DIST",
            home_groups_column,
        ],
    )

    # Assign each unique weekly date its ordinal position within its month.
    week_lookup = (
        pois_weekly.select("DATE_RANGE_START")
        .unique()
        .with_columns(pl.col("DATE_RANGE_START").dt.truncate("1mo").alias("MONTH"))
        .sort(["MONTH", "DATE_RANGE_START"])
        .with_columns(
            pl.col("DATE_RANGE_START")
            .rank(method="ordinal")
            .over("MONTH")
            .cast(pl.Int8)
            .alias("WEEK_OF_MONTH")
        )
        .select(
            "DATE_RANGE_START",
            "WEEK_OF_MONTH",
        )
    )

    plot_data = (
        pois_weekly.join(
            week_lookup,
            on="DATE_RANGE_START",
            how="left",
            validate="m:1",
        )
        .select(
            "WEEK_OF_MONTH",
            "AVG_DIST",
            home_groups_column,
        )
        .drop_nulls()
        .to_pandas()
    )

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(10, 8),
        sharex=True,
        constrained_layout=True,
    )

    sns.boxplot(
        data=plot_data,
        x="WEEK_OF_MONTH",
        y="AVG_DIST",
        showfliers=False,
        color="#4C78A8",
        ax=axes[0],
    )

    sns.boxplot(
        data=plot_data,
        x="WEEK_OF_MONTH",
        y=home_groups_column,
        showfliers=False,
        color="#F58518",
        ax=axes[1],
    )

    axes[0].set(
        title="Travel-distance distribution by week of month",
        xlabel="",
        ylabel="AVG_DIST",
    )

    axes[1].set(
        title="Home block-group distribution by week of month",
        xlabel="Ordinal week within month",
        ylabel="Home block groups per POI",
    )

    for ax in axes:
        ax.grid(axis="y", alpha=0.15)

    sns.despine(fig=fig)

    return fig


def plot_all(
    *,
    pois: pl.DataFrame | None = None,
    categories: pl.DataFrame | None = None,
    pois_weekly: pl.DataFrame | None = None,
    base_path: Path | None = None,
) -> None:
    base_path = base_path or project_root() / "figures" / "descriptive"
    base_path.mkdir(parents=True, exist_ok=True)

    if categories is not None:
        _save_figure(
            plot_category_counts(categories), base_path / "category_counts.pdf"
        )
    if pois is not None:
        _save_figure(plot_poi_metrics_ccdf(pois), base_path / "poi_metrics_ccdf.pdf")
    if pois_weekly is not None:
        _save_figure(plot_pois_weekly(pois_weekly), base_path / "pois_weekly_stats.pdf")
        _save_figure(
            plot_weekly_coverage(pois_weekly), base_path / "weekly_coverage.pdf"
        )
        _save_figure(
            plot_poi_week_coverage(pois_weekly), base_path / "poi_week_coverage.pdf"
        )
        _save_figure(
            plot_weekly_distribution(
                pois_weekly, "AVG_DIST", ylabel="Average distance", log_scale=True
            ),
            base_path / "weekly_distance_distribution.pdf",
        )
        _save_figure(
            plot_week_of_month_distance_home_groups(pois_weekly),
            base_path / "week_of_month_distance_home_groups.pdf",
        )
        _save_figure(
            plot_weekly_distribution(
                pois_weekly,
                "NUM_HOME_GROUPS",
                ylabel="Number of home groups",
                log_scale=True,
            ),
            base_path / "weekly_home_group_distribution.pdf",
        )
        _save_figure(
            plot_week_of_month_distributions(pois_weekly),
            base_path / "week_of_month_distributions.pdf",
        )
        _save_figure(
            plot_weekly_missingness(pois_weekly), base_path / "weekly_missingness.pdf"
        )
