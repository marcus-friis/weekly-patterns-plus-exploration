CREATE OR REPLACE TABLE prism_normals AS
SELECT
    CELL_ID,
    EXTRACT(MONTH FROM n.date) AS MONTH,
    EXTRACT(DAY FROM n.date) AS DAY,
    EXTRACT(DOY FROM n.date) AS DAY_OF_YEAR,
    EXTRACT(WEEK FROM n.date) AS WEEK_OF_YEAR,
    tmin AS TMIN,
    tmean AS TMEAN,
    tmax AS TMAX
FROM read_parquet('data/prism/prism_normals/*.parquet') n
JOIN prism_cells c ON n.ROW = c.ROW AND n.COL = C.COL
ORDER BY DATE, CELL_ID;

CREATE OR REPLACE TABLE prism_t_daily AS
WITH d AS (
    SELECT
        c.CELL_ID,
        date AS DATE,
        EXTRACT(MONTH FROM date) AS MONTH,
        EXTRACT(DAY FROM date) AS DAY,
        tmin AS TMIN,
        tmean AS TMEAN,
        tmax AS TMAX
    FROM read_parquet('data/prism/prism_daily/*.parquet') p
    JOIN prism_cells c
      ON p.ROW = c.ROW
     AND p.COL = c.COL
)
SELECT
    d.CELL_ID,
    d.DATE,
    d.TMIN,
    d.TMEAN,
    d.TMAX,
    n.TMIN AS TMIN_NORM,
    n.TMEAN AS TMEAN_NORM,
    n.TMAX AS TMAX_NORM
FROM d
LEFT JOIN prism_normals n
  ON d.CELL_ID = n.CELL_ID
 AND d.MONTH = n.MONTH
 AND d.DAY = n.DAY
ORDER BY d.DATE, d.CELL_ID;

CREATE OR REPLACE TABLE cbsa_t_daily AS
SELECT
    cpc.CBSAFP,
    t.DATE,
    SUM(t.TMEAN * cpc.INTERSECTION_AREA) / SUM(cpc.INTERSECTION_AREA) AS AVG_TMEAN
FROM cbsa_prism_cells cpc
JOIN cbsa ON cpc.CBSAFP = cbsa.CBSAFP
JOIN prism_t_daily t ON cpc.CELL_ID = t.CELL_ID
GROUP BY cpc.CBSAFP, t.DATE
ORDER BY t.DATE, cpc.CBSAFP;

CREATE OR REPLACE TABLE block_group_t_daily AS
SELECT
    bgpc.GEOID,
    t.DATE,
    SUM(t.TMEAN * bgpc.INTERSECTION_AREA) / SUM(bgpc.INTERSECTION_AREA) AS AVG_TMEAN
FROM block_group_prism_cells bgpc
JOIN block_groups bg ON bgpc.GEOID = bg.GEOID
JOIN prism_t_daily t ON bgpc.CELL_ID = t.CELL_ID
GROUP BY bgpc.GEOID, t.DATE
ORDER BY t.DATE, bgpc.GEOID;
