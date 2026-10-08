#!/usr/bin/env python3
"""Fetch active campaign metrics for the 'CM' project from the Meta Graph API.

For every ACTIVE campaign in the ad account whose name contains the project
keyword, prints each ad's status, effective status, Spend, Clicks and CTR, and
flags delivery issues, review feedback and active ads that aren't delivering.
"""

import argparse
import json
import os
import sys

import requests

# --- Configuration -----------------------------------------------------------
# Replace these placeholders, or set META_ACCESS_TOKEN / META_AD_ACCOUNT_ID
# environment variables (recommended, so the token never lands in git).
ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "YOUR_AD_ACCOUNT_ID_HERE")

API_VERSION = os.environ.get("META_API_VERSION", "v23.0")
PROJECT_KEYWORD = "CM"
# -----------------------------------------------------------------------------

BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


def graph_get(path, params):
    """GET a Graph API edge and follow pagination, returning all rows."""
    url = f"{BASE_URL}/{path}"
    params = {**params, "access_token": ACCESS_TOKEN}
    rows = []
    while url:
        try:
            resp = requests.get(url, params=params, timeout=30)
            body = resp.json()
        except (requests.RequestException, ValueError) as exc:
            # Don't print the exception: its URL contains the access token.
            sys.exit(f"Could not reach the Graph API ({type(exc).__name__}). "
                     "Check your network connection and try again.")
        if "error" in body:
            err = body["error"]
            sys.exit(f"Graph API error ({err.get('code')}): {err.get('message')}")
        rows.extend(body.get("data", []))
        # The "next" URL already carries every query parameter.
        url = body.get("paging", {}).get("next")
        params = None
    return rows


def get_active_campaigns(account_id, keyword):
    """Return ACTIVE campaigns whose name contains the keyword."""
    return graph_get(
        f"{account_id}/campaigns",
        {
            "fields": "id,name",
            "effective_status": json.dumps(["ACTIVE"]),
            "filtering": json.dumps(
                [{"field": "name", "operator": "CONTAIN", "value": keyword}]
            ),
            "limit": 100,
        },
    )


def get_ads(campaign_id):
    """Return every ad in the campaign (any status), with delivery diagnostics."""
    return graph_get(
        f"{campaign_id}/ads",
        {
            "fields": "id,name,status,effective_status,issues_info,ad_review_feedback",
            "limit": 100,
        },
    )


def get_ad_metrics(account_id, campaign_ids, date_preset):
    """Return ad-level insights for every ad in the given campaigns."""
    return graph_get(
        f"{account_id}/insights",
        {
            "level": "ad",
            "fields": "ad_id,ad_name,spend,impressions,clicks,ctr",
            "date_preset": date_preset,
            "filtering": json.dumps(
                [{"field": "campaign.id", "operator": "IN", "value": campaign_ids}]
            ),
            "limit": 100,
        },
    )


def print_report(campaign, ads, metrics):
    by_id = {m["ad_id"]: m for m in metrics}
    header = (f"{'Ad':<30} {'Status':<8} {'Effective status':<18} "
              f"{'Spend':>10} {'Clicks':>7} {'CTR %':>7}")
    print(f"Campaign: {campaign['name']} ({campaign['id']})")
    print(header)
    print("-" * len(header))

    totals = {"spend": 0.0, "impressions": 0, "clicks": 0}
    problems = []
    for ad in ads:
        m = by_id.get(ad["id"], {})  # ads with no delivery have no insights row
        spend = float(m.get("spend", 0))
        impressions = int(m.get("impressions", 0))
        clicks = int(m.get("clicks", 0))
        ctr = float(m.get("ctr", 0))
        totals["spend"] += spend
        totals["impressions"] += impressions
        totals["clicks"] += clicks
        print(f"{ad['name'][:30]:<30} {ad['status']:<8} {ad['effective_status']:<18} "
              f"{spend:>10,.2f} {clicks:>7,} {ctr:>7.2f}")

        for issue in ad.get("issues_info", []):
            problems.append(f"{ad['name']}: {issue.get('level', 'ISSUE')} - "
                            f"{issue.get('error_summary') or issue.get('error_message')}")
        for placement, reason in (ad.get("ad_review_feedback") or {}).get("global", {}).items():
            problems.append(f"{ad['name']}: review feedback ({placement}) - {reason}")
        if ad["effective_status"] == "ACTIVE" and impressions == 0:
            problems.append(f"{ad['name']}: active but has no impressions in this period")

    total_ctr = totals["clicks"] / totals["impressions"] * 100 if totals["impressions"] else 0
    print("-" * len(header))
    print(f"{'TOTAL':<30} {'':<8} {'':<18} {totals['spend']:>10,.2f} "
          f"{totals['clicks']:>7,} {total_ctr:>7.2f}")

    if problems:
        print("\nIssues:")
        for p in problems:
            print(f"  - {p}")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date-preset",
        default="last_7d",
        help="Graph API date preset, e.g. today, yesterday, last_7d, last_30d, maximum",
    )
    parser.add_argument("--keyword", default=PROJECT_KEYWORD, help="Campaign name filter")
    args = parser.parse_args()

    if "YOUR_" in ACCESS_TOKEN or "YOUR_" in AD_ACCOUNT_ID:
        sys.exit("Set your Access Token and Ad Account ID (see README.md).")

    account_id = AD_ACCOUNT_ID if AD_ACCOUNT_ID.startswith("act_") else f"act_{AD_ACCOUNT_ID}"

    campaigns = get_active_campaigns(account_id, args.keyword)
    if not campaigns:
        print(f"No active campaigns matching '{args.keyword}' in {account_id}.")
        return

    metrics = get_ad_metrics(account_id, [c["id"] for c in campaigns], args.date_preset)
    print(f"Ads in active '{args.keyword}' campaigns in {account_id} ({args.date_preset})\n")
    for campaign in campaigns:
        print_report(campaign, get_ads(campaign["id"]), metrics)


if __name__ == "__main__":
    main()
