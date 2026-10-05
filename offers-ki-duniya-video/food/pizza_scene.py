"""Photoreal pizza, built procedurally and path-traced with Blender Cycles.

Run with the `bpy` module (pip install bpy):  python3 food/pizza_scene.py <shot> [options]

Everything is generated from a seed: the dough rim, the sauce, the melted cheese
with its blisters, every topping and the board it sits on. Units: the pizza has a
radius of 1.0 (about 12.5 cm), so subsurface radii are set in those units.
"""
import math
import os
import random
import sys
import time

import bpy
import numpy as np
from mathutils import Vector, Euler, noise

TAU = math.tau
METRES_PER_UNIT = 0.127   # pizza radius 1.0 = 12.7 cm (a 10-inch medium)


# ----------------------------------------------------------------- colours
def lin(hexstr, a=1.0):
    """sRGB hex -> linear RGBA for Blender sockets."""
    h = hexstr.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (a,)


def n1(x, seed=0.0):
    """Smooth 1-D noise in [-1, 1] (Perlin through mathutils)."""
    return noise.noise(Vector((x, seed * 13.37, seed * 7.1))) * 1.6


def ang_noise(theta, freq, seed):
    """Periodic noise around the circle (works on scalars and numpy arrays)."""
    if isinstance(theta, np.ndarray):
        return np.array([ang_noise(float(t), freq, seed) for t in theta.ravel()]).reshape(theta.shape)
    return n1(math.cos(theta) * freq + 10, seed) * 0.6 + n1(math.sin(theta) * freq + 20, seed + 3) * 0.6


def vnoise(x, y, seed=0, octaves=4):
    """Vectorised 2-D value noise (fBm) in about [-1, 1]."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    total = np.zeros_like(x)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        f = 2.0 ** o
        xi, yi = np.floor(x * f), np.floor(y * f)
        xf, yf = x * f - xi, y * f - yi
        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
        v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
        def h(a, b):
            n = (a.astype(np.int64) * 374761393 + b.astype(np.int64) * 668265263 + (seed + o * 101) * 2147483647) & 0xFFFFFFFF
            n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
            return (n & 0xFFFF) / 32767.5 - 1.0
        a = h(xi, yi); b = h(xi + 1, yi); c = h(xi, yi + 1); d = h(xi + 1, yi + 1)
        total += amp * ((a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v)
        norm += amp
        amp *= 0.5
    return total / norm


def _hash(ix, iy, seed):
    """Integer lattice hash -> [0, 1)."""
    n = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n = n ^ (n >> 16)
    return (n & 0xFFFFFF) / float(0x1000000)


def worley(x, y, seed=0, jitter=0.9):
    """Cellular noise: distances to the nearest two feature points (F1, F2) and a random
    value for the nearest cell. Melted cheese is a field of cells: F2 - F1 is 0 on the
    creases between bubbles and grows towards each bubble's middle."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xi, yi = np.floor(x), np.floor(y)
    F1 = np.full(x.shape, 9.0)
    F2 = np.full(x.shape, 9.0)
    C = np.zeros(x.shape)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx, cy = xi + dx, yi + dy
            px = cx + 0.5 + (_hash(cx, cy, seed) - 0.5) * jitter
            py = cy + 0.5 + (_hash(cx, cy, seed + 1) - 0.5) * jitter
            d = np.hypot(x - px, y - py)
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d))
            C = np.where(closer, _hash(cx, cy, seed + 2), C)
            F1 = np.where(closer, d, F1)
    return F1, F2, C


# ------------------------------------------------------------------ meshes
def polar_mesh(name, rings, n_t, height, keep=None, attrs=None):
    """A disc as a polar grid. rings: radii (rings[0] == 0).
    height(R, T) -> Z works on numpy arrays. keep(t) drops faces outside an angular range
    (for slices). attrs: {name: fn(R, T, Z) -> array} stored as point attributes."""
    ts = np.linspace(0, TAU, n_t, endpoint=False)
    rr = np.asarray(rings[1:], dtype=np.float64)
    T, Rr = np.meshgrid(ts, rr)                       # (n_r-1, n_t)
    Z = height(Rr, T)
    z0 = float(height(np.array([[0.0]]), np.array([[0.0]]))[0, 0])
    X, Y = Rr * np.cos(T), Rr * np.sin(T)
    verts = np.concatenate([[[0.0, 0.0, z0]], np.stack([X, Y, Z], -1).reshape(-1, 3)])
    nr = len(rr)
    jj = np.arange(n_t)
    mid = (ts + np.pi / n_t) % TAU
    ok = np.array([True] * n_t) if keep is None else np.array([bool(keep(m)) for m in mid])
    idx = lambda i, j: 1 + i * n_t + (j % n_t)
    tris = [(0, idx(0, j), idx(0, j + 1)) for j in jj if ok[j]]
    quads = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(nr - 1) for j in jj if ok[j]]
    used = sorted({v for f in tris + quads for v in f})
    remap = {v: k for k, v in enumerate(used)}
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts[used].tolist(), [], [tuple(remap[v] for v in f) for f in tris + quads])
    me.update()
    for k, fn in (attrs or {}).items():
        vals = np.concatenate([[float(fn(np.array([[0.0]]), np.array([[0.0]]), np.array([[z0]]))[0, 0])], fn(Rr, T, Z).ravel()])
        a = me.attributes.new(k, 'FLOAT', 'POINT')
        a.data.foreach_set('value', vals[used].astype(np.float32))
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def ring_radii(r_max, n, dense_from=None, dense_n=0):
    """Radii for a polar grid, denser near the rim."""
    if dense_from is None:
        return list(np.linspace(0, r_max, n))
    a = list(np.linspace(0, dense_from, n, endpoint=False))
    b = list(np.linspace(dense_from, r_max, dense_n))
    return a + b


def sweep_arc(name, r_in, thick, height, arc, segs=28, bevel=0.35):
    """A curved strip (pepper / onion ring segment) lying flat, centred on the origin.
    Point attribute 'skin' is 1 on the outer edge of the ring."""
    verts, faces, skin = [], [], []
    # cross-section: rounded rectangle in (radial, z)
    prof = []
    m = 10
    for k in range(m):
        a = k / m * TAU
        x = math.cos(a)
        y = math.sin(a)
        # superellipse for a soft box
        px = math.copysign(abs(x) ** (1 - bevel), x)
        py = math.copysign(abs(y) ** (1 - bevel), y)
        prof.append((px * thick / 2, py * height / 2, (px + 1) / 2))
    rc = r_in + thick / 2
    for s in range(segs + 1):
        th = -arc / 2 + arc * s / segs
        # taper the ends
        taper = math.sin(math.pi * (0.06 + 0.88 * s / segs)) ** 0.35
        for (px, pz, sk) in prof:
            r = rc + px * taper
            verts.append((r * math.cos(th) - rc, r * math.sin(th), pz * taper + height / 2))
            skin.append(sk)
    for s in range(segs):
        for k in range(m):
            a = s * m + k
            b = s * m + (k + 1) % m
            faces.append((a, b, b + m, a + m))
    faces.append(tuple(range(m))[::-1])
    faces.append(tuple(range(segs * m, segs * m + m)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    a = me.attributes.new('skin', 'FLOAT', 'POINT')
    a.data.foreach_set('value', np.asarray(skin, dtype=np.float32))
    me.shade_smooth()
    return me


def rounded_box(name, sx, sy, sz, r=0.25, subdiv=3):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    mod = ob.modifiers.new('bev', 'BEVEL')
    mod.width = min(sx, sy, sz) * r
    mod.segments = 4
    bpy.ops.object.modifier_apply(modifier='bev')
    me = ob.data
    me.name = name
    me.shade_smooth()
    bpy.data.objects.remove(ob)
    return me


def jitter_mesh(me, rng, amp, freq=18.0):
    """Low-frequency vertex noise so nothing looks machined."""
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    sd = rng.random() * 100
    off = np.stack([vnoise(co[:, 0] * freq + sd, co[:, 1] * freq, int(sd) + k, 2) for k in range(3)], -1)
    co = co + off * amp
    me.vertices.foreach_set('co', co.ravel())
    me.update()
    return me


def chunk_mesh(name, sx, sy, sz, rng, skin_axis='side', round_=0.3):
    """A diced piece (pepper, tomato, onion): an irregular rounded box.
    'skin' marks one face (the vegetable's outer skin)."""
    me = rounded_box(name, sx, sy, sz, round_)
    jitter_mesh(me, rng, min(sx, sy, sz) * 0.35, 9.0 / max(sx, sy))
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    if skin_axis == 'side':
        v = np.clip((co[:, 1] / (sy / 2) - 0.45) / 0.55, 0, 1)
    else:
        v = np.clip((co[:, 2] / (sz / 2) - 0.2) / 0.8, 0, 1)
    a = me.attributes.new('skin', 'FLOAT', 'POINT')
    a.data.foreach_set('value', v.astype(np.float32))
    return me


def torus_mesh(name, major, minor, squash=0.7):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=40, minor_segments=14)
    ob = bpy.context.object
    ob.scale = (1, 1, squash)
    bpy.ops.object.transform_apply(scale=True)
    me = ob.data
    me.name = name
    me.shade_smooth()
    bpy.data.objects.remove(ob)
    return me


def ring_mesh(name, r_out, r_in, thick, rng, ellip=0.1, segs=48, prof_n=14, bevel=0.5):
    """A sliced ring (olive, jalapeno): an oval annulus with soft edges and a slightly
    off-centre hole. Point attribute 'skin' is 1 on the outer wall (the glossy skin) and
    0 on the two cut faces and the hole, which show the flesh."""
    e1 = rng.uniform(-ellip, ellip)
    ph = rng.uniform(0, TAU)
    ox, oy = (rng.uniform(-0.15, 0.15) * (r_out - r_in), rng.uniform(-0.15, 0.15) * (r_out - r_in))
    sd = rng.uniform(0, 50)
    prof = []
    for k in range(prof_n):
        a = k / prof_n * TAU
        x, y = math.cos(a), math.sin(a)
        prof.append((math.copysign(abs(x) ** (1 - bevel), x), math.copysign(abs(y) ** (1 - bevel), y)))
    verts, skin, rad = [], [], []
    for s in range(segs):
        th = s / segs * TAU
        wob = 1 + e1 * math.cos(2 * (th - ph)) + 0.035 * n1(math.cos(th) * 1.4 + sd, sd)
        ro, ri = r_out * wob, r_in * (1 + 0.7 * e1 * math.cos(2 * (th - ph)))
        c, s_ = math.cos(th), math.sin(th)
        for px, py in prof:
            u = (px + 1) / 2
            x = (ri * c + ox) * (1 - u) + ro * c * u
            y = (ri * s_ + oy) * (1 - u) + ro * s_ * u
            z = (py + 1) / 2 * thick * (1 - 0.12 * n1(th * 2 + sd, sd + 1))
            verts.append((x, y, z))
            skin.append(min(1.0, max(0.0, (px - 0.6) / 0.35)))
            rad.append(u)
    faces = []
    for s in range(segs):
        for k in range(prof_n):
            a = s * prof_n + k
            b = s * prof_n + (k + 1) % prof_n
            c2 = ((s + 1) % segs) * prof_n + (k + 1) % prof_n
            d = ((s + 1) % segs) * prof_n + k
            faces.append((a, d, c2, b))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    a = me.attributes.new('skin', 'FLOAT', 'POINT')
    a.data.foreach_set('value', np.asarray(skin, dtype=np.float32))
    a = me.attributes.new('rad', 'FLOAT', 'POINT')
    a.data.foreach_set('value', np.asarray(rad, dtype=np.float32))
    me.shade_smooth()
    me.update()
    return me


def kernel_mesh(name, rng):
    """A sweetcorn kernel: a rounded crown that tapers to a pointed base."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=9, radius=1.0)
    ob = bpy.context.object
    me = ob.data
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    z = co[:, 2].copy()
    taper = np.where(z < 0, 1 - 0.6 * (-z) ** 1.4, 1.0)
    co[:, 0] *= taper * 0.021 * rng.uniform(0.85, 1.15)
    co[:, 1] *= taper * 0.017 * rng.uniform(0.85, 1.15)
    co[:, 2] = np.where(z < 0, z * 0.019, z * 0.011)
    me.vertices.foreach_set('co', co.ravel())
    me.update()
    me.shade_smooth()
    me.name = name
    bpy.data.objects.remove(ob)
    return me


def pepper_piece(name, sx, sy, thick, rng, bend=0.22):
    """A diced piece of bell pepper: a small curved tile (the pepper's wall). 'skin' is the
    convex top: glossy, dark; the underside and the cut edges are the paler flesh."""
    me = rounded_box(name, sx, sy, thick, 0.32)
    jitter_mesh(me, rng, max(sx, sy) * 0.16, 6.0 / max(sx, sy))
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    co[:, 2] -= bend * (co[:, 0] / (sx / 2)) ** 2 * thick * 1.6
    co[:, 2] -= 0.4 * bend * (co[:, 1] / (sy / 2)) ** 2 * thick
    me.vertices.foreach_set('co', co.ravel())
    zc = co[:, 2] + bend * (co[:, 0] / (sx / 2)) ** 2 * thick * 1.6 + 0.4 * bend * (co[:, 1] / (sy / 2)) ** 2 * thick
    v = np.clip((zc / (thick / 2) - 0.35) / 0.5, 0, 1)
    a = me.attributes.new('skin', 'FLOAT', 'POINT')
    a.data.foreach_set('value', v.astype(np.float32))
    me.update()
    return me


def mushroom_mesh(name, size):
    """A sliced button mushroom: the cap's arc over a short stem, extruded thin."""
    pts = []
    n = 26
    for k in range(n + 1):
        a = math.pi * k / n
        pts.append((math.cos(a) * size * 0.5, math.sin(a) * size * 0.42 + size * 0.08))
    pts += [(-size * 0.13, size * 0.08), (-size * 0.1, -size * 0.3), (size * 0.11, -size * 0.31), (size * 0.14, size * 0.08)]
    thick = size * 0.075
    verts = [(x, y, 0) for x, y in pts] + [(x, y, thick) for x, y in pts]
    m = len(pts)
    faces = [tuple(range(m))[::-1], tuple(range(m, 2 * m))]
    for k in range(m):
        faces.append((k, (k + 1) % m, (k + 1) % m + m, k + m))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    edge = me.attributes.new('skin', 'FLOAT', 'POINT')
    # the cap's outer arc gets the brown skin
    vals = []
    for (x, y, z) in verts:
        d = math.hypot(x, y - size * 0.08)
        vals.append(min(1.0, max(0.0, (d - size * 0.3) / (size * 0.12))) if y > size * 0.02 else 0.15)
    edge.data.foreach_set('value', np.asarray(vals, dtype=np.float32))
    bev = None
    me.update()
    ob = bpy.data.objects.new('tmp', me)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    mod = ob.modifiers.new('bev', 'BEVEL')
    mod.width = thick * 0.4
    mod.segments = 3
    mod.limit_method = 'ANGLE'
    bpy.ops.object.modifier_apply(modifier='bev')
    me = ob.data
    me.shade_smooth()
    bpy.data.objects.remove(ob)
    return me


# --------------------------------------------------------------- materials
def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = nt.nodes['Material Output']
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.subsurface_method = 'RANDOM_WALK'
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return m, nt, bsdf


def mix_rgb(nt, fac=None, a=None, b=None, fac_value=0.0, a_col=None, b_col=None):
    m = nt.nodes.new('ShaderNodeMix')
    m.data_type = 'RGBA'
    sock = lambda coll, ident: next(x for x in coll if x.identifier == ident)
    f, A, B, out = sock(m.inputs, 'Factor_Float'), sock(m.inputs, 'A_Color'), sock(m.inputs, 'B_Color'), sock(m.outputs, 'Result_Color')
    f.default_value = fac_value
    if fac is not None:
        nt.links.new(fac, f)
    if a is not None:
        nt.links.new(a, A)
    if b is not None:
        nt.links.new(b, B)
    if a_col:
        A.default_value = lin(a_col)
    if b_col:
        B.default_value = lin(b_col)
    return out


def ramp(nt, stops, interp='LINEAR'):
    r = nt.nodes.new('ShaderNodeValToRGB')
    r.color_ramp.interpolation = interp
    els = r.color_ramp.elements
    while len(els) > len(stops):
        els.remove(els[-1])
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, col) in zip(els, stops):
        el.position = pos
        el.color = lin(col)
    return r


def attr(nt, name):
    a = nt.nodes.new('ShaderNodeAttribute')
    a.attribute_name = name
    a.attribute_type = 'GEOMETRY'
    return a


def noise_tex(nt, scale, detail=6, rough=0.55, dist=0.0, coord=None):
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough
    n.inputs['Distortion'].default_value = dist
    if coord is not None:
        nt.links.new(coord, n.inputs['Vector'])
    return n


def math_node(nt, op, a=None, b=None, va=0.0, vb=0.0, clamp=False):
    m = nt.nodes.new('ShaderNodeMath')
    m.operation = op
    m.use_clamp = clamp
    m.inputs[0].default_value = va
    m.inputs[1].default_value = vb
    if a is not None:
        nt.links.new(a, m.inputs[0])
    if b is not None:
        nt.links.new(b, m.inputs[1])
    return m


def bump(nt, height_socket, strength, distance=0.02, normal=None):
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = distance
    nt.links.new(height_socket, bp.inputs['Height'])
    if normal is not None:
        nt.links.new(normal, bp.inputs['Normal'])
    return bp


def mat_cheese():
    """Melted mozzarella. 'brown' (blister tops, the edge) and 'oil' (creases, pools) are
    point attributes baked from the same cells that shape the surface, so the colour,
    the gloss and the bumps always agree with each other."""
    m, nt, b = node_mat('cheese')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    br = attr(nt, 'brown')
    oil = attr(nt, 'oil')
    fine = noise_tex(nt, 95.0, 6, 0.55, 0.0, tc.outputs['Object'])
    mid = noise_tex(nt, 24.0, 5, 0.55, 0.35, tc.outputs['Object'])
    # ragged edges on the browning so no spot looks stencilled
    jit = math_node(nt, 'MULTIPLY_ADD', mid.outputs['Fac'], None, 0, 0.34)
    jit.inputs[2].default_value = -0.17
    b2 = math_node(nt, 'ADD', br.outputs['Fac'], jit.outputs[0], clamp=True)
    col = ramp(nt, [(0.0, '#f4dc98'), (0.2, '#f2cc74'), (0.4, '#ebb04f'), (0.58, '#d4842f'),
                    (0.75, '#a55a20'), (0.9, '#6a3413'), (1.0, '#3a1a0a')])
    nt.links.new(b2.outputs[0], col.inputs['Fac'])
    # oil: a golden film in the creases and in a few pools
    of = math_node(nt, 'MULTIPLY', oil.outputs['Fac'], None, 0, 0.6)
    c2 = mix_rgb(nt, fac=of.outputs[0], a=col.outputs['Color'], b_col='#f2a238')
    nt.links.new(c2, b.inputs['Base Color'])
    # wet in the oil, drier where it browned
    r1 = math_node(nt, 'MULTIPLY_ADD', oil.outputs['Fac'], None, 0, -0.2)
    r1.inputs[2].default_value = 0.3
    r2 = math_node(nt, 'MULTIPLY_ADD', b2.outputs[0], None, 0, 0.28)
    nt.links.new(r1.outputs[0], r2.inputs[2])
    r3 = math_node(nt, 'MULTIPLY_ADD', fine.outputs['Fac'], None, 0, 0.12)
    nt.links.new(r2.outputs[0], r3.inputs[2])
    r4 = math_node(nt, 'SUBTRACT', r3.outputs[0], None, 0, 0.06, clamp=True)
    nt.links.new(r4.outputs[0], b.inputs['Roughness'])
    cw = math_node(nt, 'MULTIPLY_ADD', oil.outputs['Fac'], None, 0, 0.55)
    cw.inputs[2].default_value = 0.15
    nt.links.new(cw.outputs[0], b.inputs['Coat Weight'])
    b.inputs['Coat Roughness'].default_value = 0.035
    b.inputs['Coat Tint'].default_value = lin('#fff1cc')
    b.inputs['Subsurface Weight'].default_value = 0.45
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.55, 0.2)
    b.inputs['Subsurface Scale'].default_value = 0.025
    b.inputs['Specular IOR Level'].default_value = 0.6
    h = math_node(nt, 'MULTIPLY_ADD', mid.outputs['Fac'], None, 0, 0.7)
    nt.links.new(fine.outputs['Fac'], h.inputs[2])
    bp = bump(nt, h.outputs[0], 0.22, 0.006)
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Coat Normal'])
    return m


def mat_crust():
    m, nt, b = node_mat('crust')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    toast = attr(nt, 'toast')
    nz = noise_tex(nt, 14.0, 8, 0.62, 0.3, tc.outputs['Object'])
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 38.0
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
    a1 = math_node(nt, 'SUBTRACT', nz.outputs['Fac'], None, 0, 0.5)
    a2 = math_node(nt, 'MULTIPLY', a1.outputs[0], None, 0, 0.55)
    a3 = math_node(nt, 'ADD', toast.outputs['Fac'], a2.outputs[0])
    col = ramp(nt, [(0.0, '#eec98c'), (0.25, '#e0a250'), (0.5, '#c97a2c'), (0.72, '#9d521a'), (0.88, '#6a3311'), (1.0, '#33180a')])
    nt.links.new(a3.outputs[0], col.inputs['Fac'])
    # flour dust on the high spots
    flour_n = noise_tex(nt, 5.0, 4, 0.5, 0.0, tc.outputs['Object'])
    flour = math_node(nt, 'GREATER_THAN', flour_n.outputs['Fac'], None, 0, 0.62)
    fmul = math_node(nt, 'MULTIPLY', flour.outputs[0], None, 0, 0.07)
    fl = mix_rgb(nt, fac=fmul.outputs[0], a=col.outputs['Color'], b_col='#f6ead2')
    nt.links.new(fl, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.46
    b.inputs['Coat Weight'].default_value = 0.25
    b.inputs['Coat Roughness'].default_value = 0.3
    b.inputs['Subsurface Weight'].default_value = 0.25
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.6, 0.35)
    b.inputs['Subsurface Scale'].default_value = 0.02
    b.inputs['Specular IOR Level'].default_value = 0.4
    det = noise_tex(nt, 90.0, 5, 0.55, 0.0, tc.outputs['Object'])
    h = math_node(nt, 'ADD', det.outputs['Fac'], vor.outputs['Distance'])
    bp = bump(nt, h.outputs[0], 0.35, 0.02)
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_simple(name, base, rough=0.3, sss=0.0, sss_rad=(1, 0.3, 0.2), coat=0.0, skin=None, spec=0.5,
               transmission=0.0, skin_rough=None, bump_s=0.08, char=0.0):
    """skin=(hex) mixes a second colour (and skin_rough) by the 'skin' point attribute."""
    m, nt, b = node_mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = noise_tex(nt, 40.0, 4, 0.5, 0.0, tc.outputs['Object'])
    var = noise_tex(nt, 9.0, 3, 0.5, 0.0, tc.outputs['Object'])
    if skin:
        sk = attr(nt, 'skin')
        col = mix_rgb(nt, fac=sk.outputs['Fac'], a_col=base, b_col=skin)
        if skin_rough is not None:
            mr = nt.nodes.new('ShaderNodeMapRange')
            nt.links.new(sk.outputs['Fac'], mr.inputs['Value'])
            mr.inputs['To Min'].default_value = rough
            mr.inputs['To Max'].default_value = skin_rough
            nt.links.new(mr.outputs['Result'], b.inputs['Roughness'])
        else:
            b.inputs['Roughness'].default_value = rough
    else:
        col = None
        b.inputs['Roughness'].default_value = rough
    # a little colour variation so no two pieces are identical
    vmix = nt.nodes.new('ShaderNodeHueSaturation')
    vmix.inputs['Saturation'].default_value = 1.0
    vv = math_node(nt, 'MULTIPLY_ADD', var.outputs['Fac'], None, 0, 0.3)
    vv.inputs[2].default_value = 0.85
    nt.links.new(vv.outputs[0], vmix.inputs['Value'])
    if col is not None:
        nt.links.new(col, vmix.inputs['Color'])
    else:
        vmix.inputs['Color'].default_value = lin(base)
    final = vmix.outputs['Color']
    if char:
        # the oven browns sharp edges and tips first
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        pr = ramp(nt, [(0.5, '#000000'), (0.62, '#ffffff')])
        nt.links.new(geo.outputs['Pointiness'], pr.inputs['Fac'])
        cn = noise_tex(nt, 30.0, 3, 0.5, 0.0, tc.outputs['Object'])
        cf = math_node(nt, 'MULTIPLY', pr.outputs['Color'], cn.outputs['Fac'])
        cf2 = math_node(nt, 'MULTIPLY', cf.outputs[0], None, 0, char * 1.6, clamp=True)
        final = mix_rgb(nt, fac=cf2.outputs[0], a=final, b_col='#3b2412')
    nt.links.new(final, b.inputs['Base Color'])
    b.inputs['Subsurface Weight'].default_value = sss
    b.inputs['Subsurface Radius'].default_value = sss_rad
    b.inputs['Subsurface Scale'].default_value = 0.01
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = 0.05
    b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['Transmission Weight'].default_value = transmission
    bp = bump(nt, nz.outputs['Fac'], bump_s, 0.01)
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Coat Normal'])
    return m


def mat_jalapeno():
    """A pickled jalapeno slice: pale seeded pith in the middle, olive flesh, a dark glossy skin."""
    m, nt, b = node_mat('jalapeno')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    rad = attr(nt, 'rad')
    sk = attr(nt, 'skin')
    flesh = ramp(nt, [(0.0, '#efe4b0'), (0.36, '#e2d38c'), (0.5, '#a9ad4f'), (1.0, '#7c8a34')])
    nt.links.new(rad.outputs['Fac'], flesh.inputs['Fac'])
    col = mix_rgb(nt, fac=sk.outputs['Fac'], a=flesh.outputs['Color'], b_col='#2a4815')
    nt.links.new(col, b.inputs['Base Color'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(sk.outputs['Fac'], mr.inputs['Value'])
    mr.inputs['To Min'].default_value = 0.34
    mr.inputs['To Max'].default_value = 0.12
    nt.links.new(mr.outputs['Result'], b.inputs['Roughness'])
    b.inputs['Subsurface Weight'].default_value = 0.45
    b.inputs['Subsurface Radius'].default_value = (0.7, 1.0, 0.4)
    b.inputs['Subsurface Scale'].default_value = 0.01
    b.inputs['Coat Weight'].default_value = 0.5
    b.inputs['Coat Roughness'].default_value = 0.05
    # seeds: small bumps where the pith is
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 160.0
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
    inv = math_node(nt, 'SUBTRACT', None, rad.outputs['Fac'], 0.5, 0, clamp=True)
    h = math_node(nt, 'MULTIPLY', vor.outputs['Distance'], inv.outputs[0])
    bp = bump(nt, h.outputs[0], 0.5, 0.004)
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_sauce():
    return mat_simple('sauce', '#a8240f', rough=0.28, sss=0.35, sss_rad=(1, 0.2, 0.1), coat=0.3)


def mat_board(kind='wood'):
    m, nt, b = node_mat('board_' + kind)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    if kind in ('wood', 'oak'):
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (0.25, 2.2, 1.0)
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
        dist = noise_tex(nt, 1.6, 6, 0.6, 0.0, mp.outputs['Vector'])
        wave = nt.nodes.new('ShaderNodeTexWave')
        wave.wave_type = 'BANDS'
        wave.inputs['Scale'].default_value = 2.6
        wave.inputs['Distortion'].default_value = 2.2
        wave.inputs['Detail'].default_value = 6
        wave.inputs['Detail Scale'].default_value = 1.6
        nt.links.new(mp.outputs['Vector'], wave.inputs['Vector'])
        mix = math_node(nt, 'MULTIPLY_ADD', wave.outputs['Fac'], dist.outputs['Fac'], 0, 0)
        mix.inputs[2].default_value = 0.0
        col = ramp(nt, [(0.0, '#1a0e07'), (0.35, '#3a2214'), (0.6, '#5a3820'), (0.85, '#6d4428'), (1.0, '#2a170c')] if kind == 'wood' else
                   [(0.0, '#7a4e2a'), (0.35, '#a06b3c'), (0.6, '#b98350'), (0.85, '#c99662'), (1.0, '#8c5a30')])
        nt.links.new(mix.outputs[0], col.inputs['Fac'])
        nt.links.new(col.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.6
        bp = bump(nt, wave.outputs['Fac'], 0.25, 0.02)
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    else:  # dark slate
        nz = noise_tex(nt, 6.0, 10, 0.65, 0.2, tc.outputs['Object'])
        col = ramp(nt, [(0.0, '#141110'), (0.5, '#24201d'), (1.0, '#383230')])
        nt.links.new(nz.outputs['Fac'], col.inputs['Fac'])
        nt.links.new(col.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.75
        bp = bump(nt, nz.outputs['Fac'], 0.3, 0.02)
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


# ------------------------------------------------------------------- pizza
RECIPES = {
    'vegx': [('olive', 3), ('onion', 3), ('capsicum', 3), ('mushroom', 2), ('corn', 3), ('tomato', 2), ('jalapeno', 2)],
    'farm': [('onion', 3), ('capsicum', 3), ('tomato', 3), ('mushroom', 3)],
    'peppy': [('paneer', 5), ('capsicum', 3), ('paprika', 3)],
    'marg': [],
}


class Pizza:
    def __init__(self, recipe='vegx', seed=7, wedge=None, extra_cheese=False):
        self.rng = random.Random(seed)
        self.seed = seed
        self.recipe = recipe
        self.wedge = wedge            # (t0, t1): angular range removed from the pie (the slice)
        s = seed * 0.37
        self.s = s
        self.base = 0.035
        # blisters on the cheese
        r = self.rng
        self.bubbles = []
        for _ in range(48 if extra_cheese else 36):
            rr = math.sqrt(r.random()) * 0.84
            tt = r.random() * TAU
            self.bubbles.append((rr * math.cos(tt), rr * math.sin(tt), r.uniform(0.035, 0.085), r.uniform(0.012, 0.03)))
        self.mats = {}
        self._ts = np.linspace(0, TAU, 720, endpoint=False)
        self._ce = np.array([self.cheese_edge(float(t)) for t in self._ts])

    # outline, rim and cheese edge as functions of angle (scalar or array)
    def R(self, t):
        return 1.0 + 0.016 * ang_noise(t, 1.3, self.s) + 0.006 * ang_noise(t, 5.0, self.s + 1)

    def rim(self, t):
        rc = self.R(t) - 0.078 - 0.008 * ang_noise(t, 2.2, self.s + 2)
        w = 0.082 + 0.012 * ang_noise(t, 3.1, self.s + 3)
        h = 0.088 + 0.018 * ang_noise(t, 2.7, self.s + 4) + 0.01 * ang_noise(t, 9.0, self.s + 5)
        return rc, w, h

    CUTS = [math.pi / 8 + k * math.pi / 4 for k in range(4)]   # 8 slices; a slice spans 3pi/2 +- pi/8

    def cut_depth(self, X, Y, depth, width):
        g = np.zeros_like(np.asarray(X, dtype=np.float64))
        for a in self.CUTS:
            d = np.abs(X * math.sin(a) - Y * math.cos(a))
            g = np.maximum(g, np.exp(-(d / width) ** 2))
        return depth * g

    def cheese_edge(self, t):
        rc, w, _ = self.rim(t)
        return rc - w * 0.62 + 0.018 * ang_noise(t, 4.3, self.s + 6) + 0.01 * ang_noise(t, 11.0, self.s + 7)

    def _angle_cache(self, T):
        key = (T.shape[1], float(T[0, 1] - T[0, 0]) if T.shape[1] > 1 else 0.0)
        if getattr(self, '_ak', None) != key:
            ts = T[0]
            R = self.R(ts)
            rc, w, h = self.rim(ts)
            self._ac = dict(R=R, rc=rc, w=w, h=h, ce=self.cheese_edge(ts))
            self._ak = key
        return self._ac

    def crust_h(self, Rr, T):
        if Rr.size == 1:
            t = float(T.ravel()[0])
            A = dict(R=np.array([self.R(t)]), rc=np.array([self.rim(t)[0]]), w=np.array([self.rim(t)[1]]), h=np.array([self.rim(t)[2]]))
        else:
            A = self._angle_cache(T)
        R, rc, w, h = A['R'], A['rc'], A['w'], A['h']
        b = self.base
        inner = rc - w
        u_in = np.clip((rc - Rr) / w, 0, 1)
        z_in = b + (h - b) * np.sqrt(np.clip(1 - u_in ** 2, 0, 1))
        u_out = np.clip((Rr - rc) / np.maximum(R - rc, 1e-6), 0, 1)
        z_out = h * np.sqrt(np.clip(1 - u_out ** 2.2, 0, 1))
        z = np.where(Rr <= inner, b, np.where(Rr <= rc, z_in, np.where(Rr < R, z_out, 0.0)))
        X, Y = Rr * np.cos(T), Rr * np.sin(T)
        puff = 0.014 * vnoise(X * 6 + 3, Y * 6 + 7, self.seed, 3) + 0.004 * vnoise(X * 30, Y * 30, self.seed + 5, 2)
        z = z + np.where((Rr > inner) & (Rr < R), puff * np.clip((Rr - inner) / w, 0, 1), 0.0)
        z = z - np.where(Rr > inner - 0.02, self.cut_depth(X, Y, 0.012, 0.008), 0.0)
        return z

    def melt(self, X, Y):
        """Melted cheese as two scales of cells that puff into domes.
        Returns (big domes 0..1, small domes 0..1, cell amplitude 0..1, crease 0..1 with
        0 on the creases between bubbles)."""
        s = self.seed
        X = np.asarray(X, dtype=np.float64)
        Y = np.asarray(Y, dtype=np.float64)
        wx = X + 0.055 * vnoise(X * 4.5 + 11, Y * 4.5, s + 31, 3)
        wy = Y + 0.055 * vnoise(X * 4.5, Y * 4.5 + 7, s + 32, 3)
        F1, F2, C = worley(wx * 7.0, wy * 7.0, s + 40)
        e = np.clip((F2 - F1) / 0.42, 0, 1)
        dome = 1 - (1 - e) ** 2.2
        amp = np.clip((C - 0.42) / 0.58, 0, 1) ** 1.2
        f1, f2, c2 = worley(wx * 17.0 + 5, wy * 17.0 + 3, s + 41)
        e2 = np.clip((f2 - f1) / 0.45, 0, 1)
        small = np.clip((c2 - 0.35) / 0.65, 0, 1) * (1 - (1 - e2) ** 2)
        return dome * amp, small, amp, e

    def _edge(self, X, Y):
        r = np.hypot(X, Y)
        t = np.mod(np.arctan2(Y, X), TAU)
        ce = np.interp(t.ravel(), self._ts, self._ce, period=TAU).reshape(t.shape)
        return ce - r

    def cheese_h(self, X, Y):
        X = np.asarray(X, dtype=np.float64)
        Y = np.asarray(Y, dtype=np.float64)
        e = self._edge(X, Y)
        top = self.base + 0.006
        th = 0.022 * (1 - np.exp(-np.maximum(e, 0) / 0.02))
        big, small, amp, crease = self.melt(X, Y)
        z = top + th + 0.0035 * vnoise(X * 4, Y * 4, self.seed + 9, 3)
        z = z + (0.015 * big + 0.005 * small + 0.004 * vnoise(X * 9 + 3, Y * 9, self.seed + 77, 3)) * np.clip(e / 0.04, 0, 1)
        for mx, my, mr, mh in getattr(self, 'mounds', []):
            d = np.hypot(X - mx, Y - my)
            z = np.maximum(z, np.where(d < mr, mh * np.clip(1 - (d / mr) ** 2, 0, 1) ** 1.3 + top, z))
        bub = np.zeros_like(z)
        for bx, by, br, bh in self.bubbles:
            d = np.hypot(X - bx, Y - by)
            bub += np.where(d < br, bh * np.clip(1 - (d / br) ** 2, 0, 1) ** 1.6, 0.0)
        z = z + bub * np.clip(e / 0.03, 0, 1)
        z = z - self.cut_depth(X, Y, 0.016, 0.007) * np.clip(e / 0.02, 0, 1)
        return np.where(e < 0, top - 0.012 - np.minimum(0.02, -e), z)

    def brown_at(self, X, Y):
        X = np.asarray(X, dtype=np.float64)
        Y = np.asarray(Y, dtype=np.float64)
        v = np.zeros_like(X)
        for bx, by, br, bh in self.bubbles:
            d = np.hypot(X - bx, Y - by)
            v = np.maximum(v, np.where(d < br * 0.8, (bh / 0.026) * np.clip(1 - d / (br * 0.8), 0, 1) ** 1.4, 0.0))
        big, small, amp, crease = self.melt(X, Y)
        gate = np.clip((vnoise(X * 2.6 + 40, Y * 2.6, self.seed + 50, 2) + 0.7) / 0.5, 0, 1)
        v = np.maximum(v, 1.2 * amp ** 1.0 * crease ** 1.6 * gate)
        v = np.maximum(v, 0.6 * np.exp(-np.maximum(0, self._edge(X, Y)) / 0.03))
        v = v + 0.12 * np.clip(vnoise(X * 14, Y * 14, self.seed + 21, 3), 0, 1)
        return np.clip(v, 0, 1)

    def oil_at(self, X, Y):
        X = np.asarray(X, dtype=np.float64)
        Y = np.asarray(Y, dtype=np.float64)
        big, small, amp, crease = self.melt(X, Y)
        pool = np.clip((vnoise(X * 2.2 + 70, Y * 2.2, self.seed + 60, 2) - 0.25) / 0.3, 0, 1)
        oil = 0.3 * (1 - crease) ** 5 * (0.25 + 0.75 * amp) + 0.5 * pool ** 1.5
        return np.clip(oil, 0, 1)

    def build(self, part='pie'):
        """part: 'pie' (minus the wedge, if any) or 'slice' (only the wedge)."""
        keep = None
        if self.wedge:
            t0, t1 = self.wedge
            inside = lambda t: (t0 <= t <= t1) if t0 < t1 else (t >= t0 or t <= t1)
            keep = inside if part == 'slice' else (lambda t: not inside(t))
        objs = []
        n_t = 900
        crust_rings = ring_radii(1.03, 70, dense_from=0.78, dense_n=120)
        crust = polar_mesh(f'crust_{part}', crust_rings, n_t,
                           lambda Rr, T: self.crust_h(Rr, T),
                           keep=keep,
                           attrs={'toast': lambda Rr, T, Z: self._toast(Rr, T, Z)})
        crust.data.materials.append(self.mat('crust'))
        objs.append(crust)
        def sauce_h(Rr, T):
            ts = T[0] if T.ndim == 2 else T
            rc, w, _ = self.rim(ts)
            lim = rc - w * 0.35
            X, Y = Rr * np.cos(T), Rr * np.sin(T)
            z = self.base + 0.004 + 0.0015 * vnoise(X * 9, Y * 9, self.seed + 2, 3)
            return np.where(Rr < lim, z, self.base - 0.01)
        sauce = polar_mesh(f'sauce_{part}', ring_radii(0.95, 120), n_t, sauce_h, keep=keep)
        sauce.data.materials.append(self.mat('sauce'))
        objs.append(sauce)
        self.plan()                                 # mounds must exist before the cheese
        tops = self.toppings(keep)
        cheese = polar_mesh(f'cheese_{part}', ring_radii(0.95, 300), 1400,
                            lambda Rr, T: self.cheese_h(Rr * np.cos(T), Rr * np.sin(T)),
                            keep=keep,
                            attrs={'brown': lambda Rr, T, Z: self.brown_at(Rr * np.cos(T), Rr * np.sin(T)),
                                   'oil': lambda Rr, T, Z: self.oil_at(Rr * np.cos(T), Rr * np.sin(T))})
        cheese.data.materials.append(self.mat('cheese'))
        objs.append(cheese)
        objs += tops
        return objs

    def _toast(self, Rr, T, Z):
        A = self._angle_cache(T) if Rr.size > 1 else dict(zip(('rc', 'w', 'h'), [np.array([v]) for v in self.rim(float(T.ravel()[0]))]))
        rc, w, h = A['rc'], A['w'], A['h']
        k = np.clip((Z - self.base) / np.maximum(1e-6, h - self.base), 0, 1)
        X, Y = Rr * np.cos(T), Rr * np.sin(T)
        v = 0.22 + 0.62 * k ** 1.25 + 0.35 * np.clip(vnoise(X * 11, Y * 11, self.seed + 4, 3), 0, 1) - 0.12 * np.clip(-vnoise(X * 23, Y * 23, self.seed + 8, 2), 0, 1)
        v = np.where(Rr > rc, v * 0.92, v)
        return np.clip(np.where(Rr < rc - w, 0.08, v), 0, 1)

    def mat(self, k):
        if k in self.mats:
            return self.mats[k]
        f = {
            'cheese': mat_cheese, 'crust': mat_crust, 'sauce': mat_sauce,
            'capsicum': lambda: mat_simple('capsicum', '#a7bb62', 0.34, 0.45, (0.5, 1, 0.3), 0.6, skin='#1d4a13', skin_rough=0.1, char=0.85, bump_s=0.3),
            'paprika': lambda: mat_simple('paprika', '#b8321f', 0.3, 0.45, (1, 0.3, 0.2), 0.6, skin='#7d1208', skin_rough=0.1, char=0.8, bump_s=0.25),
            'onion': lambda: mat_simple('onion', '#efe2e8', 0.16, 0.85, (1, 0.8, 0.9), 0.55, skin='#93306f', transmission=0.3, skin_rough=0.14, char=0.45),
            'olive': lambda: mat_simple('olive', '#1e1615', 0.42, 0.15, (1, 0.5, 0.5), 0.35, skin='#0a0708', skin_rough=0.12, spec=0.5, bump_s=0.15),
            'corn': lambda: mat_simple('corn', '#f6c12c', 0.14, 0.65, (1, 0.75, 0.2), 0.6, char=0.35),
            'tomato': lambda: mat_simple('tomato', '#b8301c', 0.2, 0.6, (1, 0.25, 0.15), 0.55, skin='#8f170c', skin_rough=0.1, char=0.7, bump_s=0.25),
            'mushroom': lambda: mat_simple('mushroom', '#cbb08a', 0.4, 0.35, (1, 0.85, 0.65), 0.35, skin='#6a4729', skin_rough=0.45, char=0.7, bump_s=0.4),
            'paneer': lambda: mat_simple('paneer', '#f4ecdc', 0.5, 0.7, (1, 0.95, 0.85), 0.15, skin='#c97a30', char=0.5),
            'jalapeno': mat_jalapeno,
            'herb': lambda: mat_simple('herb', '#2f3b14', 0.6),
        }[k]
        self.mats[k] = f()
        return self.mats[k]

    def topping_meshes(self):
        if hasattr(self, '_tm'):
            return self._tm
        r = self.rng
        tm = {
            'capsicum': [pepper_piece(f'capd{i}', r.uniform(0.06, 0.095), r.uniform(0.045, 0.075), 0.019, r, bend=r.uniform(0.3, 0.6)) for i in range(6)]
                        + [jitter_mesh(sweep_arc(f'caps{i}', r.uniform(0.2, 0.3), 0.036, 0.024, r.uniform(0.45, 0.7)), r, 0.006) for i in range(2)],
            'paprika': [jitter_mesh(sweep_arc(f'pap{i}', r.uniform(0.12, 0.2), r.uniform(0.022, 0.03), 0.013, r.uniform(0.5, 0.8), bevel=0.25), r, 0.005) for i in range(4)],
            'onion': [jitter_mesh(sweep_arc(f'onis{i}', r.uniform(0.07, 0.16), r.uniform(0.018, 0.028), 0.009, r.uniform(0.7, 1.4), bevel=0.15), r, 0.004) for i in range(6)]
                     + [chunk_mesh(f'oni{i}', r.uniform(0.07, 0.1), r.uniform(0.03, 0.04), 0.01, r, round_=0.45) for i in range(2)],
            'olive': [ring_mesh(f'olive{i}', r.uniform(0.06, 0.07), r.uniform(0.024, 0.03), 0.022, r) for i in range(4)],
            'corn': [kernel_mesh(f'corn{i}', r) for i in range(5)],
            'tomato': [chunk_mesh(f'tom{i}', r.uniform(0.07, 0.095), r.uniform(0.06, 0.08), 0.022, r, 'top', round_=0.45) for i in range(4)],
            'mushroom': [jitter_mesh(mushroom_mesh(f'mush{i}', r.uniform(0.16, 0.21)), r, 0.018) for i in range(4)],
            'paneer': [jitter_mesh(rounded_box(f'pan{i}', 0.11, 0.1, 0.075, 0.3), r, 0.009) for i in range(4)],
            'jalapeno': [ring_mesh(f'jal{i}', r.uniform(0.062, 0.075), r.uniform(0.006, 0.012), 0.016, r, ellip=0.07) for i in range(3)],
        }
        # paneer: toasted top edges ('skin' by height)
        for me in tm['paneer']:
            a = me.attributes.new('skin', 'FLOAT', 'POINT')
            zs = [v.co.z for v in me.vertices]
            zmax = max(zs)
            a.data.foreach_set('value', np.asarray([max(0.0, (z / zmax)) ** 3 * 0.85 for z in zs], dtype=np.float32))
        self._tm = tm
        return tm

    def plan(self):
        """Decide every topping once (kind, mesh, pose) and the cheese mounds around them."""
        if hasattr(self, '_plan'):
            return self._plan
        recipe = RECIPES[self.recipe]
        r = self.rng
        tm = self.topping_meshes()
        self.mounds = []
        plan = []
        if recipe:
            pts = []
            min_d = 0.102
            tries = 0
            while tries < 9000:
                tries += 1
                rr = math.sqrt(r.random()) * 0.78
                tt = r.random() * TAU
                x, y = rr * math.cos(tt), rr * math.sin(tt)
                if all((x - a) ** 2 + (y - b) ** 2 > min_d * min_d for a, b in pts):
                    pts.append((x, y))
            total = sum(w for _, w in recipe)
            for (x, y) in pts:
                k = r.random() * total
                kind = recipe[-1][0]
                for name, w in recipe:
                    k -= w
                    if k <= 0:
                        kind = name
                        break
                reps = 4 if kind == 'corn' else 1
                for j in range(reps):
                    ox, oy = (r.uniform(-0.05, 0.05), r.uniform(-0.05, 0.05)) if reps > 1 else (0, 0)
                    me = r.choice(tm[kind])
                    px, py = x + ox, y + oy
                    z = float(self.cheese_h(np.array([px]), np.array([py]))[0])
                    sink = {'olive': 0.45, 'paneer': 0.35, 'corn': 0.45, 'tomato': 0.45, 'jalapeno': 0.45, 'mushroom': 0.45,
                            'capsicum': 0.5, 'paprika': 0.5, 'onion': 0.55}.get(kind, 0.45)
                    zs = [v.co.z for v in me.vertices]
                    zmin, zmax = min(zs), max(zs)
                    height = zmax - zmin
                    foot = {'capsicum': 0.075, 'paprika': 0.05, 'onion': 0.07, 'olive': 0.075, 'corn': 0.035,
                            'tomato': 0.07, 'mushroom': 0.11, 'paneer': 0.085, 'jalapeno': 0.085}.get(kind, 0.06)
                    # a third of the pepper pieces land skin-down, showing the paler flesh
                    flip = kind in ('capsicum', 'paprika') and r.random() < 0.3
                    tip = 0.6 if kind == 'corn' else 0.12          # kernels land every which way
                    rot = (r.uniform(-tip, tip) + (math.pi if flip else 0), r.uniform(-tip, tip), r.uniform(0, TAU))
                    sc = r.uniform(0.85, 1.15)
                    scale = (sc * r.uniform(0.85, 1.15), sc * r.uniform(0.85, 1.15), sc * r.uniform(0.8, 1.1))
                    bottom = -zmax if flip else zmin
                    plan.append((kind, me, px, py, z - height * sink - bottom * scale[2], rot, scale))
                    self.mounds.append((px, py, foot * 1.25, (z - self.base - 0.006) + height * r.uniform(0.3, 0.5)))
        herbs = []
        for _ in range(320):
            rr = math.sqrt(r.random()) * 0.82
            tt = r.random() * TAU
            herbs.append((rr * math.cos(tt), rr * math.sin(tt), (r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), r.uniform(0, TAU)),
                          r.uniform(0.5, 1.4), r.uniform(0.4, 1.0)))
        self._plan = (plan, herbs)
        return self._plan

    def toppings(self, keep):
        plan, _ = self.plan()
        objs = []
        for kind, me, px, py, z, rot, scale in plan:
            if keep and not keep(math.atan2(py, px) % TAU):
                continue
            ob = bpy.data.objects.new(kind, me)
            bpy.context.collection.objects.link(ob)
            ob.location = (px, py, z)
            ob.rotation_euler = Euler(rot)
            ob.scale = scale
            if not me.materials:
                me.materials.append(self.mat(kind))
            objs.append(ob)
        return objs + self.herbs(keep)

    def herbs(self, keep):
        _, herbs = self.plan()
        if not hasattr(self, '_flake'):
            bpy.ops.mesh.primitive_plane_add(size=0.014)
            self._flake = bpy.context.object.data
            self._flake.name = 'flake'
            bpy.data.objects.remove(bpy.context.object)
            self._flake.materials.append(self.mat('herb'))
        objs = []
        for x, y, rot, s1, s2 in herbs:
            if keep and not keep(math.atan2(y, x) % TAU):
                continue
            ob = bpy.data.objects.new('herb', self._flake)
            bpy.context.collection.objects.link(ob)
            ob.location = (x, y, float(self.cheese_h(np.array([x]), np.array([y]))[0]) + 0.001)
            ob.rotation_euler = Euler(rot)
            ob.scale = (s1, s1 * s2, 1)
            objs.append(ob)
        return objs


# ------------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 8
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 4
    sc.cycles.volume_bounces = 1
    sc.view_settings.view_transform = 'Khronos PBR Neutral'
    sc.view_settings.look = 'Medium High Contrast'
    sc.view_settings.exposure = -0.6
    sc.view_settings.gamma = 1.0
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    return sc


def area_light(name, loc, target, energy, size, color='#ffffff', size_y=None):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.size = size
    if size_y:
        ld.shape = 'RECTANGLE'
        ld.size_y = size_y
    ld.color = lin(color)[:3]
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def camera(loc, target, lens=50, dof=None, fstop=2.8, ortho=None):
    cd = bpy.data.cameras.new('cam')
    cd.lens = lens
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    if dof:
        cd.dof.use_dof = True
        cd.dof.focus_distance = dof
        cd.dof.aperture_fstop = fstop * METRES_PER_UNIT   # f-number as if the pizza were real size
    ob = bpy.data.objects.new('cam', cd)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = ob
    return ob


def world(color='#0b0806', strength=1.0):
    w = bpy.data.worlds.new('w')
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = lin(color)
    w.node_tree.nodes['Background'].inputs[1].default_value = strength


HDRI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hdri')


def world_hdri(name='lebombo_1k.hdr', strength=0.4, rot=0.0, bg='#0a0705', bg_strength=1.0):
    """Light and reflections from a real room (a CC0 Poly Haven HDRI), while the camera
    itself sees a dark, moody background."""
    w = bpy.data.worlds.new('w')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_WORLD':
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, rot)
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(os.path.join(HDRI_DIR, name), check_existing=True)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    b1 = nt.nodes.new('ShaderNodeBackground')
    b1.inputs['Strength'].default_value = strength
    nt.links.new(env.outputs['Color'], b1.inputs['Color'])
    b2 = nt.nodes.new('ShaderNodeBackground')
    b2.inputs['Color'].default_value = lin(bg)
    b2.inputs['Strength'].default_value = bg_strength
    lp = nt.nodes.new('ShaderNodeLightPath')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
    nt.links.new(b1.outputs[0], mix.inputs[1])
    nt.links.new(b2.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return w


def board(kind='wood', size=6.0, z=-0.002):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    ob = bpy.context.object
    ob.data.materials.append(mat_board(kind))
    return ob


def serving_board(radius=1.17, thick=0.07):
    """A round wooden pizza board; its top is at z = 0, where the pizza sits."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=radius, depth=thick, location=(0, 0, -thick / 2 - 0.002))
    ob = bpy.context.object
    mod = ob.modifiers.new('bev', 'BEVEL')
    mod.width = 0.014
    mod.segments = 4
    bpy.ops.object.modifier_apply(modifier='bev')
    ob.data.shade_smooth()
    ob.data.materials.append(mat_board('oak'))
    return ob


def shadow_catcher(size=6.0, z=-0.002):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    ob = bpy.context.object
    ob.is_shadow_catcher = True
    return ob


def lights_food(top=False):
    """Softboxes the way a food photographer places them: a big source behind and to the
    side so the cheese throws highlights at the lens, a warm rim, a weak front fill."""
    if top:
        area_light('key', (-3.2, 2.6, 3.4), (0, 0, 0), 520, 2.4, '#fff0da')
        area_light('fill', (3.4, -1.6, 2.6), (0, 0, 0), 60, 3.0, '#ffe6cc')
        area_light('rim', (2.6, 3.2, 1.0), (0, 0, 0.05), 300, 1.2, '#ffc98f')
        area_light('gloss', (-1.6, 1.2, 7.0), (0, 0, 0), 180, 1.6, '#fff6ea', size_y=0.7)
    else:
        area_light('key', (-0.9, 3.0, 1.85), (0, 0, 0), 620, 2.4, '#fff1de')
        area_light('rim', (2.5, 2.7, 0.85), (0, 0.2, 0.05), 380, 1.2, '#ffc78a')
        area_light('top', (0.3, 0.5, 4.0), (0, 0, 0.05), 110, 3.0, '#fff4e6')
        area_light('fill', (1.6, -3.2, 2.2), (0, -0.2, 0.05), 70, 3.2, '#ffe7cf')


def render(path, w, h, samples=96, transparent=False, border=None):
    sc = bpy.context.scene
    if border:
        sc.render.use_border = True
        sc.render.use_crop_to_border = True
        sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = border
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.render.film_transparent = transparent
    sc.render.filepath = path
    t0 = time.time()
    if path.endswith('.exr'):
        sc.render.image_settings.file_format = 'OPEN_EXR'
        sc.render.image_settings.color_depth = '16'
        sc.render.image_settings.exr_codec = 'ZIP'
    bpy.ops.render.render(write_still=True)
    print(f'render {w}x{h} {samples}spp: {time.time() - t0:.1f}s', flush=True)


# ------------------------------------------------------------------- shots
def aim(elev_deg, dist, target, az_deg=0.0):
    """Camera position at an elevation and distance from a target, looking from -y."""
    e, a = math.radians(elev_deg), math.radians(az_deg)
    tx, ty, tz = target
    return (tx + dist * math.cos(e) * math.sin(a), ty - dist * math.cos(e) * math.cos(a), tz + dist * math.sin(e))


def shot_top(out, recipe='vegx', seed=7, w=1600, h=1600, samples=96, bg='board', half=1.25):
    """Straight down on the pizza on its board. half: half-width of the frame in pizza radii."""
    reset()
    sc = bpy.context.scene
    sc.view_settings.exposure = -1.0
    world_hdri('lebombo_1k.hdr', 0.3, rot=1.2)
    pz = Pizza(recipe, seed)
    pz.build()
    if bg == 'transparent':
        shadow_catcher()
    else:
        serving_board()
        board('slate', size=12.0, z=-0.074)
    lights_food(top=True)
    cam = camera((0, 0, 9.0), (0, 0.0001, 0), lens=60)
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.sensor_width = 36
    cam.data.lens = 36 * 9.0 / (2 * float(half))
    render(out, int(w), int(h), int(samples), transparent=(bg == 'transparent'))


def shot_hero(out, recipe='vegx', seed=7, w=1080, h=1920, samples=128, fstop=5.6, elev=32, dist=3.0,
              lens=60, ty=-0.15, focus=-0.45, exposure=-0.6, az=0, hdri='lebombo_1k.hdr', hdri_rot=2.6, crop=None):
    """Low three-quarter angle, shallow depth of field, backlit: the appetite shot."""
    reset()
    bpy.context.scene.view_settings.exposure = float(exposure)
    world_hdri(hdri, 0.35, rot=float(hdri_rot))
    Pizza(recipe, int(seed)).build()
    serving_board()
    board('slate', size=60.0, z=-0.074)
    lights_food(top=False)
    target = (0, float(ty), 0.05)
    loc = aim(float(elev), float(dist), target, float(az))
    fpt = Vector((0, float(focus), 0.06))
    cam = camera(loc, target, lens=float(lens), dof=(fpt - Vector(loc)).length, fstop=float(fstop))
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.sensor_width = 36
    border = tuple(float(v) for v in crop.split(',')) if crop else None
    render(out, int(w), int(h), int(samples), border=border)


def _arg(v):
    for f in (int, float):
        try:
            return f(v)
        except ValueError:
            pass
    return v


if __name__ == '__main__':
    shot = sys.argv[1] if len(sys.argv) > 1 else 'top'
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.abspath(f'{shot}.png')
    kw = {k: _arg(v) for k, v in (a.split('=', 1) for a in sys.argv[3:])}
    {'top': shot_top, 'hero': shot_hero}[shot](out, **kw)
