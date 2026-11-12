import polars as pl

from wpp import data
from wpp.utils import project_root

ROOT = project_root()
DATA_DIR = ROOT / "data"

if __name__ == "__main__":
    data_path = DATA_DIR / "2025-weekly-patterns-plus"
    lf = data.load_weekly_patterns_plus_parquet(data_path)

    poi_cols = [
        "ID_STORE",
        "LOCATION_NAME",
        "BRAND",
        "NAICS_CODE",
        "TOP_CATEGORY",
        "SUB_CATEGORY",
        "MSA_CODE",
        "POI_CBG",
        "LONGITUDE",
        "LATITUDE",
        "STREET_ADDRESS",
        "CITY",
        "REGION",
        "ISO_COUNTRY_CODE",
        "OPEN_DATE",
        "CLOSE_DATE",
    ]
    fct_cols = [
        "ID_STORE",
        "DATE_RANGE_START",
        "DATE_RANGE_END",
        "VISITOR_COUNTS",
        "VISITOR_HOME_CBGS",
    ]
    msa_set = {35620, 33100, 40140}
    pair_re = r'"[^"]*"\s*:\s*-?\d+'
    filtered = (
        lf.filter(pl.col("MSA_CODE").is_in(msa_set))
        .with_columns(
            pl.col("VISITOR_HOME_CBGS")
            .str.extract_all(r"\d+\":")
            .list.len()
            .alias("VISITOR_NUM_HOMES"),
            pl.col("VISITOR_HOME_CBGS")
            .str.extract_all(r":\s*(-?\d+)")
            .list.eval(pl.element().str.extract(r"(-?\d+)").cast(pl.Int64))
            .list.sum()
            .alias("VISITOR_HOME_CBGS_SUM"),
        )
        .filter(
            pl.col("VISITOR_HOME_CBGS_SUM") >= 100, pl.col("VISITOR_NUM_HOMES") >= 10
        )
        .with_columns(pl.len().over("ID_STORE").alias("NUM_POI_WEEKS"))
        .filter(pl.col("NUM_POI_WEEKS") >= 52 / 2)
        .with_columns(
            pl.col("VISITOR_HOME_CBGS")
            .str.extract_all(pair_re)
            .list.eval(
                pl.struct(
                    cbg=pl.element().str.extract(r'"([^"]*)"'),
                    visitors=pl.element().str.extract(r":\s*(-?\d+)").cast(pl.Int64),
                )
            )
            .alias("VISITOR_HOME_CBGS")
        )
    )
    # print(filtered.head().collect())

    output_path = DATA_DIR / "filtered-wpp"
    pois_path = output_path / "pois"
    fct_path = output_path / "visits"
    pois_path.mkdir(parents=True, exist_ok=True)
    fct_path.mkdir(parents=True, exist_ok=True)

    filtered.select(fct_cols).sink_parquet(
        pl.PartitionBy(
            fct_path,
            key="DATE_RANGE_START",
        )
    )

    filtered.select(poi_cols).unique().sink_parquet(
        pl.PartitionBy(
            pois_path,
            key="MSA_CODE",
        )
    )

    # print(lf.head().collect())
    #
    # n_rows = lf.select(pl.len()).collect()[0, 0]
    # print(f"Number of rows {n_rows:,}")
    #
    # n_pois = lf.select(pl.col("ID_STORE").n_unique()).collect()[0, 0]
    # print(f"Number of POIs {n_pois:,}")
    #
    # n_with_vhc = (
    #     lf.filter(pl.col("VISITOR_HOME_CBGS").is_not_null())
    #     .select(pl.len())
    #     .collect()[0, 0]
    # )
    # print(f"Share with `VISITOR_HOME_CBGS` {n_with_vhc / n_rows:%}")

    # share_with_valid_vhc = (
    #     lf.filter(pl.col("VISITOR_HOME_CBGS").str.contains(r'":\d'))
    #     .select(pl.len())
    #     .collect()[0, 0]
    #     / n_rows
    # )
    # print(f"Share with valid `VISITOR_HOME_CBGS` {share_with_valid_vhc:%}")
    #
    # share_with_daily_visits_all_days = (
    #     lf.with_columns(
    #         pl.col("VISITS_BY_DAY").str.json_decode(pl.List(pl.Int64)).list.to_array(7)
    #     )
    #     .filter(pl.col("VISITS_BY_DAY").arr.min() != 0)
    #     .select(pl.len())
    #     .collect()[0, 0]
    #     / n_rows
    # )
    # print(
    #     f"Share with no 0 entry in `VISITS_BY_DAY` {share_with_daily_visits_all_days:%}"
    # )
    #
    # share_with_visits_gt_100 = (
    #     lf.filter(pl.col("VISITOR_COUNTS") >= 100).select(pl.len()).collect()[0, 0]
    #     / n_rows
    # )
    # print(f"Share with `VISITOR_COUNTS` >= 100 {share_with_visits_gt_100:%}")
    #
    # share_with_bg_visits_gt_100 = (
    #     lf.select(
    #         pl.col("VISITOR_HOME_CBGS")
    #         .str.extract_all(r":\s*(-?\d+)")
    #         .list.eval(pl.element().str.extract(r"(-?\d+)").cast(pl.Int64))
    #         .list.sum()
    #         .alias("VISITOR_HOME_CBGS_SUM")
    #     )
    #     .filter(pl.col("VISITOR_HOME_CBGS_SUM") >= 100)
    #     .select(pl.len())
    #     .collect()[0, 0]
    #     / n_rows
    # )
    # print(f"Share with `VISITOR_HOME_CBGS_SUM` >= 100 {share_with_bg_visits_gt_100:%}")
    #
    # share_with_1_home_bg = (
    #     lf.with_columns(
    #         pl.col("VISITOR_HOME_CBGS")
    #         .str.extract_all(r"\d+\":")
    #         .list.len()
    #         .alias("VISITOR_NUM_HOMES"),
    #         pl.col("VISITOR_HOME_CBGS")
    #         .str.extract_all(r":\s*(-?\d+)")
    #         .list.eval(pl.element().str.extract(r"(-?\d+)").cast(pl.Int64))
    #         .list.sum()
    #         .alias("VISITOR_HOME_CBGS_SUM"),
    #     )
    #     .filter(pl.col("VISITOR_NUM_HOMES") == 1)
    #     .select(pl.len())
    #     .collect()[0, 0]
    #     / n_rows
    # )
    # print(f"Share with visits from ONLY 1 home cbg {share_with_1_home_bg:%}")

    # share_with_gte_5_home_bg = (
    #     lf.with_columns(
    #         pl.col("VISITOR_HOME_CBGS")
    #         .str.extract_all(r"\d+\":")
    #         .list.len()
    #         .alias("VISITOR_NUM_HOMES"),
    #         pl.col("VISITOR_HOME_CBGS")
    #         .str.extract_all(r":\s*(-?\d+)")
    #         .list.eval(pl.element().str.extract(r"(-?\d+)").cast(pl.Int64))
    #         .list.sum()
    #         .alias("VISITOR_HOME_CBGS_SUM"),
    #     )
    #     .filter(pl.col("VISITOR_NUM_HOMES") >= 5)
    #     .select(pl.len())
    #     .collect()[0, 0]
    #     / n_with_vhc
    # )
    # print(f"Share with visits from >= 5 home cbg {share_with_gte_5_home_bg:%}")
    #
    # poi_num_weeks = (
    #     lf.with_columns(
    #         pl.col("VISITOR_HOME_CBGS")
    #         .str.extract_all(r"\d+\":")
    #         .list.len()
    #         .alias("VISITOR_NUM_HOMES"),
    #     )
    #     .filter(pl.col("VISITOR_NUM_HOMES") >= 5)
    #     .group_by("ID_STORE")
    #     .agg(pl.len().alias("NUM_WEEKS"))
    #     .group_by("NUM_WEEKS")
    #     .agg(pl.len().alias("NUM_POIS"))
    #     .sort("NUM_WEEKS")
    #     .collect()
    # )
    # print(poi_num_weeks)
    #
