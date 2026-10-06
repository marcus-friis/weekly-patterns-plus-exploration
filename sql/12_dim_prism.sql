CREATE OR REPLACE TABLE prism_cells AS
SELECT DISTINCT
    ROW,
    COL,
    ROW::VARCHAR || '_' || COL::VARCHAR AS CELL_ID,
    geometry AS GEOM
FROM read_parquet(
    'data/prism/tmean_daily_2025_parquet/*.parquet'
);

CREATE INDEX prism_cells_geom_idx
ON prism_cells
USING RTREE (GEOM);


CREATE OR REPLACE TABLE prism_tmean_daily AS
SELECT
    ROW::VARCHAR || '_' || COL::VARCHAR AS CELL_ID,
    DATE::DATE AS DATE,
    TMEAN
FROM read_parquet(
    'data/prism/tmean_daily_2025_parquet/*.parquet'
)
WHERE TMEAN IS NOT NULL
ORDER BY DATE, CELL_ID;
