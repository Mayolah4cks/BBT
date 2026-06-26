#!/bin/bash
# Step 1: Enumerate live TikTok subdomains via crt.sh + subfinder
set -e

DOMAIN="tiktok.com"
OUT="/home/user/BBT/output"
PATH=$PATH:$HOME/go/bin

echo "[*] Querying crt.sh for $DOMAIN ..."
curl -s "https://crt.sh/?q=%25.$DOMAIN&output=json" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
names = set()
for entry in data:
    for name in entry.get('name_value','').split('\n'):
        name = name.strip().lstrip('*.')
        if name.endswith('$DOMAIN') or name == '$DOMAIN':
            names.add(name)
for n in sorted(names):
    print(n)
" > "$OUT/crtsh_subs.txt" 2>/dev/null || echo "[!] crt.sh parse failed"

echo "[*] Running subfinder on $DOMAIN ..."
subfinder -d "$DOMAIN" -silent -o "$OUT/subfinder_subs.txt" 2>/dev/null

echo "[*] Merging and deduplicating ..."
cat "$OUT/crtsh_subs.txt" "$OUT/subfinder_subs.txt" 2>/dev/null \
  | sort -u > "$OUT/all_subs.txt"

echo "[*] Probing live hosts with httpx ..."
httpx -l "$OUT/all_subs.txt" -silent -o "$OUT/live_subs.txt" \
  -mc 200,301,302,403 -timeout 10 -threads 50 2>/dev/null

echo "[+] Done. Live hosts saved to $OUT/live_subs.txt"
wc -l "$OUT/live_subs.txt"
