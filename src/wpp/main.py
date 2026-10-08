from collections import defaultdict
from datetime import datetime

import matplotlib.pyplot as plt
import polars as pl
import seaborn as sns
from matplotlib.lines import Line2D

from wpp import data, db
from wpp.utils import project_root

ROOT = project_root()
DATA_PATH = ROOT / "data"
DB_PATH = ROOT / "wpp.duckdb"

sns.set_theme(style="ticks")
pl.Config.set_engine_affinity("streaming")

if __name__ == "__main__":
    # load data
    con = db.connect(DB_PATH)
    events = data.get_climate_events()
    cbsa_visits = con.sql("""
        WITH cbsa AS (
            SELECT
                *,
                POP_RANK_IN_TYPE,
                POP_RANK_IN_TYPE <= 6 AS IS_TOP
            FROM cbsa
            WHERE LSAD = 'M1'
        )
        SELECT
            DATE_RANGE_START,
            DATE_RANGE_END,
            p.CBSAFP,
            cbsa.CBSA_NAME,
            POP_RANK_IN_TYPE,
            IS_TOP,
            SUM(VISITOR_COUNTS) AS VISITOR_COUNTS,
            SUM(DIST * VISITOR_COUNTS) / SUM(VISITOR_COUNTS) AS AVG_DIST
        FROM block_group_visits_enhanced bgv
        JOIN pois p ON bgv.ID_STORE = p.ID_STORE
        JOIN cbsa ON p.CBSAFP = cbsa.CBSAFP
        GROUP BY 1, 2, 3, 4, 5, 6
    """).pl()

    # color per top CBSA
    top_names = (
        cbsa_visits.filter(pl.col("IS_TOP"))
        .select("CBSA_NAME", "POP_RANK_IN_TYPE")
        .unique()
        .sort("POP_RANK_IN_TYPE")["CBSA_NAME"]
        .to_list()
    )
    palette = sns.color_palette("tab10", len(top_names))
    c = dict(zip(top_names, palette))

    # How does avg dist to home evolve over time?
    def background_style():
        return dict(color="lightgrey", linewidth=0.8, alpha=0.6, zorder=1)

    kwarg_map = defaultdict(
        background_style,
        {
            name: dict(color=color, linewidth=2, alpha=1, zorder=3, label=name)
            for name, color in zip(top_names, palette)
        },
    )
    fig, axes = plt.subplots(1, 3, sharex=True, figsize=(18, 5))
    for (cbsa_name,), g in cbsa_visits.group_by("CBSA_NAME"):
        g = g.sort("DATE_RANGE_START")
        is_top = g["IS_TOP"][0]
        axes[0].plot(g["DATE_RANGE_START"], g["VISITOR_COUNTS"], **kwarg_map[cbsa_name])
        axes[1].plot(g["DATE_RANGE_START"], g["AVG_DIST"], **kwarg_map[cbsa_name])

    handles = [Line2D([0], [0], color=c, lw=2, label=n) for n, c in c.items()]
    handles.append(Line2D([0], [0], color="lightgray", lw=1, label="Other CBSAs"))
    axes[2].legend(handles=handles, loc="center left", frameon=False)
    axes[2].axis("off")

    axes[0].set(title="MSA visitors over time", xlabel="DATE", ylabel="Visitors")
    axes[1].set(
        title="Avg distance traveled over time by MSA",
        xlabel="DATE",
        ylabel="Avg distance",
    )
    fig.tight_layout()
    fig.savefig("lol.png", dpi=400)
