#!/usr/bin/env python3
"""Snapshot the campaign's ads into original_ads_structure.json for re-launching.

For each distinct ad name in the campaign (Ad1 · Problem, Ad2 · Workflow,
Ad3 · Demo) the snapshot takes the *original* ad, the oldest one with that
name, not the copies made later when the ads were split into their own ad
sets. It records:

- campaign settings: objective, buying type, bid strategy, stop time
- the ad set each ad lives in: budget, schedule, optimization goal, billing,
  bid strategy, promoted object, attribution and the full targeting spec
- the ad: name, status, tracking specs
- the creative: post ID, object story spec, asset feed spec, URL tags, the
  Instagram account it posts as, and the ad copy (primary text, headline,
  description, call to action, link)
- every media file: kind, Meta ID (image hash / video ID), the file name it
  was uploaded with, dimensions or length, and the matching backup file name
  in assets/creative_backup/ (the same names backup_creatives.py writes), so a
  launch script can open the file directly

Run backup_creatives.py first if you want `backup_file` filled in; until then
it is null and `backup_file_stem` shows the name the file will get.

Environment variables: META_ACCESS_TOKEN, META_AD_ACCOUNT_ID (see README.md).
"""

import argparse
import datetime as dt
import glob
import json
import os
import sys

from backup_creatives import (AD_ACCOUNT_ID, CREATIVE_FIELDS, DEFAULT_CAMPAIGN_ID,
                              OUT_DIR, GraphError, backup_stem, collect_copy, copy_from_post,
                              get, media_for, post_media_items, source_creative)

OUTPUT_FILE = "original_ads_structure.json"
SCHEMA_VERSION = 1

CAMPAIGN_FIELDS = ("name,objective,buying_type,bid_strategy,special_ad_categories,"
                   "status,start_time,stop_time,daily_budget,lifetime_budget,"
                   "is_adset_budget_sharing_enabled")
ADSET_FIELDS = ("name,status,daily_budget,lifetime_budget,start_time,end_time,"
                "optimization_goal,billing_event,bid_strategy,bid_amount,destination_type,"
                "promoted_object,attribution_spec,pacing_type,targeting")
AD_FIELDS = (f"id,name,status,effective_status,created_time,adset_id,tracking_specs,"
             f"conversion_domain,creative{{{CREATIVE_FIELDS}}}")


def backup_file_for(stem):
    """The existing backup file for a stem (any extension), relative to the repo, or None."""
    matches = sorted(glob.glob(glob.escape(stem) + ".*"))
    return matches[0] if matches else None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    if not AD_ACCOUNT_ID:
        sys.exit("Set META_AD_ACCOUNT_ID, and META_ACCESS_TOKEN unless the token is a network secret (see README.md).")
    account_id = AD_ACCOUNT_ID if AD_ACCOUNT_ID.startswith("act_") else f"act_{AD_ACCOUNT_ID}"

    try:
        campaign = get(args.campaign_id, fields=CAMPAIGN_FIELDS)
        all_ads = get(f"{args.campaign_id}/ads", fields=AD_FIELDS, limit=100)["data"]
    except GraphError as exc:
        sys.exit(f"Graph API error: {exc}")

    # One ad per name: the oldest, i.e. the original rather than a later copy.
    originals = {}
    for ad in sorted(all_ads, key=lambda a: a["created_time"]):
        if ad["effective_status"] not in ("DELETED", "ARCHIVED"):
            originals.setdefault(ad["name"], ad)

    adsets, ads_out, warnings = {}, [], []
    for name in sorted(originals):
        ad = originals[name]
        creative = ad["creative"]
        if ad["adset_id"] not in adsets:
            try:
                adsets[ad["adset_id"]] = get(ad["adset_id"], fields=ADSET_FIELDS)
            except GraphError as exc:
                sys.exit(f"Graph API error reading ad set {ad['adset_id']}: {exc}")

        notes = []
        src = source_creative(account_id, creative, notes)
        copy = collect_copy(src)
        media = media_for(src, account_id, notes, name)
        post_id = creative.get("effective_object_story_id")
        if post_id and (not copy["primary_text"] or not media):
            post_media = copy_from_post(post_id, copy, notes)
            if not media:
                media = post_media_items(post_media)

        media_out = []
        for item in media:
            stem = backup_stem(OUT_DIR, name, item)
            media_out.append({
                "kind": item["kind"],
                "meta_id": item["id"],
                "uploaded_file_name": item.get("name"),
                "backup_file": backup_file_for(stem),
                "backup_file_stem": stem,
                **{k: item[k] for k in ("width", "height", "length_seconds", "aspect_ratio",
                                        "library_video_id", "placements", "match_basis")
                   if item.get(k)},
            })
        if not media_out:
            notes.append("no media found for this creative")
        warnings += [f"{name}: {n}" for n in notes]

        ads_out.append({
            "name": name,
            "ad_id": ad["id"],
            "created_time": ad["created_time"],
            "status": ad["status"],
            "adset_id": ad["adset_id"],
            "tracking_specs": ad.get("tracking_specs"),
            "conversion_domain": ad.get("conversion_domain"),
            "creative": {
                "creative_id": creative["id"],
                "name": creative.get("name"),
                "object_type": creative.get("object_type"),
                "source_creative_id": src["id"],
                "source_creative_name": src.get("name"),
                "object_story_id": post_id,
                "instagram_user_id": src.get("instagram_user_id") or creative.get("instagram_user_id"),
                "object_story_spec": src.get("object_story_spec") or creative.get("object_story_spec"),
                "asset_feed_spec": src.get("asset_feed_spec") or creative.get("asset_feed_spec"),
                "url_tags": src.get("url_tags") or creative.get("url_tags"),
                "copy": {
                    "primary_text": copy["primary_text"],
                    "headline": copy["headline"],
                    "description": copy["description"],
                    "call_to_action": copy["cta"],
                    "link": copy["link"],
                },
            },
            "media": media_out,
            "notes": notes,
        })

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_taken_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "ad_account_id": account_id,
        "campaign_id": args.campaign_id,
        "campaign": {k: v for k, v in campaign.items() if k != "id"},
        "ad_sets": {i: {k: v for k, v in s.items() if k != "id"} for i, s in adsets.items()},
        "ads": ads_out,
        "recreate_hint": ("Re-use creative.object_story_id to run the same post (keeps likes and "
                          "comments); otherwise rebuild from object_story_spec, uploading each "
                          "media backup_file and swapping in the new image hash or video ID."),
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {args.output}: {len(ads_out)} ads in {len(adsets)} ad set(s)")
    for a in ads_out:
        files = ", ".join(m["backup_file"] or f"{m['backup_file_stem']}.* (not backed up yet)"
                          for m in a["media"]) or "no media"
        print(f"  {a['name']} (ad {a['ad_id']}): {files}")
    for w in warnings:
        print(f"  warning: {w}")


if __name__ == "__main__":
    main()
