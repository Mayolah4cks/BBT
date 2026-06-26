#!/bin/bash
# Step 2: Pull historical URLs from web archives for all live subdomains
set -e

OUT="/home/user/BBT/output"
PATH=$PATH:$HOME/go/bin

echo "[*] Fetching archived URLs via gau for tiktok.com scope ..."

# Use gau on the root domain + key subdomains of interest
TARGETS=(
  "tiktok.com"
  "www.tiktok.com"
  "studio.tiktok.com"
  "webapp.tiktok.com"
  "api.tiktok.com"
  "api16-normal.tiktokv.com"
  "api19-normal.tiktokv.com"
  "api21-normal.tiktokv.com"
  "api32-normal.tiktokv.com"
  "aggr32-normal.tiktokv.com"
  "api-normal.tiktokv.com"
)

> "$OUT/gau_raw_urls.txt"

for target in "${TARGETS[@]}"; do
  echo "  [>] $target"
  gau --subs --providers wayback,commoncrawl,otx "$target" 2>/dev/null \
    >> "$OUT/gau_raw_urls.txt" || true
done

echo "[*] Total raw URLs: $(wc -l < $OUT/gau_raw_urls.txt)"

# Extract just the paths (strip domain + query params for dedup)
grep -oP '(?<=https?://[^/]{5,60})/[^?#]+' "$OUT/gau_raw_urls.txt" \
  | sort -u > "$OUT/gau_paths.txt" 2>/dev/null || true

echo "[+] Unique paths: $(wc -l < $OUT/gau_paths.txt)"
echo "[+] Saved to $OUT/gau_paths.txt and $OUT/gau_raw_urls.txt"
