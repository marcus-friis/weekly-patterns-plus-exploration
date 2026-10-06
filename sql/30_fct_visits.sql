CREATE OR REPLACE TABLE visits AS
SELECT
    ID_STORE, DATE_RANGE_START, DATE_RANGE_END,
    VISITOR_COUNTS, VISIT_COUNTS, VISITS_BY_DAY, VISITS_BY_EACH_HOUR,
    DISTANCE_FROM_HOME, MEDIAN_DWELL
FROM read_parquet('data/2025-weekly-patterns-plus/*.parquet', union_by_name=false)
WHERE MSA_CODE::VARCHAR IN (SELECT CBSAFP FROM cbsa_top)
ORDER BY DATE_RANGE_START, ID_STORE;

CREATE OR REPLACE TABLE block_group_visits AS

WITH source AS (
    SELECT
        ID_STORE,
        MSA_CODE::VARCHAR AS POI_CBSAFP,
        DATE_RANGE_START,
        DATE_RANGE_END,
        CAST(
            VISITOR_HOME_CBGS::JSON
            AS MAP(VARCHAR, INTEGER)
        ) AS M
    FROM read_parquet(
        'data/2025-weekly-patterns-plus/*.parquet',
        union_by_name = false
    )
    WHERE MSA_CODE::VARCHAR IN (
        SELECT CBSAFP
        FROM cbsa_top
    )
),

unnested AS (
    SELECT
        UNNEST(map_keys(M)) AS HOME_GEOID,
        ID_STORE,
        POI_CBSAFP,
        DATE_RANGE_START,
        DATE_RANGE_END,
        UNNEST(map_values(M)) AS VISITOR_COUNTS
    FROM source
)

SELECT
    u.HOME_GEOID,
    u.ID_STORE,
    u.DATE_RANGE_START,
    u.DATE_RANGE_END,
    u.VISITOR_COUNTS
FROM unnested u
JOIN block_groups bg
    ON u.HOME_GEOID = bg.GEOID
   AND u.POI_CBSAFP = bg.CBSAFP
ORDER BY
    u.DATE_RANGE_START,
    u.HOME_GEOID,
    u.ID_STORE;

CREATE OR REPLACE TABLE block_group_visits_enhanced AS
SELECT
    bgv.DATE_RANGE_START,
    bgv.DATE_RANGE_END,
    bgv.HOME_GEOID,
    bgv.ID_STORE,
    bgv.VISITOR_COUNTS,
    ST_Distance_Sphere(p.GEOM, hbg.CENTROID) AS DIST
FROM block_group_visits bgv
JOIN pois p                   ON bgv.ID_STORE   = p.ID_STORE
LEFT JOIN block_groups_cbsa hbg ON bgv.HOME_GEOID = hbg.GEOID
ORDER BY bgv.DATE_RANGE_START, bgv.HOME_GEOID, bgv.ID_STORE;
