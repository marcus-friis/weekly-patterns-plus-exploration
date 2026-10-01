from datetime import datetime

import matplotlib.pyplot as plt
import polars as pl
import seaborn as sns

from wpp import data, db
from wpp.utils import project_root

ROOT = project_root()
DATA_PATH = ROOT / "data"
DB_PATH = ROOT / "wpp.duckdb"

sns.set_theme(style="ticks")
pl.Config.set_engine_affinity("streaming")

if __name__ == "__main__":
    con = db.connect(DB_PATH)
    events = data.get_climate_events()
    bg = data.get_top_cbsa_block_groups(con).collect()

    visits_query = """
        WITH TOP_CBSA_GEOIDS AS (
            SELECT GEOID, CBSAFP, CBSA_NAME
            FROM block_groups_cbsa
            WHERE LSAD = 'M1'
              AND CBSA_POP_RANK <= 50
        )
        SELECT bgv.*
        FROM block_group_visits_enhanced bgv
        WHERE DATE_RANGE_START BETWEEN date'2025-01-01' AND date'2025-02-28'
    """
    visits = con.sql(visits_query).pl(lazy=False)
    df = visits.join(bg, left_on="HOME_GEOID", right_on="GEOID")
    print(df["CBSA_TITLE_TOP"].value_counts())

    sns.kdeplot(
        df,
        x="DIST",
        weights="VISITOR_COUNTS",
        hue="CBSA_TITLE_TOP",
        log_scale=True,
        legend=False,
        # stat="density",
        common_norm=False,
        # kde=True,
    )
    plt.show()

    avg_dist = df.group_by(["DATE_RANGE_START", "CBSA_TITLE_TOP"]).agg(
        pl.col("VISITOR_COUNTS").sum(),
        (
            (pl.col("VISITOR_COUNTS") * pl.col("DIST")).sum()
            / pl.col("VISITOR_COUNTS").sum()
        ).alias("DIST"),
    )
    print(avg_dist)
    print(avg_dist["CBSA_TITLE_TOP"].value_counts())
    sns.lineplot(avg_dist, x="DATE_RANGE_START", y="DIST", hue="CBSA_TITLE_TOP")
    plt.show()
    plt.close()

    # trips_lf = (
    #     visits_lf.with_columns(pl.int_ranges(pl.col("VISITOR_COUNTS")).alias("range"))
    #     .explode("range")
    #     .drop("VISITOR_COUNTS", "range")
    #     .join(bg_lf, left_on="HOME_GEOID", right_on="GEOID")
    # )

    # sns.boxplot(
    #     trips_lf.collect(),
    #     x="CBSA_TITLE_TOP",
    #     y="DIST",
    #     log_scale=True,
    #     legend=False,
    # )
    # plt.show()
