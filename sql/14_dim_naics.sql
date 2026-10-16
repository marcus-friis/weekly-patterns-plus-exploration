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
