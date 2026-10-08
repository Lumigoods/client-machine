#!/usr/bin/env python3
"""Build a new, fully paused 'CM' campaign from original_ads_structure.json.

1. Uploads the 6 backup videos in assets/creative_backup/ to the ad account
   (checking each file's SHA-256 against the snapshot first).
2. Creates one creative per ad with the saved copy and Gumroad link: the 9x16
   video on Stories and Reels, the 4x5 video everywhere else, with the
   Facebook Page as the identity and no Instagram account.
3. Creates a Traffic campaign with one ad set per ad (landing page views,
   US, the snapshot's interests, ages 18-44) and one ad in each, tracking the
   pixel's Purchase events. Everything is created PAUSED.

Every new ID is written to new_campaign.json as soon as it exists, so the
script is safe to re-run after a partial failure: it reuses what it made.

  python launch_campaign.py              # build (paused)
  python launch_campaign.py --previews   # write ad_previews.html for review
"""

import argparse
import hashlib
import html
import json
import os
import sys
import time
from pathlib import Path

import requests

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
# Without a token, it comes from a network secret added by the proxy.
AUTH = {"access_token": ACCESS_TOKEN} if ACCESS_TOKEN else {}
API_VERSION = os.environ.get("META_API_VERSION", "v23.0")
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
VIDEO_URL = f"https://graph-video.facebook.com/{API_VERSION}"

AD_ACCOUNT_ID = "act_2524309034712212"
PAGE_ID = "1334749129727460"            # LumiGoods
PIXEL_ID = "2239569883568957"           # LumiGoods Pixel
DAILY_BUDGET = 666                      # RM 6.66, in sen
CAMPAIGN_NAME = "CM · Relaunch · LumiGoods Page"
AGE_MIN, AGE_MAX = 18, 44
COUNTRIES = ["US"]

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "original_ads_structure.json"
STATE = ROOT / "new_campaign.json"
PREVIEWS = ROOT / "ad_previews.html"

VERTICAL_POSITIONS = {
    "publisher_platforms": ["facebook", "instagram"],
    "facebook_positions": ["story", "facebook_reels"],
    "instagram_positions": ["story", "reels"],
}
PREVIEW_FORMATS = [
    ("Facebook Feed (mobile)", "MOBILE_FEED_STANDARD"),
    ("Facebook Feed (desktop)", "DESKTOP_FEED_STANDARD"),
    ("Facebook Stories", "FACEBOOK_STORY_MOBILE"),
    ("Facebook Reels", "FACEBOOK_REELS_MOBILE"),
    ("Instagram Feed", "INSTAGRAM_STANDARD"),
    ("Instagram Stories", "INSTAGRAM_STORY"),
    ("Instagram Reels", "INSTAGRAM_REELS"),
    ("Instagram Explore home", "INSTAGRAM_EXPLORE_GRID_HOME"),
]


def call(method, url, files=None, **params):
    data = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in params.items()}
    try:
        if method == "GET":
            resp = requests.get(url, params={**AUTH, **data}, timeout=120)
        else:
            resp = requests.post(url, data={**AUTH, **data}, files=files, timeout=600)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        # Don't print the exception: its URL may contain the access token.
        sys.exit(f"Could not reach the Graph API ({type(exc).__name__}).")
    if "error" in body:
        err = body["error"]
        detail = err.get("error_user_msg") or err.get("message")
        sys.exit(f"Graph API error ({err.get('code')}/{err.get('error_subcode')}): {detail}")
    return body


def get(path, **params):
    return call("GET", f"{BASE_URL}/{path}", **params)


def post(path, **params):
    return call("POST", f"{BASE_URL}/{path}", **params)


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"videos": {}, "ads": {}}


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def ad_specs(snapshot):
    """Per original ad: copy, link and the 9x16 / 4x5 backup files."""
    specs = []
    for ad in snapshot["ads"]:
        media = {m["aspect_ratio"]: m for m in ad["media"] if m["kind"] == "video"}
        copy = ad["creative"]["copy"]
        specs.append({
            "name": ad["name"],
            "body": copy["primary_text"][0],
            "title": copy["headline"][0],
            "description": copy["description"][0],
            "cta": copy["call_to_action"][0],
            "link": copy["link"][0],
            "videos": {ratio: media[ratio] for ratio in ("9x16", "4x5")},
        })
    return specs


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_video(state, media):
    name = Path(media["backup_file"]).name
    if name in state["videos"]:
        return state["videos"][name]["video_id"]
    path = ROOT / media["backup_file"]
    if sha256(path) != media["local_file"]["sha256"]:
        sys.exit(f"{name} doesn't match the SHA-256 in {SNAPSHOT.name}; not uploading it.")
    with open(path, "rb") as f:
        video_id = call("POST", f"{VIDEO_URL}/{AD_ACCOUNT_ID}/advideos",
                        files={"source": (name, f, "video/mp4")}, name=name)["id"]
    state["videos"][name] = {"video_id": video_id, "aspect_ratio": media["aspect_ratio"],
                             "original_video_id": media["meta_id"]}
    save_state(state)
    print(f"  uploaded {name} -> video {video_id}")
    return video_id


def wait_ready(video_id):
    """Wait for Meta to finish processing a video; return its preferred thumbnail."""
    for _ in range(60):
        status = get(video_id, fields="status")["status"]["video_status"]
        if status == "ready":
            thumbs = get(f"{video_id}/thumbnails", fields="uri,is_preferred")["data"]
            if thumbs:
                return next((t for t in thumbs if t.get("is_preferred")), thumbs[0])["uri"]
        elif status == "error":
            sys.exit(f"Meta could not process video {video_id}.")
        time.sleep(5)
    sys.exit(f"Video {video_id} still processing after 5 minutes; re-run later.")


def creative_params(spec, vertical_id, vertical_thumb, square_id, square_thumb):
    """Placement asset customization: 9x16 on Stories/Reels, 4x5 elsewhere."""
    def label(kind, ratio):
        return {"name": f"{kind}_{ratio}"}

    rules = []
    for priority, (ratio, spec_extra) in enumerate(
            [("9x16", VERTICAL_POSITIONS), ("4x5", {})], start=1):
        rules.append({
            "customization_spec": {"age_min": 13, "age_max": 65, **spec_extra},
            "video_label": label("video", ratio),
            "body_label": label("body", ratio),
            "title_label": label("title", ratio),
            "link_url_label": label("link", ratio),
            "priority": priority,
        })
    both = lambda kind: [label(kind, "9x16"), label(kind, "4x5")]
    return {
        "name": f"{spec['name']} · 9x16 Stories/Reels · 4x5 other",
        "object_story_spec": {"page_id": PAGE_ID},
        "asset_feed_spec": {
            "videos": [
                {"video_id": vertical_id, "thumbnail_url": vertical_thumb,
                 "adlabels": [label("video", "9x16")]},
                {"video_id": square_id, "thumbnail_url": square_thumb,
                 "adlabels": [label("video", "4x5")]},
            ],
            "bodies": [{"text": spec["body"], "adlabels": both("body")}],
            "titles": [{"text": spec["title"], "adlabels": both("title")}],
            "descriptions": [{"text": spec["description"]}],
            "link_urls": [{"website_url": spec["link"], "adlabels": both("link")}],
            "call_to_action_types": [spec["cta"]],
            "ad_formats": ["AUTOMATIC_FORMAT"],
            "optimization_type": "PLACEMENT",
            "asset_customization_rules": rules,
        },
    }


def targeting(snapshot):
    original = next(iter(snapshot["ad_sets"].values()))["targeting"]
    keep = ("flexible_spec", "locales", "publisher_platforms", "facebook_positions",
            "instagram_positions", "device_platforms")
    t = {k: original[k] for k in keep if k in original}
    t.update({
        "age_min": AGE_MIN,
        "age_max": AGE_MAX,
        "geo_locations": {"countries": COUNTRIES,
                          "location_types": original["geo_locations"].get("location_types",
                                                                          ["home", "recent"])},
        "targeting_automation": {"advantage_audience": 0},
    })
    return t


def build():
    snapshot = json.loads(SNAPSHOT.read_text())
    state = load_state()
    specs = ad_specs(snapshot)

    print("Videos:")
    for spec in specs:
        for media in spec["videos"].values():
            upload_video(state, media)
    for info in state["videos"].values():
        if "thumbnail_url" not in info:
            info["thumbnail_url"] = wait_ready(info["video_id"])
            save_state(state)
    for name, info in state["videos"].items():
        print(f"  {name:<34} {info['video_id']}  (was {info['original_video_id']})")

    if "campaign_id" not in state:
        state["campaign_id"] = post(f"{AD_ACCOUNT_ID}/campaigns", name=CAMPAIGN_NAME,
                                    objective="OUTCOME_TRAFFIC", buying_type="AUCTION",
                                    special_ad_categories=[], status="PAUSED",
                                    is_adset_budget_sharing_enabled="false")["id"]
        save_state(state)
    print(f"\nCampaign: {CAMPAIGN_NAME} ({state['campaign_id']}), PAUSED")

    target = targeting(snapshot)
    for spec in specs:
        ad = state["ads"].setdefault(spec["name"], {})
        v = {r: state["videos"][Path(m["backup_file"]).name] for r, m in spec["videos"].items()}
        if "creative_id" not in ad:
            ad["creative_id"] = post(f"{AD_ACCOUNT_ID}/adcreatives", **creative_params(
                spec, v["9x16"]["video_id"], v["9x16"]["thumbnail_url"],
                v["4x5"]["video_id"], v["4x5"]["thumbnail_url"]))["id"]
            save_state(state)
        if "adset_id" not in ad:
            ad["adset_id"] = post(
                f"{AD_ACCOUNT_ID}/adsets", campaign_id=state["campaign_id"],
                name=f"US · {AGE_MIN}-{AGE_MAX} · Editors interests · {spec['name']}",
                daily_budget=DAILY_BUDGET, billing_event="IMPRESSIONS",
                optimization_goal="LANDING_PAGE_VIEWS", bid_strategy="LOWEST_COST_WITHOUT_CAP",
                destination_type="WEBSITE", targeting=target, status="PAUSED")["id"]
            save_state(state)
        if "ad_id" not in ad:
            ad["ad_id"] = post(
                f"{AD_ACCOUNT_ID}/ads", name=spec["name"], adset_id=ad["adset_id"],
                creative={"creative_id": ad["creative_id"]}, status="PAUSED",
                tracking_specs=[{"action.type": ["offsite_conversion"],
                                 "fb_pixel": [PIXEL_ID]}])["id"]
            save_state(state)

    print("\nConfirmed from the API:")
    for name, ad in state["ads"].items():
        a = get(ad["ad_id"], fields="name,status,effective_status,tracking_specs")
        s = get(ad["adset_id"], fields="name,status,daily_budget,optimization_goal,targeting")
        t = s["targeting"]
        interests = [i["name"] for f in t.get("flexible_spec", []) for i in f.get("interests", [])]
        print(f"  {a['name']}: ad {ad['ad_id']} {a['status']}/{a['effective_status']}, "
              f"creative {ad['creative_id']}")
        print(f"    ad set {ad['adset_id']} {s['status']}: RM {int(s['daily_budget']) / 100:.2f}/day, "
              f"{s['optimization_goal']}, {','.join(t['geo_locations']['countries'])}, "
              f"{t['age_min']}-{t['age_max']}, {len(interests)} interests")
    print(f"\nIDs saved to {STATE.name}. Nothing is live: everything is PAUSED.")


def previews():
    state = load_state()
    if not state.get("ads"):
        sys.exit("Run the build first.")
    parts = []
    for name, ad in state["ads"].items():
        parts.append(f"<h2>{html.escape(name)} <small>ad {ad['ad_id']}</small></h2><div class=row>")
        for title, fmt in PREVIEW_FORMATS:
            body = call("GET", f"{BASE_URL}/{ad['ad_id']}/previews", ad_format=fmt)["data"]
            frame = body[0]["body"] if body else "<p>No preview for this placement.</p>"
            parts.append(f"<figure><figcaption>{title}</figcaption>{frame}</figure>")
        parts.append("</div>")
    PREVIEWS.write_text(
        "<!doctype html><meta charset=utf-8><title>CM ad previews</title><style>"
        "body{font-family:system-ui;margin:16px}.row{display:flex;flex-wrap:wrap;gap:16px}"
        "figure{margin:0}figcaption{font-weight:600;margin-bottom:4px}</style>"
        "<h1>CM · Relaunch previews (all paused)</h1>"
        "<p>Open while logged in to Facebook. Preview links expire after about 24 hours.</p>"
        + "".join(parts))
    print(f"Wrote {PREVIEWS.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--previews", action="store_true",
                        help="Write ad_previews.html with each ad's placement previews")
    args = parser.parse_args()
    previews() if args.previews else build()


if __name__ == "__main__":
    main()
