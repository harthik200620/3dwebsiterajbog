"""Food grade for linear EXRs from the Blender scenes.

python3 food/grade.py <in.exr | in_dir> <out.jpg | out.png | out_dir> [exposure=-0.8] [warm=0.08] [sat=1.45]
                      [contrast=1.22] [bloom=0]

Exposure in stops, a white-balance push towards warm, optional bloom (the warm halo a real
lens throws around bright highlights), a filmic (Hable) shoulder so highlights roll off like
film instead of clipping, then saturation and contrast in display space. One grade for every
food shot keeps them matched. In directory mode, matte_*.png files are reduced to white +
alpha so they compress to almost nothing.
"""
import os
import sys

import bpy
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, zoom

A, B, C, D, E, F = 0.15, 0.50, 0.10, 0.20, 0.02, 0.30


def hable(x):
    return ((x * (A * x + C * B) + D * E) / (x * (A * x + B) + D * F)) - E / F


def bloom_pass(rgb, strength, threshold=0.9):
    """Energy above the threshold, blurred wide and narrow, added back with a warm tint."""
    lum = (rgb * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
    hi = rgb * np.clip(lum - threshold, 0, None) / np.maximum(lum, 1e-6)
    small = zoom(hi, (0.25, 0.25, 1), order=1)
    h, w = small.shape[:2]
    glow = gaussian_filter(small, (w * 0.02, w * 0.02, 0)) * 0.6 + gaussian_filter(small, (w * 0.006, w * 0.006, 0)) * 0.4
    glow = zoom(glow, (rgb.shape[0] / h, rgb.shape[1] / w, 1), order=1)
    return rgb + strength * glow * np.array([1.0, 0.82, 0.6])


def grade(src, out, exposure=-0.8, warm=0.08, sat=1.45, contrast=1.22, white=6.0, bloom=0.0):
    img = bpy.data.images.load(src)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    rgb = px.reshape(h, w, 4)[::-1, :, :3].astype(np.float64)
    rgb *= 2.0 ** exposure
    rgb *= np.array([1 + warm, 1.0, 1 - warm * 1.4])
    if bloom > 0:
        rgb = bloom_pass(rgb, bloom)
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
            elif name.startswith('matte_') and name.endswith('.png'):
                a = Image.open(os.path.join(src, name)).split()[-1]
                m = Image.new('LA', a.size, 255)
                m.putalpha(a)
                m.save(os.path.join(dst, name), optimize=True)
    else:
        grade(src, dst, **kw)
        print('graded', dst)
