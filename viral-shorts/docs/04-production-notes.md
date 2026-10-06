# Production Notes — how this Short was built

## 1. Facts of the build

| Item | Value |
|---|---|
| Format | 1080×1920 (9:16), 30 fps, H.264 High, yuv420p, +faststart |
| Runtime | 45.0 s (locked) |
| VO | Male US voice, 19 lines, 135 words, pauses tightened then pitch-preserving atempo fit (1.177×) |
| Music | Original 100 BPM dark-tech cue (synth bass, kick, hats, pads, arp, risers) — built from scratch, royalty-free |
| SFX | 11 original cues (boom, impact, whoosh, riser, tick, shimmer, cash, Mars wind) — synthesised from scratch |
| Visuals | 16 generated cinematic stills, each animated with punch-in / pull-out / parallax + grain + vignette + unsharp |
| Cuts | 29 shots, average 1.55 s, longest 2.33 s (a visual change better than every 2.5 s) |
| Captions | Word-level karaoke, 148 overlay elements → 175 unique composited frames |

## 2. Timeline map (dialogue ↔ visuals ↔ sound)

| Beat | Time | VO | Visual | Sound |
|---|---|---|---|---|
| **Visual hook** | 0.00–3.47 | "A Google AI is running in space right now." / "Not on Earth. Up there." | Earth at night with USA city lights → cut to the satellite's glowing chip bay | Reverse whoosh + sub boom on frame 1, music in |
| Curiosity gap | 3.47–9.53 | launch, "four AI chips, one fridge-sized satellite" | Falcon 9 night launch → hard punch-in on the chip bay | Whooshes on each cut, `4 CHIPS / 1 SATELLITE` card |
| Micro-hook | 9.53–12.86 | "And it just woke up." / "it can only think 15 minutes" | TPU macro with light bloom → radiator panels | Rising shimmer, tick, music riser |
| Escalating payoff | 12.86–21.89 | "too hot… shuts down" / "space has no air" / "heat just sits there" | Radiator heat haze, tighter crops, desaturated dread beat | Drone swell, music thins out |
| Escalation | 21.97–27.06 | "the Sun is eight times stronger" / "free power forever" / "until you do the math" | Sun flare punch-in → solar arrays → desert data center reveal | 2.4 s riser, music drop #1, `8x POWER` |
| Payoff numbers | 27.14–32.75 | "$100 million" / "same money: ten on Earth" | Data-center close crop, power grid | Count-up cash ticks + impact, `$100,000,000` card |
| **Climax** | 32.86–39.06 | "Then a hundred" / "one giant AI brain" / "nobody knows if it works" | Satellite armada pull-back, then a desaturated doubt hold | 1.4 s riser → biggest impact + music drop #2, `THEN 100` |
| **Comment bait** | 39.15–42.98 | "But Mars is the coldest planet, so cooling there is easy… right?" | Mars canyon → Mars dust storm | Mars wind (stereo), bait card |
| **Loop** | 43.95–45.00 | "It's all happening right now." | Pull back to the exact hook framing | Reverse whoosh out, music stripped |

## 3. Structure vs. your 7 rules

1. **No intro** — first frame is already the claim; no logo, no name, no "hey guys". VO starts at 0.15 s.
2. **Impossible-sounding claim** — "A Google AI is running in space right now." True, but it sounds fake. Backed by a second claim 11 s in: the AI can only think for 15 minutes.
3. **Micro-hook every 4–5 s** — 19 VO lines, average 2.35 s each (9 of them under 2.3 s); every line ends by opening the next question, and 29 visual cuts prevent any 3-second flat spot.
4. **2nd–3rd grade English** — short sentences, one idea each, no clause stacking, 135 words total.
5. **Numbers and specifics** — 4 chips, 1 satellite, 15 minutes, 8× solar, $100,000,000, 10 Earth data centers, "then 100", Mars.
6. **One deliberately wrong thing** — "Mars is the coldest planet" (Neptune is) plus a second debatable claim ("cooling there is easy") that contradicts what the video just explained. Both are comment fuel; the upload kit ships with a pinned correction that harvests the second wave.
7. **Seamless loop** — the last 1.05 s returns to the hook image at the same zoom/grade as frame 1, the music is stripped back for the cut, and the final spoken words ("…right now.") run straight into the opening line. Verified numerically: mean |frame(0.10) − frame(44.87)| is checked by `build/verify.py`.

## 4. Why these choices beat the alternative

- **Stills, not stock video**: every frame is on-message (a fridge-sized satellite with glowing AI chips, thermal radiators, a Mars dust storm). Stock libraries reached from this sandbox were unreachable, and generic clips would have diluted the story. Animated stills with punch-ins are the current top-performing Shorts look for story content.
- **Cut rhythm 1.5–2.3 s** — matches the 2026 pacing rule (>1 visual change per 1.5 s average) while staying readable.
- **Karaoke captions sized at 102 px** — readable one-glance at arm's length, and the video still works muted (85% of first views are silent).
- **Ducking** — music sits at −22 dB under the VO via a sidechain compressor, so the numbers always land.
- **Loudness** — mastered to YouTube's −14 LUFS / ≤ −1 dBTP target so YouTube does not turn the Short down.

## 5. Reusing this pipeline
```bash
cd viral-shorts/build
python3 make_audio.py      # rebuild music + SFX (new seed = new cue)
python3 video_build.py timeline   # shots/cards/SFX timed to the VO
python3 captions.py        # burn-in overlay
python3 video_build.py shots      # render the 29 shots
python3 video_build.py concat
python3 video_build.py mix        # final file in ../output
python3 verify.py          # specs, loudness, loop test, beat frames
```
Swap the topic by editing `LINES`, `SHOTS`, `CARDS` and `CUES` at the top of `build/video_build.py`; the timing, captions, SFX placement and loop all follow automatically.

## 6. Licensing / disclosure
- Visuals: AI-generated for this project.
- Voice: AI-generated male narration.
- Music + SFX: original synthesis in `build/make_audio.py` — no third-party samples, no royalty obligations.
- YouTube: tick **Altered content** on upload (realistic synthetic imagery + voice).
