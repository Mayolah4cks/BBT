#!/usr/bin/env python3
"""
Deep scan of TikTok Studio / Creator Center JS bundles.
These are the richest source of undocumented API endpoints.
Targets: www.tiktok.com/tiktokstudio, creator center, ads, effect house.
"""

import re
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

OUT = "/home/user/BBT/output"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Entry pages that load the most relevant JS bundles
ENTRY_PAGES = [
    "https://www.tiktok.com/tiktokstudio/upload",
    "https://www.tiktok.com/tiktokstudio/content",
    "https://www.tiktok.com/tiktokstudio/content?tab=draft",
    "https://www.tiktok.com/creator-center/analytics",
    "https://www.tiktok.com/creator-center/inbox",
    "https://www.tiktok.com/creator#",
    "https://ads.tiktok.com/business/creativecenter/tools/detail/video_editor/pc/en",
    "https://effecthouse.tiktok.com/",
    "https://www.tiktok.com/music/",
]

# Regex to find JS bundle URLs in HTML
JS_SRC = re.compile(r'(?:src|href)=["\']([^"\']+(?:chunk|bundle|main|app|index|studio|creator)[^"\']*\.js(?:\?[^"\']*)?)["\']', re.IGNORECASE)
JS_GENERIC = re.compile(r'src=["\']([^"\']+\.js(?:\?[^"\']*)?)["\']')

# API path patterns — ordered from most to least specific
API_PATTERNS = [
    # Explicit API-looking paths with version prefix
    re.compile(r'["`\']((?:/(?:api|aweme|tiktok_creator|creator|web|studio|v\d+))[a-zA-Z0-9_/\-\.]{6,})["`\']'),
    # Paths with common action words
    re.compile(r'["`\']((?:/[a-z][a-z0-9_]+){2,}/(?:save|get|list|detail|create|update|delete|upload|download|export|preview|publish|draft|play|stream|info|check|init|query|fetch|load)[/a-z0-9_\-]*)["`\']', re.IGNORECASE),
]

# Keywords that suggest this endpoint touches video content
VIDEO_CONTEXT = re.compile(
    r'video_id|aweme_id|item_id|draft_id|vid\b|aweme\b|subscription|sub.?only|'
    r'play_url|download_url|stream|audio|media_info|post_draft|editor',
    re.IGNORECASE
)

# High-value paths we specifically want (expanded from your original bug)
PRIORITY_KEYWORDS = re.compile(
    r'draft|editor|upload|download|export|preview|play|stream|clip|trim|'
    r'duet|stitch|remix|caption|subtitle|cover|thumbnail|aweme|subscription|'
    r'post_draft|video_param|media_draft|vedit|player',
    re.IGNORECASE
)


def fetch(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def get_js_urls(html, base_url):
    urls = set()
    for pat in [JS_SRC, JS_GENERIC]:
        for m in pat.findall(html):
            full = urljoin(base_url, m)
            if urlparse(full).netloc.endswith("tiktok.com") or "tiktokstatic" in full:
                urls.add(full)
    return urls


def extract_endpoints(js_text, source_url):
    found = []
    # Slide a context window over the JS looking for video-related API paths
    for pat in API_PATTERNS:
        for m in pat.finditer(js_text):
            path = m.group(1)
            # Get surrounding context
            start = max(0, m.start() - 300)
            end = min(len(js_text), m.end() + 300)
            context = js_text[start:end]

            if VIDEO_CONTEXT.search(context) or PRIORITY_KEYWORDS.search(path):
                # Filter out obvious non-API paths
                if not re.search(r'\.(png|jpg|css|woff|svg|ico|mp4|gif)', path):
                    if len(path) > 8 and path.count('/') >= 2:
                        found.append({
                            "path": path,
                            "source": source_url,
                            "priority": "HIGH" if PRIORITY_KEYWORDS.search(path) else "MEDIUM",
                            "context_snippet": context[250:350].replace("\n", " ")[:100],
                        })
    return found


def scan_page(page_url):
    results = []
    print(f"  [>] Fetching page: {page_url}")
    html = fetch(page_url)
    if not html:
        return results

    js_urls = get_js_urls(html, page_url)
    print(f"      Found {len(js_urls)} JS files")

    for js_url in list(js_urls)[:40]:  # cap per page
        js_text = fetch(js_url, timeout=20)
        if js_text and len(js_text) > 1000:
            endpoints = extract_endpoints(js_text, js_url)
            results.extend(endpoints)

    return results


def main():
    all_endpoints = []

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(scan_page, url): url for url in ENTRY_PAGES}
        for fut in as_completed(futures):
            res = fut.result()
            all_endpoints.extend(res)

    # Deduplicate by path
    seen = {}
    for ep in all_endpoints:
        path = ep["path"]
        if path not in seen or ep["priority"] == "HIGH":
            seen[path] = ep

    deduped = list(seen.values())
    high = [e for e in deduped if e["priority"] == "HIGH"]
    medium = [e for e in deduped if e["priority"] == "MEDIUM"]

    # Save full JSON
    with open(f"{OUT}/studio_endpoints_full.json", "w") as f:
        json.dump(sorted(deduped, key=lambda x: (x["priority"], x["path"])), f, indent=2)

    # Save high-priority paths as plaintext for probing
    with open(f"{OUT}/studio_endpoints_HIGH.txt", "w") as f:
        for e in sorted(high, key=lambda x: x["path"]):
            f.write(f"{e['path']}\n")

    with open(f"{OUT}/studio_endpoints_MEDIUM.txt", "w") as f:
        for e in sorted(medium, key=lambda x: x["path"]):
            f.write(f"{e['path']}\n")

    print(f"\n[+] Total unique endpoints: {len(deduped)}")
    print(f"[+] HIGH priority: {len(high)}")
    print(f"[+] MEDIUM priority: {len(medium)}")
    print(f"\n--- HIGH PRIORITY ENDPOINTS ---")
    for e in sorted(high, key=lambda x: x["path"])[:50]:
        print(f"  {e['path']}")
        print(f"    src: {e['source']}")
        print(f"    ctx: {e['context_snippet']}")
        print()


if __name__ == "__main__":
    main()
