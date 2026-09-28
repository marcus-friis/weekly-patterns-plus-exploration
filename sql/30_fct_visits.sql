CREATE TABLE IF NOT EXISTS visits AS
SELECT
    ID_STORE, DATE_RANGE_START, DATE_RANGE_END,
    VISITOR_COUNTS, VISIT_COUNTS, VISITS_BY_DAY, VISITS_BY_EACH_HOUR,
    DISTANCE_FROM_HOME, MEDIAN_DWELL
FROM read_parquet('data/2025-weekly-patterns-plus/*.parquet', union_by_name=false);

CREATE TABLE IF NOT EXISTS block_group_visits AS
SELECT
     ID_STORE,
     DATE_RANGE_START, DATE_RANGE_END,
     UNNEST(map_keys(M)) AS HOME_GEOID,
     UNNEST(map_values(M)) AS VISITOR_COUNT
FROM (
     SELECT *, CAST(VISITOR_HOME_CBGS::JSON AS MAP(VARCHAR, INTEGER)) AS M
     FROM read_parquet('data/2025-weekly-patterns-plus/*.parquet', union_by_name=false)
);
