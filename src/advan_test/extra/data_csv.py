from pathlib import Path

import orjson
import polars as pl


def _parse_str_int_obj(x: str | None) -> dict[str, int] | None:
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


def load_weekly_patterns_plus_csv(file_path: Path | str) -> pl.DataFrame:
    """Load Weekly Patterns Plus By Advan Research from csv into polars dataframe"""
    schema = {
        "id_store": pl.Utf8,
        "ticker": pl.Utf8,
        "persistent_id": pl.Utf8,
        "persistent_id_store": pl.Utf8,
        "footprint_id": pl.Int64,
        "is_distributor": pl.Boolean,
        "location_name": pl.Utf8,
        "street_address": pl.Utf8,
        "city": pl.Utf8,
        "region": pl.Utf8,
        "postal_code": pl.Utf8,
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
        "visit_counts": pl.Int64,
        "visitor_counts": pl.Int64,
        "visits_by_day": pl.Utf8,
        "visits_by_each_hour": pl.Utf8,
        "visitor_home_cbgs": pl.Utf8,
        "visitor_home_aggregation": pl.Utf8,
        "visitor_daytime_cbgs": pl.Utf8,
        "visitor_country_of_origin": pl.Utf8,
        "distance_from_home": pl.Float32,
        "median_dwell": pl.Float32,
        "bucketed_dwell_times": pl.Utf8,
        "related_same_day_brand": pl.Utf8,
        "related_same_week_brand": pl.Utf8,
        "device_type": pl.Utf8,
    }

    df = pl.read_csv(file_path, schema_overrides=schema, null_values="None")
    obj_cols = [
        "related_same_week_brand",
        "related_same_day_brand",
        "bucketed_dwell_times",
        "visitor_home_cbgs",
        "visitor_country_of_origin",
        "visitor_daytime_cbgs",
        "visitor_home_aggregation",
    ]
    df = df.with_columns(
        pl.col("visits_by_day")
        .str.json_decode(dtype=pl.List(pl.Int64))
        .list.to_array(7),
        pl.col("visits_by_each_hour")
        .str.json_decode(dtype=pl.List(pl.Int64))
        .list.to_array(168),
        *[
            pl.col(col).map_elements(
                _parse_str_int_obj,
                return_dtype=pl.Object,
            )
            for col in obj_cols
        ],
    )
    return df
