CREATE OR REPLACE TABLE block_groups_raw AS
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

CREATE INDEX bg_geom_idx ON block_groups USING RTREE (geom);
CREATE INDEX idx_bg_geoid ON block_groups(GEOID);

CREATE OR REPLACE TABLE median_household_income AS
    SELECT *
    FROM 'data/acs-5-year-median-household-income/*.parquet';

CREATE OR REPLACE TABLE metropolitan_statistical_areas AS
    SELECT DISTINCT
        "MSA Code" AS MSA_CODE,
        "MSA Title" AS MSA_NAME,
        "County Code" AS COUNTY_CODE,
        SUBSTR("County Code", 3, 3) AS COUNTYFP,
        SUBSTR("County Code", 1, 2) AS STATEFP,
        "County Title" AS COUNTY_NAME
    FROM Read_xlsx('data/qcew-county-msa-csa-crosswalk.xlsx', sheet = 'Jul. 2023 Crosswalk');

CREATE OR REPLACE TABLE block_groups AS
    WITH mhi AS (
        SELECT GEOID, MEDIAN_HH_INCOME, MEDIAN_HH_INCOME_MOE
        FROM median_household_income
        WHERE YEAR_END = 2024
    )
    SELECT
        bg.GEOID,
        bg.OGC_FID, bg.STATEFP, bg.COUNTYFP,
        msa.MSA_CODE, msa.MSA_NAME,
        mhi.MEDIAN_HH_INCOME, mhi.MEDIAN_HH_INCOME_MOE,
        geom AS GEOM
    FROM block_groups_raw bg
    LEFT JOIN metropolitan_statistical_areas msa ON bg.COUNTYFP = msa.COUNTYFP AND bg.STATEFP = msa.STATEFP
    LEFT JOIN mhi ON bg.GEOID = mhi.GEOID;
