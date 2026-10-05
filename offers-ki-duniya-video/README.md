# Offers Ki Duniya: promo video

A 43-second vertical (1080 × 1920, 30 fps) ad for **offerskiduniya.com**, the same Domino pizza at a lower price with the best offer applied automatically.

The final cut is `out/offers-ki-duniya-promo.mp4`: H.264 + AAC, 25.6 MB, -14.6 LUFS, -2 dBTP. `scripts/render.mjs` writes a CRF 16 master. The committed file is a two-pass 4.8 Mbps encode of that master (SSIM 0.993), which keeps it under upload limits:

```bash
node scripts/render.mjs --parts 3 --out out/offers-ki-duniya-promo-master.mp4
for p in 1 2; do ffmpeg -y -i out/offers-ki-duniya-promo-master.mp4 -c:v libx264 -preset slow -tune film -b:v 4800k -maxrate 9000k -bufsize 12000k \
  -pix_fmt yuv420p -profile:v high -level 4.2 -pass $p -c:a aac -b:a 192k -movflags +faststart out/offers-ki-duniya-promo.mp4; done
```

Version 2 changes three things:

- **The food is photoreal.** Every pizza in the video is path-traced in Blender Cycles from a procedural model, with no illustrations. The model has melted cheese with blisters that brown on top and oil that pools in the creases, sliced olives and jalapeños with skin and flesh, curved capsicum dice, mushrooms and corn, and a pie that is pre-cut into eight slices like a delivered one. It is lit like a food shoot: a big soft source behind for the glisten, plus a real room's light from a CC0 HDRI. The opening is a 60-frame cheese pull whose strands thin as they stretch and glow in the backlight. Steam and film grain are added in the composition.
- **The website is the real site.** The 10–24 s segment is the phone recording of offerskiduniya.com (`site/recording.mp4`), cut to 14 seconds. It shows the location sheet, the menu, Peppy Paneer customised and added, the price dropping to ₹492.60, Veg Extravaganza added, "Top offer unlocked — you save ₹295", and the Domino vs Yours bill. The recording sits in a phone with a cleaned status bar (the screen-record timer is covered). The camera pushes in on the numbers, and taps are marked where the finger went.
- **The new logo** is in `brand/`. It is a pizza cut along the "/" of a % sign, with cheese stretching across the cut, set beside "Offers ki Duniya".

Everything else is still generated here. The voice is offline neural TTS. The music and sound design are synthesised in Python, with real-world sounds only: cheese sizzle, a receipt printing and phone taps. There is no stock footage, no sample library and no licensed track.

## The cut

| Time | Scene | Voiceover | On screen |
|---|---|---|---|
| 0.0–3.3 | Hook | "Love pizza? But hate the bill?" | Cheese pull, backlit, with bokeh and steam. A receipt slides in with the real basket at Domino prices: Peppy Paneer ₹589 + Veg Extravaganza ₹609 + taxes ₹84.05 = ₹1,282.05 |
| 3.3–6.0 | Problem | "Why pay full price, for the same pizza?" | The whole pizza, low and close, with "full price" struck through |
| 6.0–10.0 | Reveal | "We bring to you… Offers Ki Duniya!" | The new logo on cream, with "Domino pizza, for less." and offerskiduniya.com |
| 10.0–24.0 | The real website | "Set your location, anywhere in India. The same Domino menu. Just add to cart… and watch the price drop. Live! The best offer applies automatically. No coupon code." | The phone recording, with captions and push-ins on ₹492.60 (saving ₹195), YOU SAVE ₹195, "Top offer unlocked", YOU SAVE ₹295 and the bill |
| 24.0–32.0 | Offer ladder | "Save up to ₹295, with free delivery! The bigger the order, the bigger the saving." | UP TO ₹295 OFF and the five tiers over the pizza turning slowly |
| 32.0–36.0 | Promise | "Same pizza. Delivered by Domino. At a lower price." | Three lines over the end of the cheese pull in slow motion |
| 36.0–43.0 | Call to action | "Order now on offerskiduniya.com! Offers Ki Duniya. Domino pizza, for less." | Logo, URL, ORDER NOW, "Up to ₹295 off · Free delivery · Order on WhatsApp" |

The ladder uses the tiers the live site applies (`Me` in its bundle). They are not the ₹399 / ₹499 / ₹999 thresholds from the first brief:

| Item total | You save | Made of |
|---|---|---|
| ₹199+ | ₹125 | ₹80 off + ₹45 free delivery |
| ₹400+ | ₹165 | ₹120 off + ₹45 free delivery |
| ₹500+ | ₹195 | ₹150 off + ₹45 free delivery |
| ₹699+ | ₹245 | ₹200 off + ₹45 free delivery |
| ₹1,000+ | ₹295 | ₹250 off + ₹45 free delivery |

## Read this before you publish

- **₹295 vs the bill on screen.** In the recording, the bill's Domino column also shows delivery as "₹45 FREE". So the two To Pay totals are ₹1,282.05 and ₹1,032.05, which is ₹250 apart, while the card above says "You save ₹295". The ₹195 step has the same gap: ₹642.60 vs ₹492.60 is ₹150. Anyone who pauses on the bill will see it. Either charge the ₹45 in the Domino column (if Domino charges it for that order) or word the claim as "₹250 off + free delivery". The video uses your brief's wording.
- **Thresholds.** The ladder shows ₹400 / ₹500 / ₹1,000, matching what the site does. Showing ₹399 would promise an offer that a ₹399 basket doesn't get. If you change the site to ₹399 / ₹499 / ₹999, change `tiers` in `timeline.json` and re-render.
- **Prices are per kitchen.** The site prices the menu at the Domino kitchen nearest the address, so the numbers in the recording are IIT Kharagpur's (checked 22 Sept on the site). The video says so on screen ("Menu & prices from your nearest Domino kitchen") and never claims the same price everywhere.
- **The pizza is a render.** It is styled after a Veg Extravaganza but carries no Domino branding, box or trade dress. Inside the recording, the menu photos are the ones your site loads from images.dominos.co.in, so they are Domino's own photographs.
- **"Domino", not "Domino's"**, on screen and in the voice, the same as the site's `brand.js`.

## Rebuild

```bash
npm install                                  # fonts + Playwright (uses the preinstalled Chromium)
pip install numpy scipy soundfile pillow bpy  # bpy is Blender 5 as a Python module

python3 scripts/site_frames.py               # recording -> src/site/*.jpg (1.5x Lanczos) + frames.json
(cd food && ./render_all.sh)                 # optional, about 1.5-2 h on 4 cores: the graded JPEGs are committed
python3 audio/mix.py                         # music + SFX + VO mix -> audio/build/mix.wav (-14 LUFS)
node scripts/render.mjs --parts 3            # frames -> H.264 + AAC -> out/offers-ki-duniya-promo.mp4
```

- **Voiceover.** The WAVs are committed, so you only need the model to change a line. The voice is Kokoro v1.0 (`kokoro-v1.0.onnx` and `voices-v1.0.bin` from the `thewh1teagle/kokoro-onnx` release `model-files-v1.0`) in `audio/models/`, voice `af_heart`. `python3 audio/vo.py loc` regenerates one line. Run it from its own virtualenv (`pip install kokoro-onnx soundfile`), because kokoro-onnx needs numpy 2 and bpy pins numpy 1.26. "Offers Ki Duniya" is spoken from hand-written phonemes (`ˈɔfɚz kˈi dˈʊnɪjɑ`).
- **Food shots.** `food/pizza_scene.py` builds the pizza and renders `hero` and `top` shots. `food/cheese_pull.py` renders the pull, and `food/grade.py` applies one food grade to every linear EXR (filmic shoulder, warm balance, saturation). The HDRIs in `food/hdri/` are from Poly Haven (CC0).
- **The website segment** is edited in `timeline.json`: `site_edl` lists the source seconds and output duration of each segment, and `taps` lists where the finger went. The phone camera moves are `CAMS` in `src/main.js`.
- **Review stills.** `node scripts/frames.mjs <dir> 1.0 12.5 …` writes full-size stills; `src/index.html?t=12.5` shows a single frame in a browser.
- **Logo.** `brand/src/build.sh` rebuilds every file in `brand/` (SVG with outlined text, so no fonts are needed, plus PNGs).

## Layout

```
timeline.json        VO cues, scenes, the real-site edit (site_edl, taps), tiers, bill, SFX cues
src/index.html       the composition (all scenes)
src/styles.css       look and layout: photo plates, phone, type
src/main.js          seek(t): every frame is a pure function of time
site/recording.mp4   the phone recording of offerskiduniya.com
food/                procedural pizza + cheese pull (Blender Cycles), grade, renders/ (graded JPEGs)
brand/               the logo: SVG, PNG, app icons, favicons, and the source that builds them
audio/vo.py          voiceover (Kokoro TTS)
audio/mix.py         music, sound design, ducking, limiting, loudness
scripts/render.mjs   frame-accurate render + mux
```
