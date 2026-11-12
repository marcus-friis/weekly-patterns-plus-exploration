CREATE OR REPLACE TABLE pois AS
WITH p AS (
    SELECT DISTINCT
        ID_STORE, POI_CBG AS POI_GEOID, MSA_CODE::VARCHAR AS CBSAFP,
        BRAND, LOCATION_NAME,
        STREET_ADDRESS, CITY, REGION, ISO_COUNTRY_CODE,
        NAICS_CODE, TOP_CATEGORY, SUB_CATEGORY,
        OPEN_DATE, CLOSE_DATE,
        LONGITUDE, LATITUDE,
        ST_Transform(
            ST_Point(LONGITUDE, LATITUDE)::GEOMETRY('EPSG:4326'),
            'EPSG:4326', 'EPSG:4269'
        )::GEOMETRY('EPSG:4269') AS GEOM
    FROM read_parquet('data/filtered-wpp/pois/*/*.parquet', union_by_name=false)
    ORDER BY ID_STORE
)
SELECT p.*, pc.CELL_ID AS CELL_ID
FROM p
LEFT JOIN prism_cells pc
  ON ST_Intersects(ST_Transform(p.GEOM, 'EPSG:4326', 'EPSG:4269'), pc.GEOM);
