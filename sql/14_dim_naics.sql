CREATE TABLE naics AS
SELECT
    "Seq. No." AS seq_num,
    "2022 NAICS US   Code" AS NAICS_CODE,
    "2022 NAICS US Title" AS NAICS_TITLE
FROM read_xlsx(
    'data/2-6 digit_2022_Codes.xlsx',
    sheet = 'tbl_2022_title_description_coun',
    range = 'A1:C',
    header = true,
    all_varchar = true
)
WHERE "Seq. No." IS NOT NULL;

CREATE OR REPLACE TABLE naics_categories AS
WITH classified AS (
    SELECT
        n.NAICS_CODE,
        n.NAICS_TITLE,

        CASE
            -- Schools
            WHEN n.NAICS_CODE IN ('611210', '611310')
                THEN 'Schools'

            -- Libraries
            WHEN n.NAICS_CODE = '519210'
                THEN 'Libraries'

            -- Museums + historical sites
            WHEN n.NAICS_CODE IN ('712110', '712120')
                THEN 'Museums_Historical'

            -- Parks + forests
            WHEN n.NAICS_CODE IN ('712130', '712190')
                THEN 'Parks_Forests'

            -- Restaurants
            WHEN n.NAICS_CODE IN ('722511', '722513', '722514')
                THEN 'Restaurants'

            -- Cafes & coffee shops
            WHEN n.NAICS_CODE = '722515'
                THEN 'Cafes_Coffee'

            -- Grocery stores
            WHEN n.NAICS_CODE LIKE '4451%'
                THEN 'Grocery_Stores'

            -- Specialty food stores
            WHEN n.NAICS_CODE LIKE '4452%'
              OR n.NAICS_CODE LIKE '4453%'
                THEN 'Specialty_Food'

            -- Clothing stores + etc.
            WHEN n.NAICS_CODE LIKE '45%'
                THEN 'Retail'

            -- Bars
            WHEN n.NAICS_CODE = '722410'
                THEN 'Bars'

            -- Public transportation
            WHEN n.NAICS_CODE IN (
                '482111',      -- rail
                '481111',      -- scheduled passenger air
                '481211'       -- charter air
            )
                THEN 'Public_Transportation'

            WHEN n.NAICS_CODE LIKE '485%'
                THEN 'Public_Transportation'

            ELSE NULL
        END AS CATEGORY
    FROM naics n
)

SELECT
    NAICS_CODE,
    NAICS_TITLE,
    CATEGORY
FROM classified
WHERE CATEGORY IS NOT NULL
  AND LENGTH(NAICS_CODE) = 6;
