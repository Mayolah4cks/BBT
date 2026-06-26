#!/bin/bash
# Master runner — execute all steps in order
set -e
export PATH=$PATH:$HOME/go/bin

cd /home/user/BBT
mkdir -p output

echo "========================================="
echo " TikTok Sub-Only Video Leak Hunter"
echo "========================================="

echo ""
echo "[STEP 1] Subdomain enumeration ..."
bash scripts/01_enum_subdomains.sh

echo ""
echo "[STEP 2] GAU - fetch archived URLs ..."
bash scripts/02_gau_endpoints.sh

echo ""
echo "[STEP 3] JS endpoint extraction ..."
python3 scripts/03_js_endpoint_extract.py

echo ""
echo "[STEP 4] Filter + rank candidates ..."
python3 scripts/04_filter_candidates.py

echo ""
echo "========================================="
echo " Steps 1-4 complete."
echo " Review output/candidates_tier1.txt"
echo " Then configure and run:"
echo "   python3 scripts/05_probe_endpoints.py"
echo "========================================="
