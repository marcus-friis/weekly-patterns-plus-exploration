import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from advan_test.utils import save_fig


@save_fig()
def plot_visitor_dist_by_region(df: pl.DataFrame) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots()
    bins = np.linspace(0, 200, 11)
    for region in df["region"].unique():
        df_filtered = df.filter(df["region"] == region)
        ax.hist(df_filtered["visitor_counts"], bins=bins, label=region)
    ax.legend()
    return fig, ax


@save_fig()
def plot_pois_by_dimension(
    df: pl.DataFrame, dimension: str = "top_category", top_k: int | None = None
) -> tuple[Figure, Axes]:
    agg = (
        df.group_by(dimension)
        .agg(pl.col("id_store").n_unique().alias("num"))
        .sort("num", descending=True)
    )
    if top_k is not None:
        agg = agg.top_k(top_k, by="num")
    fig, ax = plt.subplots()
    ax.barh(agg[dimension][::-1], agg["num"][::-1])
    ax.set_xlabel("#POI")
    ax.set_ylabel(dimension)
    return fig, ax


@save_fig()
def plot_visits_by_hour(df: pl.DataFrame) -> tuple[Figure, Axes]:
    hour_sum = df["visits_by_each_hour"].to_numpy().sum(axis=0)
    n = hour_sum.shape[0]
    x = np.arange(n)
    fig, ax = plt.subplots()
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
    return fig, ax


@save_fig()
def plot_visits_by_hour_per_day(df: pl.DataFrame) -> tuple[Figure, Axes]:
    hour_sum = df["visits_by_each_hour"].to_numpy().sum(axis=0)
    n = hour_sum.shape[0]

    hours_per_day = 24
    n_days = n // hours_per_day  # 7

    x = np.arange(hours_per_day)
    fig, ax = plt.subplots()

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
    return fig, ax


@save_fig()
def plot_visits_by_weekday(df: pl.DataFrame) -> tuple[Figure, Axes]:
    """Total visits per weekday, summed across all POIs and weeks."""
    day_sum = df["visits_by_day"].to_numpy().sum(axis=0)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    fig, ax = plt.subplots()
    ax.bar(day_names, day_sum, color="steelblue")
    ax.set_xlabel("Day of week")
    ax.set_ylabel("#Visitors")
    return fig, ax


@save_fig()
def plot_weekly_visits_trend(df: pl.DataFrame) -> tuple[Figure, Axes]:
    """Total visitor counts per week, to see trend/seasonality over time."""
    weekly = (
        df.group_by("date_range_start")
        .agg(pl.col("visitor_counts").sum().alias("total_visitors"))
        .sort("date_range_start")
    )

    fig, ax = plt.subplots()
    ax.plot(weekly["date_range_start"], weekly["total_visitors"], marker="o")
    ax.set_xlabel("Week starting")
    ax.set_ylabel("#Visitors")
    fig.autofmt_xdate()
    return fig, ax


@save_fig()
def plot_distance_from_home_dist(
    df: pl.DataFrame, max_distance: float | None = None, log_scale: bool = False
) -> tuple[Figure, Axes]:
    """Distribution of how far visitors traveled from home (meters, per Advan schema)."""
    dist = df["distance_from_home"].drop_nulls()
    if max_distance is not None:
        dist = dist.filter(dist <= max_distance)

    fig, ax = plt.subplots()

    if log_scale:
        dist = dist.filter(dist > 0)  # logspace needs strictly positive values
        dist_np = dist.to_numpy()
        bins = np.logspace(np.log10(dist_np.min()), np.log10(dist_np.max()), 30)
        ax.hist(dist_np, bins=bins, color="darkorange", edgecolor="white")
        ax.set_xscale("log")
        ax.set_xlabel("Distance from home (m, log scale)")
    else:
        ax.hist(dist, bins=30, color="darkorange", edgecolor="white")
        ax.set_xlabel("Distance from home (m)")

    ax.set_ylabel("#POI-weeks")
    return fig, ax


@save_fig()
def plot_dwell_time_dist(
    df: pl.DataFrame, log_scale: bool = False
) -> tuple[Figure, Axes]:
    """Distribution of median dwell time. median_dwell is cast to numeric, dropping non-parsable values."""
    dwell = df["median_dwell"].cast(pl.Float64, strict=False).drop_nulls()

    fig, ax = plt.subplots()

    if log_scale:
        dwell = dwell.filter(dwell > 0)  # logspace needs strictly positive values
        dwell_np = dwell.to_numpy()
        bins = np.logspace(np.log10(dwell_np.min()), np.log10(dwell_np.max()), 30)
        ax.hist(dwell_np, bins=bins, color="mediumseagreen", edgecolor="white")
        ax.set_xscale("log")
        ax.set_xlabel("Median dwell time (minutes, log scale)")
    else:
        ax.hist(dwell, bins=30, color="mediumseagreen", edgecolor="white")
        ax.set_xlabel("Median dwell time (minutes)")

    ax.set_ylabel("#POI-weeks")
    return fig, ax


@save_fig()
def plot_visits_vs_visitors_scatter(df: pl.DataFrame) -> tuple[Figure, Axes]:
    """Relationship between total visits and unique visitors per POI-week."""
    fig, ax = plt.subplots()
    ax.scatter(df["visitor_counts"], df["visit_counts"], alpha=0.3, s=10)
    ax.set_xlabel("#Unique visitors")
    ax.set_ylabel("#Visits")
    ax.plot(
        [0, df["visitor_counts"].max()],
        [0, df["visitor_counts"].max()],
        color="gray",
        linestyle="--",
        linewidth=0.8,
        label="visits = visitors",
    )
    ax.legend()
    return fig, ax


@save_fig()
def plot_poi_locations(
    points: gpd.GeoDataFrame, base: gpd.GeoDataFrame
) -> tuple[Figure, Axes]:
    """Plot location of POIs onto basemap"""
    fig, ax = plt.subplots(figsize=(12, 8))
    base.plot(ax=ax, color="#f0efeb", edgecolor="gray", linewidth=0.5)
    points.plot(ax=ax, markersize="visitor_counts", alpha=0.6, color="crimson")
    for x, y, location_name in zip(
        points.geometry.x, points.geometry.y, points["location_name"]
    ):
        ax.annotate(
            location_name,
            xy=(x, y),
            xytext=(3, 3),  # offset in points, so label sits outside the marker
            textcoords="offset points",
            fontsize=6,
        )
    ax.set_xlim(-125, -66)
    ax.set_ylim(24, 50)
    ax.set_axis_off()
    return fig, ax


@save_fig()
def plot_region_population_counts(
    points: gpd.GeoDataFrame, base: gpd.GeoDataFrame
) -> tuple[Figure, Axes]:
    joined = base.sjoin(points, how="left", predicate="intersects")
    agg = joined.groupby(["id", "region"])["visitor_counts"].sum().reset_index()
    agg["visitor_counts"] = agg["visitor_counts"]
    result = base.merge(agg, on="id", how="left").fillna(0)

    fig, ax = plt.subplots()
    result.plot(
        column="visitor_counts",
        ax=ax,
        legend=True,
        cmap="viridis",
        edgecolor="black",
    )
    ax.set_title("Visitor Counts by Region")
    ax.axis("off")
    return fig, ax


@save_fig()
def plot_poi_visitor_distribution(df: pl.DataFrame) -> tuple[Figure, Axes]:
    agg = df.group_by("id_store").agg(pl.col("visitor_counts").sum())
    series = agg["visitor_counts"]
    fig, ax = plt.subplots()
    ax.hist(series)
    return fig, ax


@save_fig()
def plot_poi_visitor_ccdf(df: pl.DataFrame) -> tuple[Figure, Axes]:
    agg = df.group_by("id_store").agg(pl.col("visitor_counts").sum())
    series = agg["visitor_counts"].to_numpy()

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

    return fig, ax
