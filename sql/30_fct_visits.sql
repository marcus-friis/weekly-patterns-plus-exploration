CREATE OR REPLACE TABLE visits AS
SELECT
    ID_STORE, DATE_RANGE_START, DATE_RANGE_END,
    VISITOR_COUNTS, VISIT_COUNTS, VISITS_BY_DAY, VISITS_BY_EACH_HOUR,
    DISTANCE_FROM_HOME, MEDIAN_DWELL
FROM read_parquet('data/2025-weekly-patterns-plus/*.parquet', union_by_name=false);

CREATE OR REPLACE TABLE block_group_visits AS
SELECT
     UNNEST(map_keys(M)) AS HOME_GEOID,
     ID_STORE,
     DATE_RANGE_START, DATE_RANGE_END,
     UNNEST(map_values(M)) AS VISITOR_COUNTS
FROM (
     SELECT *, CAST(VISITOR_HOME_CBGS::JSON AS MAP(VARCHAR, INTEGER)) AS M
     FROM read_parquet('data/2025-weekly-patterns-plus/*.parquet', union_by_name=false)
);

-- focused only on top 50 metropolitan statistic areas
CREATE OR REPLACE TABLE block_group_visit_dist AS
    WITH cbsa_filter AS (
        SELECT GEOID, CENTROID
        FROM block_groups_cbsa
        WHERE CBSA_TYPE = 'Metropolitan'
        AND CBSA_POP_RANK <= 50
    )
    SELECT bgv.*, ST_Distance_Sphere(p.GEOM, cbsa_filter.CENTROID) AS DIST
    FROM block_group_visits bgv
    JOIN cbsa_filter ON bgv.HOME_GEOID = cbsa_filter.GEOID
    JOIN pois p ON bgv.ID_STORE = p.ID_STORE;
