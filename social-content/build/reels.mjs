// Reel definitions (9:16, 1080x1920). Each scene runs from s to e seconds.
// Animated elements carry data-in (seconds after scene start), data-fx and
// optionally data-dur. render.mjs calls window.setTime(t) for every frame.
import { CHECK, CROSS } from "./slides.mjs";

const em = (s) => s.replace(/\*(.+?)\*/g, "<em>$1</em>");
const a = (fx, at, html, extra = "") => `<div class="a" data-fx="${fx}" data-in="${at}" ${extra}>${html}</div>`;

const ENGINE = `
<script>
const ease = (x) => 1 - Math.pow(1 - Math.min(Math.max(x, 0), 1), 3);
window.setTime = (t) => {
  document.querySelectorAll(".scene").forEach((sc) => {
    const s = +sc.dataset.s, e = +sc.dataset.e, last = sc.dataset.last === "1";
    const fin = ease((t - s) / 0.35), fout = last ? 1 : ease((e - t) / 0.3);
    const vis = t >= s - 0.01 && (last || t <= e);
    sc.style.opacity = vis ? Math.min(fin, fout) : 0;
    sc.style.transform = "scale(" + (1 + 0.025 * Math.min(Math.max((t - s) / (e - s), 0), 1)) + ")";
    sc.querySelectorAll(".a").forEach((el) => {
      const dur = +(el.dataset.dur || 0.55), p = (t - s - +el.dataset.in) / dur, k = ease(p);
      const fx = el.dataset.fx;
      if (fx === "up") { el.style.opacity = k; el.style.transform = "translateY(" + (1 - k) * 70 + "px)"; }
      else if (fx === "left") { el.style.opacity = k; el.style.transform = "translateX(" + (1 - k) * -90 + "px)"; }
      else if (fx === "pop") { el.style.opacity = k; el.style.transform = "scale(" + (0.82 + 0.18 * k) + ")"; }
      else if (fx === "fade") { el.style.opacity = k; }
      else if (fx === "strike") { el.style.textDecorationColor = "rgba(47,126,237," + k + ")"; }
      else if (fx === "type") {
        const txt = el.dataset.text, n = Math.round(Math.min(Math.max(p, 0), 1) * txt.length);
        el.innerHTML = txt.slice(0, n) + (p < 1 && p > 0 ? '<span style="color:var(--blue)">|</span>' : "");
      }
      else if (fx === "shrink") { el.style.opacity = 1 - k; el.style.maxHeight = (1 - k) * 60 + "px"; el.style.marginTop = (1 - k) * 22 + "px"; }
      else if (fx === "tick") { el.style.opacity = 0.25 + 0.75 * k; el.querySelector(".mk").style.background = k > 0.5 ? "var(--blue)" : "transparent"; }
      else if (fx === "ring") { el.style.setProperty("--p", Math.min(Math.max(p, 0), 1)); }
    });
  });
};
</script>`;

const CSS = `
<style>
.scene { position: absolute; inset: 0; padding: 250px 100px 430px 90px; display: flex; flex-direction: column; justify-content: center; transform-origin: 50% 45%; }
.scene h1 { font-size: 112px; }
.scene h2 { font-size: 88px; }
.scene .card { padding: 50px 56px; }
.big { font-size: 46px; line-height: 1.38; }
.tk { display: flex; gap: 28px; align-items: flex-start; margin-top: 30px; }
.tk .mk { flex: 0 0 auto; width: 64px; height: 64px; border-radius: 16px; border: 4px solid var(--blue); display: grid; place-items: center; }
.tk b { font-family: var(--head); font-weight: 800; font-size: 44px; display: block; }
.tk span.d { display: block; font-size: 34px; color: var(--muted); margin-top: 6px; }
.ring { --p: 0; width: 220px; height: 220px; border-radius: 50%; background: conic-gradient(var(--blue) calc(var(--p) * 360deg), rgba(255,255,255,.1) 0); display: grid; place-items: center; }
.ring::after { content: "60s"; width: 176px; height: 176px; border-radius: 50%; background: var(--navy); display: grid; place-items: center; font-family: var(--head); font-weight: 900; font-size: 54px; }
.ghostline { height: 26px; border-radius: 13px; background: #dfe4ee; margin-top: 22px; overflow: hidden; }
.chat { background: #0a1122; border: 3px solid rgba(255,255,255,.12); border-radius: 36px; padding: 40px; font-size: 38px; line-height: 1.45; min-height: 520px; }
.chat .who { font-family: var(--head); font-weight: 800; font-size: 26px; letter-spacing: .08em; color: var(--muted); margin-bottom: 18px; text-transform: uppercase; }
.flow { display: flex; flex-direction: column; gap: 22px; margin-top: 40px; }
.flow .stepbox { display: flex; align-items: center; gap: 28px; }
.flow .stepbox .n { width: 88px; height: 88px; border-radius: 50%; background: var(--blue); display: grid; place-items: center; font-family: var(--head); font-weight: 900; font-size: 40px; }
.flow .stepbox b { font-family: var(--head); font-weight: 900; font-size: 60px; text-transform: uppercase; }
.flow .stepbox span { font-size: 34px; color: var(--muted); display: block; }
.handle { position: absolute; left: 90px; bottom: 300px; font-family: var(--head); font-weight: 800; font-size: 26px; letter-spacing: .18em; color: rgba(255,255,255,.45); }
</style>`;

function build({ scenes }) {
  const body = scenes.map((sc, i) => `<div class="scene" data-s="${sc.s}" data-e="${sc.e}" data-last="${i === scenes.length - 1 ? 1 : 0}">${sc.html}</div>`).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="style.css">${CSS}</head>
<body><div class="frame f916">${body}<div class="handle">LUMIGOODS</div></div>${ENGINE}</body></html>`;
}

const tick = (at, h, d) => `<div class="a tk" data-fx="tick" data-in="${at}" data-dur="0.5"><span class="mk">${CHECK}</span><div><b>${h}</b>${d ? `<span class="d">${d}</span>` : ""}</div></div>`;
const kicker = (at, t, ghost = false) => a("left", at, `<span class="kicker ${ghost ? "ghost" : ""}">${t}</span>`);

export const REELS = {
  2: {
    duration: 25, coverAt: 2.9,
    alt: "Reel: stop asking 'Do you need an editor?' Point to something you can actually see in the prospect's content, then use Observe, Personalize, Connect, Ask.",
    scenes: [
      { s: 0, e: 3.3, html: `
        ${kicker(0.1, "Outreach")}
        ${a("pop", 0.2, `<div class="card" style="padding:64px 56px"><div class="a quote strike" data-fx="strike" data-in="1.1" data-dur="0.4" style="display:block;font-size:88px">“Do you need an editor?”</div></div>`)}
        ${a("up", 1.6, `<h2 style="margin-top:60px">Stop sending <em>this.</em></h2>`)}` },
      { s: 3.3, e: 7.6, html: `
        ${a("up", 0.1, `<div class="phone"><div style="text-align:right"><span class="bubble me">Hi! Do you need an editor?</span></div>${a("fade", 0.9, '<div class="seen">Seen</div>')}<div style="height:120px"></div></div>`)}
        ${a("up", 1.5, `<h2 style="margin-top:70px;font-size:80px">It makes them do <em>all the thinking.</em></h2>`)}` },
      { s: 7.6, e: 13.4, html: `
        ${a("up", 0.1, `<h2 style="font-size:84px;margin-bottom:50px">Point to something you can <em>actually see.</em></h2>`)}
        ${["Long videos, no short clips", "Great old episodes never reused", "A business that just started posting video"]
          .map((c, i) => a("left", 1.1 + i * 0.8, `<div class="card" style="margin-top:24px;padding:38px 48px"><span style="font-family:var(--head);font-weight:800;font-size:42px">${c}</span></div>`)).join("")}
        ${a("fade", 3.8, `<p class="sub">Real and observable. Not a problem you made up.</p>`)}` },
      { s: 13.4, e: 20.4, html: `
        ${kicker(0.1, "Better")}
        ${a("up", 0.2, `<div class="card"><p class="big a" data-fx="type" data-in="0.6" data-dur="4.6" style="font-weight:600;min-height:470px" data-text="Hi Sam, I watched your latest episode on pricing. The part at 14:20 about raising rates would work well as a 30-second vertical clip. I sketched how I'd cut it. Want me to send it over?"></p></div>`)}
        ${a("fade", 5.4, `<p class="sub">Example only. Write your own.</p>`)}` },
      { s: 20.4, e: 25, html: `
        ${a("up", 0.1, `<h2 style="font-size:80px">Build it in <em>4 steps</em></h2>`)}
        <div class="flow">${[["Observe", "something real and public"], ["Personalize", "connect it to their situation"], ["Connect", "why you're relevant"], ["Ask", "one simple next step"]]
          .map(([b, s], i) => a("left", 0.5 + i * 0.55, `<div class="stepbox"><span class="n">${i + 1}</span><div><b>${b}</b><span>${s}</span></div></div>`)).join("")}</div>
        ${a("fade", 3.0, `<p class="sub" style="margin-top:50px">Save this for your next outreach session.</p>`)}` },
    ],
    script: `
DAY 2 REEL · "Stop asking 'Do you need an editor?'" · 25 s · 9:16
The video has on-screen text and music only. The voiceover lines are optional, if you want to record a voice track.

0.0–3.3 s   ON SCREEN: "Do you need an editor?" (struck through) / Stop sending this.
            VOICEOVER: "Stop sending this message."
3.3–7.6 s   ON SCREEN: DM bubble "Hi! Do you need an editor?" → Seen / It makes them do all the thinking.
            VOICEOVER: "It makes them do all the thinking. They have to work out why they'd need you."
7.6–13.4 s  ON SCREEN: Point to something you can actually see. / Long videos, no short clips / Great old episodes never reused / A business that just started posting video / Real and observable. Not a problem you made up.
            VOICEOVER: "Before you message, look at their content. Find something specific you can genuinely observe."
13.4–20.4 s ON SCREEN: BETTER / "Hi Sam, I watched your latest episode on pricing. The part at 14:20 about raising rates would work well as a 30-second vertical clip. I sketched how I'd cut it. Want me to send it over?" / Example only. Write your own.
            VOICEOVER: "Then make it about them, show why you're relevant, and ask for one small next step."
20.4–25.0 s ON SCREEN: Build it in 4 steps: Observe · Personalize · Connect · Ask / Save this for your next outreach session.
            VOICEOVER: "Observe. Personalize. Connect. Ask."`,
  },

  5: {
    duration: 30, coverAt: 23.5,
    alt: "Reel: a 60-second portfolio audit for video editors with five checks, plus a tip to make a clearly labelled spec sample if you have no client work yet.",
    scenes: [
      { s: 0, e: 3.2, html: `
        ${a("pop", 0.1, `<div class="ring a" data-fx="ring" data-in="0.2" data-dur="2.8"></div>`)}
        ${a("up", 0.4, `<h1 style="margin-top:60px">Audit your portfolio in <em>60 seconds</em></h1>`)}` },
      { s: 3.2, e: 25, html: `
        ${kicker(0.1, "Portfolio audit")}
        ${tick(0.4, "Your best piece comes first", "…and it matches the client you want")}
        ${tick(4.6, "It matches your offer", "Selling short clips? Show short clips.")}
        ${tick(8.8, "2–4 pieces, not 20", "A few strong, relevant pieces beat a long list.")}
        ${tick(13.0, "One line of context per piece", "Who it was for, what you did, the goal.")}
        ${tick(17.2, "One-tap contact", "Can they reach you without searching?")}` },
      { s: 25, e: 30, html: `
        ${a("up", 0.1, `<h2>No client work <em>yet?</em></h2>`)}
        ${a("up", 0.7, `<p class="body" style="font-size:50px">Make a spec sample for the client you want. <b style="color:var(--blue)">Label it clearly as a sample.</b></p>`)}
        ${a("fade", 1.6, `<p class="sub">Don't post someone else's footage publicly without permission.</p>`)}` },
    ],
    script: `
DAY 5 REEL · "The 60-second portfolio audit" · 30 s · 9:16
The video has on-screen text and music only. The voiceover lines are optional.

0.0–3.2 s   ON SCREEN: 60s timer / Audit your portfolio in 60 seconds
            VOICEOVER: "Open your portfolio. Let's audit it."
3.2–7.6 s   ON SCREEN: ✓ Your best piece comes first …and it matches the client you want
            VOICEOVER: "Is the first video your best one, and does it match the client you want?"
7.8–11.8 s  ON SCREEN: ✓ It matches your offer. Selling short clips? Show short clips.
            VOICEOVER: "Selling short clips? Show short clips, not a wedding film from two years ago."
12.0–16.0 s ON SCREEN: ✓ 2–4 pieces, not 20. A few strong, relevant pieces beat a long list.
            VOICEOVER: "A few strong, relevant pieces beat a long list."
16.2–20.2 s ON SCREEN: ✓ One line of context per piece. Who it was for, what you did, the goal.
            VOICEOVER: "Who was it for, what did you do, what was the goal?"
20.4–25.0 s ON SCREEN: ✓ One-tap contact. Can they reach you without searching?
            VOICEOVER: "Can they contact you in one tap?"
25.0–30.0 s ON SCREEN: No client work yet? Make a spec sample for the client you want. Label it clearly as a sample. / Don't post someone else's footage publicly without permission.
            VOICEOVER: "No client work yet? Make one sample for the client you want, and label it as a sample."`,
  },

  9: {
    duration: 30, coverAt: 2.6,
    alt: "Reel: how to follow up without being pushy. Follow up while there's a relevant reason, stop when someone declines, keep nudges short, write again only with a new reason, and close the loop politely.",
    scenes: [
      { s: 0, e: 3.5, html: `
        ${kicker(0.1, "Follow-up")}
        ${a("up", 0.2, `<h1>No reply isn't <em>a no.</em></h1>`)}
        ${a("up", 1.2, `<p class="sub" style="font-size:48px">But it isn't a yes either.</p>`)}` },
      { s: 3.5, e: 13, html: `
        ${a("up", 0.1, `<div class="card"><div class="label" style="font-size:30px">Follow up when…</div><p class="big" style="font-weight:600">there's still a relevant reason to talk.</p></div>`)}
        ${a("up", 2.0, `<div class="card" style="margin-top:34px;background:#1f2c48;color:var(--white)"><div class="label" style="font-size:30px;color:var(--blue-soft)">Don't follow up when…</div>
          ${["they clearly declined", "they asked you to stop", "you'd just be repeating yourself"].map((x, i) => a("left", 2.8 + i * 0.9, `<p class="big" style="display:flex;gap:20px;align-items:center;margin-top:16px"><span style="width:52px;height:52px;border-radius:50%;background:#3a4767;display:grid;place-items:center;flex:0 0 auto">${CROSS}</span>${x}</p>`)).join("")}</div>`)}` },
      { s: 13, e: 19, html: `
        ${kicker(0.1, "The nudge")}
        ${a("up", 0.3, `<div class="phone"><div style="text-align:right"><span class="bubble me">Hi Sam, bringing this back to the top of your inbox. The clip idea is ready whenever you'd like to see it.</span></div></div>`)}
        ${a("up", 1.6, `<h2 style="margin-top:60px;font-size:76px">Short. Friendly. <em>Not a second pitch.</em></h2>`)}` },
      { s: 19, e: 24, html: `
        ${kicker(0.1, "New reason?")}
        ${["A new launch", "A new video", "A date they gave you"].map((c, i) => a("left", 0.5 + i * 0.6, `<div class="card" style="margin-top:24px;padding:36px 48px"><span style="font-family:var(--head);font-weight:800;font-size:46px">${c}</span></div>`)).join("")}
        ${a("up", 2.6, `<h2 style="margin-top:50px;font-size:72px">That's a fresh message, <em>not pressure.</em></h2>`)}` },
      { s: 24, e: 30, html: `
        ${kicker(0.1, "Close the loop")}
        ${a("up", 0.3, `<div class="phone"><div style="text-align:right"><span class="bubble me">No worries if the timing isn't right. I'll stop here, and you know where to find me.</span></div></div>`)}
        ${a("up", 1.8, `<h2 style="margin-top:60px;font-size:72px">Pick your follow-up gap. <em>Write the date down.</em></h2>`)}` },
    ],
    script: `
DAY 9 REEL · "Follow up without being pushy" · 30 s · 9:16
The video has on-screen text and music only. The voiceover lines are optional.

0.0–3.5 s   ON SCREEN: No reply isn't a no. / But it isn't a yes either.
            VOICEOVER: "No reply isn't a no. But it isn't a yes either."
3.5–13.0 s  ON SCREEN: Follow up when… there's still a relevant reason to talk. / Don't follow up when… they clearly declined · they asked you to stop · you'd just be repeating yourself
            VOICEOVER: "Follow up while there's still a real reason for the conversation. Not when they've said no, asked you to stop, or you're just repeating yourself."
13.0–19.0 s ON SCREEN: THE NUDGE / "Hi Sam, bringing this back to the top of your inbox. The clip idea is ready whenever you'd like to see it." / Short. Friendly. Not a second pitch.
            VOICEOVER: "A nudge is short. It isn't a second pitch."
19.0–24.0 s ON SCREEN: NEW REASON? A new launch · A new video · A date they gave you / That's a fresh message, not pressure.
            VOICEOVER: "If something new happens, that's a real reason to write again."
24.0–30.0 s ON SCREEN: CLOSE THE LOOP / "No worries if the timing isn't right. I'll stop here, and you know where to find me." / Pick your follow-up gap. Write the date down.
            VOICEOVER: "And when it's time to stop, close the loop kindly."`,
  },

  12: {
    duration: 30, coverAt: 2.4,
    alt: "Reel: four rules for using AI to draft outreach messages. Give it real details, cut it to three or four lines, check every claim, and read it out loud. AI writes the draft; you decide.",
    scenes: [
      { s: 0, e: 3, html: `
        ${kicker(0.1, "AI + outreach")}
        ${a("up", 0.2, `<h1>Using AI for outreach? <em>Read this first.</em></h1>`)}` },
      { s: 3, e: 10, html: `
        ${kicker(0.1, "Rule 1 · Give it real details")}
        ${a("up", 0.2, `<div class="chat"><div class="who">Your prompt</div><div class="a" data-fx="type" data-in="0.5" data-dur="5.2" data-text="Write a short, friendly first message (max 4 sentences) to a podcaster. I noticed their latest episode about [topic] has a strong 30-second section at [timestamp]. My offer: I turn full episodes into 5 short clips within 3 days. End with one simple next step. Use only these details. Don't add anything I haven't told you, and no flattery."></div></div>`)}` },
      { s: 10, e: 16, html: `
        ${kicker(0.1, "Rule 2 · Cut it to 3–4 lines")}
        ${a("up", 0.2, `<div class="card"><div class="label">AI draft</div>
          ${[92, 100, 96, 88, 100, 94, 70, 98, 60].map((w, i) => `<div class="ghostline ${i > 2 ? "a" : ""}" ${i > 2 ? `data-fx="shrink" data-in="${1.4 + (i - 3) * 0.25}" data-dur="0.4"` : ""} style="width:${w}%"></div>`).join("")}</div>`)}
        ${a("up", 3.4, `<h2 style="margin-top:50px;font-size:74px">AI drafts run long. <em>Cut them.</em></h2>`)}` },
      { s: 16, e: 22, html: `
        ${kicker(0.1, "Rule 3 · Check every claim")}
        ${a("up", 0.2, `<div class="card"><p class="big">Hi Sam,</p><p class="big a strike" data-fx="strike" data-in="1.4" data-dur="0.4" style="margin-top:14px;background:rgba(255,198,26,.35);padding:0 8px">I loved your episode with Jamie last week!</p><p class="big" style="margin-top:14px">The part at 14:20 would work well as a short clip…</p></div>`)}
        ${a("up", 2.2, `<h2 style="margin-top:50px;font-size:70px">Didn't actually see it? <em>Delete it.</em></h2>`)}
        ${a("fade", 3.2, `<p class="sub">Check names, facts, links and prices.</p>`)}` },
      { s: 22, e: 26.5, html: `
        ${kicker(0.1, "Rule 4 · Read it out loud")}
        ${a("up", 0.3, `<h1 style="font-size:100px">If you wouldn't <em>say it,</em> don't send it.</h1>`)}` },
      { s: 26.5, e: 30, html: `
        ${a("up", 0.1, `<h1>AI writes the draft. <em>You decide.</em></h1>`)}
        ${a("fade", 1.0, `<p class="sub">Screenshot the prompt and swap in your details.</p>`)}` },
    ],
    script: `
DAY 12 REEL · "AI drafts, you decide" · 30 s · 9:16
The video has on-screen text and music only. The voiceover lines are optional.

0.0–3.0 s   ON SCREEN: Using AI for outreach? Read this first.
            VOICEOVER: "If you use AI to write outreach, do this."
3.0–10.0 s  ON SCREEN: RULE 1 · GIVE IT REAL DETAILS / prompt typed out:
            "Write a short, friendly first message (max 4 sentences) to a podcaster. I noticed their latest episode about [topic] has a strong 30-second section at [timestamp]. My offer: I turn full episodes into 5 short clips within 3 days. End with one simple next step. Use only these details. Don't add anything I haven't told you, and no flattery."
            VOICEOVER: "Give it the real details: what you noticed and your offer. Generic input, generic message."
10.0–16.0 s ON SCREEN: RULE 2 · CUT IT TO 3–4 LINES / a long draft shrinks to three lines / AI drafts run long. Cut them.
            VOICEOVER: "AI drafts run long. Cut it to three or four lines."
16.0–22.0 s ON SCREEN: RULE 3 · CHECK EVERY CLAIM / "I loved your episode with Jamie last week!" highlighted and struck through / Didn't actually see it? Delete it. / Check names, facts, links and prices.
            VOICEOVER: "Check every claim. If it mentions something you didn't actually see, delete it."
22.0–26.5 s ON SCREEN: RULE 4 · READ IT OUT LOUD / If you wouldn't say it, don't send it.
            VOICEOVER: "Read it out loud. If you wouldn't say it, don't send it."
26.5–30.0 s ON SCREEN: AI writes the draft. You decide. / Screenshot the prompt and swap in your details.`,
  },
};

for (const r of Object.values(REELS)) r.html = build(r);
