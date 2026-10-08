#!/usr/bin/env python3
"""Write the final Instagram and Facebook captions for every post.

Source of truth for caption text: ../03_week-1-drafts.md and
../04_week-2-drafts.md (the **Caption** block and **Hashtags:** line of each
day). Platform variants are marked inline with [IG] ... / [FB] ...

Output, per post folder in ../posts/:
  caption-instagram.txt   caption + hashtags
  caption-facebook.txt    caption + up to 3 hashtags
  facebook-first-comment.txt   only for posts that mention the product
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
POSTS = ROOT / "posts"
LINK = ("https://lumigoods.gumroad.com/l/client-machine"
        "?utm_source={src}&utm_medium=organic&utm_campaign=cm-organic-w1w2&utm_content=day{day:02d}")


def folder(p):
    return POSTS / f"{p['day']:02d}_{p['date']}_{p['weekday']}_{p['format']}_{p['slug']}"


def parse_days():
    text = "\n".join((ROOT / f).read_text() for f in ("03_week-1-drafts.md", "04_week-2-drafts.md"))
    days = {}
    for block in re.split(r"^## Day ", text, flags=re.M)[1:]:
        day = int(block.split(" ", 1)[0])
        cap = re.search(r"\*\*Caption\*\*\n(.*?)(?:\n\n(?!>)|\Z)", block, re.S).group(1)
        lines = [re.sub(r"^> ?", "", l) for l in cap.splitlines()]
        tags = re.search(r"\*\*Hashtags(?: \(IG[^)]*\))?:\*\*\s*(.+)", block).group(1).split()
        days[day] = ("\n".join(lines).strip(), tags)
    return days


def variant(text, keep, drop):
    # Drop the other platform's sentence, then remove the marker for ours.
    text = re.sub(rf"\s*\[{drop}\][^.]*\.", "", text)
    text = text.replace(f"[{keep}] ", "")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # no markdown bold on social
    return re.sub(r"[ \t]+\n", "\n", text)


def main():
    posts = json.loads((HERE / "posts.json").read_text())
    days = parse_days()
    for p in posts:
        d = folder(p)
        d.mkdir(parents=True, exist_ok=True)
        cap, tags = days[p["day"]]
        assert "[IG]" not in variant(cap, "IG", "FB") and "[FB]" not in variant(cap, "FB", "IG")
        (d / "caption-instagram.txt").write_text(variant(cap, "IG", "FB") + "\n\n" + " ".join(tags) + "\n")
        (d / "caption-facebook.txt").write_text(variant(cap, "FB", "IG") + "\n\n" + " ".join(tags[:3]) + "\n")
        first = d / "facebook-first-comment.txt"
        if p["product"] != "none":
            first.write_text("CLIENT MACHINE, the 30-day client acquisition system for beginner video editors:\n"
                             + LINK.format(src="facebook", day=p["day"]) + "\n")
        elif first.exists():
            first.unlink()
        print(d.name)


if __name__ == "__main__":
    main()
