import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import requests

START = date(2025, 1, 1)
END = date(2025, 12, 31)

OUT = Path("prism/tmean_daily_2025")
BASE_URL = "https://services.nacse.org/prism/data/get/us/4km/tmean"

OUT.mkdir(parents=True, exist_ok=True)

day = START

while day <= END:
    date_string = day.strftime("%Y%m%d")
    path = OUT / f"prism_tmean_us_4km_{date_string}.zip"

    if path.exists() and zipfile.is_zipfile(path):
        print(f"Exists: {date_string}")
        day += timedelta(days=1)
        continue

    response = requests.get(
        f"{BASE_URL}/{date_string}",
        timeout=120,
    )
    response.raise_for_status()
    path.write_bytes(response.content)

    if not zipfile.is_zipfile(path):
        path.unlink()
        raise RuntimeError(f"Invalid ZIP: {date_string}")

    print(f"Downloaded: {date_string}")

    time.sleep(2)
    day += timedelta(days=1)
