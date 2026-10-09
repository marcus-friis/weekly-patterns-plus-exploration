import polars as pl
from duckdb import DuckDBPyConnection


def get_pois(con: DuckDBPyConnection) -> pl.DataFrame:
    query = """
        SELECT *
        FROM pois
    """
    pois = con.sql(query).pl()
    return pois


def get_heat_daily(
    con: DuckDBPyConnection, *, cbsafp: str | None = None
) -> pl.DataFrame:
    cbsa_snippet = f"WHERE CBSAFP = '{cbsafp}'" if cbsafp else ""
    query = f"""
        SELECT CBSAFP, DATE, AVG_TMEAN
        FROM cbsa_t_daily
        {cbsa_snippet}
        ORDER BY DATE, CBSAFP
    """
    return con.sql(query).pl()


def get_df(
    con: DuckDBPyConnection,
    *,
    n_income_groups: int = 4,
    cbsafp: str | None = None,
    limit: int | None = None,
) -> pl.DataFrame:
    cbsa_snippet = f"AND CBSAFP = '{cbsafp}'" if cbsafp else ""
    limit_snippet = f"LIMIT {limit}" if limit else ""
    query = f"""
        WITH bg AS (
            SELECT
                GEOID, CBSAFP, CBSA_NAME, CBSA_POP_RANK,
                MEDIAN_HH_INCOME,
                NTILE({n_income_groups}) OVER (PARTITION BY CBSAFP ORDER BY MEDIAN_HH_INCOME ASC) AS INCOME_GROUP
            FROM block_groups_cbsa
            WHERE LSAD = 'M1'
              AND MEDIAN_HH_INCOME IS NOT NULL
              {cbsa_snippet}
        )
        SELECT
            bgv.*,
            p.POI_GEOID, bgp.CBSAFP AS POI_CBSAFP, bgp.CBSA_NAME AS CBSA_NAME, bgp.INCOME_GROUP AS POI_INCOME_GROUP,
            bgh.MEDIAN_HH_INCOME AS HOME_MEDIAN_HH_INCOME, bgh.INCOME_GROUP AS HOME_INCOME_GROUP, bgh.CBSAFP AS HOME_CBSAFP
        FROM block_group_visits_enhanced bgv
        JOIN pois p ON bgv.ID_STORE = p.ID_STORE
        JOIN bg bgp ON p.POI_GEOID = bgp.GEOID
        JOIN bg bgh ON bgv.HOME_GEOID = bgh.GEOID
        {limit_snippet}
    """
    df = con.sql(query).pl()
    return df


def entropy_segregation_sql(n_groups: int) -> str:
    return f"""
        1.0
        + SUM(TAU * LN(TAU)) / LN({n_groups})
    """


def l1_segregation_sql(n_groups: int) -> str:
    expected_share = 1 / n_groups
    normalization = n_groups / (2 * (n_groups - 1))

    return f"""
        {normalization} * (
            SUM(ABS(TAU - {expected_share}))
            + ({n_groups} - COUNT(HOME_INCOME_GROUP)) * {expected_share}
        )
    """


def get_daily_segregation(
    con: DuckDBPyConnection,
    n_income_groups: int = 4,
    segregation_expression: str = "l1",
) -> pl.DataFrame:
    if segregation_expression == "entropy":
        segregation_sql = entropy_segregation_sql(n_income_groups)
    elif segregation_expression == "l1":
        segregation_sql = l1_segregation_sql(n_income_groups)
    else:
        raise ValueError(f"Unknown segregation expression: {segregation_expression}")

    query = f"""
        WITH bg AS (
            SELECT
                GEOID,
                CBSAFP,
                CBSA_NAME,
                NTILE({n_income_groups}) OVER (
                    PARTITION BY CBSAFP
                    ORDER BY MEDIAN_HH_INCOME
                ) AS INCOME_GROUP
            FROM block_groups_cbsa
            WHERE LSAD = 'M1'
              AND MEDIAN_HH_INCOME IS NOT NULL
        ),

        source AS (
            SELECT
                bgp.CBSAFP,
                bgp.CBSA_NAME,
                bgv.ID_STORE,
                bgv.DATE_RANGE_START,
                bgh.INCOME_GROUP AS HOME_INCOME_GROUP,
                bgv.VISITOR_COUNTS,
                bgv.DIST
            FROM block_group_visits_enhanced AS bgv
            INNER JOIN pois AS p
                ON bgv.ID_STORE = p.ID_STORE
            INNER JOIN bg AS bgp
                ON p.POI_GEOID = bgp.GEOID
            INNER JOIN bg AS bgh
                ON bgv.HOME_GEOID = bgh.GEOID
            WHERE bgv.VISITOR_COUNTS > 0
        ),

        group_visitors AS (
            SELECT
                CBSAFP,
                CBSA_NAME,
                ID_STORE,
                DATE_RANGE_START,
                HOME_INCOME_GROUP,
                SUM(VISITOR_COUNTS) AS GROUP_VISITORS
            FROM source
            GROUP BY
                CBSAFP,
                CBSA_NAME,
                ID_STORE,
                DATE_RANGE_START,
                HOME_INCOME_GROUP
        ),

        visitor_distribution AS (
            SELECT
                CBSAFP,
                CBSA_NAME,
                ID_STORE,
                DATE_RANGE_START,
                HOME_INCOME_GROUP,
                GROUP_VISITORS,

                SUM(GROUP_VISITORS) OVER (
                    PARTITION BY
                        CBSAFP,
                        ID_STORE,
                        DATE_RANGE_START
                ) AS TOTAL_VISITORS,

                GROUP_VISITORS
                    / SUM(GROUP_VISITORS) OVER (
                        PARTITION BY
                            CBSAFP,
                            ID_STORE,
                            DATE_RANGE_START
                    ) AS TAU

            FROM group_visitors
        ),

        poi_segregation AS (
            SELECT
                CBSAFP,
                CBSA_NAME,
                ID_STORE,
                DATE_RANGE_START,
                MAX(TOTAL_VISITORS) AS TOTAL_VISITORS,
                {segregation_sql} AS INCOME_SEGREGATION
            FROM visitor_distribution
            GROUP BY
                CBSAFP,
                CBSA_NAME,
                ID_STORE,
                DATE_RANGE_START
        ),

        poi_distance AS (
            SELECT
                CBSAFP,
                ID_STORE,
                DATE_RANGE_START,

                SUM(DIST * VISITOR_COUNTS)
                    FILTER (WHERE DIST IS NOT NULL)
                    / NULLIF(
                        SUM(VISITOR_COUNTS)
                            FILTER (WHERE DIST IS NOT NULL),
                        0
                    ) AS DIST

            FROM source
            GROUP BY
                CBSAFP,
                ID_STORE,
                DATE_RANGE_START
        ),

        poi_daily AS (
            SELECT
                s.CBSAFP,
                s.CBSA_NAME,
                s.ID_STORE,
                s.DATE_RANGE_START,
                s.TOTAL_VISITORS,
                s.INCOME_SEGREGATION,
                d.DIST
            FROM poi_segregation AS s
            LEFT JOIN poi_distance AS d
                ON s.CBSAFP = d.CBSAFP
               AND s.ID_STORE = d.ID_STORE
               AND s.DATE_RANGE_START = d.DATE_RANGE_START
        )

        SELECT
            CBSAFP,
            CBSA_NAME,
            DATE_RANGE_START,

            COUNT(ID_STORE) AS N_POIS,

            AVG(TOTAL_VISITORS) AS AVG_VISITORS,

            AVG(INCOME_SEGREGATION)
                AS AVG_INCOME_SEGREGATION,

            SUM(INCOME_SEGREGATION * TOTAL_VISITORS)
                / NULLIF(SUM(TOTAL_VISITORS), 0)
                AS W_AVG_INCOME_SEGREGATION,

            AVG(DIST) AS AVG_DIST,

            SUM(DIST * TOTAL_VISITORS)
                FILTER (WHERE DIST IS NOT NULL)
                / NULLIF(
                    SUM(TOTAL_VISITORS)
                        FILTER (WHERE DIST IS NOT NULL),
                    0
                ) AS W_AVG_DIST

        FROM poi_daily
        GROUP BY
            CBSAFP,
            CBSA_NAME,
            DATE_RANGE_START
        ORDER BY
            CBSAFP,
            DATE_RANGE_START
    """

    return con.sql(query).pl()
