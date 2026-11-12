CREATE OR REPLACE TABLE visits AS
SELECT ID_STORE, DATE_RANGE_START, DATE_RANGE_END, VISITOR_COUNTS, VISITOR_HOME_CBGS
FROM read_parquet(
    'data/filtered-wpp/visits/*/*.parquet',
    union_by_name=false,
    hive_partitioning=true,
    hive_types = {'DATE_RANGE_START': 'TIMESTAMP'}
)
ORDER BY DATE_RANGE_START, ID_STORE;

CREATE OR REPLACE TABLE block_group_visits AS
WITH src AS (
    SELECT
      DATE_RANGE_START, DATE_RANGE_END,
      ID_STORE,
      unnest(VISITOR_HOME_CBGS) AS v
    FROM visits
)
SELECT
    DATE_RANGE_START, DATE_RANGE_END,
    src.ID_STORE,
    v.cbg      AS HOME_GEOID,
    v.visitors AS VISITOR_COUNTS
FROM src
JOIN pois p ON src.ID_STORE = p.ID_STORE
JOIN block_groups bg ON src.v.cbg = bg.GEOID
WHERE p.CBSAFP = bg.CBSAFP
ORDER BY DATE_RANGE_START, ID_STORE, HOME_GEOID;

CREATE OR REPLACE TABLE poi_home_dist AS
SELECT pr.ID_STORE, pr.HOME_GEOID, ST_Distance_Sphere(p.GEOM, b.CENTROID) AS DIST
FROM (SELECT DISTINCT ID_STORE, HOME_GEOID FROM block_group_visits) pr
JOIN pois p          USING (ID_STORE)
JOIN block_groups b  ON b.GEOID = pr.HOME_GEOID;

CREATE OR REPLACE TABLE block_group_visits_enhanced AS
SELECT v.*, d.DIST
FROM block_group_visits v
LEFT JOIN poi_home_dist d USING (ID_STORE, HOME_GEOID);
