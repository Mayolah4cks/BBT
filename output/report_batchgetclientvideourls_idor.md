# Broken Access Control (IDOR) in CreativeOne/Asset/BatchGetClientVideoURLs — Subscriber-Only Video Disclosure

## Summary

The endpoint `POST /CreativeOne/Asset/BatchGetClientVideoURLs` on `ads.tiktok.com`
returns a playable/downloadable URL for **any** `videoID` supplied in the request
body, without verifying that the authenticated caller has a subscription to, or
any authorized relationship with, the content owner. This allows any
authenticated `ads.tiktok.com` user to bypass TikTok's subscriber-only ("sub
only") content paywall and view video content they have not paid for and are
not authorized to access, simply by supplying the video's ID.

This is the same root-cause issue as `CreativeOne/Asset/BatchGetImgURLs`
(same `Asset` service, same missing ownership check), suggesting the
underlying authorization gap is systemic to this internal asset-resolution
service rather than a one-off bug in a single handler.

## Vulnerability Class

- **Type:** Broken Access Control / Insecure Direct Object Reference (IDOR)
- **CWE:** CWE-639 (Authorization Bypass Through User-Controlled Key)
- **OWASP:** A01:2021 – Broken Access Control

## Affected Asset

- **Host:** `ads.tiktok.com`
- **Endpoint:** `POST /CreativeOne/Asset/BatchGetClientVideoURLs`
- **Application:** TikTok One (Creative Assets), reachable from
  `https://ads.tiktok.com/creative/assets/my-brand?region=row`

## Prerequisites

- Any valid, authenticated `ads.tiktok.com` session (i.e. any advertiser/user
  account in good standing — no special privileges required).
- The numeric `video_id` / `aweme_id` of a subscriber-only video belonging to
  a creator the tester has **not** subscribed to (video IDs for locked
  content are visible in public post metadata even though playback is
  gated — see Steps to Reproduce).

## Steps to Reproduce

1. Identify a TikTok video published under a creator's paid subscription
   (sub-only) tier. Obtain its `video_id`
   (e.g. from the post's public metadata/URL — playback is gated, but the ID
   itself is exposed) — `[REDACTED_SUB_ONLY_VIDEO_ID]`.
2. Confirm the tester's TikTok/ads.tiktok.com account has **no** active
   subscription to that creator, and no other relationship (not a
   collaborator, not the creator's own account, no shared campaign/order).
3. Using an authenticated `ads.tiktok.com` session (any advertiser account),
   send the following request:

   ```
   POST /CreativeOne/Asset/BatchGetClientVideoURLs HTTP/2
   Host: ads.tiktok.com
   Cookie: <valid session cookie>
   Content-Type: application/json
   X-Csrftoken: <valid csrf token>
   Origin: https://ads.tiktok.com
   Referer: https://ads.tiktok.com/creative/assets/my-brand?region=row

   {"videoIDs":["[REDACTED_SUB_ONLY_VIDEO_ID]"]}
   ```

4. Observe the response contains a valid, directly playable video URL for
   the requested `videoID`.
5. Open the returned URL directly (no TikTok session/subscription attached)
   and confirm the sub-only video plays back in full.

## Proof of Concept

**Request:**
```
[PASTE your redacted request here — strip Cookie/X-Csrftoken values before
sharing anywhere outside the report form]
```

**Response:**
```
[PASTE the redacted JSON response here, keeping the returned video URL
structure but redacting anything account-identifying if needed]
```

**Evidence:** [Attach screenshot/screen recording showing: (1) the request/
response in Burp, and (2) the returned URL playing the sub-only video in a
fresh browser session with no subscription to the creator.]

## Impact

- Any authenticated `ads.tiktok.com` user can retrieve playable URLs for
  **any** video on the platform by ID, including content gated behind
  creator paid subscriptions, entirely bypassing the paywall.
- Video IDs are not high-entropy secrets — they are routinely exposed in
  public post metadata, share links, and app responses — making this
  practically exploitable at scale (e.g. scripted enumeration against a
  list of known sub-only video IDs).
- Direct harm: loss of revenue/incentive for creators relying on
  subscription-gated content; violation of the content owner's and
  subscribers' expectation of access control.
- The sibling endpoint `BatchGetImgURLs` in the same `Asset` service
  accepts an analogous `imageURIs` parameter and is expected to share the
  same root cause for photo-mode/sub-only image content (recommend TikTok's
  security team audit the entire `CreativeOne/Asset/*` namespace for the
  same missing check, not just this one method).

## Suggested Remediation

Before minting/returning a URL for any given `videoID`, the service should
verify that the authenticated caller has the relationship the front-end flow
this endpoint was built for actually requires — e.g., an active subscription
to the content's creator, ownership of the asset, or membership in the
order/campaign the asset is scoped to — and reject the request (403) if not.
Given the same pattern likely repeats across `BatchGetImgURLs` and possibly
other `Batch*`/`M*` endpoints in the same service, a shared authorization
check at the service layer (rather than per-handler) is recommended.

## Severity (suggested)

High — unauthenticated-relative-to-content-owner disclosure of paid/gated
media at scale, no user interaction required beyond having any valid
platform account.

---
*Report drafted [DATE]. Tested against the tester's own account(s) only;
no other users' accounts or data beyond the described video ID were
accessed or modified.*
