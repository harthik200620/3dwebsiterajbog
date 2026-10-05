"""Voiceover: one WAV per line with Kokoro (offline neural TTS).

The brand name is spoken from hand-written phonemes: English G2P reads
"Ki Duniya" as "kai dyoo-nee-ya"; the Hindi is "kee DOO-nee-yaa".
Model files: github.com/thewh1teagle/kokoro-onnx releases (model-files-v1.0).
"""
import json, os, sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

MODELS = os.environ.get("KOKORO_DIR", os.path.join(os.path.dirname(__file__), "models"))
OUT = os.path.join(os.path.dirname(__file__), "vo")
VOICE = os.environ.get("VO_VOICE", "af_heart")
BRAND = "ˈɔfɚz kˈi dˈʊnɪjɑ"

# id, text (or None when phonemes given), phonemes, speed
LINES = [
    ("love",     "Love pizza?", None, 1.0),
    ("hate",     "But hate the bill?", None, 1.0),
    ("why",      "Why pay full price, for the same pizza?", None, 1.05),
    ("bring",    "We bring to you...", None, 0.95),
    ("brand",    None, BRAND + "!", 0.9),
    ("loc",      "Set your location, anywhere in India.", None, 1.12),
    ("menu",     "The same Domino's menu.", None, 1.05),
    ("add",      "Just add to cart...", None, 1.05),
    ("drop",     "and watch the price drop. Live!", None, 1.05),
    ("auto",     "The best offer applies automatically. No coupon code.", None, 1.1),
    ("save",     "Save up to two hundred and ninety-five rupees, with free delivery!", None, 1.1),
    ("bigger",   "The bigger the order, the bigger the saving.", None, 1.05),
    ("same",     "Same pizza.", None, 1.0),
    ("deliv",    "Delivered by Domino's.", None, 1.0),
    ("lower",    "At a lower price.", None, 1.0),
    ("cta",      None, None, 1.0),  # built below: "Order now on" + brand + "dot com"
    ("tag",      None, None, 0.95),  # built below: brand + "Domino pizza, for less."
]

def main():
    """python3 audio/vo.py [id ...]: all lines, or only the ids given (merged into lines.json)."""
    only = set(sys.argv[1:])
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    os.makedirs(OUT, exist_ok=True)
    meta_path = os.path.join(OUT, "lines.json")
    meta = json.load(open(meta_path)) if only and os.path.exists(meta_path) else {}
    for lid, text, ph, speed in LINES:
        if only and lid not in only:
            continue
        if lid == "cta":
            ph = k.tokenizer.phonemize("Order now on", "en-us") + " " + BRAND + " dˈɑt kˈɑm!"
        if lid == "tag":
            ph = BRAND + ". " + k.tokenizer.phonemize("Domino's pizza, for less.", "en-us")
        if ph is not None:
            audio, sr = k.create(ph, voice=VOICE, speed=speed, is_phonemes=True)
        else:
            audio, sr = k.create(text, voice=VOICE, speed=speed, lang="en-us")
        audio = np.asarray(audio, dtype=np.float32)
        sf.write(os.path.join(OUT, f"{lid}.wav"), audio, sr)
        meta[lid] = {"dur": round(len(audio) / sr, 3), "sr": sr, "text": text or ph}
        print(f"{lid:6s} {meta[lid]['dur']:.2f}s  {text or ph}")
    order = [l[0] for l in LINES]
    meta = {k2: meta[k2] for k2 in sorted(meta, key=lambda x: order.index(x) if x in order else 99)}
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main()
