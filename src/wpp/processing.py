import polars as pl

from wpp import data, db
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
        "VISITOR_HOME_AGGREGATION",
    ]
    # msa_set = {35620, 33100, 40140}
    msa_set = {35620}
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
        .with_columns(pl.len().over("ID_STORE").alias("NUM_POI_WEEKS"))
        .with_columns(
            pl.col("VISITOR_HOME_CBGS")
            .str.extract_all(pair_re)
            .list.eval(
                pl.struct(
                    cbg=pl.element().str.extract(r'"([^"]*)"'),
                    visitors=pl.element().str.extract(r":\s*(-?\d+)").cast(pl.Int64),
                )
            )
            .alias("VISITOR_HOME_CBGS"),
            pl.col("VISITOR_HOME_AGGREGATION")
            .str.extract_all(pair_re)
            .list.eval(
                pl.struct(
                    ct=pl.element().str.extract(r'"([^"]*)"'),
                    visitors=pl.element().str.extract(r":\s*(-?\d+)").cast(pl.Int64),
                )
            )
            .alias("VISITOR_HOME_AGGREGATION"),
        )
    )

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

    # Construct sql tables
    with db.get_con() as con:
        db.run_sql_dir(con)
