from collections.abc import Callable
from functools import wraps

import polars as pl

from wpp.config import ROOT

CACHE_DIR = ROOT / "cache"


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


def wipe_cache(*names: str) -> list[str]:
    """Delete cached parquet files.

    With no arguments, removes every cached file. Otherwise removes only the
    named entries (the `name` passed to `cached_parquet`, or the decorated
    function's `__name__`).

    Returns the names of the entries that were actually deleted.
    """
    if not CACHE_DIR.exists():
        return []

    if names:
        paths = [CACHE_DIR / f"{name}.parquet" for name in names]
    else:
        paths = list(CACHE_DIR.glob("*.parquet"))

    deleted = []
    for path in paths:
        if path.exists():
            path.unlink()
            deleted.append(path.stem)
    return deleted
