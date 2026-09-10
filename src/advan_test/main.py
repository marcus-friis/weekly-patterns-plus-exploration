import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

from advan_test.data import load_weekly_patterns_plus
from advan_test.plot import (
    plot_pois_by_dimension,
    plot_visits_by_hour,
    plot_visits_by_hour_per_day,
)
from advan_test.utils import project_root

DATA_PATH = project_root() / "data"
CSV_PATH = DATA_PATH / "weekly-patterns-plus-sample.csv"
US_PATH = DATA_PATH / "us-states.json"

if __name__ == "__main__":
    df = load_weekly_patterns_plus(CSV_PATH)
    states = gpd.read_file(US_PATH)
    points = gpd.GeoDataFrame(
        df.to_pandas(),
        geometry=[Point(xy) for xy in zip(df["longitude"], df["latitude"])],
        crs="EPSG:4326",
    )

    plot_pois_by_dimension(df, "top_category", 10)
    plot_pois_by_dimension(df, "region", 10)
    plot_visits_by_hour(df)
    plot_visits_by_hour_per_day(df)

    fig, ax = plt.subplots(figsize=(12, 8))
    states.plot(ax=ax, color="#f0efeb", edgecolor="gray", linewidth=0.5)
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
    plt.show()
