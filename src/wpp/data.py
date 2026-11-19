from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import polars as pl
from duckdb import DuckDBPyConnection


@dataclass(frozen=True)
class ClimateEvent:
    label: str
    start: datetime
    end: datetime | None = None  # None = single-day / point event

    @property
    def is_range(self) -> bool:
        return self.end is not None and self.end != self.start

    @property
    def last_day(self) -> datetime:
        return self.end or self.start


def get_climate_events() -> list[ClimateEvent]:
    events = [
        ClimateEvent(
            label="Southern California wildfires",
            start=datetime.fromisoformat("2025-01-07"),
            end=datetime.fromisoformat("2025-01-31"),
        ),
        ClimateEvent(
            label="Central Texas floods",
            start=datetime.fromisoformat("2025-07-04"),
            end=datetime.fromisoformat("2025-07-05"),
        ),
        ClimateEvent(
            label="Tampa, Florida heat record",
            start=datetime.fromisoformat("2025-07-27"),
        ),
    ]
    return sorted(events, key=lambda e: e.start)


def load_weekly_patterns_plus_parquet(dir_path: Path | str) -> pl.LazyFrame:
    """Lazily load Weekly Patterns Plus parquet shards into a single LazyFrame."""
    dir_path = Path(dir_path)

    lf = pl.scan_parquet(dir_path / "*.parquet")
    return lf


def load_pois(con: DuckDBPyConnection) -> pl.DataFrame:
    query = """
        WITH v AS (
            SELECT ID_STORE, SUM(VISITOR_COUNTS) AS TOTAL_VISITORS
            FROM visits
            GROUP BY ID_STORE
        )
        SELECT
            CBSA_NAME, p.*, v.TOTAL_VISITORS AS VISITORS,
            COALESCE(CATEGORY, 'Other') AS CATEGORY, SUB_CATEGORY AS NAICS_TITLE
        FROM pois p
        JOIN v ON p.ID_STORE = v.ID_STORE
        JOIN cbsa c ON p.CBSAFP = c.CBSAFP
        LEFT JOIN NAICS_CATEGORIES nc ON p.NAICS_CODE = nc.NAICS_CODE
    """
    pois_dim = (
        con.sql(query)
        .pl()
        .with_columns(
            pl.col("CBSA_NAME").alias("CBSA_NAME_FULL"),
            pl.col("CBSA_NAME").str.extract(r"^([^-]*)", 1).alias("CBSA_NAME"),
        )
    )
    return pois_dim


def load_static_poi_segregation(con: DuckDBPyConnection) -> pl.DataFrame:
    query = """
        WITH bg AS (
            SELECT
                GEOID, CBSAFP, MEDIAN_HH_INCOME,
                NTILE(4) OVER (PARTITION BY CBSAFP ORDER BY MEDIAN_HH_INCOME ASC) AS INCOME_GROUP
            FROM block_groups_cbsa
            WHERE MEDIAN_HH_INCOME IS NOT NULL
        )
        SELECT
            v.ID_STORE, INCOME_GROUP,
            SUM(VISITOR_COUNTS) AS TOTAL_VISITORS,
            COUNT(*) AS NUM_WEEKS,
            COUNT(DISTINCT HOME_GEOID) AS NUM_HOME_GROUPS,
            SUM(DIST * VISITOR_COUNTS) / SUM(VISITOR_COUNTS) AS AVG_DIST
        FROM block_group_visits_enhanced v
        JOIN bg ON v.HOME_GEOID = bg.GEOID
        GROUP BY v.ID_STORE, INCOME_GROUP
    """
    poi_group_visits = con.sql(query).pl()
    poi_summary = poi_group_visits.group_by("ID_STORE").agg(
        (
            (pl.col("AVG_DIST") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("AVG_DIST"),
        pl.col("NUM_HOME_GROUPS").sum().alias("NUM_HOME_GROUPS"),
    )
    poi_visits = (
        poi_group_visits.sort("INCOME_GROUP")
        .pivot(
            "INCOME_GROUP",
            index="ID_STORE",
            values=["TOTAL_VISITORS"],
            column_naming="combine",
        )
        .fill_null(0)
        .with_columns(
            pl.sum_horizontal(pl.selectors.starts_with("TOTAL_VISITORS_")).alias(
                "TOTAL_VISITORS"
            )
        )
        .with_columns(
            (
                pl.selectors.starts_with("TOTAL_VISITORS_").cast(pl.Float64)
                / pl.col("TOTAL_VISITORS").replace({0: None})
            ).name.replace("TOTAL_VISITORS_", "TAU_")
        )
        .with_columns(
            (
                (2 / 3)
                * pl.sum_horizontal((pl.selectors.starts_with("TAU_") - (1 / 4)).abs())
            ).alias("SEGREGATION")
        )
        .filter(pl.col("TOTAL_VISITORS") > 0)
        .join(poi_summary, on="ID_STORE", how="left")
    )
    return poi_visits


def load_weekly_poi_segregation(con: DuckDBPyConnection) -> pl.DataFrame:
    query = """
    WITH bg AS (
        SELECT
            GEOID,
            CBSAFP,
            MEDIAN_HH_INCOME,
            NTILE(4) OVER (
                PARTITION BY CBSAFP
                ORDER BY MEDIAN_HH_INCOME
            ) AS INCOME_GROUP
        FROM block_groups_cbsa
        WHERE MEDIAN_HH_INCOME IS NOT NULL
    ),
    poi_weeks AS (
        SELECT DISTINCT
            v.ID_STORE,
            v.DATE_RANGE_START,
            v.DATE_RANGE_END
        FROM block_group_visits v
    ),
    poi_temperature_weekly AS (
        SELECT
            pw.ID_STORE,
            pw.DATE_RANGE_START,
            pw.DATE_RANGE_END,
            AVG(t.TMEAN) AS AVG_TMEAN,
            AVG(t.TMIN) AS AVG_TMIN,
            AVG(t.TMAX) AS AVG_TMAX,
            AVG(t.TMEAN_NORM) AS AVG_TMEAN_NORM,
            AVG(t.TMIN_NORM) AS AVG_TMIN_NORM,
            AVG(t.TMAX_NORM) AS AVG_TMAX_NORM,
            COUNT(t.DATE) AS NUM_TEMPERATURE_DAYS
        FROM poi_weeks pw
        JOIN pois p
            ON pw.ID_STORE = p.ID_STORE
        LEFT JOIN prism_t_daily t
            ON p.CELL_ID = t.CELL_ID
           AND t.DATE >= pw.DATE_RANGE_START
           AND t.DATE <= pw.DATE_RANGE_END
        GROUP BY
            pw.ID_STORE,
            pw.DATE_RANGE_START,
            pw.DATE_RANGE_END
    ),
    poi_group_visits_weekly AS (
        SELECT
            v.ID_STORE,
            v.DATE_RANGE_START,
            v.DATE_RANGE_END,
            bg.INCOME_GROUP,
            SUM(v.VISITOR_COUNTS) AS TOTAL_VISITORS,
            SUM(v.DIST * v.VISITOR_COUNTS) / SUM(v.VISITOR_COUNTS) AS AVG_DIST,
            COUNT(DISTINCT v.HOME_GEOID) AS NUM_HOME_GROUPS
        FROM block_group_visits_enhanced v
        JOIN bg
            ON v.HOME_GEOID = bg.GEOID
        GROUP BY
            v.ID_STORE,
            v.DATE_RANGE_START,
            v.DATE_RANGE_END,
            bg.INCOME_GROUP
    )
    SELECT
        v.ID_STORE,
        v.DATE_RANGE_START,
        v.DATE_RANGE_END,
        v.INCOME_GROUP,
        v.TOTAL_VISITORS,
        v.AVG_DIST,
        v.NUM_HOME_GROUPS,
        t.AVG_TMEAN,
        t.AVG_TMIN,
        t.AVG_TMAX,
        t.NUM_TEMPERATURE_DAYS
    FROM poi_group_visits_weekly v
    LEFT JOIN poi_temperature_weekly t
        USING (
            ID_STORE,
            DATE_RANGE_START,
            DATE_RANGE_END
        )
    ORDER BY
        v.ID_STORE,
        v.DATE_RANGE_START,
        v.INCOME_GROUP
    """
    poi_group_visits_weekly = con.sql(query).pl()
    poi_summary_weekly = poi_group_visits_weekly.group_by(
        "ID_STORE", "DATE_RANGE_START"
    ).agg(
        (
            (pl.col("AVG_DIST") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("AVG_DIST"),
        pl.col("NUM_HOME_GROUPS").sum().alias("NUM_HOME_GROUPS"),
    )

    poi_visits_weekly = (
        poi_group_visits_weekly.sort("INCOME_GROUP")
        .pivot(
            "INCOME_GROUP",
            index=[
                "ID_STORE",
                "DATE_RANGE_START",
                "DATE_RANGE_END",
                "AVG_TMEAN",
                "AVG_TMIN",
                "AVG_TMAX",
                "NUM_TEMPERATURE_DAYS",
            ],
            column_naming="combine",
        )
        .fill_null(
            0,
            matches_supertype=False,
        )
        .with_columns(
            pl.sum_horizontal(pl.selectors.starts_with("TOTAL_VISITORS_")).alias(
                "TOTAL_VISITORS"
            )
        )
        .with_columns(
            (
                pl.selectors.starts_with("TOTAL_VISITORS_").cast(pl.Float64)
                / pl.col("TOTAL_VISITORS").replace(0, None)
            ).name.replace("TOTAL_VISITORS_", "TAU_")
        )
        .with_columns(
            (
                (2 / 3)
                * pl.sum_horizontal((pl.selectors.starts_with("TAU_") - 0.25).abs())
            ).alias("SEGREGATION")
        )
        .filter(pl.col("TOTAL_VISITORS") > 0)
        .join(poi_summary_weekly, on=["ID_STORE", "DATE_RANGE_START"], how="left")
    )

    return poi_visits_weekly


def load_static_cbg_segregation(con: DuckDBPyConnection) -> pl.DataFrame:
    query = """
        WITH bg AS (
            SELECT
                GEOID, CBSAFP, MEDIAN_HH_INCOME,
                NTILE(4) OVER (PARTITION BY CBSAFP ORDER BY MEDIAN_HH_INCOME ASC) AS INCOME_GROUP
            FROM block_groups_cbsa
            WHERE MEDIAN_HH_INCOME IS NOT NULL
        )
        SELECT
            v.HOME_GEOID AS GEOID, INCOME_GROUP,
            SUM(VISITOR_COUNTS) AS TOTAL_VISITORS,
            SUM(DIST * VISITOR_COUNTS) / SUM(VISITOR_COUNTS) AS AVG_DIST
        FROM block_group_visits_enhanced v
        JOIN pois p ON v.ID_STORE = p.ID_STORE
        JOIN bg ON p.POI_GEOID = bg.GEOID
        GROUP BY 1, 2
    """
    cbg_group_visits = con.sql(query).pl()

    cbg_summary = cbg_group_visits.group_by("GEOID").agg(
        (
            (pl.col("AVG_DIST") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("AVG_DIST"),
    )
    cbg_visits = (
        cbg_group_visits.sort("INCOME_GROUP")
        .pivot(
            "INCOME_GROUP",
            index="GEOID",
            values=["TOTAL_VISITORS"],
            column_naming="combine",
        )
        .fill_null(0)
        .with_columns(
            pl.sum_horizontal(pl.selectors.starts_with("TOTAL_VISITORS_")).alias(
                "TOTAL_VISITORS"
            )
        )
        .with_columns(
            (
                pl.selectors.starts_with("TOTAL_VISITORS_").cast(pl.Float64)
                / pl.col("TOTAL_VISITORS").replace({0: None})
            ).name.replace("TOTAL_VISITORS_", "TAU_")
        )
        .with_columns(
            (
                (2 / 3)
                * pl.sum_horizontal((pl.selectors.starts_with("TAU_") - (1 / 4)).abs())
            ).alias("SEGREGATION")
        )
        .filter(pl.col("TOTAL_VISITORS") > 0)
        .join(cbg_summary, on="GEOID", how="left")
    )
    return cbg_visits


def load_weekly_cbg_segregation(con: DuckDBPyConnection) -> pl.DataFrame:
    query = """
    WITH bg AS (
        SELECT
            GEOID,
            CBSAFP,
            MEDIAN_HH_INCOME,
            NTILE(4) OVER (
                PARTITION BY CBSAFP
                ORDER BY MEDIAN_HH_INCOME
            ) AS INCOME_GROUP
        FROM block_groups_cbsa
        WHERE MEDIAN_HH_INCOME IS NOT NULL
    ),
    cbg_group_visits_weekly AS (
        SELECT
            v.HOME_GEOID AS GEOID,
            v.DATE_RANGE_START,
            v.DATE_RANGE_END,
            bg.INCOME_GROUP,
            SUM(v.VISITOR_COUNTS) AS TOTAL_VISITORS,
            SUM(v.DIST * v.VISITOR_COUNTS)
                / SUM(v.VISITOR_COUNTS) AS AVG_DIST,
            COUNT(*) AS NUM_POIS
        FROM block_group_visits_enhanced v
        JOIN pois p
            ON v.ID_STORE = p.ID_STORE
        JOIN bg
            ON p.POI_GEOID = bg.GEOID
        GROUP BY
            v.HOME_GEOID,
            v.DATE_RANGE_START,
            v.DATE_RANGE_END,
            bg.INCOME_GROUP
    )
    SELECT *
    FROM cbg_group_visits_weekly
    ORDER BY
        GEOID,
        DATE_RANGE_START,
        INCOME_GROUP
    """
    cbg_group_visits_weekly = con.sql(query).pl()

    cbg_summary_weekly = cbg_group_visits_weekly.group_by(
        "GEOID",
        "DATE_RANGE_START",
    ).agg(
        (
            (pl.col("AVG_DIST") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("AVG_DIST"),
        pl.col("NUM_POIS").sum().alias("NUM_POIS"),
    )

    cbg_visits_weekly = (
        cbg_group_visits_weekly.sort("INCOME_GROUP")
        .pivot(
            "INCOME_GROUP",
            index=[
                "GEOID",
                "DATE_RANGE_START",
                "DATE_RANGE_END",
            ],
            column_naming="combine",
        )
        .fill_null(
            0,
            matches_supertype=False,
        )
        .with_columns(
            pl.sum_horizontal(pl.selectors.starts_with("TOTAL_VISITORS_")).alias(
                "TOTAL_VISITORS"
            )
        )
        .with_columns(
            (
                pl.selectors.starts_with("TOTAL_VISITORS_").cast(pl.Float64)
                / pl.col("TOTAL_VISITORS").replace(0, None)
            ).name.replace("TOTAL_VISITORS_", "TAU_")
        )
        .with_columns(
            (
                (2 / 3)
                * pl.sum_horizontal((pl.selectors.starts_with("TAU_") - 0.25).abs())
            ).alias("SEGREGATION")
        )
        .filter(pl.col("TOTAL_VISITORS") > 0)
        .join(
            cbg_summary_weekly,
            on=["GEOID", "DATE_RANGE_START"],
            how="left",
        )
    )

    return cbg_visits_weekly
