# Build scripts

These regenerate everything in `../posts/`. You don't need them to post, only to change something.

| Script | Makes |
|---|---|
| `captions.py` | `caption-*.txt` and `facebook-first-comment.txt` from the **Caption** blocks in `../03_week-1-drafts.md` and `../04_week-2-drafts.md` |
| `music.py` | Original Reel music beds in `music/` (synthesized here, no samples) |
| `render.mjs` | Slides/images (from `slides.mjs`) and Reels (from `reels.mjs`) |

```bash
pip install numpy scipy        # for music.py
npm install playwright         # plus ffmpeg on your PATH
python3 captions.py
python3 music.py
node render.mjs                # everything (Reels take a few minutes)
node render.mjs 4 9            # only days 4 and 9
```

- `posts.json` holds the dates, formats and folder names.
- `assets/` holds product images: workbook covers rendered from your PDFs, and
  crops of the Demo ad (roadmap, script page, tracker with demo data, Canva templates).
- `fonts/` holds Montserrat and Open Sans (SIL Open Font License, licenses included).
- Style tokens (colors, type) are in `style.css`, matched to the ad creative.
