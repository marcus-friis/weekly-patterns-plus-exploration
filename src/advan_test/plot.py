import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from advan_test.utils import save_fig


@save_fig()
def plot_visitor_dist_by_region(df: pl.DataFrame):
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
):
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
def plot_visits_by_hour(df: pl.DataFrame):
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
def plot_visits_by_hour_per_day(df: pl.DataFrame):
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
