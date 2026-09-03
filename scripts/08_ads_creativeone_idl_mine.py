#!/usr/bin/env python3
"""
Step 8: Mine the CreativeOne IDL bundle served to ads.tiktok.com ("TikTok One" /
creative asset app — same app that serves /CreativeOne/Asset/BatchGetImgURLs).

The SPA shell at /creative/assets/* references a shared webpack chunk whose
filename contains "idls" — it's an auto-generated RPC interface manifest
listing every backend method path for the CreativeOne service, e.g.:
    CreativeOne/Asset/BatchGetImgURLs
    CreativeOne/Asset/BatchGetClientVideoURLs

No authentication is needed to fetch these static JS chunks — only calling
the resulting endpoints requires a session. This script only reads public
static assets; it does not send any authenticated requests.
"""

import re
import json
import requests

OUT = "/home/user/BBT/output"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Entry pages for the CreativeOne / "TikTok One" app on ads.tiktok.com
ENTRY_PAGES = [
    "https://ads.tiktok.com/creative/assets/my-brand?region=row",
]

JS_SRC = re.compile(r'src="(https?:)?(//[^"]+\.js(?:\?[^"]*)?)"')

# RPC-style path: 2+ PascalCase segments, e.g. Asset/BatchGetImgURLs
RPC_PATH = re.compile(r'\bCreativeOne(?:/[A-Z][A-Za-z0-9]+){2,}')

# Keywords marking a path as "returns/consumes a viewable URL/URI for an asset"
# — the same shape as BatchGetImgURLs — and therefore worth checking for IDOR
# (does it verify the caller owns the referenced asset before minting a URL?).
URL_DISCLOSURE_KEYWORDS = re.compile(
    r'URL|Uri\b|Asset|Material|Preview|Download|Share[Ll]ink|Cover|Thumb',
    re.IGNORECASE,
)


def fetch(url, timeout=20):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None


def find_js_urls(html):
    urls = set()
    for scheme, path in JS_SRC.findall(html):
        full = ("https:" if not scheme else scheme) + path
        urls.add(full)
    return urls


def main():
    all_paths = set()
    idl_sources = []

    for page in ENTRY_PAGES:
        print(f"[*] Fetching entry page: {page}")
        html = fetch(page)
        if not html:
            print("    [!] failed to fetch (may require auth or be geo/CDN blocked)")
            continue

        js_urls = find_js_urls(html)
        print(f"    {len(js_urls)} JS bundles referenced")

        # Prioritize the chunk(s) whose filename hints at IDL/interface defs,
        # but fall back to scanning everything if none match.
        idl_candidates = [u for u in js_urls if "idl" in u.lower()]
        targets = idl_candidates if idl_candidates else js_urls

        for js_url in targets:
            js = fetch(js_url, timeout=30)
            if not js:
                continue
            found = set(RPC_PATH.findall(js))
            if found:
                idl_sources.append(js_url)
                all_paths.update(found)

    if not all_paths:
        print("[!] No CreativeOne RPC paths found. The bundle hash/name may have "
              "changed — open the entry page in a browser, find the JS chunk "
              "containing 'CreativeOne/Asset/BatchGetImgURLs' via view-source or "
              "devtools, and add its URL to ENTRY_PAGES/idl_candidates.")
        return

    sorted_paths = sorted(all_paths)
    disclosure_candidates = sorted(p for p in sorted_paths if URL_DISCLOSURE_KEYWORDS.search(p))

    with open(f"{OUT}/creativeone_endpoints_full.txt", "w") as f:
        for p in sorted_paths:
            f.write(p + "\n")

    with open(f"{OUT}/creativeone_url_disclosure_candidates.txt", "w") as f:
        for p in disclosure_candidates:
            f.write(p + "\n")

    print(f"\n[+] IDL source(s): {idl_sources}")
    print(f"[+] Total unique CreativeOne endpoints: {len(sorted_paths)} -> "
          f"{OUT}/creativeone_endpoints_full.txt")
    print(f"[+] URL/asset-disclosure-shaped candidates: {len(disclosure_candidates)} -> "
          f"{OUT}/creativeone_url_disclosure_candidates.txt")
    print("\n--- candidates (endpoints that mint or consume a URL/URI for an asset) ---")
    for p in disclosure_candidates:
        print(f"  {p}")


if __name__ == "__main__":
    main()
