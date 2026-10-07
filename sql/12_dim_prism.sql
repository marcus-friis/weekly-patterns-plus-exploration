CREATE OR REPLACE TABLE prism_cells AS
SELECT
    CELL_ID,
    ROW,
    COL,
    GEOMETRY AS GEOM
FROM read_parquet('data/prism/prism_cells.parquet');
 
CREATE INDEX prism_cells_geom_idx
ON prism_cells
USING RTREE (GEOM);

CREATE OR REPLACE TABLE cbsa_prism_cells AS
SELECT
    cbsa.CBSAFP,
    pc.CELL_ID,
    ST_Area(ST_Intersection(cbsa.GEOM, pc.GEOM)) AS INTERSECTION_AREA,
    ST_Area(ST_Intersection(cbsa.GEOM, pc.GEOM))
        / ST_Area(cbsa.GEOM) AS CBSA_WEIGHT
FROM cbsa
JOIN prism_cells pc
    ON ST_Intersects(cbsa.GEOM, pc.GEOM)
WHERE ST_Area(ST_Intersection(cbsa.GEOM, pc.GEOM)) > 0;

CREATE OR REPLACE TABLE block_group_prism_cells AS
SELECT
    bg.GEOID,
    pc.CELL_ID,
    ST_Area(ST_Intersection(bg.GEOM, pc.GEOM)) AS INTERSECTION_AREA,
    ST_Area(ST_Intersection(bg.GEOM, pc.GEOM))
        / ST_Area(bg.GEOM) AS BG_WEIGHT
FROM block_groups bg
JOIN prism_cells pc
    ON ST_Intersects(bg.GEOM, pc.GEOM)
WHERE ST_Area(ST_Intersection(bg.GEOM, pc.GEOM)) > 0;
