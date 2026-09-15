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

    lp.plot_visitor_dist_by_region(lf)
    lp.plot_visitor_dist_by_region_duckdb(PARQUET_DIR_PATH)
