"""Final logo files: text set with HarfBuzz and converted to outlines, so the SVGs need no fonts."""
import io, os, re
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen

NM = 'node_modules'
def load(path, wght=None):
    f = TTFont(path)
    if wght is not None and 'fvar' in f:
        f = instantiateVariableFont(f, {'wght': wght})
    f.flavor = None
    buf = io.BytesIO(); f.save(buf); data = buf.getvalue()
    return TTFont(io.BytesIO(data)), hb.Font(hb.Face(hb.Blob(data)))

SHRIK = load(f'{NM}/@fontsource/shrikhand/files/shrikhand-latin-400-normal.woff2')
BALOO8 = load(f'{NM}/@fontsource-variable/baloo-2/files/baloo-2-latin-wght-normal.woff2', 800)
BALOO6 = load(f'{NM}/@fontsource-variable/baloo-2/files/baloo-2-latin-wght-normal.woff2', 600)

def text_path(font, text, size, x, baseline, tracking=0.0):
    """Returns (svg path d, advance width, (xmin, ymin, xmax, ymax)) in px."""
    tt, hbf = font
    upm = tt['head'].unitsPerEm
    s = size / upm
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(hbf, buf, {'kern': True, 'liga': True})
    gs = tt.getGlyphSet(); order = tt.getGlyphOrder()
    pen_x = 0.0; ds = []; bx = [1e9, 1e9, -1e9, -1e9]
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        ox = x + (pen_x + pos.x_offset) * s
        oy = baseline - pos.y_offset * s
        sp = SVGPathPen(gs)
        gs[name].draw(TransformPen(sp, (s, 0, 0, -s, ox, oy)))   # font units, y up -> px, y down
        d = sp.getCommands()
        if d:
            ds.append(d)
        bp = BoundsPen(gs); gs[name].draw(TransformPen(bp, (s, 0, 0, -s, ox, oy)))
        if bp.bounds:
            x0, y0, x1, y1 = bp.bounds
            bx = [min(bx[0], x0), min(bx[1], y0), max(bx[2], x1), max(bx[3], y1)]
        pen_x += pos.x_advance + tracking * upm
    return ''.join(ds), pen_x * s, bx

ICON = open('icon.svg').read()
icon_inner = ICON[ICON.index('>') + 1: ICON.rindex('</svg>')]

PAL = {
    'light': {'offers': '#e23a28', 'ki': '#2a1a12', 'tag': '#8a6e55', 'bg': None},
    'dark': {'offers': '#ff5a3c', 'ki': '#fff6e8', 'tag': '#f6d48a', 'bg': None},
}

def lockup(kind='horizontal', theme='light', tagline=False, bg=None, pad=24):
    P = PAL[theme]
    parts = []
    if kind == 'horizontal':
        isz = 200
        ox = isz + 26
        d1, w1, b1 = text_path(SHRIK, 'Offers', 126, ox, 0)
        d2, w2, b2 = text_path(BALOO8, 'ki Duniya', 60, ox + 6, 0)
        # stack: "Offers" cap top at 0, "ki Duniya" 10px under it
        o_top, o_bot = b1[1], b1[3]
        k_top, k_bot = b2[1], b2[3]
        y_off = -o_top
        k_base = (o_bot - o_top) + 12 - k_top
        blocks = [(d1, P['offers'], 0, y_off), (d2, P['ki'], 0, k_base)]
        h_text = (o_bot - o_top) + 12 + (k_bot - k_top)
        if tagline:
            d3, w3, b3 = text_path(BALOO6, 'Domino pizza, for less.', 27, ox + 8, 0, 0.02)
            t_base = h_text + 14 - b3[1]
            blocks.append((d3, P['tag'], 0, t_base))
            h_text += 14 + (b3[3] - b3[1])
        H = max(isz, h_text)
        text_dy = (H - h_text) / 2
        icon_dy = (H - isz) / 2
        W = ox + max(b1[2], b2[2], (b3[2] if tagline else 0)) - ox
        W = max(b1[2], b2[2], (b3[2] if tagline else 0))
        parts.append(f'<g transform="translate(0 {icon_dy:.2f}) scale({isz / 240:.5f})">{icon_inner}</g>')
        for d, col, dx, dy in blocks:
            parts.append(f'<path transform="translate({dx} {text_dy + dy:.2f})" d="{d}" fill="{col}"/>')
    elif kind == 'stacked':
        isz = 260
        d1, w1, b1 = text_path(SHRIK, 'Offers', 140, 0, 0)
        d2, w2, b2 = text_path(BALOO8, 'ki Duniya', 66, 0, 0)
        W = max(isz, b1[2] - b1[0], b2[2] - b2[0])
        parts.append(f'<g transform="translate({(W - isz) / 2:.2f} 0) scale({isz / 240:.5f})">{icon_inner}</g>')
        y = isz + 18
        parts.append(f'<path transform="translate({(W - (b1[2] - b1[0])) / 2 - b1[0]:.2f} {y - b1[1]:.2f})" d="{d1}" fill="{P["offers"]}"/>')
        y += (b1[3] - b1[1]) + 12
        parts.append(f'<path transform="translate({(W - (b2[2] - b2[0])) / 2 - b2[0]:.2f} {y - b2[1]:.2f})" d="{d2}" fill="{P["ki"]}"/>')
        H = y + (b2[3] - b2[1])
    else:  # icon
        W = H = 240
        parts.append(icon_inner)
        pad = 0
    vb = f'{-pad} {-pad} {W + 2 * pad:.2f} {H + 2 * pad:.2f}'
    bgrect = f'<rect x="{-pad}" y="{-pad}" width="{W + 2 * pad:.2f}" height="{H + 2 * pad:.2f}" fill="{bg}"/>' if bg else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{W + 2 * pad:.0f}" height="{H + 2 * pad:.0f}">'
            f'<title>Offers Ki Duniya</title>{bgrect}{"".join(parts)}</svg>')

os.makedirs('out', exist_ok=True)
files = {
    'offers-ki-duniya-logo.svg': lockup('horizontal', 'light'),
    'offers-ki-duniya-logo-dark.svg': lockup('horizontal', 'dark'),
    'offers-ki-duniya-logo-tagline.svg': lockup('horizontal', 'light', tagline=True),
    'offers-ki-duniya-logo-stacked.svg': lockup('stacked', 'light'),
    'offers-ki-duniya-logo-stacked-dark.svg': lockup('stacked', 'dark'),
    'offers-ki-duniya-icon.svg': lockup('icon'),
}
for name, svg in files.items():
    open(f'../{name}', 'w').write(svg)
    print(name, len(svg))
