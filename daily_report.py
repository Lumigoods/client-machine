#!/usr/bin/env python3
"""Daily ad-spend vs. sales report for the USD 47 Gumroad product.

Pulls daily spend, link clicks and landing page views for the 'CM' campaigns
from the Meta Graph API, and daily sales from the Gumroad API, then prints:

- one row per day: spend, landing page views, sales, revenue, cost per sale
  and ROAS (revenue / spend, both in USD)
- one row per ad for the whole period
- the break-even cost per sale, so you can see at a glance whether ads pay

Days are counted in the ad account's time zone. Meta spend is converted to
USD with --myr-per-usd. Gumroad is optional: without GUMROAD_ACCESS_TOKEN the
report shows the Meta side only.

Environment variables:
  META_ACCESS_TOKEN, META_AD_ACCOUNT_ID   same as ad_monitor.py
  GUMROAD_ACCESS_TOKEN                   Gumroad -> Settings -> Advanced ->
                                         Applications -> create app -> token
  GUMROAD_PRODUCT_ID                     optional; limits sales to one product
"""

import argparse
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from zoneinfo import ZoneInfo

import requests

META_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "")
# Without a token, it comes from a network secret added by the proxy.
META_AUTH = {"access_token": META_TOKEN} if META_TOKEN else {}
GUMROAD_TOKEN = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
GUMROAD_PRODUCT_ID = os.environ.get("GUMROAD_PRODUCT_ID", "")
API_VERSION = os.environ.get("META_API_VERSION", "v23.0")

PRODUCT_PRICE_USD = 47.00
# Gumroad's fee on direct sales: 10% + USD 0.50 per sale. Check your plan.
GUMROAD_FEE_PCT = 0.10
GUMROAD_FEE_FIXED_USD = 0.50


def fetch_json(url, params, what):
    """GET a URL and return the JSON body; exit with a clean message on failure."""
    try:
        resp = requests.get(url, params=params, timeout=60)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        # Don't print the exception: its URL contains the access token.
        sys.exit(f"Could not reach the {what} API ({type(exc).__name__}).")
    return body


def meta_daily_ad_rows(account_id, keyword, since, until):
    """Return one insights row per ad per day for campaigns matching the keyword."""
    url = f"https://graph.facebook.com/{API_VERSION}/{account_id}/insights"
    params = {
        **META_AUTH,
        "level": "ad",
        "time_increment": 1,
        "time_range": json.dumps({"since": since.isoformat(), "until": until.isoformat()}),
        "fields": "ad_id,ad_name,adset_name,spend,impressions,inline_link_clicks,actions",
        "filtering": json.dumps(
            [{"field": "campaign.name", "operator": "CONTAIN", "value": keyword}]
        ),
        "limit": 500,
    }
    rows = []
    while url:
        body = fetch_json(url, params, "Meta Graph")
        if "error" in body:
            err = body["error"]
            sys.exit(f"Graph API error ({err.get('code')}): {err.get('message')}")
        rows.extend(body.get("data", []))
        url, params = body.get("paging", {}).get("next"), None
    return rows


def gumroad_sales(since, until, tz):
    """Return non-refunded sales as (local_date, price_usd), or None if not configured."""
    if not GUMROAD_TOKEN:
        return None
    params = {
        "access_token": GUMROAD_TOKEN,
        # Gumroad filters by UTC date; widen by a day and filter locally.
        "after": (since - dt.timedelta(days=1)).isoformat(),
        "before": (until + dt.timedelta(days=1)).isoformat(),
    }
    if GUMROAD_PRODUCT_ID:
        params["product_id"] = GUMROAD_PRODUCT_ID
    sales = []
    while True:
        body = fetch_json("https://api.gumroad.com/v2/sales", params, "Gumroad")
        if not body.get("success"):
            sys.exit(f"Gumroad API error: {body.get('message', 'unknown error')}")
        for s in body.get("sales", []):
            if s.get("refunded") or s.get("chargedback") or s.get("disputed"):
                continue
            created = dt.datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
            day = created.astimezone(tz).date()
            if since <= day <= until:
                sales.append((day, int(s.get("price", 0)) / 100))
        if not body.get("next_page_key"):
            return sales
        params["page_key"] = body["next_page_key"]


def landing_page_views(row):
    for a in row.get("actions", []):
        if a["action_type"] == "landing_page_view":
            return int(a["value"])
    return 0


def fmt_ratio(value, suffix=""):
    return "-" if value is None else f"{value:,.2f}{suffix}"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=7, help="Days to report, ending today (default 7)")
    parser.add_argument("--keyword", default="CM", help="Campaign name filter (default: CM)")
    parser.add_argument("--myr-per-usd", type=float, default=4.20,
                        help="Exchange rate for converting ad spend to USD (default 4.20; update it)")
    args = parser.parse_args()

    if not AD_ACCOUNT_ID:
        sys.exit("Set META_AD_ACCOUNT_ID, and META_ACCESS_TOKEN unless the token is a network secret (see README.md).")
    account_id = AD_ACCOUNT_ID if AD_ACCOUNT_ID.startswith("act_") else f"act_{AD_ACCOUNT_ID}"

    account = fetch_json(f"https://graph.facebook.com/{API_VERSION}/{account_id}",
                         {**META_AUTH, "fields": "currency,timezone_name"}, "Meta Graph")
    if "error" in account:
        sys.exit(f"Graph API error: {account['error'].get('message')}")
    tz = ZoneInfo(account["timezone_name"])
    currency = account["currency"]
    rate = args.myr_per_usd if currency == "MYR" else 1.0
    until = dt.datetime.now(tz).date()
    since = until - dt.timedelta(days=args.days - 1)

    rows = meta_daily_ad_rows(account_id, args.keyword, since, until)
    sales = gumroad_sales(since, until, tz)

    by_day = defaultdict(lambda: {"spend": 0.0, "lpv": 0, "clicks": 0, "sales": 0, "revenue": 0.0})
    by_ad = defaultdict(lambda: {"adset": "", "spend": 0.0, "impressions": 0, "clicks": 0, "lpv": 0})
    for r in rows:
        day = dt.date.fromisoformat(r["date_start"])
        spend = float(r.get("spend", 0))
        by_day[day]["spend"] += spend
        by_day[day]["clicks"] += int(r.get("inline_link_clicks", 0))
        by_day[day]["lpv"] += landing_page_views(r)
        ad = by_ad[r["ad_name"]]
        ad["adset"] = r.get("adset_name", "")
        ad["spend"] += spend
        ad["impressions"] += int(r.get("impressions", 0))
        ad["clicks"] += int(r.get("inline_link_clicks", 0))
        ad["lpv"] += landing_page_views(r)
    for day, price in sales or []:
        by_day[day]["sales"] += 1
        by_day[day]["revenue"] += price

    net_per_sale = PRODUCT_PRICE_USD * (1 - GUMROAD_FEE_PCT) - GUMROAD_FEE_FIXED_USD
    print(f"Daily report: '{args.keyword}' campaigns, {since} to {until} ({account['timezone_name']})")
    print(f"Product: USD {PRODUCT_PRICE_USD:.2f}, about USD {net_per_sale:.2f} after Gumroad fees "
          f"= break-even cost per sale")
    if currency == "MYR":
        print(f"Spend converted at {args.myr_per_usd:.2f} MYR per USD")
    if sales is None:
        print("Gumroad: GUMROAD_ACCESS_TOKEN not set, so sales columns are empty.")
    print()

    header = (f"{'Date':<10} {'Spend ' + currency:>11} {'Spend USD':>10} {'Clicks':>7} {'LPV':>5} "
              f"{'Sales':>6} {'Rev USD':>9} {'CPA USD':>8} {'ROAS':>6}")
    print(header)
    print("-" * len(header))
    tot = {"spend": 0.0, "clicks": 0, "lpv": 0, "sales": 0, "revenue": 0.0}
    for i in range(args.days):
        day = since + dt.timedelta(days=i)
        d = by_day[day]
        for k in tot:
            tot[k] += d[k]
        print(_day_line(str(day), d, rate))
    print("-" * len(header))
    print(_day_line("TOTAL", tot, rate))

    print(f"\nBy ad ({since} to {until})")
    header = f"{'Ad':<20} {'Spend ' + currency:>11} {'Impr':>6} {'Clicks':>7} {'LPV':>5} {'Cost/LPV':>9}"
    print(header)
    print("-" * len(header))
    for name, a in sorted(by_ad.items()):
        cost_lpv = a["spend"] / a["lpv"] if a["lpv"] else None
        print(f"{name[:20]:<20} {a['spend']:>11,.2f} {a['impressions']:>6,} {a['clicks']:>7,} "
              f"{a['lpv']:>5,} {fmt_ratio(cost_lpv):>9}")

    spend_usd = tot["spend"] / rate
    print()
    if sales is not None and tot["lpv"]:
        print(f"Landing page -> sale conversion: {tot['sales'] / tot['lpv'] * 100:.1f}% "
              f"({tot['sales']} of {tot['lpv']})")
    if tot["sales"]:
        cpa = spend_usd / tot["sales"]
        verdict = "profitable" if cpa < net_per_sale else "losing money"
        print(f"Cost per sale USD {cpa:.2f} vs break-even USD {net_per_sale:.2f}: {verdict} per sale")
    elif sales is not None:
        print(f"No sales yet. Spend so far is USD {spend_usd:.2f}; break-even is "
              f"one sale per USD {net_per_sale:.2f} of spend.")


def _day_line(label, d, rate):
    spend_usd = d["spend"] / rate
    cpa = spend_usd / d["sales"] if d["sales"] else None
    roas = d["revenue"] / spend_usd if spend_usd else None
    return (f"{label:<10} {d['spend']:>11,.2f} {spend_usd:>10,.2f} {d['clicks']:>7,} {d['lpv']:>5,} "
            f"{d['sales']:>6,} {d['revenue']:>9,.2f} {fmt_ratio(cpa):>8} {fmt_ratio(roas, 'x'):>6}")


if __name__ == "__main__":
    main()
