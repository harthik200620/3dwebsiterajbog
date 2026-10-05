"""Voiceover: one WAV per line, spoken by Sarvam AI's Bulbul v3 voice "shubh" in Indian English.

Needs network access to api.sarvam.ai and an API key in SARVAM_API_KEY. The key is read
from the environment only; it is never written to the repo.

    SARVAM_API_KEY=... python3 audio/vo.py             # every line
    SARVAM_API_KEY=... python3 audio/vo.py loc menu    # only these ids (merged into lines.json)
    python3 audio/vo.py --dry                          # print the requests and slots, call nothing

Every line has to end before the next VO cue in timeline.json. A take that runs long is
requested again at a faster pace, up to MAX_PACE.
"""
import base64, io, json, os, sys, time, urllib.error, urllib.request
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "vo")
TL = json.load(open(os.path.join(HERE, "..", "timeline.json")))
API = "https://api.sarvam.ai/text-to-speech"
MODEL = "bulbul:v3"
SPEAKER = os.environ.get("VO_SPEAKER", "shubh")
LANG = "en-IN"
SR = 24000            # Bulbul v3's native rate
MAX_PACE = 1.4        # faster than this stops sounding like a read
GAP = 0.08            # seconds of air before the next line
TAIL = 0.4            # the last line ends this long before the video does

# id, text, starting pace
LINES = [
    ("love",   "Love pizza?", 1.0),
    ("hate",   "But hate the bill?", 1.0),
    ("why",    "Why pay full price, for the same pizza?", 1.05),
    ("bring",  "We bring to you...", 0.95),
    ("brand",  "Offers Ki Duniya!", 0.95),
    ("loc",    "Set your location, anywhere in India.", 1.1),
    ("menu",   "The same Domino's menu.", 1.05),
    ("add",    "Just add to cart...", 1.05),
    ("drop",   "and watch the price drop. Live!", 1.05),
    ("auto",   "The best offer applies automatically. No coupon code.", 1.1),
    ("save",   "Save up to two hundred and ninety-five rupees, with free delivery!", 1.1),
    ("bigger", "The bigger the order, the bigger the saving.", 1.05),
    ("same",   "Same pizza.", 1.0),
    ("deliv",  "Delivered by Domino's.", 1.0),
    ("lower",  "At a lower price.", 1.0),
    ("cta",    "Order now on Offers Ki Duniya dot com!", 1.0),
    ("tag",    "Offers Ki Duniya. Domino's pizza, for less.", 0.95),
]


def slots():
    """Seconds each line may run: up to the next cue (less GAP), or to the end of the video."""
    cues = sorted(TL["vo"].items(), key=lambda kv: kv[1])
    out = {}
    for k, (lid, t0) in enumerate(cues):
        out[lid] = (cues[k + 1][1] - GAP if k + 1 < len(cues) else TL["duration"] - TAIL) - t0
    return out


def tts(text, pace, key, tries=4):
    body = json.dumps({"text": text, "language_code": LANG, "model": MODEL, "speaker": SPEAKER,
                       "pace": round(pace, 3), "speech_sample_rate": SR}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "api-subscription-key": key, "Content-Type": "application/json", "Accept": "application/json"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 502, 503, 504) and i + 1 < tries:
                time.sleep(2 ** (i + 1))
                continue
            sys.exit(f"Sarvam TTS {e.code}: {msg}")
    a, sr = sf.read(io.BytesIO(base64.b64decode("".join(data["audios"]))), dtype="float32")
    return (a.mean(axis=1) if a.ndim > 1 else a), sr


def trim(a, sr, pre=0.03, post=0.08, floor_db=-42.0):
    """Cut the silence the model leaves around a take, so each line starts on its cue."""
    env = np.convolve(np.abs(a), np.ones(int(0.005 * sr)) / int(0.005 * sr), mode="same")
    loud = np.nonzero(env > env.max() * 10 ** (floor_db / 20))[0]
    if not len(loud):
        return a
    out = a[max(0, loud[0] - int(pre * sr)):min(len(a), loud[-1] + int(post * sr))].copy()
    f = int(0.008 * sr)
    out[:f] *= np.linspace(0, 1, f)
    out[-f:] *= np.linspace(1, 0, f)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    only = set(args)
    unknown = only - {l[0] for l in LINES}
    if unknown:
        sys.exit(f"unknown line ids: {', '.join(sorted(unknown))}")
    key = os.environ.get("SARVAM_API_KEY", "")
    if not key and not dry:
        sys.exit("set SARVAM_API_KEY (see the docstring)")
    S = slots()
    os.makedirs(OUT, exist_ok=True)
    meta_path = os.path.join(OUT, "lines.json")
    meta = json.load(open(meta_path)) if only and os.path.exists(meta_path) else {}
    long_lines = []
    for lid, text, pace in LINES:
        if only and lid not in only:
            continue
        if dry:
            print(f"{lid:6s} slot {S[lid]:.2f}s  pace {pace:.2f}  {text}")
            continue
        for _ in range(4):
            a, sr = tts(text, pace, key)
            a = trim(a, sr)
            dur = len(a) / sr
            if dur <= S[lid] or pace >= MAX_PACE:
                break
            pace = min(MAX_PACE, pace * dur / S[lid] * 1.03)
        if dur > S[lid]:
            long_lines.append(lid)
        sf.write(os.path.join(OUT, f"{lid}.wav"), a, sr, subtype="PCM_16")
        meta[lid] = {"dur": round(dur, 3), "slot": round(S[lid], 3), "pace": round(pace, 3), "sr": sr,
                     "voice": f"sarvam {MODEL} {SPEAKER} {LANG}", "text": text}
        print(f"{lid:6s} {dur:.2f}s of {S[lid]:.2f}s  pace {pace:.2f}  {text}", flush=True)
    if dry:
        return
    order = [l[0] for l in LINES]
    meta = {k: meta[k] for k in sorted(meta, key=lambda x: order.index(x) if x in order else 99)}
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    if long_lines:
        sys.exit(f"still longer than their slot at pace {MAX_PACE}: {', '.join(long_lines)}")


if __name__ == "__main__":
    main()
