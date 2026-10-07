CREATE OR REPLACE TABLE prism_t_daily AS
SELECT
    CELL_ID,
    DATE::DATE AS DATE,
    TMEAN,
    TMIN,
    TMAX
FROM read_parquet(
    'data/prism/daily/*.parquet'
)
WHERE TMEAN IS NOT NULL
ORDER BY DATE, CELL_ID;

CREATE TABLE cbsa_t_daily AS
SELECT
    cpc.CBSAFP,
    t.DATE,
    SUM(t.TMEAN * cpc.INTERSECTION_AREA) / SUM(cpc.INTERSECTION_AREA) AS AVG_TMEAN
FROM cbsa_prism_cells cpc
JOIN cbsa ON cpc.CBSAFP = cbsa.CBSAFP
JOIN prism_t_daily t ON cpc.CELL_ID = t.CELL_ID
GROUP BY cpc.CBSAFP, t.DATE
ORDER BY t.DATE, cpc.CBSAFP;

CREATE TABLE block_group_t_daily AS
SELECT
    bgpc.GEOID,
    t.DATE,
    SUM(t.TMEAN * bgpc.INTERSECTION_AREA) / SUM(bgpc.INTERSECTION_AREA) AS AVG_TMEAN
FROM block_group_prism_cells bgpc
JOIN block_groups bg ON bgpc.GEOID = bg.GEOID
JOIN prism_tmean_daily t ON bgpc.CELL_ID = t.CELL_ID
GROUP BY bgpc.GEOID, t.DATE
ORDER BY t.DATE, bgpc.GEOID;
