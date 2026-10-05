# Offers Ki Duniya: promo video

A 43-second vertical (1080 × 1920, 30 fps) ad for **offerskiduniya.com**, the same Domino's pizza at a lower price with the best offer applied automatically.

The final cut is `out/offers-ki-duniya-promo.mp4`: H.264 + AAC, 25.7 MB, -14.6 LUFS, -2.1 dBTP. `scripts/render.mjs` writes a CRF 16 master. The committed file is a two-pass 4.8 Mbps encode of that master (SSIM 0.992), which keeps it under upload limits:

```bash
node scripts/render.mjs --parts 3 --out out/offers-ki-duniya-promo-master.mp4
for p in 1 2; do ffmpeg -y -i out/offers-ki-duniya-promo-master.mp4 -c:v libx264 -preset slow -tune film -b:v 4800k -maxrate 9000k -bufsize 12000k \
  -pix_fmt yuv420p -profile:v high -level 4.2 -pass $p -c:a aac -b:a 192k -movflags +faststart out/offers-ki-duniya-promo.mp4; done
```

To change only the voice or the mix, put the new `audio/build/mix.wav` on the existing video stream instead of re-rendering. The picture stays bit for bit the same:

```bash
ffmpeg -i out/offers-ki-duniya-promo.mp4 -i audio/build/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 \
  -shortest -movflags +faststart out/new.mp4 && mv out/new.mp4 out/offers-ki-duniya-promo.mp4
```

What's in it:

- **Path-traced food.** Every pizza is rendered in Blender Cycles from a procedural model; nothing is illustrated (`food/`).
  - Melted cheese blisters, browns on top and pools oil.
  - The toppings sit sunk into the cheese: sliced olives, jalapeño slices with seeded centres, translucent onion petals, curved capsicum, mushroom slices and corn kernels.
  - The pie is pre-cut into eight slices, like a delivered one.
  - It is lit like a food shoot, with a CC0 HDRI for the room light.
- **The opening cheese pull** is a 60-frame animation. The slice is lifted by its crust and flops under its own weight, more at the tip. Its strands are a mix of thick ropes, thin threads and flat ribbons: they thin as they stretch, sag under their weight, and some snap into hanging tails. As the slice rises, the focus racks from the pie onto it, the way a focus puller would follow it, so the slice stays sharp while the pie falls into soft focus. Every frame also renders an alpha matte of the slice, so the type can sit behind it ("LOVE PIZZA?"). The grade adds the warm bloom a real lens throws around bright highlights.
- **The website is the real site.** The 10–24 s segment is the phone recording of offerskiduniya.com (`site/recording.mp4`), cut to 14 seconds. It plays in a phone that swings in 3D over drifting bokeh. The numbers lift off the screen as floating cards while the phone dims behind them: ₹492.60 (saving ₹195), YOU SAVE ₹195, "Top offer unlocked", YOU SAVE ₹295, and To Pay ₹1,282.05 → ₹1,032.05. Taps are marked where the finger went, and the screen-record timer is covered by a clean status bar.
- **Type and edit.** Headlines are set in Anton. The name "OFFERS KI DUNIYA" is set as plain type, filled with the cheese pull before it turns gold; there is no logo in the video. Light leaks wash across the big cuts, the picture punches in on the hits, and the cuts land with a short zoom blur.
- **Sound.** The voice is Sarvam AI's Shubh (`bulbul:v3`), reading the script in Indian English. Each line was checked by transcribing it back with Sarvam's speech-to-text. The music is synthesised: a 120 BPM groove with 808 sub-bass, layered claps and snares, hi-hat rolls into each cut, and a half-time trap feel under "Same pizza…". The sound effects are real-world ones: cheese sizzle, a receipt printing and phone taps.

There is no stock footage, no sample library and no licensed track. The logo files from round two are still in `brand/` but are not used in the video.

## The cut

| Time | Scene | Voiceover | On screen |
|---|---|---|---|
| 0.0–3.3 | Hook | "Love pizza? But hate the bill?" | Cheese pull, backlit, with bokeh and steam. "LOVE PIZZA?" sits behind the rising slice. A receipt slides in with the real basket at Domino's prices: Peppy Paneer ₹589 + Veg Extravaganza ₹609 + taxes ₹84.05 = ₹1,282.05 |
| 3.3–6.0 | Problem | "Why pay full price, for the same pizza?" | The whole pizza, low and close, with "full price" struck through |
| 6.0–10.0 | Reveal | "We bring to you… Offers Ki Duniya!" | "OFFERS KI DUNIYA", filled with the cheese pull and then turning gold, with "Domino's pizza, for less." and offerskiduniya.com |
| 10.0–24.0 | The real website | "Set your location, anywhere in India. The same Domino's menu. Just add to cart… and watch the price drop. Live! The best offer applies automatically. No coupon code." | The phone recording in a 3D phone. Pop-out cards show ₹492.60 (saving ₹195), YOU SAVE ₹195, "Top offer unlocked", YOU SAVE ₹295 and To Pay |
| 24.0–32.0 | Offer ladder | "Save up to ₹295, with free delivery! The bigger the order, the bigger the saving." | UP TO ₹295 OFF and the five tiers over the pizza turning slowly |
| 32.0–36.0 | Promise | "Same pizza. Delivered by Domino's. At a lower price." | Three lines, each set to the same width, above the slice as the end of the cheese pull plays in slow motion |
| 36.0–43.0 | Call to action | "Order now on offerskiduniya.com! Offers Ki Duniya. Domino's pizza, for less." | The name in gold, URL, ORDER NOW, "Up to ₹295 off · Free delivery · Order on WhatsApp", over the pizza turning |

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
- **Prices are per kitchen.** The site prices the menu at the Domino kitchen nearest the address, so the numbers in the recording are IIT Kharagpur's (checked 22 Sept on the site). The video says so on screen ("Menu & prices from your nearest Domino's kitchen") and never claims the same price everywhere.
- **The pizza is a render.** It is styled after a Veg Extravaganza but carries no Domino's branding, box or trade dress. Inside the recording, the menu photos are the ones your site loads from images.dominos.co.in, so they are Domino's own photographs.
- **"Domino's" is used on screen and in the voice, at your request.** Your site's own `brand.js` deliberately writes "Domino" and never shows their logo, presumably to keep clear of the trademark. Naming them is generally fine when it describes what you deliver, but an ad does put the name in front of more eyes. If you plan to run paid ads, check with someone who knows Indian trademark law. Changing it back is a text edit in `src/index.html` and `src/main.js` plus three VO lines (`menu`, `deliv`, `tag` in `audio/vo.py`).

- **The voice is generated by Sarvam's API under your account.** Check Sarvam's terms for commercial use of generated speech before you run this as a paid ad.

## Rebuild

```bash
npm install                                  # fonts + Playwright (uses the preinstalled Chromium)
pip install numpy scipy soundfile pillow bpy  # bpy is Blender 5 as a Python module

python3 scripts/site_frames.py               # recording -> src/site/*.jpg (1.5x Lanczos) + frames.json
(cd food && ./render_all.sh)                 # optional, about 1.5-2 h on 4 cores: the graded JPEGs are committed
python3 audio/mix.py                         # music + SFX + VO mix -> audio/build/mix.wav (-14 LUFS)
node scripts/render.mjs --parts 3            # frames -> H.264 + AAC -> out/offers-ki-duniya-promo.mp4
```

- **Voiceover.** `audio/vo.py` generates every line with Sarvam AI's text-to-speech (model `bulbul:v3`, voice `shubh`, Indian English). The WAVs are committed, so you only need it to change a line. It needs network access to `api.sarvam.ai` and your key in the `SARVAM_API_KEY` environment variable; the key never goes in the repo. `SARVAM_API_KEY=… python3 audio/vo.py loc` regenerates one line, and `--dry` prints each line's text and time slot without calling the API. A take that runs past the next line's cue is requested again at a faster pace, up to 1.4×.
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
audio/vo.py          voiceover (Sarvam bulbul:v3, voice shubh)
audio/mix.py         music, sound design, ducking, limiting, loudness
scripts/render.mjs   frame-accurate render + mux
```
