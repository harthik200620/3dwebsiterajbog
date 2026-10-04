# Offers Ki Duniya: promo video

A 43-second vertical (1080 × 1920, 30 fps) ad for **offerskiduniya.com**, the same Domino pizza at a lower price with the offer applied automatically.

The final cut is `out/offers-ki-duniya-promo.mp4` (H.264 + AAC, ~5 Mbps, -14 LUFS). `scripts/render.mjs` writes a CRF 16 master; the committed file is a two-pass 5 Mbps encode of it (SSIM 0.997) so it stays under upload limits.

Everything in it is generated from this folder: the animation is an HTML page rendered frame by frame, the voice is offline neural TTS, and the music and sound effects are synthesised in Python. There is no stock footage, no sample library and no licensed track, so nothing needs clearing before it goes out.

## The cut

| Time | Scene | Voiceover | On screen |
|---|---|---|---|
| 0.0–3.3 | Hook | "Love pizza? But hate the bill?" | Spinning pizza, kinetic type; a receipt slides in |
| 3.3–6.0 | Problem | "Why pay full price, for the same pizza?" | Receipt prints to ₹1,242 and gets a FULL PRICE stamp |
| 6.0–10.0 | Reveal | "We bring to you… Offers Ki Duniya!" | Riser into silence, then the logo slams in on the downbeat with a rupee-coin burst; the URL types out |
| 10.0–24.0 | The website | "The same Domino menu. Just add to cart… and watch the price drop. Live! The best offer applies automatically. No coupon code." | The URL pill flies into the browser bar. Three items are added one by one, and each time the price counts up to the Domino total and drops to yours (₹459 → ₹538 → ₹947). The offer meter climbs, the cart opens on a Domino-vs-Yours bill, and the camera zooms through "You save ₹295" |
| 24.0–32.0 | Offer ladder | "Save up to ₹295, with free delivery! The bigger the order, the bigger the saving." | UP TO ₹295 OFF, then all five tiers on the beat |
| 32.0–36.0 | Promise | "Same pizza. Delivered by Domino. At a lower price." | Three kinetic lines on cream |
| 36.0–43.0 | Call to action | "Order now on offerskiduniya.com! Offers Ki Duniya. Domino pizza, for less." | Logo, URL, ORDER NOW, offer chips, fine print |

The offer tiers come straight from the brief:

| Item total | Total off | Made of |
|---|---|---|
| ₹199+ | ₹125 | ₹80 off + ₹45 free delivery |
| ₹399+ | ₹165 | ₹120 off + ₹45 free delivery |
| ₹499+ | ₹195 | ₹150 off + ₹45 free delivery |
| ₹699+ | ₹245 | ₹200 off + ₹45 free delivery |
| ₹999+ | ₹295 | ₹250 off + ₹45 free delivery |

The cart in the demo is Veg Extravaganza ₹609, then Garlic Breadsticks ₹129, then Peppy Paneer ₹459. That is ₹1,197 of food plus ₹45 delivery, so ₹1,242 at the Domino price and ₹947 with the ₹295 offer. Every number on screen is computed from `timeline.json`, so if you change a price or a tier there, the bar, the meter, the bill and the ladder all follow.

## Read this before you publish

- **The website in the video is a recreation, not a screen recording.** This build sandbox's network policy blocks `offerskiduniya.com` and `images.dominos.co.in`, so the live site couldn't be opened. The storefront was rebuilt from the site's own source on Vercel: the espresso, cream and gold palette, Inter plus a serif, the header with location and kitchen, cards with ADD on the photo, the bottom bar with the offer meter and its "Add ₹X more to save ₹Y" hint, the dual-column Domino | Yours bill, and auto-applied offers with no coupon box. The food is illustrated rather than photographed.
- **The logo is a stand-in.** The site describes its mark as "Offers Ki Duniya in gold on red" (`okd-logo.webp`), but that file couldn't be downloaded here. The red-and-gold badge in the video follows that description. Drop the real artwork in and swap it for the `.logo` element.
- **Check the item prices.** ₹609 for a Medium Veg Extravaganza comes from the site's own code. ₹459 (Peppy Paneer, Farmhouse), ₹129 (Garlic Breadsticks), ₹119 (Choco Lava Cake) and ₹259 (Margherita) are placeholders. Set them to what the live site shows for IIT Kharagpur in `timeline.json` (cart) and `src/main.js` (`MENU`).
- **"Domino", not "Domino's".** The site's `brand.js` deliberately says "Domino" and never shows their logo or styled wordmark, so the video follows the same rule on screen and in the voice. It also uses none of their colours or trade dress.

## Re-shooting the website segment from the real site

Add `offerskiduniya.com` and `images.dominos.co.in` to the environment's allowed domains (Network access → Custom), and the 10–24 s segment can be recorded from the live site with Playwright instead of the recreation. The camera moves, captions, music and sound effects already follow the same timings.

## Rebuild

```bash
npm install                 # fonts + Playwright (uses the preinstalled Chromium)
pip install numpy scipy soundfile kokoro-onnx

python3 audio/vo.py         # voiceover -> audio/vo/*.wav   (needs the Kokoro model, below)
python3 audio/mix.py        # music + SFX + mix -> audio/build/mix.wav (-14 LUFS)
node scripts/render.mjs --parts 3   # frames -> H.264 + AAC -> out/offers-ki-duniya-promo.mp4
```

- The voiceover WAVs are committed, so you only need the TTS model if you change the script. The model is Kokoro v1.0 (`kokoro-v1.0.onnx` and `voices-v1.0.bin` from the `thewh1teagle/kokoro-onnx` GitHub release `model-files-v1.0`), placed in `audio/models/`. The voice is `af_heart`. "Offers Ki Duniya" is spoken from hand-written phonemes (`ˈɔfɚz kˈi dˈʊnɪjɑ`), because English text-to-speech reads it as "kai dyoo-nee-ya".
- `node scripts/stills.mjs sheet.png 1.0 8.3 16.6 …` renders a contact sheet at any timestamps, and `src/index.html?t=12.5` shows a single frame in a browser.
- The music runs at 120 BPM in F major: bright intro, D minor tension, riser, the drop on the logo, an F–C–Dm–B♭ groove, a half-time breakdown and a V–I ending. Cuts land on beats because bars are exactly 2 s.

## Layout

```
timeline.json        single source of truth: VO cues, scene times, cart, tiers, SFX cues
src/index.html       the composition (all scenes)
src/styles.css       look and layout
src/main.js          seek(t): every frame is a pure function of time
src/art.js           procedural pizzas, garlic breadsticks, lava cake
audio/vo.py          voiceover (Kokoro TTS)
audio/mix.py         music, sound design, ducking, limiting, loudness
scripts/render.mjs   frame-accurate render + mux
scripts/stills.mjs   contact sheets for review
```
