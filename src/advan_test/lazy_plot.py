import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.axes import Axes

from advan_test.utils import save_fig


def _resolve_ax(ax: Axes | None, **subplots_kwargs) -> Axes:
    """Return ax. If ax is given, reuse its figure; else create both."""
    if ax is None:
        _, ax = plt.subplots(**subplots_kwargs)
    return ax


@save_fig()
def plot_visitor_dist_by_region(lf: pl.LazyFrame, ax: Axes | None = None) -> Axes:
    """THIS IS SLOW!!!"""
    ax = _resolve_ax(ax)
    bins = np.linspace(0, 200, 11)
    regions = lf.select("REGION").unique().collect()["REGION"]
    for region in regions:
        df_filtered = lf.filter(pl.col("REGION") == region).collect()
        ax.hist(df_filtered["VISITOR_COUNTS"], bins=bins, label=region)
    ax.legend()
    return ax


@save_fig()
def plot_pois_by_dimension(
    lf: pl.LazyFrame,
    dimension: str = "TOP_CATEGORY",
    top_k: int | None = None,
    ax: Axes | None = None,
) -> Axes:
    lf_agg = (
        lf.group_by(dimension)
        .agg(pl.col("ID_STORE").n_unique().alias("NUM"))
        .sort("NUM", descending=True)
    )
    if top_k is not None:
        lf_agg = lf_agg.top_k(top_k, by="NUM")
    agg = lf_agg.collect()
    ax = _resolve_ax(ax)
    ax.barh(agg[dimension][::-1], agg["NUM"][::-1])
    ax.set_xlabel("#POI")
    ax.set_ylabel(dimension)
    return ax


@save_fig()
def plot_visits_by_hour(
    lf: pl.LazyFrame,
    ax: Axes | None = None,
) -> Axes:
    hour_sum = lf["visits_by_each_hour"].to_numpy().sum(axis=0)
    n = hour_sum.shape[0]
    x = np.arange(n)
    ax = _resolve_ax(ax)
    ax.plot(x, hour_sum)

    hours_per_day = 24
    n_days = n // hours_per_day  # should be 7

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for i in range(n_days):
        start = i * hours_per_day

        if i > 0:
            ax.axvline(start, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)

        mid = start + hours_per_day / 2
        label = day_names[i] if i < len(day_names) else f"Day {i + 1}"
        ax.text(
            mid,
            ax.get_ylim()[1] * 0.95,
            label,
            ha="center",
            va="top",
            fontsize=9,
            color="gray",
        )

    ax.set_xticks(np.arange(0, n + 1, hours_per_day))
    ax.set_xlabel("Hour")
    ax.set_ylabel("#Visitors")
    return ax


@save_fig()
def plot_visits_by_hour_per_day(
    lf: pl.LazyFrame,
    ax: Axes | None = None,
) -> Axes:
    dtype = pl.List(pl.UInt32)
    hour_sum = (
        lf.filter(pl.col("VISITS_BY_EACH_HOUR").is_not_null())
        .select(pl.col("VISITS_BY_EACH_HOUR").str.json_decode(dtype).list.to_array(168))
        .collect()
        .to_numpy()
        .sum(axis=0)
    )[0]
    n = hour_sum.shape[0]

    hours_per_day = 24
    n_days = n // hours_per_day  # 7

    x = np.arange(hours_per_day)
    ax = _resolve_ax(ax)

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for i in range(n_days):
        start = i * hours_per_day
        end = start + hours_per_day
        day_data = hour_sum[start:end]
        label = day_names[i] if i < len(day_names) else f"Day {i + 1}"
        ax.plot(x, day_data, label=label, marker="o", markersize=3)

    ax.set_xticks(x)
    ax.set_xlabel("Hour")
    ax.set_ylabel("#Visitors")
    ax.legend(title="Day")
    return ax


@save_fig()
def plot_visits_by_weekday(
    lf: pl.LazyFrame,
    ax: Axes | None = None,
) -> Axes:
    """Total visits per weekday, summed across all POIs and weeks."""
    dtype = pl.List(pl.UInt32)
    day_sum = (
        lf.select(pl.col("VISITS_BY_DAY").str.json_decode(dtype).list.to_array(7))
        .collect()
        .to_numpy()
        .sum(axis=0)
    )[0]
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    ax = _resolve_ax(ax)
    ax.bar(day_names, day_sum, color="steelblue")
    ax.set_xlabel("Day of week")
    ax.set_ylabel("#Visitors")
    return ax


@save_fig()
def plot_weekly_visits_trend(
    lf: pl.LazyFrame,
    ax: Axes | None = None,
) -> Axes:
    """Total visitor counts per week, to see trend/seasonality over time."""
    weekly = (
        lf.group_by("DATE_RANGE_START")
        .agg(pl.col("VISITOR_COUNTS").sum().alias("TOTAL_VISITORS"))
        .sort("DATE_RANGE_START")
        .collect()
    )

    ax = _resolve_ax(ax)
    ax.plot(weekly["DATE_RANGE_START"], weekly["TOTAL_VISITORS"], marker="o")
    ax.set_xlabel("Week starting")
    ax.set_ylabel("#Visitors")
    fig = ax.get_figure()
    if fig:
        fig.autofmt_xdate()
    return ax


@save_fig()
def plot_distance_from_home_dist(
    lf: pl.LazyFrame,
    max_distance: float | None = None,
    log_scale: bool = False,
    ax: Axes | None = None,
) -> Axes:
    """Distribution of how far visitors traveled from home."""
    dist_lf = lf.select("DISTANCE_FROM_HOME").drop_nulls()
    if max_distance is not None:
        dist_lf = dist_lf.filter(pl.col("DISTANCE_FROM_HOME") <= max_distance)

    ax = _resolve_ax(ax)

    if log_scale:
        dist = dist_lf.filter(
            pl.col("DISTANCE_FROM_HOME") > 0
        ).collect()  # logspace needs strictly positive values
        dist_np = dist.to_numpy()
        bins = np.logspace(np.log10(dist_np.min()), np.log10(dist_np.max()), 30)
        ax.hist(dist_np, bins=bins, color="darkorange", edgecolor="white")
        ax.set_xscale("log")
        ax.set_xlabel("Distance from home (m, log scale)")
    else:
        dist = dist_lf.collect()
        ax.hist(dist, bins=30, color="darkorange", edgecolor="white")
        ax.set_xlabel("Distance from home (m)")

    ax.set_ylabel("#POI-weeks")
    return ax


@save_fig()
def plot_dwell_time_dist(
    lf: pl.LazyFrame,
    log_scale: bool = False,
    ax: Axes | None = None,
) -> Axes:
    """Distribution of median dwell time. median_dwell is cast to numeric, dropping non-parsable values."""
    dwell = lf.select("MEDIAN_DWELL").cast(pl.Float64, strict=False).drop_nulls()

    ax = _resolve_ax(ax)

    if log_scale:
        dwell = dwell.filter(
            pl.col("MEDIAN_DWELL") > 0
        )  # logspace needs strictly positive values
        dwell_np = dwell.collect().to_numpy()
        bins = np.logspace(np.log10(dwell_np.min()), np.log10(dwell_np.max()), 30)
        ax.hist(dwell_np, bins=bins, color="mediumseagreen", edgecolor="white")
        ax.set_xscale("log")
        ax.set_xlabel("Median dwell time (minutes, log scale)")
    else:
        ax.hist(dwell.collect(), bins=30, color="mediumseagreen", edgecolor="white")
        ax.set_xlabel("Median dwell time (minutes)")

    ax.set_ylabel("#POI-weeks")
    return ax


@save_fig()
def plot_visits_vs_visitors_scatter(
    lf: pl.LazyFrame,
    ax: Axes | None = None,
) -> Axes:
    """Relationship between total visits and unique visitors per POI-week."""
    df = lf.select("VISITOR_COUNTS", "VISIT_COUNTS").collect()
    ax = _resolve_ax(ax)
    ax.scatter(df["VISITOR_COUNTS"], df["VISIT_COUNTS"], alpha=0.3, s=10)
    ax.set_xlabel("#Unique visitors")
    ax.set_ylabel("#Visits")
    ax.plot(
        [0, df["VISITOR_COUNTS"].max()],
        [0, df["VISITOR_COUNTS"].max()],
        color="gray",
        linestyle="--",
        linewidth=0.8,
        label="visits = visitors",
    )
    ax.legend()
    return ax


@save_fig()
def plot_poi_visitor_distribution(
    lf: pl.LazyFrame,
    ax: Axes | None = None,
) -> Axes:
    agg = lf.group_by("ID_STORE").agg(pl.col("VISITOR_COUNTS").sum()).collect()
    series = agg["VISITOR_COUNTS"]
    ax = _resolve_ax(ax)
    ax.hist(series)
    return ax


@save_fig()
def plot_poi_visitor_ccdf(
    lf: pl.LazyFrame,
    ax: Axes | None = None,
) -> Axes:
    visitors_by_poi = (
        lf.group_by("ID_STORE")
        .agg(pl.col("VISITOR_COUNTS").sum())
        .sort(pl.col("VISITOR_COUNTS"))
        .collect()
    )
    series = visitors_by_poi["VISITOR_COUNTS"].to_numpy()
    n = len(series)
    # CCDF: P(X > x) for each sorted value
    # For the i-th smallest value (1-indexed), the fraction of points
    # strictly greater than it is (n - i) / n
    ccdf = 1.0 - (np.arange(1, n + 1) / n)

    ax = _resolve_ax(ax)
    ax.scatter(series, ccdf, marker=".", linestyle="none")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Visitor counts")
    ax.set_ylabel("P(X > x)")
    ax.set_title("CCDF of POI Visitor Counts")

    return ax
