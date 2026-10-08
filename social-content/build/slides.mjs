// Slide content for every carousel and single-image post (4:5, 1080x1350).
// Text here is the on-image copy. Captions live in ../03_ and ../04_ drafts.

const em = (s) => s.replace(/\*(.+?)\*/g, "<em>$1</em>");
export const CHECK = '<svg viewBox="0 0 24 24" width="34" height="34"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
export const CROSS = '<svg viewBox="0 0 24 24" width="30" height="30"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round"/></svg>';
const SAVE = '<svg viewBox="0 0 24 24" width="44" height="44"><path d="M6 3h12v18l-6-4.5L6 21z" fill="none" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/></svg>';

// ---------- templates ----------
const wrap = (inner, style = "") => `<div class="inner" style="display:flex;flex-direction:column;justify-content:center;height:100%;${style}">${inner}</div>`;

export function cover({ kicker, title, sub, size = 104 }) {
  return wrap(`
    ${kicker ? `<div><span class="kicker">${kicker}</span></div>` : ""}
    <h1 style="font-size:${size}px">${em(title)}</h1>
    ${sub ? `<p class="sub">${em(sub)}</p>` : ""}`);
}

export function step({ n, tag, title, note, body, dot, wide }) {
  const dots = dot ? `<div class="dots">${Array.from({ length: 10 }, (_, i) => `<i class="${dot.includes(i + 1) ? "on" : ""}"></i>`).join("")}</div>` : "";
  return dots + wrap(`
    <div class="steprow"><div class="num ${wide ? "wide" : ""}">${n}</div><div class="tag">${tag}</div></div>
    <h2>${em(title)}</h2>
    ${body ? `<p class="body">${em(body)}</p>` : ""}
    ${note ? `<div class="note">${note}</div>` : ""}`);
}

export function listSlide({ kicker, title, items, mk = "num", foot, titleSize = 72, gap }) {
  const lis = items.map((it, i) => {
    const mark = mk === "check" ? CHECK : mk === "box" ? "" : mk === "cross" ? CROSS : i + 1;
    const [h, d] = Array.isArray(it) ? it : [it, null];
    return `<li><span class="mk ${mk === "box" ? "box" : ""}">${mark}</span><div><b>${em(h)}</b>${d ? `<span class="d">${d}</span>` : ""}</div></li>`;
  }).join("");
  return wrap(`
    ${kicker ? `<div><span class="kicker ghost">${kicker}</span></div>` : ""}
    <h2 style="font-size:${titleSize}px;margin-bottom:46px">${em(title)}</h2>
    <div class="card"><ul class="list" ${gap ? `style="gap:${gap}px"` : ""}>${lis}</ul></div>
    ${foot ? `<p class="small" style="margin-top:34px">${foot}</p>` : ""}`);
}

export function endSlide({ title, sub, extra = "" }) {
  return wrap(`
    <h2 style="font-size:86px">${em(title)}</h2>
    ${sub ? `<p class="sub">${em(sub)}</p>` : ""}
    ${extra}
    <div style="display:flex;gap:22px;margin-top:60px">
      <span class="chip">${SAVE} Save</span>
      <span class="chip">Share with an editor friend</span>
    </div>`);
}

export function exampleSlide({ label, who, text, tagline }) {
  return wrap(`
    <div><span class="kicker ghost">${label}</span></div>
    <h2 style="font-size:84px;margin-bottom:46px">${who}</h2>
    <div class="card" style="padding:56px"><p style="font-size:52px;line-height:1.38;font-weight:600">“${text}”</p></div>
    ${tagline ? `<p class="small" style="margin-top:34px">${tagline}</p>` : ""}`);
}

export function mistakeSlide({ n, mistake, fix }) {
  return wrap(`
    <div><span class="kicker ghost">Mistake ${n} of 6</span></div>
    <h2 style="font-size:70px;margin-bottom:50px"><span style="opacity:.55">✕</span> ${em(mistake)}</h2>
    <div class="card"><div class="label">Instead</div><p style="font-size:40px;line-height:1.4;font-weight:600">${fix}</p></div>`);
}

const seq = ["Offer", "Price", "Proof", "Prospects", "Outreach", "Follow-up", "Conversation", "Proposal", "Onboarding", "Delivery"];
const seqChips = (on = []) => `<div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:50px">${seq.map((s, i) =>
  `<span class="chip" style="${on.includes(i + 1) ? "background:var(--blue);border-color:var(--blue)" : ""}">${i + 1} · ${s}</span>`).join("")}</div>`;

// ---------- posts ----------
export const POSTS = {
  1: {
    alt: "Carousel: the 10-step client sequence for new video editors. Offer, price, proof, prospects, outreach, follow-up, conversation, proposal, onboarding, delivery.",
    slides: [
      cover({ kicker: "For new video editors", title: "Getting clients isn't one skill. It's a *sequence.*", sub: "10 steps most new editors skip around in" }),
      step({ n: 1, tag: "Offer", dot: [1], title: "Decide what you sell, and who it's *for.*", note: "“I edit videos” is a skill, not an offer." }),
      step({ n: 2, tag: "Price", dot: [2], title: "Set a starting price *before* anyone asks.", note: "Deciding on the spot is how you undercharge." }),
      step({ n: 3, tag: "Proof", dot: [3], title: "Show 2–4 examples that *match the offer.*", note: "Not your whole hard drive." }),
      step({ n: 4, tag: "Prospects", dot: [4], title: "List real people or businesses *who fit.*", note: "Names, not “YouTubers”." }),
      step({ n: 5, tag: "Outreach", dot: [5], title: "Message them about something you can *actually see.*", note: "Cold DMs are step 5, not step 1." }),
      step({ n: 6, tag: "Follow-up", dot: [6], title: "Most conversations need *more than one* message.", note: "Write down when you'll follow up." }),
      step({ n: "7–8", wide: true, tag: "Conversation → Proposal", dot: [7, 8], title: "Turn interest into a *clear next step.*", body: "Then put scope, price and timing in writing." }),
      step({ n: "9–10", wide: true, tag: "Onboarding → Delivery", dot: [9, 10], title: "Start every project *the same way.*", body: "Deliver in a way that makes the second project easy." }),
      endSlide({ title: "Which step do you usually *skip?*", sub: "Comment the number. Start with the earliest one you've skipped.", extra: seqChips() }),
    ],
  },

  3: {
    alt: "Pick one target client for the next 30 days: three questions to choose who to focus on.",
    slides: [
      wrap(`
        <div><span class="kicker">10-minute exercise</span></div>
        <h1 style="font-size:92px;margin-bottom:54px">Pick <em>one</em> target client for the next 30 days.</h1>
        <div class="card"><ul class="list">
          <li><span class="mk">1</span><div><b>Who already publishes video regularly?</b><span class="d">Podcasters, coaches, local businesses, small YouTube channels…</span></div></li>
          <li><span class="mk">2</span><div><b>Which of them can you find and understand easily?</b></div></li>
          <li><span class="mk">3</span><div><b>Which matches the examples you already have?</b></div></li>
        </ul></div>
        <p class="sub" style="font-size:34px">You can change it after 30 days. Pick one for now.</p>`),
    ],
  },

  4: {
    alt: "Carousel: write your video editing offer in one sentence, with a fill-in-the-blank formula and three examples.",
    slides: [
      cover({ kicker: "Offer basics", title: "Your offer, in *one sentence.*", sub: "If you can't say it simply, prospects can't repeat it." }),
      wrap(`
        <div><span class="kicker ghost">The usual version</span></div>
        <div class="card" style="padding:60px 56px"><span class="quote"><span class="strike">“I'm a video editor. I can edit anything.”</span></span></div>
        <div style="margin-top:56px"><span class="pill">That's a skill, not an offer.</span></div>`),
      wrap(`
        <div><span class="kicker">Fill in the blanks</span></div>
        <div class="card" style="padding:64px 56px"><p style="font-family:var(--head);font-weight:800;font-size:58px;line-height:1.45;color:var(--ink)">
          I help <span class="blank">who</span> turn <span class="blank">what they already have</span> into <span class="blank">what they get</span>, delivered <span class="blank">how often / how fast</span>.</p></div>
        <p class="sub">“What they already have” shows you're working with what they already make.</p>`),
      exampleSlide({ label: "Example 1", who: "Podcasters", text: "I help podcasters turn each full episode into 5 short vertical clips, delivered within 3 days of recording." }),
      exampleSlide({ label: "Example 2", who: "Coaches", text: "I help coaches turn their weekly live sessions into edited YouTube videos with captions, ready to post every Monday." }),
      exampleSlide({ label: "Example 3", who: "Local businesses", text: "I help local gyms turn phone footage into 4 short promo videos a month.", tagline: "Starting points only. Swap in your client and your best service." }),
      listSlide({ kicker: "Check yours", title: "Does it have…", mk: "check", items: ["A specific who", "Something they already have", "A clear deliverable", "A number or timeframe", "No promised results (views, sales, leads)"], foot: "Write yours in the comments. Short and specific beats clever." }),
    ],
  },

  6: {
    alt: "Carousel: build a simple 6-column prospect tracker in a spreadsheet, plus four rules for using it.",
    slides: [
      cover({ kicker: "Pipeline", title: "If it's not written down, you *won't follow up.*", sub: "Build a simple prospect tracker in 10 minutes" }),
      wrap(`
        <div><span class="kicker ghost">Google Sheets or Excel</span></div>
        <h2 style="font-size:70px;margin-bottom:44px">Make <em>6 columns</em></h2>
        <div class="card" style="padding:20px 0">
          ${[["Prospect / Business", "[Podcast name]"], ["Contact name", "Sam"], ["Platform", "YouTube"], ["Contact method", "Email"], ["Last contact", "12 Oct"], ["Next step + date", "Follow up · 16 Oct"]]
            .map(([c, v], i) => `<div style="display:flex;justify-content:space-between;align-items:center;padding:26px 48px;${i ? "border-top:2px solid #e3e7ef" : ""}">
              <span style="font-family:var(--head);font-weight:800;font-size:36px;color:var(--ink)">${c}</span>
              <span style="font-size:32px;color:var(--blue);font-weight:600">${v}</span></div>`).join("")}
        </div>
        <p class="small" style="margin-top:28px">Example row. Use your own prospects.</p>`),
      listSlide({ kicker: "Make it work", title: "4 rules", mk: "box", items: ["Add 5 prospects before you send anything", "Fill in “next step + date” every time you message someone", "Check that column every morning", "Never leave a row without a date"] }),
    ],
  },

  7: {
    alt: "Question post: which of these five questions are you stuck on? What do I offer, who do I contact, what do I say, when do I follow up, what do I charge.",
    slides: [
      wrap(`
        <h1 style="font-size:88px;margin-bottom:56px">Which one are you <em>stuck on?</em></h1>
        <div style="display:flex;flex-direction:column;gap:26px">
          ${["What do I offer?", "Who do I contact?", "What do I say?", "When do I follow up?", "What do I charge?"]
            .map((q, i) => `<div class="sticky" style="transform:rotate(${[-1.5, 1.2, -0.8, 1.6, -1.2][i]}deg);margin-left:${[0, 60, 10, 80, 30][i]}px;width:780px"><span class="mk">${i + 1}</span>${q}</div>`).join("")}
        </div>
        <p class="sub" style="margin-top:56px">Comment the number.</p>`),
    ],
  },

  8: {
    alt: "Carousel: six pricing mistakes new video editors make, and what to do instead.",
    slides: [
      cover({ kicker: "Pricing", title: "6 pricing mistakes new editors *make.*", sub: "and what to do instead" }),
      mistakeSlide({ n: 1, mistake: "Quoting before you know the *scope.*", fix: "“How much for a YouTube edit?” can't be answered yet. Ask about footage, finished length, turnaround and revisions first." }),
      mistakeSlide({ n: 2, mistake: "Treating someone else's rate as *the* rate.", fix: "Their scope, costs and experience aren't yours. Public prices are one data point, not a standard." }),
      mistakeSlide({ n: 3, mistake: "Not knowing your own *floor.*", fix: "Roughly estimate the hours one project really takes: editing, messages, revisions, export. A planning number for you, not a price for them." }),
      mistakeSlide({ n: 4, mistake: "Discounting the *same* work.", fix: "If the budget is lower, change the scope (fewer clips, fewer revisions) instead of doing the same work for less. Or negotiate, on purpose." }),
      mistakeSlide({ n: 5, mistake: "Unlimited “small *changes.*”", fix: "Agree what one revision round means. An extra video or a new concept isn't a revision. It changes the agreement." }),
      mistakeSlide({ n: 6, mistake: "Saying the price, then *apologising.*", fix: "Price + what it covers + the next step. Then stop talking." }),
      endSlide({ title: "Which one have you *done?*", sub: "Comment the number. No judgment." }),
    ],
  },

  10: {
    alt: "Six numbers to check every Friday: messages sent, replies, positive replies, conversations, proposals, clients won. Find the biggest drop and fix that step first.",
    slides: [
      wrap(`
        <div><span class="kicker">Weekly review</span></div>
        <h1 style="font-size:74px;margin-bottom:44px">The 6 numbers to check <em>every Friday</em></h1>
        <div style="display:flex;flex-direction:column;gap:18px">
          ${[["Messages sent", 100], ["Replies", 84], ["Positive replies", 70], ["Conversations", 58], ["Proposals", 48], ["Clients won", 40]]
            .map(([l, w]) => `<div class="bar"><div class="fill" style="width:${w}%">${l}</div></div>`).join("")}
        </div>
        <p class="sub" style="margin-top:40px;font-size:36px">Find the step where the number drops the most. <em>Fix that step first.</em></p>`),
    ],
  },

  11: {
    alt: "Carousel: what to do after a client says yes. Keep what you agreed, list what's still open, ask only for what the work needs, request access not passwords, set real dates, send one short next-steps message.",
    slides: [
      cover({ kicker: "After the yes", title: "They said yes. *Now what?*", sub: "One short next-steps message, not another proposal" }),
      wrap(`
        <h2 style="font-size:70px;margin-bottom:56px">Three different <em>things</em></h2>
        <div style="display:flex;gap:20px;align-items:center">
          ${["Accepted", "Paid", "Ready to start"].map((w, i) => `${i ? '<span style="font-size:60px;color:var(--blue);font-weight:900">≠</span>' : ""}<div class="card" style="flex:1;padding:40px 20px;text-align:center"><span style="font-family:var(--head);font-weight:900;font-size:30px;text-transform:uppercase">${w}</span></div>`).join("")}
        </div>
        <p class="body">One doesn't automatically mean the others.</p>`),
      step({ n: 1, tag: "Keep what you agreed", title: "Save the accepted proposal or *written quote.*", note: "Don't rewrite the scope in your welcome message." }),
      step({ n: 2, tag: "List what's still open", title: "What isn't *settled* yet?", body: "e.g. the start date isn't confirmed, a file hasn't been sent, folder access isn't set up." }),
      step({ n: 3, tag: "Ask only for what's needed", title: "“Would I be blocked, or guessing, *without it?*”", body: "Yes → ask for it. No → don't." }),
      step({ n: 4, tag: "Access, not passwords", title: "Ask to be *invited* to the folder or tool.", note: "Never ask a client to send you a password." }),
      step({ n: 5, tag: "Real dates", title: "Turn “weekly” into *actual dates.*", body: "Footage due → first version → feedback → final. Get the start date confirmed in writing." }),
      wrap(`
        <div><span class="kicker">The message</span></div>
        <div style="display:flex;flex-direction:column;gap:24px;margin-top:10px">
          ${[["Confirm", "you're moving forward"], ["Ask", "for what's still missing"], ["Say", "what happens next"]]
            .map(([a, b], i) => `<div class="card" style="display:flex;align-items:center;gap:30px;padding:36px 44px"><span class="mk" style="width:70px;height:70px;border-radius:50%;background:var(--blue);color:#fff;display:grid;place-items:center;font-family:var(--head);font-weight:900;font-size:34px">${i + 1}</span><span style="font-size:42px"><b style="font-family:var(--head);font-weight:900;text-transform:uppercase">${a}</b> ${b}</span></div>`).join("")}
        </div>
        <p class="sub">Short. Clear. Done.</p>`),
    ],
  },

  13: {
    alt: "Carousel: a foundation week for new video editors, one task a day for seven days before sending outreach.",
    slides: [
      cover({ kicker: "Before your first DM", title: "Your *foundation* week", sub: "7 days, one small task a day" }),
      step({ n: "D1", tag: "Choose your target client", title: "One type of client for the *next 30 days.*", body: "You're not locked in forever." }),
      step({ n: "D2", tag: "Choose your core service", title: "The *one* deliverable you'll lead with.", body: "e.g. short clips from long videos." }),
      step({ n: "D3", tag: "Build your offer", title: "Write it in *one sentence.*", body: "Who, what they have, what they get, how fast." }),
      step({ n: "D4", tag: "Set your starting pricing", title: "One package. What's included. *One price.*", body: "Written down, so you can answer “how much?” calmly." }),
      step({ n: "D5", tag: "Portfolio audit", title: "Keep the 2–4 pieces that *match the offer.*", body: "Move the rest off the front page." }),
      step({ n: "D6", tag: "Create or improve examples", title: "Fill the gap with *one spec sample.*", body: "Label it clearly as a sample." }),
      step({ n: "D7", tag: "Client-ready profile", title: "Bio says the offer. Links go to the *examples.*", body: "One clear way to contact you." }),
      endSlide({ title: "Day 8? Decide what makes a prospect *worth contacting.*", sub: "Save this and start Monday." }),
    ],
  },

  14: {
    alt: "Carousel: what's inside CLIENT MACHINE. 10 PDF workbooks with 192 pages, a 30-day plan, outreach scripts, a Prospect Tracker spreadsheet with demo data, and two Canva templates. $47 USD one-time.",
    slides: [
      wrap(`
        <h1 style="font-size:92px">What's actually inside a <em>$47</em> client system for video editors?</h1>
        <div style="position:relative;height:470px;margin-top:70px">
          ${["01_30-Day_Client_Acquisition_Plan", "02_Outreach_Script_Library", "03_Offer_Builder", "05_Pricing_System", "08_Client_Onboarding_Kit"]
            .map((f, i) => `<img src="assets/cover_${f}-01.png" style="position:absolute;left:${i * 158 - 10}px;top:${[30, 0, 40, 10, 50][i]}px;width:300px;border-radius:10px;box-shadow:0 24px 50px rgba(0,0,0,.5);transform:rotate(${[-6, -2, 2, -3, 5][i]}deg)">`).join("")}
        </div>`),
      wrap(`
        <div><span class="kicker">One ZIP</span></div>
        <h2 style="font-size:84px">10 PDF workbooks · <em>192 pages</em></h2>
        <div class="card" style="margin-top:44px;padding:36px 48px"><ul class="list" style="gap:12px">
          ${["Start Here Guide", "30-Day Client Acquisition Plan", "Offer Builder", "Portfolio Builder", "Pricing System", "Outreach Script Library", "Sales System", "Proposal Kit", "Client Onboarding Kit", "Delivery & Retention"]
            .map((m, i) => `<li style="font-size:34px;align-items:center"><span class="mk" style="width:48px;height:48px;font-size:22px;margin:0">${String(i + 1).padStart(2, "0")}</span>${m}</li>`).join("")}
        </ul></div>`),
      wrap(`
        <div><span class="kicker">The workflow</span></div>
        <h2 style="font-size:70px">10 steps, each mapped to <em>a module</em></h2>
        ${seqChips([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])}
        <p class="body">Every step comes with a worksheet, script, checklist or tracker.</p>`),
      wrap(`
        <div><span class="kicker">A day-by-day plan</span></div>
        <div class="shot"><img src="assets/roadmap_phase1.png"></div>
        <p class="small" style="margin-top:22px">Phase 1 of 4 shown.</p>`),
      wrap(`
        <div><span class="kicker">Scripts you adapt</span></div>
        <div class="shot"><img src="assets/script_library_page.png"></div>
        <p class="small" style="margin-top:22px">Every script is a framework you personalize. Never a copy-paste DM.</p>`),
      wrap(`
        <div><span class="kicker">A working Prospect Tracker (.xlsx)</span></div>
        <div class="shot" style="height:880px"><img src="assets/tracker_dashboard_demo.png"></div>
        <p class="small" style="margin-top:22px">Dashboard shown with demo data.</p>`),
      wrap(`
        <div><span class="kicker">2 editable Canva templates</span></div>
        <div style="height:840px;overflow:hidden;border-radius:22px"><img src="assets/canva_templates.png" style="width:100%;margin-top:-90px"></div>
        <p class="small" style="margin-top:22px">Proposal + Client Onboarding Sheet. Free Canva account needed.</p>`),
      wrap(`
        <h1 style="font-size:96px"><span style="color:var(--blue)">Client</span> Machine</h1>
        <p class="sub" style="margin-top:20px">The 30-Day Client Acquisition System for Beginner Video Editors</p>
        <div class="card" style="margin-top:50px"><div class="label">What it won't do</div>
          <p style="font-size:38px;line-height:1.4;font-weight:600">It won't contact anyone for you, and it can't promise results. It gives you a process you can repeat.</p></div>
        <div style="display:flex;align-items:baseline;gap:20px;margin-top:50px">
          <span style="font-family:var(--head);font-weight:900;font-size:130px;color:var(--blue)">$47</span>
          <span style="font-family:var(--head);font-weight:800;font-size:36px">USD · one-time<br><span style="color:var(--muted)">instant download</span></span>
        </div>`),
    ],
  },
};
