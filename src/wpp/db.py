from contextlib import contextmanager
from pathlib import Path

import duckdb

from wpp.config import DB_PATH, ROOT

DATA_PATH = ROOT / "data"
PARQUET_DIR_PATH = DATA_PATH / "2025-weekly-patterns-plus"
DATA_GLOB = PARQUET_DIR_PATH / "*.parquet"
SQL_DIR = ROOT / "sql"


def _new_connection(
    database: str | Path = DB_PATH, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database, read_only=read_only)
    con.install_extension("spatial")
    con.load_extension("spatial")
    con.execute("SET preserve_insertion_order = false")
    return con


def connect(
    database: str | Path = DB_PATH, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    """Plain connection — caller is responsible for con.close()."""
    return _new_connection(database, read_only=read_only)


@contextmanager
def get_con(database: str | Path = DB_PATH, read_only: bool = False):
    con = _new_connection(database, read_only=read_only)
    con.execute("SET enable_progress_bar = true;")
    con.execute("SET enable_progress_bar_print = true;")
    try:
        yield con
    finally:
        con.close()


def run_sql_dir(
    con: duckdb.DuckDBPyConnection,
    sql_dir: Path = SQL_DIR,
    only: list[str] | None = None,
) -> None:
    """Execute *.sql files in lexical order (00_, 10_, 20_, ...)."""
    files = sorted(sql_dir.glob("*.sql"))
    if only:
        files = [f for f in files if any(f.name.startswith(p) for p in only)]
    for f in files:
        print(f"Running {f.name} ...")
        con.execute(f.read_text())
