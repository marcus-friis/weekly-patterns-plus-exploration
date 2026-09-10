from pathlib import Path

import orjson
import polars as pl


def _parse_cbgs(x: str | None) -> dict[str, int] | None:
    if x is None:
        return None

    x = x.strip()
    if not x:
        return None

    try:
        data = orjson.loads(x)
    except orjson.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    result: dict[str, int] = {}

    for key, value in data.items():
        if not isinstance(key, str):
            return None

        if not isinstance(value, int):
            return None

        result[key] = value

    return result


def load_weekly_patterns_plus(file_path: Path | str) -> pl.DataFrame:
    """Load Weekly Patterns Plus By Advan Research into polars dataframe"""
    schema = {
        "id_store": pl.Utf8,
        "ticker": pl.Utf8,
        "persistent_id": pl.Utf8,
        "persistent_id_store": pl.Utf8,
        # FIXED, max ~9.223e18 fits (barely) within Int64's max of 9,223,372,036,854,775,807
        "footprint_id": pl.Int64,
        "is_distributor": pl.Boolean,
        "location_name": pl.Utf8,
        "street_address": pl.Utf8,
        "city": pl.Utf8,
        "region": pl.Utf8,
        "postal_code": pl.Utf8,  # keep as string to preserve leading zeros
        "iso_country_code": pl.Utf8,
        "brand": pl.Utf8,
        "open_date": pl.Date,
        "close_date": pl.Date,
        "longitude": pl.Float64,
        "latitude": pl.Float64,
        "naics_code": pl.Utf8,
        "top_category": pl.Utf8,
        "sub_category": pl.Utf8,
        "poi_cbg": pl.Utf8,
        "msa_code": pl.Utf8,
        "date_range_start": pl.Datetime,
        "date_range_end": pl.Datetime,
    }

    df = pl.read_csv(file_path, schema_overrides=schema)
    df = df.with_columns(
        pl.col("visits_by_day")
        .str.json_decode(dtype=pl.List(pl.Int64))
        .list.to_array(7),
        pl.col("visits_by_each_hour")
        .str.json_decode(dtype=pl.List(pl.Int64))
        .list.to_array(168),
        pl.col("visitor_home_cbgs").map_elements(
            _parse_cbgs,
            return_dtype=pl.Object,
        ),
        pl.col("bucketed_dwell_times").map_elements(
            _parse_cbgs,
            return_dtype=pl.Object,
        ),
    )
    return df
