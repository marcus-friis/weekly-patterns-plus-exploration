import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from advan_test.utils import save_fig


@save_fig()
def plot_visitor_dist_by_region(df: pl.DataFrame) -> tuple[plt.Figure, plt.Axes]:
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
) -> tuple[plt.Figure, plt.Axes]:
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
def plot_visits_by_hour(df: pl.DataFrame) -> tuple[plt.Figure, plt.Axes]:
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
def plot_visits_by_hour_per_day(df: pl.DataFrame) -> tuple[plt.Figure, plt.Axes]:
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
def plot_visits_by_weekday(df: pl.DataFrame) -> tuple[plt.Figure, plt.Axes]:
    """Total visits per weekday, summed across all POIs and weeks."""
    day_sum = df["visits_by_day"].to_numpy().sum(axis=0)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    fig, ax = plt.subplots()
    ax.bar(day_names, day_sum, color="steelblue")
    ax.set_xlabel("Day of week")
    ax.set_ylabel("#Visitors")
    return fig, ax


@save_fig()
def plot_weekly_visits_trend(df: pl.DataFrame) -> tuple[plt.Figure, plt.Axes]:
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
    df: pl.DataFrame, max_distance: float | None = None
) -> tuple[plt.Figure, plt.Axes]:
    """Distribution of how far visitors traveled from home (meters, per Advan schema)."""
    dist = df["distance_from_home"].drop_nulls()
    if max_distance is not None:
        dist = dist.filter(dist <= max_distance)

    fig, ax = plt.subplots()
    ax.hist(dist, bins=30, color="darkorange", edgecolor="white")
    ax.set_xlabel("Distance from home")
    ax.set_ylabel("#POI-weeks")
    return fig, ax


@save_fig()
def plot_dwell_time_dist(df: pl.DataFrame) -> tuple[plt.Figure, plt.Axes]:
    """Distribution of median dwell time. median_dwell is cast to numeric, dropping non-parsable values."""
    dwell = df["median_dwell"].cast(pl.Float64, strict=False).drop_nulls()

    fig, ax = plt.subplots()
    ax.hist(dwell, bins=30, color="mediumseagreen", edgecolor="white")
    ax.set_xlabel("Median dwell time (minutes)")
    ax.set_ylabel("#POI-weeks")
    return fig, ax


@save_fig()
def plot_visits_vs_visitors_scatter(df: pl.DataFrame) -> tuple[plt.Figure, plt.Axes]:
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
) -> tuple[plt.Figure, plt.Axes]:
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
