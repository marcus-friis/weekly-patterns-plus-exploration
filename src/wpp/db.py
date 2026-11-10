from contextlib import contextmanager
from pathlib import Path

import duckdb

from wpp.utils import project_root

ROOT = project_root()
DATA_PATH = ROOT / "data"
DUCK_PATH = DATA_PATH / "db.duckdb"
PARQUET_DIR_PATH = DATA_PATH / "2025-weekly-patterns-plus"
DATA_GLOB = PARQUET_DIR_PATH / "*.parquet"


def _new_connection(
    database: str | Path = DUCK_PATH, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database, read_only=read_only)
    con.install_extension("spatial")
    con.load_extension("spatial")
    con.execute("SET preserve_insertion_order = false")
    return con


def connect(
    database: str | Path = DUCK_PATH, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    """Plain connection — caller is responsible for con.close()."""
    return _new_connection(database, read_only=read_only)


@contextmanager
def get_con(database: str | Path = DUCK_PATH, read_only: bool = False):
    con = _new_connection(database, read_only=read_only)
    con.execute("SET enable_progress_bar = true;")
    con.execute("SET enable_progress_bar_print = true;")
    try:
        yield con
    finally:
        con.close()
