import polars as pl
import seaborn as sns

from advan_test import data
from advan_test import lazy_plot as lp
from advan_test.utils import project_root

DATA_PATH = project_root() / "data"
CSV_PATH = DATA_PATH / "weekly-patterns-plus-sample.csv"
PARQUET_DIR_PATH = DATA_PATH / "2025-weekly-patterns-plus"
US_PATH = DATA_PATH / "us-states.json"

sns.set_theme(style="ticks")
pl.Config.set_engine_affinity("streaming")

if __name__ == "__main__":
    lf = data.load_weekly_patterns_plus_parquet(PARQUET_DIR_PATH)

    lp.plot_pois_by_dimension(lf, "TOP_CATEGORY", 10)
    lp.plot_pois_by_dimension(lf, "REGION", 10)
    lp.plot_dwell_time_dist(lf, log_scale=False)
    lp.plot_dwell_time_dist(lf, log_scale=True)
    lp.plot_poi_visitor_distribution(lf)
    lp.plot_poi_visitor_ccdf(lf)
    lp.plot_weekly_visits_trend(lf)
    lp.plot_visits_by_weekday(lf)
    # lp.plot_visitor_dist_by_region(lf)

    # plot.plot_visits_by_hour(df)
    # plot.plot_visits_by_hour_per_day(df)
    # plot.plot_visits_by_weekday(df)
    # plot.plot_weekly_visits_trend(df)
    # plot.plot_distance_from_home_dist(df, log_scale=False)
    # plot.plot_distance_from_home_dist(df, log_scale=True)
    # plot.plot_dwell_time_dist(df, log_scale=False)
    # plot.plot_dwell_time_dist(df, log_scale=True)
    # plot.plot_visits_vs_visitors_scatter(df)
    # plot.plot_poi_locations(points, states)
    # plot.plot_region_population_counts(points, states)
    # plot.plot_poi_visitor_distribution(df)
    # plot.plot_poi_visitor_ccdf(df)
