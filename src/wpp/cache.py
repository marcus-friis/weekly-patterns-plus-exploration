from collections.abc import Callable
from functools import wraps
from pathlib import Path

import polars as pl

CACHE_DIR = Path("cache")


def cached_parquet(
    name: str,
    loader: Callable[[], pl.DataFrame],
    *,
    refresh: bool = False,
) -> pl.DataFrame:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{name}.parquet"

    if path.exists() and not refresh:
        return pl.read_parquet(path)

    result = loader()
    result.write_parquet(path)
    return result


def cache(func):
    @wraps(func)
    def wrapper(*args, refresh: bool = False, **kwargs):
        return cached_parquet(
            func.__name__,
            lambda: func(*args, **kwargs),
            refresh=refresh,
        )

    return wrapper
