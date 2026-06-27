#!/usr/bin/env python3
"""
Pump.fun Community Endpoints Fetcher
Fetches community-related data from pump.fun's v3 frontend API.

Confirmed working endpoints (frontend-api-v3.pump.fun):
  GET /coins?sort=last_reply           – tokens sorted by most recent community reply
  GET /coins/currently-live            – live-streaming tokens (community engagement)
  GET /coins/recently-created          – newly launched tokens
  GET /coins/for-you                   – personalised for-you feed
  GET /coins/king-of-the-hill          – king-of-the-hill token
  GET /coins/search?q=<term>           – search tokens by name/symbol/keyword
  GET /coins/{mint}                    – single token detail (reply_count, last_reply, etc.)
  GET /users                           – list community members / users
  GET /users/{address}                 – user profile (followers, following, bio, username)

Note: /coins/{mint}/replies and /users/{address}/replies live on the v1 API
(frontend-api.pump.fun) which may be temporarily unavailable.  The script
falls back gracefully when v1 is unreachable.
"""

import json
import os
import sys
import time
import requests

BASE_V3 = "https://frontend-api-v3.pump.fun"
BASE_V1 = "https://frontend-api.pump.fun"   # replies endpoint lives here

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://pump.fun",
    "Referer": "https://pump.fun/",
}

# ──────────────────────────────────────────────
# CONFIGURE BEFORE RUNNING
# ──────────────────────────────────────────────
# Mint address of the token whose community you want to inspect.
# Leave blank to auto-use the king-of-the-hill token.
TARGET_MINT = ""

# Optional: a user's Solana wallet address to fetch their profile.
TARGET_USER = ""

# Optional: keyword to search for in the community/token list.
SEARCH_QUERY = ""

# How many tokens to pull for activity feeds.
FEED_LIMIT = 50
# ──────────────────────────────────────────────

OUT_DIR = "/home/user/BBT/output"


def get(base: str, path: str, params: dict = None) -> dict | list | None:
    url = f"{base}{path}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        if not r.content:
            return None
        return r.json()
    except requests.HTTPError as e:
        print(f"  [!] HTTP {e.response.status_code}  {url}")
    except Exception as e:
        print(f"  [!] Error {url}: {e}")
    return None


def save(filename: str, data):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = f"{OUT_DIR}/{filename}"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  → saved {path}")


def pprint_coins(coins: list, n: int = 3):
    for c in coins[:n]:
        name        = c.get("name", "?")
        symbol      = c.get("symbol", "?")
        mint        = c.get("mint", "?")
        reply_count = c.get("reply_count", "?")
        last_reply  = c.get("last_reply", "?")
        mcap        = round(c.get("market_cap", 0), 2)
        print(f"    {name} ({symbol})  replies={reply_count}  last_reply={last_reply}  mcap={mcap}  mint={mint}")


# ── 1. Tokens sorted by most recent community reply ───────────────────────────
def fetch_most_active(limit: int) -> list:
    print(f"\n[1] Tokens with most recent community replies (limit={limit})")
    data = get(BASE_V3, "/coins", params={
        "limit": limit, "offset": 0,
        "sort": "last_reply", "order": "DESC",
        "includeNsfw": "false",
    })
    coins = data if isinstance(data, list) else []
    print(f"    {len(coins)} tokens returned")
    pprint_coins(coins)
    return coins


# ── 2. Currently live tokens (community livestream activity) ──────────────────
def fetch_currently_live(limit: int) -> list:
    print(f"\n[2] Currently live tokens (limit={limit})")
    data = get(BASE_V3, "/coins/currently-live", params={"limit": limit})
    coins = data if isinstance(data, list) else []
    print(f"    {len(coins)} live tokens")
    pprint_coins(coins)
    return coins


# ── 3. Recently created tokens ────────────────────────────────────────────────
def fetch_recently_created(limit: int) -> list:
    print(f"\n[3] Recently created tokens (limit={limit})")
    data = get(BASE_V3, "/coins/recently-created", params={"limit": limit, "includeNsfw": "false"})
    coins = data if isinstance(data, list) else []
    print(f"    {len(coins)} tokens returned")
    pprint_coins(coins)
    return coins


# ── 4. For-you feed ───────────────────────────────────────────────────────────
def fetch_for_you(limit: int) -> list:
    print(f"\n[4] For-you community feed (limit={limit})")
    data = get(BASE_V3, "/coins/for-you", params={"limit": limit, "includeNsfw": "false"})
    coins = data if isinstance(data, list) else []
    print(f"    {len(coins)} tokens returned")
    pprint_coins(coins)
    return coins


# ── 5. King-of-the-hill token ─────────────────────────────────────────────────
def fetch_koth() -> dict | None:
    print("\n[5] King-of-the-hill token")
    data = get(BASE_V3, "/coins/king-of-the-hill", params={"includeNsfw": "false"})
    if data:
        print(f"    {data.get('name')} ({data.get('symbol')})  replies={data.get('reply_count')}  mint={data.get('mint')}")
    return data


# ── 6. Single token community detail ─────────────────────────────────────────
def fetch_token_detail(mint: str) -> dict | None:
    print(f"\n[6] Token community detail: {mint}")
    data = get(BASE_V3, f"/coins/{mint}")
    if data:
        fields = ["name", "symbol", "description", "reply_count", "last_reply",
                  "twitter", "telegram", "website", "market_cap", "is_currently_live"]
        summary = {k: data.get(k) for k in fields}
        for k, v in summary.items():
            print(f"    {k}: {v}")
    return data


# ── 7. Community search ────────────────────────────────────────────────────────
def fetch_search(query: str, limit: int = 50) -> list:
    print(f"\n[7] Community search: '{query}'")
    data = get(BASE_V3, "/coins/search", params={"q": query, "limit": limit})
    coins = data if isinstance(data, list) else []
    print(f"    {len(coins)} results")
    pprint_coins(coins)
    return coins


# ── 8. User community profile ──────────────────────────────────────────────────
def fetch_user_profile(address: str) -> dict | None:
    print(f"\n[8] User profile: {address}")
    data = get(BASE_V3, f"/users/{address}")
    if data:
        fields = ["username", "bio", "followers", "following", "likes_received",
                  "mentions_received", "profile_image", "x_username"]
        for k in fields:
            print(f"    {k}: {data.get(k)}")
    return data


# ── 9. Token replies (v1 API — may be unavailable) ────────────────────────────
def fetch_token_replies(mint: str, limit: int = 100) -> list:
    print(f"\n[9] Token community replies (v1): {mint}")
    all_replies = []
    for page in range(5):
        data = get(BASE_V1, f"/coins/{mint}/replies",
                   params={"limit": limit, "offset": page * limit})
        if data is None:
            print("    v1 API unreachable — skipping replies")
            break
        replies = data if isinstance(data, list) else data.get("replies", [])
        if not replies:
            break
        all_replies.extend(replies)
        print(f"    page {page + 1}: {len(replies)} replies  (total: {len(all_replies)})")
        if len(replies) < limit:
            break
        time.sleep(0.4)
    return all_replies


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    results = {}

    # 5 – KOTH (also gives us a fallback mint)
    koth = fetch_koth()
    if koth:
        results["king_of_the_hill"] = koth
        save("pump_koth.json", koth)

    # 1 – most-active-by-reply feed (fetched early so we can use it as fallback mint)
    active = fetch_most_active(FEED_LIMIT)
    results["most_active_community"] = active
    save("pump_most_active.json", active)

    # Resolve target mint: config → KOTH → first coin in activity feed
    mint = TARGET_MINT or (koth or {}).get("mint") or (active[0].get("mint") if active else None)
    if not mint:
        print("[!] No mint address. Set TARGET_MINT or check network connectivity.")
        sys.exit(1)
    print(f"\n[*] Using mint: {mint}")

    # 2 – currently live
    live = fetch_currently_live(FEED_LIMIT)
    results["currently_live"] = live
    save("pump_currently_live.json", live)

    # 3 – recently created
    recent = fetch_recently_created(FEED_LIMIT)
    results["recently_created"] = recent
    save("pump_recently_created.json", recent)

    # 4 – for-you
    foryou = fetch_for_you(FEED_LIMIT)
    results["for_you"] = foryou
    save("pump_for_you.json", foryou)

    # 6 – single token detail
    detail = fetch_token_detail(mint)
    if detail:
        results["token_detail"] = detail
        save("pump_token_detail.json", detail)

    # 7 – search
    if SEARCH_QUERY:
        search_res = fetch_search(SEARCH_QUERY)
        results["search"] = search_res
        save("pump_search.json", search_res)

    # 8 – user profile
    if TARGET_USER:
        profile = fetch_user_profile(TARGET_USER)
        if profile:
            results["user_profile"] = profile
            save("pump_user_profile.json", profile)

    # 9 – replies (v1)
    replies = fetch_token_replies(mint)
    if replies:
        results["token_replies"] = replies
        save("pump_token_replies.json", replies)

    # combined
    save("pump_communities_full.json", results)

    print("\n[+] Done — outputs in output/pump_*.json")


if __name__ == "__main__":
    main()
