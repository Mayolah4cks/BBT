#!/usr/bin/env python3
"""
Step 3: Download JS bundles from live TikTok subdomains and extract
API endpoints that reference video_id, aweme_id, item_id, or vid params.
"""

import re
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

OUT = "/home/user/BBT/output"
LIVE_SUBS_FILE = f"{OUT}/live_subs.txt"
JS_ENDPOINTS_FILE = f"{OUT}/js_extracted_endpoints.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Patterns to identify API paths that likely accept a video_id
VIDEO_ID_PATTERNS = [
    r'["\'/]((?:/[a-zA-Z0-9_\-]+){2,}/(?:video|aweme|item|draft|clip|media|play|stream|download|export|preview|trim|edit|duet|stitch|remix|caption|subtitle|cover|thumbnail)[a-zA-Z0-9_/\-]*)["\'/\?]',
    r'["\'/]((?:/api|/aweme|/tiktok_creator|/creator|/web)[a-zA-Z0-9_/\-]{5,})["\'/\?]',
]

JS_URL_PATTERN = re.compile(r'src=["\']([^"\']+\.js(?:\?[^"\']*)?)["\']')
API_PATH_RE = [re.compile(p) for p in VIDEO_ID_PATTERNS]

VIDEO_KEYWORDS = re.compile(
    r'video_id|aweme_id|item_id|vid=|aweme_ids|video_ids|post_id|draft_id',
    re.IGNORECASE
)


def fetch(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None


def extract_js_urls(html, base_url):
    return [urljoin(base_url, m) for m in JS_URL_PATTERN.findall(html or "")]


def extract_api_paths(js_text):
    found = set()
    for pattern in API_PATH_RE:
        for m in pattern.findall(js_text or ""):
            if VIDEO_KEYWORDS.search(js_text[max(0, js_text.find(m)-200):js_text.find(m)+200]):
                found.add(m)
    return found


def process_host(host):
    host = host.strip()
    if not host:
        return set()
    if not host.startswith("http"):
        host = "https://" + host

    results = set()
    html = fetch(host)
    if not html:
        return results

    js_urls = extract_js_urls(html, host)
    # Limit to first 20 JS files per host
    for js_url in js_urls[:20]:
        js_text = fetch(js_url)
        if js_text and len(js_text) > 500:
            paths = extract_api_paths(js_text)
            for p in paths:
                results.add(f"{host.rstrip('/')} {p}")

    return results


def main():
    try:
        with open(LIVE_SUBS_FILE) as f:
            hosts = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        # Fallback: scan key hosts directly
        hosts = [
            "https://www.tiktok.com",
            "https://webapp.tiktok.com",
        ]
        print(f"[!] {LIVE_SUBS_FILE} not found, using fallback hosts")

    print(f"[*] Scanning {len(hosts)} hosts for JS endpoints ...")
    all_results = set()

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(process_host, h): h for h in hosts}
        for i, f in enumerate(as_completed(futures), 1):
            res = f.result()
            all_results.update(res)
            if i % 10 == 0:
                print(f"  [{i}/{len(hosts)}] {len(all_results)} endpoints found so far")

    with open(JS_ENDPOINTS_FILE, "w") as f:
        for r in sorted(all_results):
            f.write(r + "\n")

    print(f"[+] Done. {len(all_results)} candidate endpoints saved to {JS_ENDPOINTS_FILE}")


if __name__ == "__main__":
    main()
