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

CREATE OR REPLACE TABLE cbsa_geo AS
    SELECT * FROM ST_Read('data/tl_2025_us_cbsa/tl_2025_us_cbsa.shp');

CREATE OR REPLACE TABLE median_household_income AS
    SELECT *
    FROM 'data/acs-5-year-median-household-income/*.parquet';

CREATE OR REPLACE TABLE cbsa_counties AS
    SELECT
        "CBSA Code"                                          AS CBSA_CODE,
        "CBSA Title"                                         AS CBSA_TITLE,
        CASE "Metropolitan/Micropolitan Statistical Area"
            WHEN 'Metropolitan Statistical Area'  THEN 'Metropolitan'
            WHEN 'Micropolitan Statistical Area'  THEN 'Micropolitan'
        END                                                  AS CBSA_TYPE,
        "CSA Code"                                           AS CSA_CODE,
        "CSA Title"                                          AS CSA_TITLE,
        "FIPS State Code"                                    AS STATEFP,
        "FIPS County Code"                                   AS COUNTYFP,
        "FIPS State Code" || "FIPS County Code"              AS COUNTY_GEOID,
        "County/County Equivalent"                           AS COUNTY_NAME,
        "Central/Outlying County" = 'Central'                AS IS_CENTRAL_COUNTY
    FROM read_xlsx('data/list1_2023.xlsx', range = 'A3:L2000', header = true, all_varchar = true)
    WHERE "CBSA Code" SIMILAR TO '[0-9]{5}';   -- drops footnote rows

CREATE OR REPLACE TABLE cbsa AS
    WITH est AS (
        SELECT CBSA AS CBSA_CODE, POPESTIMATE2025 AS POP_2025
        FROM read_csv('data/cbsa-est2025-alldata.csv',
                      encoding = 'latin-1', header = true,
                      types = {'CBSA': 'VARCHAR'})
        WHERE LSAD IN ('Metropolitan Statistical Area', 'Micropolitan Statistical Area')
    ),
    cbsas AS (
        SELECT DISTINCT CBSA_CODE, CBSA_TITLE, CBSA_TYPE, CSA_CODE, CSA_TITLE
        FROM cbsa_counties
    )
    SELECT
        c.*,
        e.POP_2025,
        RANK() OVER (PARTITION BY c.CBSA_TYPE ORDER BY e.POP_2025 DESC) AS POP_RANK_IN_TYPE
    FROM cbsas c
    LEFT JOIN est e USING (CBSA_CODE);

CREATE OR REPLACE TABLE block_groups AS
    WITH mhi AS (
        SELECT GEOID, MEDIAN_HH_INCOME, MEDIAN_HH_INCOME_MOE
        FROM median_household_income
        WHERE YEAR_END = 2024
    )
    SELECT
        bg.GEOID, bg.OGC_FID, bg.STATEFP, bg.COUNTYFP, bg.ALAND,
        cc.CBSA_CODE,
        mhi.MEDIAN_HH_INCOME, mhi.MEDIAN_HH_INCOME_MOE,
        bg.GEOM,
        ST_Centroid(bg.GEOM) AS CENTROID
    FROM block_groups_raw bg
    LEFT JOIN cbsa_counties cc USING (STATEFP, COUNTYFP)
    LEFT JOIN mhi USING (GEOID);

CREATE INDEX bg_geom_idx ON block_groups USING RTREE (geom);

CREATE OR REPLACE VIEW block_groups_cbsa AS
SELECT bg.*, c.CBSA_TITLE, c.CBSA_TYPE, c.POP_2025 AS CBSA_POP_2025, c.POP_RANK_IN_TYPE AS CBSA_POP_RANK
FROM block_groups bg
LEFT JOIN cbsa c USING (CBSA_CODE);
