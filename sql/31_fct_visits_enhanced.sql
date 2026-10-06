-- 1. Daily area-weighted home block-group temperature
-- ============================================================

CREATE OR REPLACE TEMP TABLE block_group_temperature_daily AS
SELECT
    bpc.GEOID,
    t.DATE,

    SUM(bpc.BG_WEIGHT * t.TMEAN)
        / NULLIF(SUM(bpc.BG_WEIGHT), 0) AS TMEAN,

    SUM(bpc.BG_WEIGHT * t.TMIN)
        / NULLIF(SUM(bpc.BG_WEIGHT), 0) AS TMIN,

    SUM(bpc.BG_WEIGHT * t.TMAX)
        / NULLIF(SUM(bpc.BG_WEIGHT), 0) AS TMAX

FROM block_group_prism_cells bpc

JOIN prism_t_daily t
    USING (CELL_ID)

GROUP BY
    bpc.GEOID,
    t.DATE

ORDER BY
    bpc.GEOID,
    t.DATE;


-- ============================================================
-- 2. Map each POI to one PRISM cell
-- ============================================================

CREATE OR REPLACE TEMP TABLE poi_prism_cells AS
SELECT
    ID_STORE,
    CELL_ID
FROM (
    SELECT
        p.ID_STORE,
        pc.CELL_ID,

        ROW_NUMBER() OVER (
            PARTITION BY p.ID_STORE
            ORDER BY pc.CELL_ID
        ) AS RN

    FROM pois p

    JOIN prism_cells pc
        ON ST_Intersects(
            pc.GEOM,
            ST_Transform(
                p.GEOM,
                'EPSG:4326',
                'EPSG:4269',
                always_xy := true
            )
        )
)
WHERE RN = 1;


-- ============================================================
-- 3. Daily POI temperature
-- ============================================================

CREATE OR REPLACE TEMP TABLE poi_temperature_daily AS
SELECT
    ppc.ID_STORE,
    t.DATE,
    t.TMEAN,
    t.TMIN,
    t.TMAX

FROM poi_prism_cells ppc

JOIN prism_t_daily t
    USING (CELL_ID)

ORDER BY
    ppc.ID_STORE,
    t.DATE;


-- ============================================================
-- 4. Unique block-group/week combinations
-- ============================================================

CREATE OR REPLACE TEMP TABLE block_group_visit_weeks AS
SELECT DISTINCT
    HOME_GEOID,
    DATE_RANGE_START,
    DATE_RANGE_END
FROM block_group_visits;


-- ============================================================
-- 5. Unique POI/week combinations
-- ============================================================

CREATE OR REPLACE TEMP TABLE poi_visit_weeks AS
SELECT DISTINCT
    ID_STORE,
    DATE_RANGE_START,
    DATE_RANGE_END
FROM block_group_visits;


-- ============================================================
-- 6. Weekly home block-group temperature
--
-- TMEAN = average daily mean temperature
-- TMIN  = average daily minimum temperature
-- TMAX  = average daily maximum temperature
--
-- DATE_RANGE_END is treated as exclusive.
-- ============================================================

CREATE OR REPLACE TEMP TABLE block_group_temperature_weekly AS
SELECT
    w.HOME_GEOID,
    w.DATE_RANGE_START,
    w.DATE_RANGE_END,

    AVG(t.TMEAN) AS HOME_TMEAN,
    AVG(t.TMIN)  AS HOME_TMIN,
    AVG(t.TMAX)  AS HOME_TMAX,

    COUNT(t.DATE) AS HOME_TEMP_DAYS

FROM block_group_visit_weeks w

JOIN block_group_temperature_daily t
    ON w.HOME_GEOID = t.GEOID
   AND t.DATE >= w.DATE_RANGE_START
   AND t.DATE <  w.DATE_RANGE_END

GROUP BY
    w.HOME_GEOID,
    w.DATE_RANGE_START,
    w.DATE_RANGE_END

ORDER BY
    w.HOME_GEOID,
    w.DATE_RANGE_START;


-- ============================================================
-- 7. Weekly POI temperature
-- ============================================================

CREATE OR REPLACE TEMP TABLE poi_temperature_weekly AS
SELECT
    w.ID_STORE,
    w.DATE_RANGE_START,
    w.DATE_RANGE_END,

    AVG(t.TMEAN) AS POI_TMEAN,
    AVG(t.TMIN)  AS POI_TMIN,
    AVG(t.TMAX)  AS POI_TMAX,

    COUNT(t.DATE) AS POI_TEMP_DAYS

FROM poi_visit_weeks w

JOIN poi_temperature_daily t
    ON w.ID_STORE = t.ID_STORE
   AND t.DATE >= w.DATE_RANGE_START
   AND t.DATE <  w.DATE_RANGE_END

GROUP BY
    w.ID_STORE,
    w.DATE_RANGE_START,
    w.DATE_RANGE_END

ORDER BY
    w.ID_STORE,
    w.DATE_RANGE_START;


-- ============================================================
-- 8. Final enhanced visit table
-- ============================================================

CREATE OR REPLACE TABLE block_group_visits_enhanced AS
SELECT
    bgv.DATE_RANGE_START,
    bgv.DATE_RANGE_END,
    bgv.HOME_GEOID,
    bgv.ID_STORE,
    bgv.VISITOR_COUNTS,

    ST_Distance_Sphere(
        p.GEOM,
        hbg.CENTROID
    ) AS DIST,

    pt.POI_TMEAN,
    pt.POI_TMIN,
    pt.POI_TMAX,

    ht.HOME_TMEAN,
    ht.HOME_TMIN,
    ht.HOME_TMAX,

    pt.POI_TMEAN - ht.HOME_TMEAN AS TMEAN_DIFF,
    pt.POI_TMIN  - ht.HOME_TMIN  AS TMIN_DIFF,
    pt.POI_TMAX  - ht.HOME_TMAX  AS TMAX_DIFF,

    pt.POI_TEMP_DAYS,
    ht.HOME_TEMP_DAYS

FROM block_group_visits bgv

JOIN pois p
    ON bgv.ID_STORE = p.ID_STORE

LEFT JOIN block_groups hbg
    ON bgv.HOME_GEOID = hbg.GEOID

LEFT JOIN poi_temperature_weekly pt
    ON bgv.ID_STORE = pt.ID_STORE
   AND bgv.DATE_RANGE_START = pt.DATE_RANGE_START
   AND bgv.DATE_RANGE_END = pt.DATE_RANGE_END

LEFT JOIN block_group_temperature_weekly ht
    ON bgv.HOME_GEOID = ht.HOME_GEOID
   AND bgv.DATE_RANGE_START = ht.DATE_RANGE_START
   AND bgv.DATE_RANGE_END = ht.DATE_RANGE_END

ORDER BY
    bgv.DATE_RANGE_START,
    bgv.HOME_GEOID,
    bgv.ID_STORE;
