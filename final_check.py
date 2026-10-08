#!/usr/bin/env python3
"""Pre-launch check of the CM relaunch campaign. Read-only: changes nothing.

Compares what is live in Meta with the local files and the saved copy:
status (must be paused), budgets and targeting, video mapping (ad -> creative
-> uploaded video -> local _music file, checked by SHA-256), the video stream
being identical to the original, music license records and audio levels, copy,
links and UTM tags, pixel tracking, identity (Facebook Page / Instagram), and
delivery errors. Prints PASS / FAIL / CHECK lines and exits 1 on any FAIL.

  python final_check.py
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
AUTH = {"access_token": TOKEN} if TOKEN else {}  # otherwise a network secret
G = f"https://graph.facebook.com/{os.environ.get('META_API_VERSION', 'v23.0')}"
ROOT = Path(__file__).resolve().parent
PIXEL_ID = "2239569883568957"
PAGE_ID = "1334749129727460"
UTM_CONTENT = {"Ad1 · Problem": "problem", "Ad2 · Workflow": "workflow", "Ad3 · Demo": "demo"}

results = []


def report(status, what, detail=""):
    results.append(status)
    print(f"[{status}] {what}" + (f": {detail}" if detail else ""))


def get(path, **params):
    for attempt in range(4):  # Meta sometimes answers "retry your request later"
        body = requests.get(f"{G}/{path}", params={**AUTH, **params}, timeout=60).json()
        if "error" not in body:
            return body
        if not body["error"].get("is_transient") and body["error"].get("code") not in (1, 2):
            break
        time.sleep(2 ** attempt)
    sys.exit(f"Graph API error on {path}: {body['error'].get('message')}")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stream_md5(path, stream):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", f"0:{stream}",
                          "-c", "copy", "-f", "md5", "-"], capture_output=True, text=True)
    return out.stdout.strip()


def loudness(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:a",
                          "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = out[out.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    return lufs, peak


def main():
    state = json.loads((ROOT / "new_campaign.json").read_text())
    snapshot = json.loads((ROOT / "original_ads_structure.json").read_text())
    copy = {a["name"]: a["creative"]["copy"] for a in snapshot["ads"]}
    music_by_video = {v["video_id"]: (name, v) for name, v in state["music_videos"].items()}
    license_text = (ROOT / "assets/music/LICENSE.md").read_text()

    print("== Campaign")
    c = get(state["campaign_id"], fields="name,status,effective_status,objective")
    report("PASS" if c["status"] == "PAUSED" else "FAIL", "campaign paused",
           f"{c['name']} {c['status']}/{c['effective_status']}")
    report("PASS" if c["objective"] == "OUTCOME_TRAFFIC" else "FAIL", "objective", c["objective"])

    print("\n== Pixel / dataset")
    px = get(PIXEL_ID, fields="name,is_unavailable,enable_automatic_matching,last_fired_time")
    report("PASS" if not px.get("is_unavailable") else "FAIL", "pixel available",
           f"{px['name']}, last fired {px.get('last_fired_time')}")
    report("PASS" if px.get("enable_automatic_matching") else "FAIL", "automatic advanced matching on")
    report("CHECK", "Purchase event", "not verified in Meta by choice; Gumroad Analytics is the source of truth")

    for adset_name, info in state["ad_sets"].items():
        print(f"\n== {adset_name}")
        s = get(info["adset_id"], fields="status,daily_budget,optimization_goal,targeting")
        t = s["targeting"]
        interests = sorted(i["id"] for f in t.get("flexible_spec", []) for i in f.get("interests", []))
        report("PASS" if s["status"] == "PAUSED" else "FAIL", "ad set paused", s["status"])
        report("PASS" if s["daily_budget"] == "666" else "FAIL", "budget RM 6.66/day", s["daily_budget"])
        report("PASS" if s["optimization_goal"] == "LANDING_PAGE_VIEWS" else "FAIL",
               "optimizes for landing page views", s["optimization_goal"])
        ok = (t["geo_locations"].get("countries") == ["US"] and t["age_min"] == 18
              and t["age_max"] == 44 and len(interests) == 6)
        report("PASS" if ok else "FAIL", "targeting US, 18-44, 6 interests",
               f"{t['geo_locations'].get('countries')}, {t['age_min']}-{t['age_max']}, {len(interests)} interests")
        other = [k for k in ("instagram_positions", "audience_network_positions", "messenger_positions",
                             "threads_positions", "whatsapp_positions") if t.get(k)]
        ok = (t.get("publisher_platforms") == ["facebook"] and not other
              and sorted(t.get("facebook_positions", [])) == ["facebook_reels", "feed", "story"])
        report("PASS" if ok else "FAIL", "placements Facebook only: Feed, Stories, Reels",
               f"{t.get('publisher_platforms')} {t.get('facebook_positions')}" + (f" + {other}" if other else ""))

        for ratio, adinfo in info["ads"].items():
            ad = get(adinfo["ad_id"], fields="name,status,effective_status,tracking_specs,creative,"
                                             "ad_review_feedback")
            cr = get(ad["creative"]["id"], fields="name,object_story_spec,instagram_user_id,actor_id,"
                                                  "effective_instagram_media_id,url_tags")
            vd = cr.get("object_story_spec", {}).get("video_data", {})
            label = f"{ad['name']}"
            report("PASS" if ad["status"] == "PAUSED" else "FAIL", f"{label}: paused",
                   f"{ad['status']}/{ad['effective_status']}")
            fb = ad.get("ad_review_feedback")
            review = {"IN_PROCESS": ("CHECK", "Meta review still in progress"),
                      "DISAPPROVED": ("FAIL", f"disapproved: {fb}"),
                      "WITH_ISSUES": ("FAIL", f"issues: {fb}")}.get(ad["effective_status"])
            report(*(review or ("FAIL" if fb else "PASS", f"{label}: Meta review",
                                f"feedback: {fb}" if fb else "no rejection or feedback")))
            if review:
                print(f"       ({label})")
            # video mapping
            vid = vd.get("video_id")
            fname, mv = music_by_video.get(vid, (None, None))
            stem = {"Ad1 · Problem": "CM_Ad1_Problem_FINAL", "Ad2 · Workflow": "CM_Ad2_Workflow_FINAL",
                    "Ad3 · Demo": "CM_Ad3_Demo_FINAL"}[adset_name]
            want = f"{stem}_{ratio}_music.mp4"
            local = ROOT / "assets/creative_backup" / want
            ok = fname == want and local.exists() and sha256(local) == mv["sha256"]
            report("PASS" if ok else "FAIL", f"{label}: video", f"{vid} = {fname} (SHA-256 matches local file)" if ok
                   else f"{vid} -> {fname}, expected {want}")
            orig = ROOT / "assets/creative_backup" / f"{stem}_{ratio}.mp4"
            same = stream_md5(local, 0) == stream_md5(orig, 0)
            report("PASS" if same else "FAIL", f"{label}: picture identical to original", orig.name)
            # copy
            cp = copy[adset_name]
            ok = (vd.get("message") == cp["primary_text"][0] and vd.get("title") == cp["headline"][0]
                  and vd.get("link_description") == cp["description"][0]
                  and vd.get("call_to_action", {}).get("type") == cp["call_to_action"][0])
            report("PASS" if ok else "FAIL", f"{label}: copy matches saved copy",
                   "primary text, headline, description, CTA")
            # link + UTMs
            link = vd.get("call_to_action", {}).get("value", {}).get("link", "")
            q = parse_qs(urlparse(link).query)
            ok = (link.startswith("https://lumigoods.gumroad.com/l/client-machine?")
                  and q.get("utm_source") == ["meta"] and q.get("utm_medium") == ["paid"]
                  and q.get("utm_campaign") == ["cm-validation"]
                  and q.get("utm_content") == [UTM_CONTENT[adset_name]] and not cr.get("url_tags"))
            report("PASS" if ok else "FAIL", f"{label}: link + UTMs", f"utm_content={q.get('utm_content')}")
            # pixel + identity
            pixels = [p for s_ in ad.get("tracking_specs", []) for p in s_.get("fb_pixel", [])]
            report("PASS" if PIXEL_ID in pixels else "FAIL", f"{label}: tracks pixel {PIXEL_ID}")
            page = cr.get("object_story_spec", {}).get("page_id")
            ok = page == PAGE_ID and cr.get("actor_id") in (None, PAGE_ID)
            report("PASS" if ok else "FAIL", f"{label}: Facebook Page identity",
                   f"Page {page}, posts as {cr.get('actor_id')}")
            ig = cr.get("instagram_user_id") or cr.get("object_story_spec", {}).get("instagram_user_id")
            report("PASS" if not ig else "FAIL", f"{label}: no Instagram account attached",
                   ig or "Facebook-only, as intended")

    print("\n== Music")
    for wav in sorted((ROOT / "assets/music").glob("*_music.wav")):
        report("PASS" if wav.name in license_text else "FAIL", f"{wav.name}: source + license recorded")
    for mp4 in sorted((ROOT / "assets/creative_backup").glob("*_music.mp4")):
        lufs, peak = loudness(mp4)
        ok = -17 <= lufs <= -13 and peak <= -1.0
        report("PASS" if ok else "FAIL", f"{mp4.name}: audio level", f"{lufs} LUFS, peak {peak} dBFS")
    report("CHECK", "music by ear", "levels measured, but nobody has listened to the final mix yet")

    print("\n== Delivery errors")
    errs = requests.get(f"{G}/{state['campaign_id']}/ads", params={**AUTH, "fields": "name,issues_info",
                                                                     "limit": 50}, timeout=60).json()
    issues = [(a["name"], i.get("error_message")) for a in errs.get("data", []) for i in a.get("issues_info", [])]
    report("PASS" if not issues else "FAIL", "no delivery issues", str(issues) if issues else "")

    fails = results.count("FAIL")
    print(f"\n{results.count('PASS')} passed, {fails} failed, {results.count('CHECK')} need a manual check")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
