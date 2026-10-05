"""Food grade for linear EXRs from the Blender scenes.

python3 food/grade.py <in.exr | in_dir> <out.jpg | out.png | out_dir> [exposure=-0.8] [warm=0.08] [sat=1.45] [contrast=1.22]

Exposure in stops, a white-balance push towards warm, a filmic (Hable) shoulder so
highlights roll off like film instead of clipping, then saturation and contrast in
display space. One grade for every food shot keeps them matched.
"""
import os
import sys

import bpy
import numpy as np
from PIL import Image

A, B, C, D, E, F = 0.15, 0.50, 0.10, 0.20, 0.02, 0.30


def hable(x):
    return ((x * (A * x + C * B) + D * E) / (x * (A * x + B) + D * F)) - E / F


def grade(src, out, exposure=-0.8, warm=0.08, sat=1.45, contrast=1.22, white=6.0):
    img = bpy.data.images.load(src)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    rgb = px.reshape(h, w, 4)[::-1, :, :3].astype(np.float64)
    rgb *= 2.0 ** exposure
    rgb *= np.array([1 + warm, 1.0, 1 - warm * 1.4])
    rgb = np.clip(hable(rgb * 2.0) / hable(white), 0, 1)
    srgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
    lum = (srgb * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
    srgb = np.clip(lum + (srgb - lum) * sat, 0, 1)
    srgb = np.clip(0.5 + (srgb - 0.5) * contrast, 0, 1)
    im = Image.fromarray((srgb * 255 + 0.5).astype(np.uint8))
    if out.endswith('.jpg'):
        im.save(out, quality=93, subsampling=0)
    else:
        im.save(out)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    kw = {k: float(v) for k, v in (a.split('=') for a in sys.argv[3:])}
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for name in sorted(os.listdir(src)):
            if name.endswith('.exr'):
                grade(os.path.join(src, name), os.path.join(dst, name[:-4] + '.jpg'), **kw)
                print('graded', name, flush=True)
    else:
        grade(src, dst, **kw)
        print('graded', dst)
