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
    "04": "arizona",
    "06": "california",
    "12": "florida",
    "15": "hawaii",
    "36": "new-york",
    "48": "texas",
}


def _check_state(state_fips: str) -> str:
    if state_fips not in STATES:
        raise ValueError(
            f"Unknown state FIPS {state_fips!r}; expected one of {sorted(STATES)}"
        )
    return state_fips


def _new_connection(database: str | Path = DUCK_PATH) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database)
    con.install_extension("spatial")
    con.load_extension("spatial")
    return con


def connect(database: str | Path = DUCK_PATH) -> duckdb.DuckDBPyConnection:
    """Plain connection — caller is responsible for con.close()."""
    return _new_connection(database)


@contextmanager
def get_con(database: str | Path = DUCK_PATH, debug: bool = True):
    con = _new_connection(database)
    con.execute("SET enable_progress_bar = true;")
    con.execute("SET enable_progress_bar_print = true;")
    try:
        yield con
    finally:
        con.close()


def create_block_group_table(state_fips: str, force: bool = False):
    """Load a TIGER block-group shapefile into a table named e.g. bg_12 (Florida)."""
    _check_state(state_fips)
    shp_path = (
        DATA_PATH / "shps" / f"tl_2025_{state_fips}_bg" / f"tl_2025_{state_fips}_bg.shp"
    )
    table_name = f"bg_{state_fips}"
    print(f"Building {table_name} from {shp_path}...")
    with get_con() as con:
        if force:
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} AS
            SELECT * FROM ST_Read('{shp_path}')
        """)
        con.execute(f"""
            CREATE INDEX IF NOT EXISTS {table_name}_idx
            ON {table_name} USING RTREE (geom)
        """)
    print(f"Done: {table_name}")


def create_state_boundaries(state_fips: str, force: bool = False):
    _check_state(state_fips)
    name = STATES[state_fips]
    print(f"Building state_boundaries entry for {name} ({state_fips})...")
    with get_con() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS state_boundaries (
                fips VARCHAR PRIMARY KEY,
                name VARCHAR,
                geom GEOMETRY
            )
        """)
        if force:
            con.execute("DELETE FROM state_boundaries WHERE fips = ?", [state_fips])
        exists = con.execute(
            "SELECT 1 FROM state_boundaries WHERE fips = ?", [state_fips]
        ).fetchone()
        if exists:
            print(f"  {name} ({state_fips}) already present, skipping")
            return
        con.execute(f"""
            INSERT INTO state_boundaries
            SELECT '{state_fips}', '{name}', ST_Union_Agg(geom)
            FROM bg_{state_fips}
        """)
    print(f"Done: state_boundaries entry for {name}")


def create_wpp(state_fips: str, force: bool = False):
    _check_state(state_fips)
    table_name = f"wpp_{state_fips}"
    bg_table = f"bg_{state_fips}"
    query = f"""
      CREATE TABLE IF NOT EXISTS {table_name} AS
        WITH t AS (
            SELECT *, ST_Point(LONGITUDE, LATITUDE) AS GEOM
            FROM '{DATA_GLOB}'
        )
        SELECT DISTINCT t.*
        FROM t
        JOIN {bg_table} AS boundary
          ON boundary.geom && t.GEOM
         AND ST_Within(t.GEOM, boundary.geom)
    """
    print(f"Building {table_name} (this may take a while)...")
    with get_con() as con:
        if force:
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(query)
        # con.execute(f"""
        #     CREATE INDEX IF NOT EXISTS {table_name}_geom_idx
        #     ON {table_name} USING RTREE (GEOM)
        # """)
    print(f"Done: {table_name}")


def create_pois(state_fips: str, force: bool = False):
    _check_state(state_fips)
    table_name = f"pois_{state_fips}"
    source_table = f"wpp_{state_fips}"
    query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} AS
        SELECT DISTINCT
            ID_STORE, BRAND, LOCATION_NAME,
            STREET_ADDRESS, POI_CBG, CITY, REGION, ISO_COUNTRY_CODE,
            TOP_CATEGORY, SUB_CATEGORY,
            OPEN_DATE, CLOSE_DATE,
            LONGITUDE, LATITUDE,
            GEOM
        FROM {source_table}
    """
    print(f"Building {table_name} from {source_table}...")
    with get_con() as con:
        if force:
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(query)
        # con.execute(f"""
        #     CREATE INDEX IF NOT EXISTS {table_name}_geom_idx
        #     ON {table_name} USING RTREE (GEOM)
        # """)
    print(f"Done: {table_name}")


def create_block_group_poi_visits(state_fips: str, force: bool = False):
    _check_state(state_fips)
    table_name = f"bg_poi_visits_{state_fips}"
    source_table = f"wpp_{state_fips}"
    query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} AS
        WITH tmp AS (
            SELECT
                 ID_STORE,
                 DATE_RANGE_START, DATE_RANGE_END,
                 UNNEST(map_keys(M)) AS HOME_CBG,
                 POI_CBG,
                 UNNEST(map_values(M)) AS VISITOR_COUNT
             FROM (
                 SELECT *, CAST(VISITOR_HOME_CBGS::JSON AS MAP(VARCHAR, INTEGER)) AS M
                 FROM {source_table}
             )
        )
        SELECT *
        FROM tmp
        WHERE HOME_CBG IN (SELECT GEOID FROM bg_{state_fips})
    """
    print(f"Building {table_name} from {source_table}...")
    with get_con() as con:
        if force:
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(query)
    print(f"Done: {table_name}")


def create_block_group_poi_distances(state_fips: str, force: bool = False):
    table_name = f"bg_poi_dist_{state_fips}"
    query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} AS
        SELECT DISTINCT
            bgpv.ID_STORE,
            bgpv.HOME_CBG,
            ST_Distance_Sphere(p.GEOM, ST_Centroid(bg.geom)) AS DIST_METERS
        FROM bg_poi_visits_{state_fips} bgpv
        JOIN pois_{state_fips} p ON bgpv.ID_STORE = p.ID_STORE
        JOIN bg_{state_fips} bg ON bgpv.HOME_CBG = bg.GEOID
    """
    with get_con() as con:
        if force:
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
            con.execute(query)


def build_state(state_fips: str, force: bool = False):
    _check_state(state_fips)
    create_block_group_table(state_fips, force=force)
    create_state_boundaries(state_fips, force=force)
    create_wpp(state_fips, force=force)
    create_pois(state_fips, force=force)
    create_block_group_poi_visits(state_fips, force=force)


def build_all(force: bool = False):
    for fips in STATES:
        print(f"=== Building state {STATES[fips]} ({fips}) ===")
        build_state(fips, force=force)
