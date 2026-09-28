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

CREATE OR REPLACE TABLE block_group_visit_dist AS
WITH data AS (
    SELECT
        DATE_RANGE_START, HOME_GEOID,
        ST_Distance_Sphere(p.GEOM, bg.CENTROID) AS DIST,
        SUM(VISITOR_COUNTS) AS VISITOR_COUNTS
    FROM block_groups bg
    JOIN block_group_visits bgv ON bg.GEOID = bgv.HOME_GEOID
    JOIN pois p ON bgv.ID_STORE = p.ID_STORE
    GROUP BY 1, 2, 3
)
SELECT
    DATE_RANGE_START, HOME_GEOID,
    SUM(DIST * VISITOR_COUNTS) / SUM(VISITOR_COUNTS) AS AVG_DIST,
    SUM(VISITOR_COUNTS) AS VISITOR_COUNTS
FROM data
GROUP BY 1, 2;
