#!/usr/bin/env python3
"""Back up the creatives (media files and ad copy) of every ad in a campaign.

For each ad in the campaign (deleted and archived ads are skipped), this:

1. Downloads the images and videos the creative uses into
   assets/creative_backup/.
2. Writes the ad copy - primary text, headline, description, call-to-action
   button and destination link - to assets/creative_backup/ad_copy_backup.txt.

Ads that share a post (e.g. a copy of an ad in another ad set) are backed up
once. If a creative is built from an existing Page post and its copy isn't on
the creative itself, the script reads the post; that needs the
pages_read_engagement permission, and the backup notes when it's missing.
A media file that can't be downloaded is listed with its URL, not skipped
silently.

Environment variables: META_ACCESS_TOKEN, META_AD_ACCOUNT_ID (see README.md).
"""

import argparse
import datetime as dt
import json
import mimetypes
import os
import re
import sys

import requests

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "")
API_VERSION = os.environ.get("META_API_VERSION", "v23.0")
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

DEFAULT_CAMPAIGN_ID = "120249369863180192"  # CM · Validation · W1
OUT_DIR = os.path.join("assets", "creative_backup")

CREATIVE_FIELDS = ",".join([
    "id", "name", "body", "title", "link_url", "call_to_action_type",
    "image_url", "image_hash", "thumbnail_url", "video_id", "object_type",
    "object_story_spec", "asset_feed_spec", "effective_object_story_id",
    "url_tags", "instagram_user_id",
])


class GraphError(Exception):
    pass


def get(path, **params):
    if ACCESS_TOKEN:
        # Without it, the token comes from a network secret added by the proxy.
        params["access_token"] = ACCESS_TOKEN
    try:
        body = requests.get(f"{BASE_URL}/{path}", params=params, timeout=60).json()
    except (requests.RequestException, ValueError) as exc:
        # Don't print the exception: its URL contains the access token.
        raise GraphError(f"could not reach the Graph API ({type(exc).__name__})")
    if "error" in body:
        err = body["error"]
        raise GraphError(f"({err.get('code')}) {err.get('message')}")
    return body


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "ad"


def collect_copy(creative):
    """Pull every piece of ad copy out of the creative, wherever Meta keeps it."""
    copy = {"primary_text": [], "headline": [], "description": [], "cta": [], "link": []}

    def add(key, value):
        if value and value not in copy[key]:
            copy[key].append(value)

    add("primary_text", creative.get("body"))
    add("headline", creative.get("title"))
    add("cta", creative.get("call_to_action_type"))
    add("link", creative.get("link_url"))

    spec = creative.get("object_story_spec") or {}
    for data in (spec.get("link_data") or {}, spec.get("video_data") or {}):
        add("primary_text", data.get("message"))
        add("headline", data.get("name") or data.get("title"))
        add("description", data.get("description") or data.get("link_description"))
        cta = data.get("call_to_action") or {}
        add("cta", cta.get("type"))
        add("link", data.get("link") or (cta.get("value") or {}).get("link"))
        for child in data.get("child_attachments", []):  # carousel cards
            add("headline", child.get("name"))
            add("description", child.get("description"))
            add("link", child.get("link"))

    feed = creative.get("asset_feed_spec") or {}  # dynamic / multi-text creatives
    for b in feed.get("bodies", []):
        add("primary_text", b.get("text"))
    for t in feed.get("titles", []):
        add("headline", t.get("text"))
    for d in feed.get("descriptions", []):
        add("description", d.get("text"))
    for c in feed.get("call_to_action_types", []):
        add("cta", c)
    for u in feed.get("link_urls", []):
        add("link", u.get("website_url"))
    return copy


def copy_from_post(post_id, copy, notes):
    """Fill gaps in the copy from the Page post the creative is built on."""
    try:
        post = get(post_id, fields="message,attachments{title,description,type,"
                   "unshimmed_url,media,subattachments}")
    except GraphError as exc:
        notes.append(f"could not read post {post_id} for its copy: {exc}")
        return []
    if post.get("message") and post["message"] not in copy["primary_text"]:
        copy["primary_text"].append(post["message"])
    media_urls = []
    for att in post.get("attachments", {}).get("data", []):
        for a in [att] + att.get("subattachments", {}).get("data", []):
            if a.get("title") and a["title"] not in copy["headline"]:
                copy["headline"].append(a["title"])
            if a.get("description") and a["description"] not in copy["description"]:
                copy["description"].append(a["description"])
            if a.get("unshimmed_url") and a["unshimmed_url"] not in copy["link"]:
                copy["link"].append(a["unshimmed_url"])
            src = (a.get("media") or {}).get("source") or ((a.get("media") or {}).get("image") or {}).get("src")
            if src:
                media_urls.append(src)
    return media_urls


_cache = {}


def _account_list(account_id, edge, fields):
    key = (account_id, edge)
    if key not in _cache:
        rows, params = [], {"fields": fields, "limit": 100}
        path = f"{account_id}/{edge}"
        while True:
            body = get(path, **params)
            rows += body.get("data", [])
            after = body.get("paging", {}).get("cursors", {}).get("after")
            if not body.get("paging", {}).get("next") or not after:
                break
            params["after"] = after
        _cache[key] = rows
    return _cache[key]


def source_creative(account_id, creative, notes):
    """The creative that holds the ad's copy and media.

    A creative built only from a post reference (e.g. the Facebook Page identity
    creatives) carries no copy or media; the original creative for the same
    post does, so use that.
    """
    def rich(c):
        spec = c.get("object_story_spec") or {}
        return bool(c.get("asset_feed_spec") or spec.get("link_data") or spec.get("video_data"))

    if rich(creative) or not creative.get("effective_object_story_id"):
        return creative
    try:
        for c in _account_list(account_id, "adcreatives", CREATIVE_FIELDS):
            if (c.get("effective_object_story_id") == creative["effective_object_story_id"]
                    and c["id"] != creative["id"] and rich(c)):
                notes.append(f"copy and media taken from original creative {c['id']} "
                             f"(the ad now uses {creative['id']}, which only references the post)")
                return c
    except GraphError as exc:
        notes.append(f"could not look up the original creative: {exc}")
    return creative


def video_placements(feed):
    """Map video ID -> {positions, vertical} from the asset feed's placement rules."""
    by_label = {l["id"]: v["video_id"] for v in feed.get("videos", []) for l in v.get("adlabels", [])}
    out = {}
    for rule in sorted(feed.get("asset_customization_rules", []), key=lambda r: r.get("priority", 0)):
        vid = by_label.get((rule.get("video_label") or {}).get("id"))
        if not vid or vid in out:
            continue
        cs = rule.get("customization_spec", {})
        positions = {k: v for k, v in cs.items() if k.endswith("_positions")}
        flat = [p for v in positions.values() for p in v]
        out[vid] = {"positions": positions or "all other placements",
                    "vertical": bool(flat) and all(p in ("story", "reels", "facebook_reels") for p in flat)}
    return out


def library_match(account_id, ad_name, aspect):
    """The ad account library video named for this ad and aspect ratio, preferring the plain upload."""
    want = slug(ad_name)
    try:
        videos = _account_list(account_id, "advideos", "id,title,length,source,picture")
    except GraphError:
        return None
    hits = [v for v in videos if want in slug(v.get("title") or "") and aspect in (v.get("title") or "")]
    hits.sort(key=lambda v: ("auto_cropped" in (v.get("title") or "").lower(), v.get("title")))
    return hits[0] if hits else None


def media_for(creative, account_id, notes, ad_name=""):
    """Return [{kind, id, url, name, ...}] for the creative's images and videos.

    `name` is the file name the media was uploaded with (images) or the video
    title, as Meta stores it.
    """
    media = []
    spec = creative.get("object_story_spec") or {}
    feed = creative.get("asset_feed_spec") or {}

    hashes = {creative.get("image_hash")}
    for data in (spec.get("link_data") or {}, spec.get("video_data") or {}):
        hashes.add(data.get("image_hash"))
        for child in data.get("child_attachments", []):
            hashes.add(child.get("image_hash"))
    hashes.update(i.get("hash") for i in feed.get("images", []))
    hashes.discard(None)
    if hashes:
        try:
            images = get(f"{account_id}/adimages", hashes=json.dumps(sorted(hashes)),
                         fields="hash,name,url,permalink_url,width,height")["data"]
            media += [{"kind": "image", "id": i["hash"], "name": i.get("name"),
                       "url": i.get("url") or i.get("permalink_url"),
                       "width": i.get("width"), "height": i.get("height")} for i in images]
        except GraphError as exc:
            notes.append(f"could not look up images {sorted(hashes)}: {exc}")

    videos = {creative.get("video_id"), (spec.get("video_data") or {}).get("video_id")}
    videos.update(v.get("video_id") for v in feed.get("videos", []))
    videos.discard(None)
    placements = video_placements(feed)
    for vid in sorted(videos):
        try:
            v = get(vid, fields="source,title,length,picture")
            media.append({"kind": "video", "id": vid, "name": v.get("title"), "url": v["source"],
                          "length_seconds": v.get("length"), "thumbnail_url": v.get("picture"),
                          "placements": placements.get(vid), "match_basis": "video ID"})
            continue
        except (GraphError, KeyError):
            pass
        # The creative points at a Page-owned copy this token can't read; find the
        # uploaded original in the ad account's library instead.
        aspect = "9x16" if placements.get(vid, {}).get("vertical") else "4x5"
        match = library_match(account_id, ad_name, aspect)
        if match:
            media.append({"kind": "video", "id": vid, "name": match.get("title"),
                          "url": match.get("source"), "length_seconds": match.get("length"),
                          "thumbnail_url": match.get("picture"), "library_video_id": match["id"],
                          "aspect_ratio": aspect, "placements": placements.get(vid),
                          "match_basis": f"library file named for '{ad_name}' and {aspect}, "
                                         f"from this video's placement rule"})
        else:
            notes.append(f"video {vid} ({aspect}): not readable and no library file matches "
                         f"'{ad_name}' + {aspect}")

    if not media and creative.get("image_url"):
        media.append({"kind": "image", "id": creative["id"], "name": None,
                      "url": creative["image_url"]})
    return media


def backup_stem(out_dir, ad_name, item):
    """The path (without extension) a media item is backed up to.

    Uses the file name it was uploaded with when Meta has one, else
    <ad>_<kind>_<id>.
    """
    if item.get("name") and os.path.splitext(item["name"])[1]:
        return os.path.join(out_dir, os.path.splitext(os.path.basename(item["name"]))[0])
    return os.path.join(out_dir, f"{slug(ad_name)}_{item['kind']}_{item['id']}")


def post_media_items(urls):
    return [{"kind": "post_media", "id": str(n + 1), "name": None, "url": u}
            for n, u in enumerate(urls)]


def download(url, path_stem):
    """Download url to path_stem + an extension from its content type; return the path."""
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "").split(";")[0]
        ext = mimetypes.guess_extension(ctype) or os.path.splitext(url.split("?")[0])[1] or ".bin"
        path = path_stem + (".jpg" if ext == ".jpe" else ext)
        with open(path, "wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--out-dir", default=OUT_DIR)
    args = parser.parse_args()

    if not AD_ACCOUNT_ID:
        sys.exit("Set META_AD_ACCOUNT_ID, and META_ACCESS_TOKEN unless the token is a network secret (see README.md).")
    account_id = AD_ACCOUNT_ID if AD_ACCOUNT_ID.startswith("act_") else f"act_{AD_ACCOUNT_ID}"
    os.makedirs(args.out_dir, exist_ok=True)

    try:
        campaign = get(args.campaign_id, fields="name")
        ads = get(f"{args.campaign_id}/ads", limit=100,
                  fields=f"id,name,effective_status,created_time,adset{{name}},"
                         f"creative{{{CREATIVE_FIELDS}}}")["data"]
    except GraphError as exc:
        sys.exit(f"Graph API error: {exc}")
    ads = [a for a in ads if a["effective_status"] not in ("DELETED", "ARCHIVED")]
    # Oldest first within a name, so a shared post is backed up under the original
    # ad's media IDs, matching the file names save_ad_metadata.py records.
    ads.sort(key=lambda a: (a["name"], a["created_time"]))

    seen_posts = {}
    sections, failures, saved = [], [], []
    for ad in ads:
        creative = ad["creative"]
        post_id = creative.get("effective_object_story_id") or creative["id"]
        if post_id in seen_posts:
            sections.append(f"=== {ad['name']} (ad {ad['id']}, {ad['effective_status']})\n"
                            f"Ad set: {ad['adset']['name']}\n"
                            f"Same post as {seen_posts[post_id]}; see above.\n")
            continue
        seen_posts[post_id] = f"ad {ad['id']}"

        notes = []
        src = source_creative(account_id, creative, notes)
        copy = collect_copy(src)
        media = media_for(src, account_id, notes, ad["name"])
        if creative.get("effective_object_story_id") and (not copy["primary_text"] or not media):
            post_media = copy_from_post(creative["effective_object_story_id"], copy, notes)
            if not media:
                media = post_media_items(post_media)

        files = []
        for item in media:
            kind, mid, url = item["kind"], item["id"], item["url"]
            try:
                path = download(url, backup_stem(args.out_dir, ad["name"], item))
                files.append(f"{os.path.basename(path)} ({os.path.getsize(path):,} bytes)")
                saved.append(path)
            except requests.RequestException as exc:
                failures.append(f"{ad['name']}: {kind} {mid}: {type(exc).__name__}")
                files.append(f"NOT DOWNLOADED ({type(exc).__name__}) - {kind} {mid}: {url}")

        lines = [f"=== {ad['name']} (ad {ad['id']}, {ad['effective_status']})",
                 f"Ad set: {ad['adset']['name']}",
                 f"Creative: {creative.get('name', '')} ({creative['id']})",
                 f"Post: {creative.get('effective_object_story_id', '-')}", ""]
        for key, label in (("primary_text", "Primary text"), ("headline", "Headline"),
                           ("description", "Description"), ("cta", "Call to action"),
                           ("link", "Link")):
            values = copy[key] or ["(none found)"]
            for i, v in enumerate(values):
                tag = label if len(values) == 1 else f"{label} {i + 1}"
                lines.append(f"{tag}:\n{v}\n" if key == "primary_text" else f"{tag}: {v}")
        lines.append("")
        lines.append("Media files:")
        lines += [f"  - {f}" for f in files] or ["  (none found)"]
        lines += [f"Note: {n}" for n in notes]
        sections.append("\n".join(lines) + "\n")

    copy_path = os.path.join(args.out_dir, "ad_copy_backup.txt")
    with open(copy_path, "w", encoding="utf-8") as f:
        f.write(f"Ad copy backup - campaign '{campaign['name']}' ({args.campaign_id})\n")
        f.write(f"Taken {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC, {len(ads)} ads\n\n")
        f.write("\n".join(sections))

    print(f"Wrote {copy_path} ({len(ads)} ads, {len(seen_posts)} unique posts)")
    for p in saved:
        print(f"Saved {p}")
    if failures:
        print(f"\n{len(failures)} media file(s) could not be downloaded (URLs are in the copy file):")
        for fl in failures:
            print(f"  - {fl}")
        sys.exit(1)


if __name__ == "__main__":
    main()
