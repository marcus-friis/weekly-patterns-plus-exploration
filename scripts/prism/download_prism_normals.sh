#!/usr/bin/env bash
set -euo pipefail

OUT="normals"
HOST="ftp://prism.oregonstate.edu"

mkdir -p "$OUT"

for variable in tmin tmean tmax; do
  echo "Downloading $variable..."

  mkdir -p "$OUT/$variable"

  lftp "$HOST" <<EOF
mirror \
  --continue \
  --only-newer \
  --parallel=1 \
  --verbose \
  --include-glob="*.zip" \
  "/normals/us/4km/${variable}/daily" \
  "$OUT/$variable"
EOF
done

echo "Done: $OUT"
