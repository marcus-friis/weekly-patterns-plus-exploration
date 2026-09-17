from contextlib import contextmanager
from pathlib import Path

import duckdb

from wpp.utils import project_root

ROOT = project_root()
DATA_PATH = ROOT / "data"
DUCK_PATH = DATA_PATH / "db.duckdb"
PARQUET_DIR_PATH = DATA_PATH / "2025-weekly-patterns-plus"
DATA_GLOB = PARQUET_DIR_PATH / "*.parquet"

STATES = {
    "12": "florida",
    "04": "arizona",
}


def _new_connection(database: str | Path = DUCK_PATH) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database)
    con.install_extension("spatial")
    con.load_extension("spatial")
    return con


def connect(database: str | Path = DUCK_PATH) -> duckdb.DuckDBPyConnection:
    """Plain connection — caller is responsible for con.close()."""
    return _new_connection(database)


@contextmanager
def get_con(database: str | Path = DUCK_PATH):
    con = _new_connection(database)
    try:
        yield con
    finally:
        con.close()


def create_block_group_table(state_fips: str):
    """Load a TIGER block-group shapefile into a table named e.g. bg_12 (Florida)."""
    shp_path = (
        DATA_PATH / "shps" / f"tl_2025_{state_fips}_bg" / f"tl_2025_{state_fips}_bg.shp"
    )
    table_name = f"bg_{state_fips}"
    with get_con() as con:
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} AS
            SELECT * FROM ST_Read('{shp_path}')
        """)
        con.execute(f"""
            CREATE INDEX IF NOT EXISTS {table_name}_idx
            ON {table_name} USING RTREE (geom)
        """)


def create_state_boundaries():
    with get_con() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS state_boundaries (
                fips VARCHAR PRIMARY KEY,
                name VARCHAR,
                geom GEOMETRY
            )
        """)
        existing = {
            row[0]
            for row in con.execute("SELECT fips FROM state_boundaries").fetchall()
        }
        for fips, name in STATES.items():
            if fips in existing:
                continue
            con.execute(f"""
                INSERT INTO state_boundaries
                SELECT '{fips}', '{name}', ST_Union_Agg(geom)
                FROM bg_{fips}
            """)


def create_wpp(state_fips: str | None = None):
    if state_fips == None:
        query = f"""
          CREATE TABLE IF NOT EXISTS wpp AS
            SELECT *
            FROM '{DATA_GLOB}'
        """
    else:
        table_name = f"wpp_{state_fips}"
        bg_table = f"bg_{state_fips}"
        query = f"""
          CREATE TABLE IF NOT EXISTS {table_name} AS
            WITH t AS (
                SELECT *, ST_Point(LONGITUDE, LATITUDE) AS pt
                FROM '{DATA_GLOB}'
            )
            SELECT DISTINCT t.* EXCLUDE (pt)
            FROM t
            JOIN {bg_table} AS boundary
              ON boundary.geom && t.pt
             AND ST_Within(t.pt, boundary.geom)
        """
    with get_con() as con:
        con.execute(query)


def create_pois(state_fips: str | None = None):
    table_name = f"pois_{state_fips}" if state_fips else "pois"
    source_table = f"wpp_{state_fips}" if state_fips else "wpp"
    query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} AS
        SELECT DISTINCT
            ID_STORE, BRAND, LOCATION_NAME,
            STREET_ADDRESS, POI_CBG, CITY, REGION, ISO_COUNTRY_CODE,
            TOP_CATEGORY, SUB_CATEGORY,
            OPEN_DATE, CLOSE_DATE,
            LONGITUDE, LATITUDE
        FROM {source_table}
    """
    with get_con() as con:
        con.execute(query)


if __name__ == "__main__":
    create_state_boundaries()
