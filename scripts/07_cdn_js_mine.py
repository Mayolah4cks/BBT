#!/usr/bin/env python3
"""
Mine TikTok CDN JS bundles for API endpoints.
Fetches the real JS files served from tiktokcdn-us.com and extracts
API paths that reference video/draft/subscription/aweme concepts.
"""

import re
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT = "/home/user/BBT/output"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.tiktok.com/",
}

# Fetch the studio upload page to get current JS bundle URLs
STUDIO_PAGES = [
    "https://www.tiktok.com/tiktokstudio/upload",
    "https://www.tiktok.com/tiktokstudio/content",
    "https://www.tiktok.com/tiktokstudio/content?tab=draft",
]

JS_URL_RE = re.compile(r'https?://(?:lf\d+-tiktok-web\.tiktokcdn[^"<>\s]+\.js|lf\d+-cdn-tos\.tiktokcdn[^"<>\s]+\.js)')

# API endpoint extraction — look for string literals that look like paths
PATH_RE = re.compile(
    r'''["'`]((?:/(?:api|aweme|tiktok_creator|creator|web|v\d+|tiktokstudio))[/a-zA-Z0-9_\-\.]{5,})["'`]'''
)

# Context keywords that indicate this path touches gated video content
HIGH_VALUE_CTX = re.compile(
    r'video_id|aweme_id|item_id|draft_id|subscription|sub_only|vid\b|'
    r'play_url|download|stream|audio|post_draft|editor_tool|vedit|'
    r'media_draft|video_file|aweme_detail|item_info',
    re.IGNORECASE
)

PRIORITY_PATH = re.compile(
    r'draft|editor|upload|download|export|preview|play|stream|clip|trim|'
    r'duet|stitch|remix|caption|subtitle|cover|thumbnail|aweme|subscription|'
    r'post_draft|video_param|media_draft|vedit|player|item_info|aweme_detail',
    re.IGNORECASE
)

EXCLUDE_PATH = re.compile(r'\.(png|jpg|css|woff|svg|ico|gif|webp|ttf)|node_modules|__webpack')


def fetch(url, timeout=20):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None


def get_js_urls_from_page(page_url):
    html = fetch(page_url)
    if not html:
        return set()
    return set(JS_URL_RE.findall(html))


def mine_js(js_url):
    js = fetch(js_url)
    if not js or len(js) < 500:
        return []

    results = []
    for m in PATH_RE.finditer(js):
        path = m.group(1)
        if EXCLUDE_PATH.search(path):
            continue
        if path.count('/') < 2:
            continue

        start = max(0, m.start() - 400)
        end = min(len(js), m.end() + 400)
        ctx = js[start:end]

        is_priority = bool(PRIORITY_PATH.search(path))
        has_video_ctx = bool(HIGH_VALUE_CTX.search(ctx))

        if is_priority or has_video_ctx:
            results.append({
                "path": path,
                "source": js_url,
                "priority": "HIGH" if (is_priority and has_video_ctx) else ("MEDIUM" if is_priority or has_video_ctx else "LOW"),
                "ctx": ctx[350:450].replace("\n", " ")[:120],
            })
    return results


def main():
    # Collect all JS URLs
    js_urls = set()
    for page in STUDIO_PAGES:
        print(f"[*] Fetching JS list from: {page}")
        found = get_js_urls_from_page(page)
        js_urls.update(found)
        print(f"    {len(found)} JS URLs found")

    print(f"\n[*] Total unique JS bundles: {len(js_urls)}")

    # Mine all JS files
    all_results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(mine_js, url): url for url in js_urls}
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            all_results.extend(res)
            if i % 20 == 0:
                print(f"  [{i}/{len(js_urls)}] {len(all_results)} raw endpoints found")

    # Deduplicate by path, keep highest priority
    seen = {}
    for ep in all_results:
        path = ep["path"]
        if path not in seen:
            seen[path] = ep
        elif ep["priority"] == "HIGH" and seen[path]["priority"] != "HIGH":
            seen[path] = ep

    deduped = list(seen.values())
    high   = sorted([e for e in deduped if e["priority"] == "HIGH"],   key=lambda x: x["path"])
    medium = sorted([e for e in deduped if e["priority"] == "MEDIUM"], key=lambda x: x["path"])
    low    = sorted([e for e in deduped if e["priority"] == "LOW"],    key=lambda x: x["path"])

    # Save outputs
    with open(f"{OUT}/cdn_endpoints_full.json", "w") as f:
        json.dump(deduped, f, indent=2)

    with open(f"{OUT}/cdn_endpoints_HIGH.txt", "w") as f:
        for e in high:
            f.write(e["path"] + "\n")

    with open(f"{OUT}/cdn_endpoints_MEDIUM.txt", "w") as f:
        for e in medium:
            f.write(e["path"] + "\n")

    print(f"\n[+] Unique paths: {len(deduped)}")
    print(f"    HIGH:   {len(high)}")
    print(f"    MEDIUM: {len(medium)}")
    print(f"    LOW:    {len(low)}")

    print("\n=== HIGH PRIORITY ENDPOINTS ===")
    for e in high:
        print(f"  {e['path']}")
        print(f"    [{e['source'].split('/')[-1]}]  ctx: {e['ctx']}")
        print()


if __name__ == "__main__":
    main()
