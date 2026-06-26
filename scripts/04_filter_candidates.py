#!/usr/bin/env python3
"""
Step 4: Filter all collected URLs/paths down to candidates that:
  - Accept video_id / aweme_id / item_id type parameters
  - Are in domains that could serve video content
  - Match patterns seen in your original bug (draft, editor, preview, download, play, stream)
"""

import re
from pathlib import Path

OUT = "/home/user/BBT/output"

# High-value endpoint keyword patterns — endpoints likely to serve video content
HIGH_VALUE = re.compile(
    r'/(draft|preview|play|stream|download|export|clip|trim|edit|duet|stitch|remix|'
    r'caption|subtitle|cover|thumbnail|media|video|aweme|item|post)[/_]',
    re.IGNORECASE
)

# Parameters that indicate video_id acceptance
VIDEO_PARAM = re.compile(
    r'(video_id|aweme_id|item_id|aweme_ids|vid=|post_id|draft_id|clip_id)',
    re.IGNORECASE
)

# Domains of interest (TikTok asset scope)
TIKTOK_DOMAIN = re.compile(
    r'tiktok\.com|tiktokv\.com|tiktokcdn\.com|tiktokstatic\.com',
    re.IGNORECASE
)

# Exclude static/non-API paths
EXCLUDE = re.compile(
    r'\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|css|map|txt|xml|json)(\?|$)',
    re.IGNORECASE
)

input_files = [
    f"{OUT}/gau_raw_urls.txt",
    f"{OUT}/gau_paths.txt",
    f"{OUT}/js_extracted_endpoints.txt",
]

candidates = set()
all_lines = []

for fp in input_files:
    try:
        with open(fp) as f:
            all_lines.extend(f.readlines())
    except FileNotFoundError:
        pass

print(f"[*] Total input lines: {len(all_lines)}")

for line in all_lines:
    line = line.strip()
    if not line:
        continue
    if EXCLUDE.search(line):
        continue
    if not TIKTOK_DOMAIN.search(line):
        continue
    if HIGH_VALUE.search(line):
        candidates.add(line)

print(f"[*] High-value candidates: {len(candidates)}")

# Further split into tiers
tier1 = set()  # Directly matches draft/editor/download/play patterns
tier2 = set()  # Other video-adjacent

TIER1 = re.compile(
    r'/(draft|post_draft|editor_tool|download|export|play|stream|duet|stitch|remix)',
    re.IGNORECASE
)

for c in candidates:
    if TIER1.search(c):
        tier1.add(c)
    else:
        tier2.add(c)

out_all = f"{OUT}/candidates_all.txt"
out_t1  = f"{OUT}/candidates_tier1.txt"
out_t2  = f"{OUT}/candidates_tier2.txt"

with open(out_all, "w") as f:
    f.write("\n".join(sorted(candidates)) + "\n")

with open(out_t1, "w") as f:
    f.write("\n".join(sorted(tier1)) + "\n")

with open(out_t2, "w") as f:
    f.write("\n".join(sorted(tier2)) + "\n")

print(f"[+] Tier 1 (highest priority): {len(tier1)} → {out_t1}")
print(f"[+] Tier 2 (medium priority):  {len(tier2)} → {out_t2}")
print(f"[+] All candidates: {out_all}")

# Print top tier1 for quick review
print("\n--- TIER 1 PREVIEW (first 30) ---")
for c in sorted(tier1)[:30]:
    print(" ", c)
