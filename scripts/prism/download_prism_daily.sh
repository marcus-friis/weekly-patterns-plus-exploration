!/usr/bin/env bash
set -euo pipefail

OUT="daily"
HOST="ftp://prism.oregonstate.edu"
YEAR=2025

mkdir -p "$OUT"

for variable in tmin tmean tmax; do
  echo "Downloading $variable..."

  mkdir -p "$OUT/$variable"

  lftp "$HOST" <<EOF
mirror \
  --continue \
  --only-newer \
  --parallel=4 \
  --verbose \
  --include-glob="*.zip" \
  "/time_series/us/an/cog/4km/${variable}/daily/${YEAR}" \
  "$OUT/$variable"
EOF
done

echo "Done: $OUT"
