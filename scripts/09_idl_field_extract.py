#!/usr/bin/env python3
"""
Step 9: Extract full request field schemas from an already-downloaded
CreativeOne IDL bundle (idls.*.js). Many of the small helper functions in
that bundle look like:

    function a(e,t){var r=n.genBaseURL("/CreativeOne/Asset/BatchGetImgURLs"),
    a={imageURIs:e.imageURIs};return n.request({url:r,method:"POST",data:a,...},t)}

This pulls out every (path, field-list) pair we can find that way, so we
don't have to guess request bodies by hand.
"""

import re
import sys

IDL_FILE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/adsjs/idls.4695b4c7.js"

with open(IDL_FILE, "r", errors="ignore") as f:
    data = f.read()

PATH_CALL = re.compile(
    r'genBaseURL\("(/CreativeOne/[A-Za-z0-9/]+)"\)\s*,\s*[a-zA-Z_$][\w$]*\s*=\s*(\{[^{}]*\})'
)
FIELD_NAME = re.compile(r'([A-Za-z_$][\w$]*)\s*:\s*[a-zA-Z_$][\w$]*\.[A-Za-z_$][\w$]*')

URL_KEYWORDS = re.compile(
    r'URL|Uri\b|Asset|Material|Preview|Download|Share|Cover|Thumb|Img|Video|Photo',
    re.IGNORECASE,
)

seen = {}
for m in PATH_CALL.finditer(data):
    path, fields_blob = m.group(1), m.group(2)
    fields = tuple(FIELD_NAME.findall(fields_blob))
    seen[path] = fields  # last one wins, dedups automatically

print(f"Total call-sites with inline field mapping: {len(seen)}\n")

relevant = {p: f for p, f in seen.items() if URL_KEYWORDS.search(p)}
print(f"URL/asset-shaped ones: {len(relevant)}\n")
for path in sorted(relevant):
    print(f"{path}")
    print(f"    fields: {list(relevant[path])}\n")
