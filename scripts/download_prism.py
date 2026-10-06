import io
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
import shapely
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

START = date(2025, 1, 1)
END = date(2025, 12, 31)

VARIABLES = ("tmean", "tmin", "tmax")

OUT = Path("prism")
DAILY_DIR = OUT / "daily"
ZIP_DIR = OUT / "zips"
CELLS_PATH = OUT / "prism_cells.parquet"

BASE_URL = "https://services.nacse.org/prism/data/get/us/4km"

DAILY_DIR.mkdir(parents=True, exist_ok=True)
ZIP_DIR.mkdir(parents=True, exist_ok=True)


session = requests.Session()
session.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
    ),
)


def grid_signature(src):
    """Everything that defines the raster grid."""

    return {
        "height": src.height,
        "width": src.width,
        "transform": tuple(src.transform),
        "crs": src.crs.to_wkt(),
    }


def assert_same_grid(reference, current, variable, day):
    if current != reference:
        differences = {
            key: {
                "expected": reference[key],
                "received": current[key],
            }
            for key in reference
            if reference[key] != current[key]
        }

        raise ValueError(f"PRISM grid mismatch for {variable} on {day}:\n{differences}")


def download_zip(variable, day):
    date_string = day.strftime("%Y%m%d")
    zip_path = ZIP_DIR / f"{variable}_{date_string}.zip"

    if zip_path.exists() and zipfile.is_zipfile(zip_path):
        return zip_path

    response = session.get(
        f"{BASE_URL}/{variable}/{date_string}",
        timeout=120,
    )
    response.raise_for_status()

    content = io.BytesIO(response.content)

    if not zipfile.is_zipfile(content):
        raise RuntimeError(f"Invalid ZIP returned for {variable} on {day}")

    zip_path.write_bytes(response.content)

    return zip_path


def read_raster(variable, day):
    zip_path = download_zip(variable, day)

    with TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(temp_dir)

        raster_paths = (
            list(temp_dir.rglob("*.tif"))
            + list(temp_dir.rglob("*.tiff"))
            + list(temp_dir.rglob("*.bil"))
        )

        if not raster_paths:
            raise FileNotFoundError(f"No raster found in {zip_path}")

        if len(raster_paths) > 1:
            raise RuntimeError(
                f"Multiple rasters found in {zip_path}: "
                f"{[p.name for p in raster_paths]}"
            )

        with rasterio.open(raster_paths[0]) as src:
            array = src.read(1, masked=True)
            signature = grid_signature(src)

    return array, signature


def create_cells(reference):
    """Create polygons for every raster position."""

    transform = rasterio.Affine(*reference["transform"])
    height = reference["height"]
    width = reference["width"]

    if not (
        transform.b == 0 and transform.d == 0 and transform.a > 0 and transform.e < 0
    ):
        raise ValueError("Expected a north-up rectangular raster grid")

    rows, cols = np.indices(
        (height, width),
        dtype="int32",
    )

    rows = rows.ravel()
    cols = cols.ravel()

    xmin = transform.c + cols * transform.a
    xmax = xmin + transform.a

    ymax = transform.f + rows * transform.e
    ymin = ymax + transform.e

    cells = gpd.GeoDataFrame(
        {
            "cell_id": (rows.astype("int64") * width + cols.astype("int64")),
            "row": rows,
            "col": cols,
        },
        geometry=shapely.box(xmin, ymin, xmax, ymax),
        crs=reference["crs"],
    )

    cells.to_parquet(CELLS_PATH, index=False)

    print(f"Created cells: {CELLS_PATH}")


def process_day(day, reference):
    arrays = {}

    for variable in VARIABLES:
        array, signature = read_raster(variable, day)

        if reference is None:
            reference = signature
        else:
            assert_same_grid(
                reference,
                signature,
                variable,
                day,
            )

        arrays[variable] = array

    if not CELLS_PATH.exists():
        create_cells(reference)

    height = reference["height"]
    width = reference["width"]

    rows, cols = np.indices(
        (height, width),
        dtype="int32",
    )

    rows = rows.ravel()
    cols = cols.ravel()

    # Retain cells with at least one valid temperature value.
    valid = np.logical_or.reduce(
        [~np.ma.getmaskarray(array).ravel() for array in arrays.values()]
    )

    rows = rows[valid]
    cols = cols[valid]

    output = pd.DataFrame(
        {
            "date": pd.Timestamp(day),
            "cell_id": (rows.astype("int64") * width + cols.astype("int64")),
            **{
                variable: np.asarray(
                    array.filled(np.nan).ravel()[valid],
                    dtype="float32",
                )
                for variable, array in arrays.items()
            },
        }
    )

    output_path = DAILY_DIR / f"prism_{day:%Y-%m-%d}.parquet"

    # Write only after every grid has been validated.
    output.to_parquet(output_path, index=False)

    return reference, len(output)


reference_grid = None
day = START

while day <= END:
    reference_grid, row_count = process_day(
        day,
        reference_grid,
    )

    print(f"Processed: {day} ({row_count:,} cells)")

    time.sleep(2)
    day += timedelta(days=1)
