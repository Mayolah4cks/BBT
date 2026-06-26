#!/usr/bin/env python3
"""
Step 5: Probe candidate endpoints with a known sub-only video_id.
Flag any response that contains CDN URLs, play_addr, download_addr,
or other indicators of leaked video content.
"""

import json
import re
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin

# ──────────────────────────────────────────────
# CONFIGURE THESE BEFORE RUNNING
# ──────────────────────────────────────────────
# Paste your authenticated session cookie here (from your browser/Burp)
SESSION_COOKIE = "YOUR_SESSION_COOKIE_HERE"

# A known sub-only video_id (complex format like from your report)
SUB_ONLY_VIDEO_ID = "YOUR_SUB_ONLY_VIDEO_ID_HERE"

# A draft_id from your previous PoC (optional, for draft endpoints)
DRAFT_ID = "YOUR_DRAFT_ID_HERE"
# ──────────────────────────────────────────────

OUT = "/home/user/BBT/output"
RESULTS_FILE = f"{OUT}/probe_results.txt"
HITS_FILE = f"{OUT}/probe_HITS.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": SESSION_COOKIE,
}

# Response indicators that suggest video content was leaked
LEAK_INDICATORS = re.compile(
    r'webapp-va\.tiktok\.com|v\d+-webapp\.tiktok\.com|tiktokcdn\.com/obj|'
    r'play_addr|download_addr|wm_video_url|audio_track|stream_url|'
    r'tos-maliva|tos-alisg|tos-useast|video_url|playUrl|play_url',
    re.IGNORECASE
)

# Payloads to try per endpoint (method + body variants)
def make_payloads(path):
    payloads = []
    base_json = {"video_id": SUB_ONLY_VIDEO_ID}
    aweme_json = {"aweme_id": SUB_ONLY_VIDEO_ID}
    item_json  = {"item_id": SUB_ONLY_VIDEO_ID}
    draft_json = {"draft_id": DRAFT_ID, "video_id": SUB_ONLY_VIDEO_ID}

    # GET with query params
    payloads.append(("GET",  f"{path}?video_id={SUB_ONLY_VIDEO_ID}", None))
    payloads.append(("GET",  f"{path}?aweme_id={SUB_ONLY_VIDEO_ID}", None))
    payloads.append(("GET",  f"{path}?item_ids={SUB_ONLY_VIDEO_ID}", None))

    # POST with JSON body
    payloads.append(("POST", path, json.dumps(base_json)))
    payloads.append(("POST", path, json.dumps(aweme_json)))
    payloads.append(("POST", path, json.dumps(draft_json)))

    return payloads


def probe(base_url, path):
    results = []
    parsed = urlparse(base_url)
    host = f"{parsed.scheme}://{parsed.netloc}"

    for method, endpoint, body in make_payloads(path):
        url = urljoin(host, endpoint)
        headers = dict(HEADERS)
        if body:
            headers["Content-Type"] = "application/json"
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
            else:
                r = requests.post(url, headers=headers, data=body, timeout=10, allow_redirects=False)

            is_hit = LEAK_INDICATORS.search(r.text or "")
            status = r.status_code

            result = {
                "url": url,
                "method": method,
                "status": status,
                "hit": bool(is_hit),
                "response_len": len(r.text),
                "snippet": r.text[:300].replace("\n", " ") if is_hit else "",
            }
            results.append(result)

            if is_hit:
                print(f"\n[!!!] POTENTIAL HIT: {method} {url} → {status}")
                print(f"      Snippet: {r.text[:200]}")

        except Exception as e:
            pass
        time.sleep(0.3)  # polite rate limiting

    return results


def main():
    if SESSION_COOKIE == "YOUR_SESSION_COOKIE_HERE":
        print("[!] Set SESSION_COOKIE and SUB_ONLY_VIDEO_ID before running this script.")
        sys.exit(1)

    try:
        with open(f"{OUT}/candidates_tier1.txt") as f:
            candidates = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(f"[!] Run scripts 01-04 first to generate candidates.")
        sys.exit(1)

    # Parse host + path from each candidate
    tasks = []
    for c in candidates:
        parsed = urlparse(c if c.startswith("http") else "https://" + c)
        base = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path or "/"
        tasks.append((base, path))

    print(f"[*] Probing {len(tasks)} candidate endpoints ...")
    all_results = []
    hits = []

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(probe, base, path): (base, path) for base, path in tasks}
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            all_results.extend(res)
            for r in res:
                if r["hit"]:
                    hits.append(r)
            if i % 20 == 0:
                print(f"  [{i}/{len(tasks)}] {len(hits)} hits so far")

    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    with open(HITS_FILE, "w") as f:
        json.dump(hits, f, indent=2)

    print(f"\n[+] Done. Total probes: {len(all_results)}")
    print(f"[+] Hits (potential leaks): {len(hits)} → {HITS_FILE}")
    print(f"[+] Full results: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
