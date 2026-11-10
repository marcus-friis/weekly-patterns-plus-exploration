import zipfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd
import numpy as np
import polars as pl
import rasterio

from wpp.utils import project_root

PRISM_DIR = project_root() / "data" / "prism"
VARIABLES = ("tmin", "tmean", "tmax")


def read_raster(zip_path: Path) -> np.ndarray:
    with TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        raster_path = Path(tmp) / f"{zip_path.stem}.tif"
        with rasterio.open(raster_path) as src:
            return src.read(1, masked=True)


def build_mesh() -> pl.DataFrame:
    mesh = gpd.read_file(PRISM_DIR / "prism_4km_mesh" / "prism_4km_mesh.shp")
    mesh.to_parquet(PRISM_DIR / "prism_cells.parquet")
    return mesh


def build(kind: str, mesh: pl.DataFrame) -> None:
    rows, cols = mesh["row"].to_numpy(), mesh["col"].to_numpy()
    base = PRISM_DIR / kind
    out_dir = PRISM_DIR / f"prism_{kind}"
    out_dir.mkdir(exist_ok=True)

    for path in sorted((base / "tmean").glob("*.zip")):
        date_str = path.stem.split("_")[4]
        out = out_dir / f"{date_str}.parquet"
        dt = datetime.strptime(date_str, "%Y%m%d")
        data = {}
        for v in VARIABLES:
            # same filename with tmean -> tmin/tmax; errors loudly if missing
            arr = read_raster(base / v / path.name.replace("tmean", v))
            data[v] = arr[rows, cols]

        pl.DataFrame(
            {"row": rows, "col": cols, "date": dt.date(), **data}
        ).write_parquet(out)
        print(kind, date_str)


if __name__ == "__main__":
    mesh = build_mesh()
    build("normals", mesh)
    build("daily", mesh)
