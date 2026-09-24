-- Load spatial extension first
-- INSTALL spatial;
-- LOAD spatial;

CREATE OR REPLACE TABLE block_groups AS
    SELECT * FROM ST_Read('data/shps/tl_2025_04_bg/tl_2025_04_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/shps/tl_2025_06_bg/tl_2025_06_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/shps/tl_2025_12_bg/tl_2025_12_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/shps/tl_2025_15_bg/tl_2025_15_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/shps/tl_2025_36_bg/tl_2025_36_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/shps/tl_2025_48_bg/tl_2025_48_bg.shp');

CREATE TABLE IF NOT EXISTS lol AS
    WITH t AS (
        SELECT *, ST_Point(LONGITUDE, LATITUDE) AS GEOM
        FROM 'data/2025-weekly-patterns-plus/*.parquet'
        WHERE DATE_RANGE_START <= date'2025-02-01'
    )
    SELECT DISTINCT t.*
    FROM t
    JOIN block_groups bg
      ON bg.geom && t.GEOM
     AND ST_Within(t.GEOM, bg.geom);
