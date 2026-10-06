# Research: How YouTube Shorts Actually Go Viral in 2026
**Project:** "Google Put an AI in Space" — 9:16 Short, 45s, USA audience
**Date:** Oct 6, 2026

---

## 1. How the Shorts algorithm decides (2026 model)

| Signal | What wins | Target for this video |
|---|---|---|
| **3-second gate** | Swipe-away under ~40% in the first 3s. Best content must land at 1.5–3.0s | Hook lands on frame 1 + payoff tease at 2.4s |
| **15-second gate** | Second retention checkpoint — needs a fresh hook or twist | "It can only think 15 minutes" twist lands at ~11s, escalation starts ~21s |
| **Completion / viewed-%** | 70%+ viewed is the real distribution switch. 85% @30s beats 50% @60s | Tight 45s with zero dead air; cuts every 1.5–2.5s |
| **Loop / rewatch** | Average view duration ≥ video length = replays. Replays are treated as a top satisfaction signal | Last line + last frame loop straight into line 1 + frame 1 |
| **Explore → Exploit** | First 200–800 seed viewers decide. Viral window is now 24–36 hours | Front-load everything; no intro, no channel branding |
| **Semantic matching** | Since the Jan 2026 Gemini update YouTube reads video/audio/text semantically. Title, spoken words, on-screen text and description must all point at one keyword intent | One intent: **"Google AI in space / space data center"** repeated in title, VO, captions |
| **Muted viewing** | ~85% watch the first seconds on mute | Burned-in captions; hook also readable as text |

**Why 45 seconds works:** the sweet spot is 15–45s. Under 15s often lacks depth; over 45s shows a hard retention drop-off. 45s with high completion + a loop is the maximum-reach configuration for a story format.

## 2. The 7 rules you gave, mapped to this edit

| # | Rule | How it is implemented |
|---|---|---|
| 1 | **No intro** | Frame 1 is Earth at night + a satellite streaking. VO starts at 0.15s: "A Google AI is running in space right now." No name, no welcome, no logo |
| 2 | **Impossible-sounding claim** | "A Google AI is running in space right now" — it's a *fact*, but sounds fake. Second claim: "It can only think 15 minutes at a time" |
| 3 | **Micro-hook every 4–5s** | 19 short VO lines, each 1.5–3.5s, every one ends by opening a new question (script beats below) |
| 4 | **2nd–3rd grade English** | Grade 2–3 vocabulary, max 11 words per line, one idea per line, no clause stacking |
| 5 | **Numbers & specifics** | 4 chips · 1 fridge-sized satellite · 15 minutes · 8x stronger sun · 100 million dollars · 2 more next year · 100 satellites · Mars coldest. Numbers get their own text-card at 27.5s and 32s |
| 6 | **One wrong/debatable thing** | "Mars is the coldest planet." (Neptune is.) Plus the follow-up "so cooling there is easy" is wrong for a second reason — a vacuum has nothing to carry heat away. Two comment lanes = engagement boom |
| 7 | **Seamless loop** | Final line "…it's all happening right now." cuts into frame 1 and "…right now." again. Same framing, same color grade, same music downbeat → no visible seam |

## 3. Topic research — why this story (launched Oct 1, 2026, trending now)

**Google Project Suncatcher** — Google put its first AI-data-center prototype satellite in orbit on **Oct 1, 2026** (SpaceX Falcon 9 rideshare, Transporter-18), built with Planet Labs.

Verified specifics used in the script:

- **4 × Trillium TPU v6e** chips on board — the same silicon as Google's Earth data centers.
- **Fridge-sized** satellite; ~**1 kW** available power.
- Chips **run ~15–20 minutes, then shut down** to dump heat — the single most visual "fact" of the story.
- **Sun-synchronous orbit ≈ 400 miles** up; solar panels can produce **~8× more power** than the same panel on Earth; future satellites barely need batteries.
- Plan: **2 more satellites in early 2027**, then constellations linked by **laser (optical) inter-satellite links** — hundreds of satellites several hundred meters apart.
- Radiation: Trillium survived a 67 MeV proton beam, **15 krad(Si)**, no hard failures.
- Economics: launch cost needs to fall **below ~$200/kg by the mid-2030s** to match Earth data centers. Space computer time is currently far more expensive per hour than Earth compute — a one-satellite test is the only rational first step.
- Competitive context: **Starcloud (Nov 2025)** already flew an **Nvidia H100** and ran a Gemini model from orbit. **SpaceX** says it wants orbital AI compute satellites as early as 2028.
- Reality check baked into the script: space is *harder*, not easier — no air = no convective cooling, so the "free solar power" is real but the "free cooling" isn't.

**Why it's Shorts-optimised:** it is a US-audience tech story (Google, SpaceX, Nvidia are US-front-page names), it is visual (satellites, launches, glowing chips), it has a built-in contradiction (space = free power but terrible cooling) which is exactly what a hook needs, and it will still be relevant for weeks.

## 4. Sources

- NPR, *Google launches Project Suncatcher, a step towards AI data centers in space* (Oct 1, 2026) — https://www.npr.org/2026/10/01/nx-s1-5983697/project-suncatcher-google-ai-data-center-space
- Science Times, *Project Suncatcher launches first prototype satellite* (Oct 2, 2026)
- Interesting Engineering, *Google's Project Suncatcher aims to build orbital AI data centers powered by sunlight* — 8× solar productivity, 400 miles, 2 satellites early 2027, 67 MeV / 15 krad test, 800 Gbps demo
- The Conversation, *Data centres in space: will 2027 be the year AI goes to orbit?* — $200/kg launch target, radiator mass
- CNBC / Tech Startups tech roundups, Oct 1–5, 2026 — trend surface for the topic
- Shorts virality: prapermedia.com *Viral YouTube Shorts 2026* (3s/15s gates, 24–36h window, muted viewing), conbersa.ai (pacing rule, loop), growthos.in (4-beat spine), air.io (stay-to-watch 70%, AVD ≥ length, captions)
- YouTube Shorts specs: 1080×1920, 9:16, MP4/H.264, 30fps, top ~225px + bottom ~575px are UI-covered

## 5. Packaging (upload kit)

- **Title (recommended):** `Google Put an AI in Space 🤖🛰️ #shorts`
  - Alt A: `Google just put an AI chip in space #shorts`
  - Alt B: `This AI works 15 minutes... then dies #shorts`
- **Description (intent-aligned, one keyword cluster):**
  ```
  Google just put an AI in space. Project Suncatcher launched 4 TPU chips on a
  SpaceX rocket on October 1, 2026. The AI runs 15 minutes at a time, then shuts
  down because space has no air to cool it. Next year Google sends two more — then
  hundreds. Would you trust an AI data center in orbit?

  #shorts #google #ai #space #spacedatacenter #suncatcher #spacex #tech #nasa #future
  ```
- **Posting time (USA):** 6–9 AM EST, Tue–Thu (highest US scroll volume), then let it run the 24–36h window untouched.
- **Cover frame:** the 0.4s "fridge-sized satellite with 4 glowing chips" frame (high contrast, single subject).
- **AI disclosure:** YouTube requires the "Altered content" flag when realistic synthetic imagery/voice is used — tick it in Studio (it does not hurt reach).
- **Do not delete/re-upload** during the first 24h; the seed distribution needs the watch history.

## 6. What will be measured after upload (and what to change)

| If retention drops at… | Cause | Fix in next Short |
|---|---|---|
| 0–3s | Hook not readable in 1 frame | Louder first image, 3-word text card |
| 3–8s | Claim doesn't pay off fast enough | Move first number earlier |
| 15–20s | Mid-video flat spot | New SFX/riser + visual scale change at 15s |
| Last 5s | Payoff arrives too late | Cut 1 VO line before the loop |
| Comments on the "coldest planet" line | Bait worked | Reply to the top correction with a pinned "you're right, it's Neptune — 1 point for science" to farm a second comment wave |
