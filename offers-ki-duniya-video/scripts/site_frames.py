"""Frames of the real site recording for the website segment.

python3 scripts/site_frames.py [site/recording.mp4]

Decodes the recording between the first and last source second the edit uses
(timeline.json "site_edl"), upscales 1.5x with Lanczos plus a light unsharp mask
(the phone mock-up shows the screen at about 1.2-1.6x the recording's 576 px width),
and writes src/site/NNNNN.jpg with src/site/frames.json listing each frame's source
time. The composition picks, for every output frame, the newest source frame at or
before the edited source time, so the edit can change without re-extracting.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'site', 'recording.mp4')
tl = json.load(open(os.path.join(ROOT, 'timeline.json')))
edl = tl['site_edl']
t0 = max(0.0, min(s['src'][0] for s in edl) - 0.5)
t1 = max(s['src'][1] for s in edl) + 0.5
out = os.path.join(ROOT, 'src', 'site')
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    if f.endswith('.jpg'):
        os.remove(os.path.join(out, f))
# showinfo logs each frame's source time; setpts then renumbers frames 0, 1, 2... so the image
# muxer never sees two frames with the same timestamp (the recording is variable frame rate)
vf = f'trim=start={t0}:end={t1},showinfo,scale=864:1944:flags=lanczos,unsharp=5:5:0.55:5:5:0.0,setpts=N/(30*TB)'
cmd = ['ffmpeg', '-v', 'info', '-y', '-i', src, '-map', '0:v', '-vf', vf, '-enc_time_base', '1/30', '-fps_mode', 'passthrough', '-q:v', '3',
       os.path.join(out, '%05d.jpg')]
log = subprocess.run(cmd, capture_output=True, text=True).stderr
times = [float(m) for m in re.findall(r'pts_time:\s*([0-9.]+)', log)]
n = len([f for f in os.listdir(out) if f.endswith('.jpg')])
assert n == len(times), (n, len(times))
json.dump({'t0': t0, 't1': t1, 'times': [round(t, 4) for t in times]}, open(os.path.join(out, 'frames.json'), 'w'))
print(f'{n} frames, {times[0]:.2f}-{times[-1]:.2f}s')
