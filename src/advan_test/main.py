import geopandas as gpd
from shapely.geometry import Point

from advan_test import plot
from advan_test.data import load_weekly_patterns_plus
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

    plot.plot_pois_by_dimension(df, "top_category", 10)
    plot.plot_pois_by_dimension(df, "region", 10)
    plot.plot_visits_by_hour(df)
    plot.plot_visits_by_hour_per_day(df)
    plot.plot_visits_by_weekday(df)
    plot.plot_weekly_visits_trend(df)
    plot.plot_distance_from_home_dist(df, log_scale=False)
    plot.plot_distance_from_home_dist(df, log_scale=True)
    plot.plot_dwell_time_dist(df, log_scale=False)
    plot.plot_dwell_time_dist(df, log_scale=True)
    plot.plot_visits_vs_visitors_scatter(df)
    plot.plot_poi_locations(points, states)
    plot.plot_region_population_counts(points, states)
