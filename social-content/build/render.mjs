// Render carousel/single-image posts (PNG) and Reels (MP4) into ../posts/.
//   node render.mjs            render everything
//   node render.mjs 4 9        render only days 4 and 9
// Needs Playwright (Chromium) and ffmpeg. Reels also need the music beds from
// music.py (run that first).
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { POSTS } from "./slides.mjs";
import { REELS } from "./reels.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, "..", "posts");
const TMP = path.join(HERE, "_render.html");
const posts = JSON.parse(fs.readFileSync(path.join(HERE, "posts.json"), "utf8"));
const only = process.argv.slice(2).map(Number);
const FPS = 30;

const folder = (p) => path.join(OUT, `${String(p.day).padStart(2, "0")}_${p.date}_${p.weekday}_${p.format}_${p.slug}`);
const page45 = (inner, foot) => `<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="style.css"></head>
<body><div class="frame f45">${inner}${foot}</div></body></html>`;

function footer(i, n) {
  const right = n === 1 ? "" : i === 0
    ? `<span class="swipe">SWIPE <span class="arrow">→</span></span>`
    : `<span class="count">${String(i + 1).padStart(2, "0")} / ${String(n).padStart(2, "0")}</span>`;
  return `<div class="foot"><span>LUMIGOODS</span>${right}</div>`;
}

async function load(page, html) {
  fs.writeFileSync(TMP, html);
  await page.goto("file://" + TMP);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState("networkidle");
}

async function renderSlides(page, p, dir) {
  const { slides, alt } = POSTS[p.day];
  await page.setViewportSize({ width: 1080, height: 1350 });
  for (const f of fs.readdirSync(dir)) if (/^(slide-\d+|image)\.png$/.test(f)) fs.unlinkSync(path.join(dir, f));
  for (let i = 0; i < slides.length; i++) {
    await load(page, page45(slides[i], footer(i, slides.length)));
    const name = slides.length === 1 ? "image.png" : `slide-${String(i + 1).padStart(2, "0")}.png`;
    await page.screenshot({ path: path.join(dir, name) });
  }
  fs.writeFileSync(path.join(dir, "alt-text.txt"), alt + "\n");
  console.log(`  ${slides.length} slide(s)`);
}

function ffmpeg(args, stdin = false) {
  const proc = spawn("ffmpeg", ["-loglevel", "error", "-y", ...args], { stdio: [stdin ? "pipe" : "ignore", "inherit", "inherit"] });
  const done = new Promise((res, rej) => proc.on("close", (c) => (c ? rej(new Error("ffmpeg " + c)) : res())));
  return { proc, done };
}

async function renderReel(page, p, dir) {
  const reel = REELS[p.day];
  await page.setViewportSize({ width: 1080, height: 1920 });
  await load(page, reel.html);
  if (process.env.PREVIEW) {
    for (const t of process.env.PREVIEW.split(",").map(Number)) {
      await page.evaluate((x) => window.setTime(x), t);
      await page.screenshot({ path: path.join(process.env.PREVIEW_DIR, `day${p.day}_${t}.png`) });
    }
    return;
  }
  const silent = path.join(dir, "reel-no-music.mp4");
  const { proc, done } = ffmpeg(["-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", String(FPS), "-movflags", "+faststart", silent], true);
  const frames = Math.round(reel.duration * FPS);
  for (let f = 0; f < frames; f++) {
    await page.evaluate((t) => window.setTime(t), f / FPS);
    const buf = await page.screenshot({ type: "jpeg", quality: 94 });
    if (!proc.stdin.write(buf)) await new Promise((r) => proc.stdin.once("drain", r));
  }
  proc.stdin.end();
  await done;
  // Cover image (for the Reel cover / grid): the designated cover moment.
  await page.evaluate((t) => window.setTime(t), reel.coverAt);
  await page.screenshot({ path: path.join(dir, "reel-cover.png") });
  const music = path.join(HERE, "music", `day${String(p.day).padStart(2, "0")}.wav`);
  await ffmpeg(["-i", silent, "-i", music, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
    "-shortest", "-movflags", "+faststart", path.join(dir, "reel.mp4")]).done;
  fs.writeFileSync(path.join(dir, "on-screen-text-and-voiceover.txt"), reel.script.trim() + "\n");
  fs.writeFileSync(path.join(dir, "alt-text.txt"), reel.alt + "\n");
  console.log(`  ${frames} frames, ${reel.duration}s`);
}

const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 1 });
for (const p of posts) {
  if (only.length && !only.includes(p.day)) continue;
  const dir = folder(p);
  fs.mkdirSync(dir, { recursive: true });
  console.log(path.basename(dir));
  if (p.format === "reel") await renderReel(page, p, dir);
  else await renderSlides(page, p, dir);
}
await browser.close();
fs.rmSync(TMP, { force: true });
