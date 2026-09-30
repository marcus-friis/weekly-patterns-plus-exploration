CREATE OR REPLACE TABLE block_groups_geo AS
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_01_bg/tl_2025_01_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_02_bg/tl_2025_02_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_04_bg/tl_2025_04_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_05_bg/tl_2025_05_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_06_bg/tl_2025_06_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_08_bg/tl_2025_08_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_09_bg/tl_2025_09_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_10_bg/tl_2025_10_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_11_bg/tl_2025_11_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_12_bg/tl_2025_12_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_13_bg/tl_2025_13_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_15_bg/tl_2025_15_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_16_bg/tl_2025_16_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_17_bg/tl_2025_17_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_18_bg/tl_2025_18_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_19_bg/tl_2025_19_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_20_bg/tl_2025_20_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_21_bg/tl_2025_21_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_22_bg/tl_2025_22_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_23_bg/tl_2025_23_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_24_bg/tl_2025_24_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_25_bg/tl_2025_25_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_26_bg/tl_2025_26_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_27_bg/tl_2025_27_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_28_bg/tl_2025_28_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_29_bg/tl_2025_29_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_30_bg/tl_2025_30_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_31_bg/tl_2025_31_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_32_bg/tl_2025_32_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_33_bg/tl_2025_33_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_34_bg/tl_2025_34_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_35_bg/tl_2025_35_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_36_bg/tl_2025_36_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_37_bg/tl_2025_37_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_38_bg/tl_2025_38_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_39_bg/tl_2025_39_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_40_bg/tl_2025_40_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_41_bg/tl_2025_41_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_42_bg/tl_2025_42_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_44_bg/tl_2025_44_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_45_bg/tl_2025_45_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_46_bg/tl_2025_46_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_47_bg/tl_2025_47_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_48_bg/tl_2025_48_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_49_bg/tl_2025_49_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_50_bg/tl_2025_50_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_51_bg/tl_2025_51_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_53_bg/tl_2025_53_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_54_bg/tl_2025_54_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_55_bg/tl_2025_55_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_56_bg/tl_2025_56_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_60_bg/tl_2025_60_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_66_bg/tl_2025_66_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_69_bg/tl_2025_69_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_72_bg/tl_2025_72_bg.shp')
    UNION ALL BY NAME
    SELECT * FROM ST_Read('data/tiger2025_bg/tl_2025_78_bg/tl_2025_78_bg.shp');

CREATE OR REPLACE TABLE median_household_income AS
    SELECT *
    FROM 'data/acs-5-year-median-household-income/*.parquet';

CREATE OR REPLACE TABLE block_groups AS
    WITH mhi AS (
        SELECT GEOID, MEDIAN_HH_INCOME, MEDIAN_HH_INCOME_MOE
        FROM median_household_income
        WHERE YEAR_END = 2024
    )
    SELECT
        bg.GEOID, bg.OGC_FID, bg.STATEFP, bg.COUNTYFP, bg.ALAND,
        cc.CBSAFP, cc.CSAFP,
        mhi.MEDIAN_HH_INCOME, mhi.MEDIAN_HH_INCOME_MOE,
        bg.GEOM AS GEOM,
        ST_Centroid(bg.GEOM) AS CENTROID
    FROM block_groups_geo bg
    LEFT JOIN cbsa_counties cc USING (STATEFP, COUNTYFP)
    LEFT JOIN mhi USING (GEOID);

CREATE INDEX bg_geom_idx ON block_groups USING RTREE (geom);

CREATE OR REPLACE VIEW block_groups_cbsa AS
SELECT bg.*, c.CBSA_NAME, c.LSAD, c.CSA_NAME, c.POP_2025 AS CBSA_POP_2025, c.POP_RANK_IN_TYPE AS CBSA_POP_RANK
FROM block_groups bg
LEFT JOIN cbsa c USING (CBSAFP);
