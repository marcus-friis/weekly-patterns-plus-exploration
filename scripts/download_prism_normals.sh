#!/usr/bin/env bash
set -euo pipefail

OUT="prism_temperature_normals_2025"
ROOT="https://data.prism.oregonstate.edu/normals/us/4km"

mkdir -p "$OUT"
cd "$OUT"

for variable in tmin tmean tmax; do
  echo "Processing $variable"

  BASE="${ROOT}/${variable}/daily/"
  mkdir -p "$variable/extracted"

  curl -fsSL "$BASE" \
    | grep -oE "prism_${variable}_us_25m_2020[0-9]{4}_avg_30y\.zip" \
    | grep -v "20200229" \
    | sort -u \
    > "$variable/filelist.txt"

  echo "Found $(wc -l < "$variable/filelist.txt" | tr -d ' ') $variable files"

  while IFS= read -r file; do
    zip_path="$variable/$file"

    if [[ -f "$zip_path" ]]; then
      echo "Skipping existing file: $zip_path"
      continue
    fi

    echo "Downloading $file"
    curl \
      --fail \
      --location \
      --retry 5 \
      --retry-delay 5 \
      --output "$zip_path" \
      "${BASE}${file}"

    echo "Extracting $file"
    unzip -o "$zip_path" -d "$variable/extracted"

    sleep 2
  done < "$variable/filelist.txt"
done

echo "Done. Extracted files are in:"
echo "  $OUT/tmin/extracted"
echo "  $OUT/tmean/extracted"
echo "  $OUT/tmax/extracted"
