CREATE OR REPLACE TABLE cbsa_geo AS
    SELECT * FROM ST_Read('data/tl_2025_us_cbsa/tl_2025_us_cbsa.shp');

CREATE OR REPLACE TABLE cbsa_counties AS
    SELECT
        "CBSA Code"                                          AS CBSAFP,
        "CBSA Title"                                         AS CBSA_TITLE,
        CASE "Metropolitan/Micropolitan Statistical Area"
            WHEN 'Metropolitan Statistical Area'  THEN 'Metropolitan'
            WHEN 'Micropolitan Statistical Area'  THEN 'Micropolitan'
        END                                                  AS CBSA_TYPE,
        "CSA Code"                                           AS CSAFP,
        "CSA Title"                                          AS CSA_TITLE,
        "FIPS State Code"                                    AS STATEFP,
        "FIPS County Code"                                   AS COUNTYFP,
        "FIPS State Code" || "FIPS County Code"              AS COUNTY_GEOID,
        "County/County Equivalent"                           AS COUNTY_NAME,
        "Central/Outlying County" = 'Central'                AS IS_CENTRAL_COUNTY
    FROM read_xlsx('data/list1_2023.xlsx', range = 'A3:L2000', header = true, all_varchar = true)
    WHERE "CBSA Code" SIMILAR TO '[0-9]{5}';   -- drops footnote rows

CREATE OR REPLACE TABLE cbsa_estimates AS
    SELECT CBSA AS CBSAFP, POPESTIMATE2025 AS POP_2025, POPESTIMATE2024 AS POP_2024
    FROM read_csv('data/cbsa-est2025-alldata.csv',
                  encoding = 'latin-1', header = true,
                  types = {'CBSA': 'VARCHAR'})
    WHERE LSAD IN ('Metropolitan Statistical Area', 'Micropolitan Statistical Area');

CREATE OR REPLACE TABLE cbsa AS
    WITH cbsas AS (
        SELECT DISTINCT
            CBSAFP, NAME AS CBSA_NAME,
            CSAFP, NAMELSAD AS CSA_NAME,
            LSAD, geom AS GEOM
        FROM cbsa_geo
    )
    SELECT
        c.*,
        e.POP_2025,
        RANK() OVER (PARTITION BY c.LSAD ORDER BY e.POP_2025 DESC) AS POP_RANK_IN_TYPE
    FROM cbsas c
    LEFT JOIN cbsa_estimates e USING (CBSAFP);

CREATE OR REPLACE VIEW cbsa_top AS
    SELECT *
    FROM cbsa
    WHERE POP_RANK_IN_TYPE <= 100
      AND LSAD = 'M1';
