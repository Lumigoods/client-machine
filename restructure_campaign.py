#!/usr/bin/env python3
"""Split a campaign's ads into one ad set each so they stop competing for budget.

Starting point: a campaign with a single ad set that holds several ads. The
script:

1. Checks that Advantage Campaign Budget (CBO) is off, i.e. the campaign has
   no campaign-level budget and ad-set budget sharing is disabled.
2. Updates the source ad set: geo targeting becomes --countries and the daily
   budget becomes --total-daily-budget split evenly across the ads. All other
   targeting (interests, ages, locales, placements) and the end date are kept.
3. Copies the source ad set once for every ad after the first (the copies
   inherit the updated targeting, budget and end date), copies each of those
   ads into its own new ad set (a new ad that reuses the original creative, so
   it shows the same post), and pauses the original ad so it doesn't also keep
   running in the source ad set. Nothing is deleted.

It runs as a dry run by default and prints the plan. Pass --apply to make the
changes. It is safe to re-run after a partial failure: the source ad set is
the campaign's oldest one, and ad sets and ads it already created (matched by
name) are reused instead of duplicated.
"""

import argparse
import json
import math
import os
import sys

import requests

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "YOUR_AD_ACCOUNT_ID_HERE")
API_VERSION = os.environ.get("META_API_VERSION", "v23.0")
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

DEFAULT_CAMPAIGN_ID = "120249369863180192"  # CM · Validation · W1


def call(method, path, **params):
    params["access_token"] = ACCESS_TOKEN
    try:
        if method == "GET":
            resp = requests.get(f"{BASE_URL}/{path}", params=params, timeout=60)
        else:
            resp = requests.post(f"{BASE_URL}/{path}", data=params, timeout=60)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        # Don't print the exception: its URL contains the access token.
        sys.exit(f"Could not reach the Graph API ({type(exc).__name__}).")
    if "error" in body:
        err = body["error"]
        detail = err.get("error_user_msg") or err.get("message")
        sys.exit(f"Graph API error on {method} {path} ({err.get('code')}): {detail}")
    return body


def get(path, **params):
    return call("GET", path, **params)


def post(path, **params):
    return call("POST", path, **params)


def money(minor_units):
    return f"{int(minor_units) / 100:,.2f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--countries", default="US,GB",
                        help="Comma-separated ISO country codes (default: US,GB)")
    parser.add_argument("--total-daily-budget", type=float, default=20.0,
                        help="Combined daily budget across all ad sets, in account "
                             "currency (default: 20.00)")
    parser.add_argument("--apply", action="store_true",
                        help="Make the changes (default is a dry run)")
    args = parser.parse_args()

    if "YOUR_" in ACCESS_TOKEN or "YOUR_" in AD_ACCOUNT_ID:
        sys.exit("Set META_ACCESS_TOKEN and META_AD_ACCOUNT_ID (see README.md).")
    account_id = AD_ACCOUNT_ID if AD_ACCOUNT_ID.startswith("act_") else f"act_{AD_ACCOUNT_ID}"
    countries = [c.strip().upper() for c in args.countries.split(",") if c.strip()]

    account = get(account_id, fields="currency,min_daily_budget")
    currency = account["currency"]

    # 1. CBO check -------------------------------------------------------------
    campaign = get(args.campaign_id, fields="name,daily_budget,lifetime_budget,"
                   "is_adset_budget_sharing_enabled,stop_time")
    cbo_on = (int(campaign.get("daily_budget", 0) or 0) > 0
              or int(campaign.get("lifetime_budget", 0) or 0) > 0)
    if cbo_on:
        sys.exit(f"Campaign '{campaign['name']}' has a campaign-level budget (CBO is on). "
                 "Turn it off in Ads Manager first: Meta only lets you remove a campaign "
                 "budget there, where it asks how to split it across ad sets.")

    adsets = get(f"{args.campaign_id}/adsets",
                 fields="id,name,created_time,daily_budget,lifetime_budget,end_time,targeting",
                 limit=100)["data"]
    adsets.sort(key=lambda a: a["created_time"])
    source, others = adsets[0], {a["name"]: a for a in adsets[1:]}
    if int(source.get("lifetime_budget", 0) or 0) > 0:
        sys.exit("The source ad set uses a lifetime budget; this script handles daily budgets only.")

    ads = get(f"{source['id']}/ads", fields="id,name,status,effective_status,creative",
              limit=100)["data"]
    ads = [a for a in ads if a["effective_status"] not in ("DELETED", "ARCHIVED")]
    ads.sort(key=lambda a: a["name"])
    if len(ads) < 2:
        sys.exit(f"Need at least 2 ads in the ad set to split, found {len(ads)}.")

    # Round down so the combined budget never exceeds the requested total.
    per_adset = math.floor(args.total_daily_budget * 100 / len(ads))
    if per_adset < int(account["min_daily_budget"]):
        sys.exit(f"{money(per_adset)} {currency}/day per ad set is below the account "
                 f"minimum of {money(account['min_daily_budget'])} {currency}.")

    targeting = dict(source["targeting"])
    geo = dict(targeting["geo_locations"])
    geo["countries"] = countries
    for key in ("regions", "cities", "zips", "custom_locations", "geo_markets"):
        geo.pop(key, None)  # countries only
    targeting["geo_locations"] = geo

    keep, move = ads[0], ads[1:]
    # The source gets renamed to "<base> · <first ad>" at the end; strip that on a re-run.
    base_name = source["name"].removesuffix(f" · {keep['name']}")
    print(f"Campaign:  {campaign['name']} ({args.campaign_id})")
    print(f"CBO:       off (budget sharing: {campaign.get('is_adset_budget_sharing_enabled')}) - no change needed")
    print(f"Ad set:    {source['name']} ({source['id']})")
    print(f"End date:  {source.get('end_time')} - unchanged")
    print(f"Countries: {','.join(source['targeting']['geo_locations'].get('countries', []))} -> {','.join(countries)}")
    print(f"Budget:    {money(source['daily_budget'])}/day in 1 ad set -> "
          f"{money(per_adset)}/day x {len(ads)} ad sets = {money(per_adset * len(ads))} {currency}/day")
    print(f"Plan:      '{keep['name']}' stays in the source ad set")
    for ad in move:
        print(f"           '{ad['name']}' -> copied into its own ad set; original paused")

    if not args.apply:
        print("\nDry run - nothing changed. Re-run with --apply to make these changes.")
        return

    print("\nApplying...")
    # 2. Update the source ad set (copies made afterwards inherit these settings).
    post(source["id"], targeting=json.dumps(targeting), daily_budget=per_adset)
    print(f"  updated source ad set: {','.join(countries)}, {money(per_adset)} {currency}/day")

    for ad in move:
        label = ad["name"]
        adset_name = f"{base_name} · {label}"
        # 3a. Copy the ad set without its ads, paused until its ad is in place.
        if adset_name in others:
            new_adset = others[adset_name]["id"]
        else:
            new_adset = post(f"{source['id']}/copies", deep_copy="false",
                             status_option="PAUSED")["copied_adset_id"]
        post(new_adset, name=adset_name, daily_budget=per_adset,
             targeting=json.dumps(targeting), end_time=source["end_time"])
        # 3b. New ad on the original creative. (Copying the ad itself with
        # /{ad_id}/copies fails Meta's Page/Instagram account check.)
        existing = [a for a in get(f"{new_adset}/ads", fields="id,name", limit=100)["data"]
                    if a["name"] == label]
        if existing:
            new_ad = existing[0]["id"]
        else:
            new_ad = post(f"{account_id}/ads", name=label, adset_id=new_adset,
                          creative=json.dumps({"creative_id": ad["creative"]["id"]}),
                          status="PAUSED")["id"]
        post(new_ad, status="ACTIVE")
        post(new_adset, status="ACTIVE")
        # 3c. Pause the original so it doesn't keep running in the source ad set.
        post(ad["id"], status="PAUSED")
        print(f"  '{label}': ad set {new_adset}, ad {new_ad}; original ad {ad['id']} paused")

    post(source["id"], name=f"{base_name} · {keep['name']}")

    # Confirmation: re-read everything from the API --------------------------------
    print("\nConfirmed state from the API:")
    total = 0
    for adset in get(f"{args.campaign_id}/adsets",
                     fields="id,name,status,daily_budget,end_time,targeting{geo_locations,flexible_spec}",
                     limit=100)["data"]:
        total += int(adset["daily_budget"])
        interests = [i["name"] for spec in adset["targeting"].get("flexible_spec", [])
                     for i in spec.get("interests", [])]
        print(f"\n  Ad set {adset['name']} ({adset['id']})")
        print(f"    status {adset['status']}, {money(adset['daily_budget'])} {currency}/day, "
              f"ends {adset['end_time']}")
        print(f"    countries {','.join(adset['targeting']['geo_locations'].get('countries', []))}; "
              f"{len(interests)} interests: {', '.join(interests)}")
        for ad in get(f"{adset['id']}/ads", fields="name,status,effective_status", limit=100)["data"]:
            print(f"    ad '{ad['name']}': {ad['status']} / {ad['effective_status']}")
    print(f"\nCombined daily budget: {money(total)} {currency}/day")


if __name__ == "__main__":
    main()
