# हिंग्लिश गाइड — ये वीडियो क्या है और कैसे बना

ये पूरी फाइल इस बात का जवाब है कि आपने जो 7 rules + format दिया था, वो कहाँ-कहाँ लागू हुआ।

## 1. वीडियो कहाँ है
```
viral-shorts/output/GOOGLE_AI_IN_SPACE_1080x1920_45s.mp4
```
- Size: 1080×1920 (9:16) · 30 fps · 45.0 second · H.264 + AAC
- YouTube Shorts / Instagram Reels / TikTok — तीनों पर सीधा upload हो सकता है
- Male voiceover (US English), background music और sound effects सब इसी वीडियो के लिए नए बनाए गए हैं (कोई copyright नहीं)

## 2. Topic क्यों चुना
**Google Project Suncatcher** — 1 October 2026 को Google ने अपना पहला **AI data-center satellite** space में भेजा (SpaceX rocket से, Planet Labs के साथ)। ये अभी US में सबसे hot tech story है:
- 4 AI chips (TPU) एक fridge-size satellite में
- AI सिर्फ **15 minute** तक सोच सकता है, फिर गरम होकर बंद हो जाता है
- वजह: space में हवा नहीं है, तो cooling नहीं होती
- अगले साल 2 satellite, फिर 100 — यानी ऊपर एक बड़ा AI दिमाग

## 3. आपके 7 rules — कहाँ लगे

| Rule | वीडियो में क्या हुआ |
|---|---|
| 1. No Intro | पहला frame ही claim है — "A Google AI is running in space right now." कोई "hey guys" नहीं, कोई logo नहीं। आवाज़ 0.15 sec पर शुरू |
| 2. Impossible claim | "Google AI space में चल रहा है" — सच है पर सुनने में नकली लगता है। दूसरा claim: "AI सिर्फ 15 minute सोच सकता है" |
| 3. हर 4–5 sec micro-hook | 19 VO lines, average 2.35 sec प्रति line, 29 visual cuts — कोई shot 2.33 sec से लंबा नहीं। हर line नया सवाल खोलती है |
| 4. Simple English | 129 words कुल, छोटे वाक्य, एक line = एक idea (2nd–3rd grade level) |
| 5. Numbers | 4 chips · 1 satellite · 15 minutes · 8x सूरज · $100,000,000 · 10 Earth data centers · 100 satellites |
| 6. जान-बूझकर गलती | "Mars is the coldest planet" (असल में Neptune है) + "cooling there is easy" (जो वीडियो खुद गलत साबित करता है)। Comments में log सुधारने आएंगे |
| 7. Seamless loop | आखिरी 1 second में frame 1 वापस आ जाता है — उसी zoom, उसी grade में। आवाज़ "…right now." से "A Google AI is running in space right now." पर loop हो जाती है |

## 4. Format (जो आपने माँगा था)
**Visual Hook (0–3.5s)** → **Curiosity Gap (3.5–13s)** → **Escalating Payoff (13–33s)** → **Climax (33–39s)** → **Comment Bait (39–43s)** → **Loop (43–45s)**

## 5. Upload कैसे करें (2 minute का काम)
1. `output/` वाला MP4 YouTube पर upload करें
2. Title रखें: `Google Put an AI in Space 🤖🛰️ #shorts`
3. Description और hashtags `docs/03-upload-kit.md` से copy-paste करें
4. Studio में **"Altered content"** (AI) वाला box टिक करें — YouTube का rule है, reach कम नहीं होती
5. Cover frame: 1.8 second वाला frame चुनें (जिसमें glowing chips दिखते हैं)
6. Upload के तुरंत बाद pinned comment लगाएं:
   `"Fun fact I left out: Mars is NOT the coldest planet — Neptune is 🥶"`
7. Time: **6–9 AM EST, मंगल–गुरु** (India time में ~3:30–6:30 PM)
8. पहले 30 minute में हर comment का reply करें — Shorts का algorithm इसी speed को देखता है

## 6. क्या-क्या files मिलेंगी

| File | क्या है |
|---|---|
| `output/GOOGLE_AI_IN_SPACE_1080x1920_45s.mp4` | **final video** |
| `output/qc/contact_sheet.jpg` | 12 अहम frames का contact sheet (जल्दी देखने के लिए) |
| `docs/01-viral-shorts-research-2026.md` | Shorts viral होने की पूरी research (algorithm gates, 2026 rules) |
| `docs/02-script-shotlist.md` | पूरी script, shot list, text cards, SFX map |
| `docs/03-upload-kit.md` | title, description, hashtags, pinned comment, upload plan |
| `docs/04-production-notes.md` | हर second कैसे बना (technical) |
| `docs/05-hinglish-guide.md` | यही फाइल |
| `build/` | पूरा Python pipeline (music, VO assembly, captions, edit, verify) |
| `assets/` | visuals, voice, music, SFX |

## 7. अगला Short बनाने के लिए
`build/video_build.py` के ऊपर `LINES`, `SHOTS`, `CARDS`, `CUES` बदल दें — timing, captions, SFX और loop अपने आप adjust हो जाएंगे। बस ये चलाएं:
```
cd viral-shorts/build
python3 video_build.py all && python3 captions.py && python3 video_build.py mix
```
