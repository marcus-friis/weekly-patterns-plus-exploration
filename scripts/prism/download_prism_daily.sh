#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 START_YEAR [END_YEAR]" >&2
  echo "  e.g. $0 2020 2025   (range)" >&2
  echo "       $0 2025        (single year)" >&2
  exit 1
}

OUT="daily"
HOST="ftp://prism.oregonstate.edu"

[[ $# -ge 1 && $# -le 2 ]] || usage

START_YEAR="$1"
END_YEAR="${2:-$START_YEAR}"

# Validate input
[[ "$START_YEAR" =~ ^[0-9]{4}$ && "$END_YEAR" =~ ^[0-9]{4}$ ]] || usage
(( START_YEAR <= END_YEAR )) || { echo "Error: START_YEAR must be <= END_YEAR" >&2; usage; }

mkdir -p "$OUT"

for variable in tmin tmean tmax; do
  for year in $(seq "$START_YEAR" "$END_YEAR"); do
    echo "Downloading $variable $year..."

    mkdir -p "$OUT/$variable/$year"

    lftp "$HOST" <<EOF
mirror \
  --continue \
  --only-newer \
  --parallel=4 \
  --verbose \
  --include-glob="*.zip" \
  "/time_series/us/an/cog/4km/${variable}/daily/${year}" \
  "$OUT/$variable"
EOF
  done
done

echo "Done: $OUT"
