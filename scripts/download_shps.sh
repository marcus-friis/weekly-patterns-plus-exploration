mkdir -p tiger2025_bg && cd tiger2025_bg

BASE="https://www2.census.gov/geo/tiger/TIGER2025/BG/"

curl -s "$BASE" | grep -oE 'tl_2025_[0-9]+_bg\.zip' | sort -u > filelist.txt
wc -l filelist.txt

while read -r f; do
  curl -C - -O "${BASE}${f}"
done < filelist.txt
