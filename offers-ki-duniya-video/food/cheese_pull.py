"""The cheese pull: a slice lifted out of the pie, mozzarella stretching between them.

python3 food/cheese_pull.py <out_dir> [frames=40] [w=720] [h=1280] [samples=32] [first=0] [last=39] [only=0,20,39]

Writes linear EXRs (pull_000.exr ...); food/grade.py turns them into graded PNGs.
Each frame is rendered on its own: the slice moves, and every strand is rebuilt from
its two anchors, thinning as it stretches (its volume stays constant) and sagging under
its own weight. The slice is one of the eight the pie is pre-cut into, so its edges
follow the cut grooves.
"""
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pizza_scene as P  # noqa: E402

TC = 0.5 * math.pi            # the slice is at the back (+y): lifted by its crust, its tip droops towards the lens
HALF = math.pi / 8            # one of eight slices
PIVOT_R = 0.96                # the hand holds the slice at its crust


def cut_wall(pz, t, name, mats):
    """The cross-section of the pie along angle t: bread, a line of sauce, cheese on top."""
    rs = np.linspace(0.0, 1.0, 160)
    verts, faces, mat_idx = [], [], []
    rows = 4
    for i, r in enumerate(rs):
        R = pz.R(t)
        rr = min(r * R, R - 1e-4)
        x, y = rr * math.cos(t), rr * math.sin(t)
        rc, w, h = pz.rim(t)
        crust_top = float(pz.crust_h(np.array([[rr]]), np.array([[t]]))[0, 0])
        cheese_top = float(pz.cheese_h(np.array([x]), np.array([y]))[0])
        interior = rr < rc - w * 0.7
        top = max(crust_top, cheese_top) if interior else crust_top
        zs = sorted([0.001, pz.base - 0.002, pz.base + 0.006, top] if interior else [0.001, top * 0.5, top * 0.8, top])
        for z in zs:
            verts.append((x, y, z))
        if i:
            for k in range(rows - 1):
                a = (i - 1) * rows + k
                b = i * rows + k
                faces.append((a, b, b + 1, a + 1))
                mat_idx.append(0 if (k == 0 or not interior) else (1 if k == 1 else 2))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set('material_index', np.asarray(mat_idx, dtype=np.int32))
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def mat_strand():
    """Stretched mozzarella: thin enough that the backlight glows through it."""
    m, nt, b = P.node_mat('strand')
    b.inputs['Base Color'].default_value = P.lin('#f1cf7a')
    b.inputs['Subsurface Weight'].default_value = 0.85
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.6, 0.25)
    b.inputs['Subsurface Scale'].default_value = 0.02
    b.inputs['Roughness'].default_value = 0.22
    b.inputs['Coat Weight'].default_value = 0.45
    b.inputs['Coat Roughness'].default_value = 0.05
    b.inputs['Specular IOR Level'].default_value = 0.6
    return m


def strand_obj(name, mat, n=18):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(n - 1)
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    return ob


def ease(u):
    return u * u * (3 - 2 * u)


def bokeh(rng, n=11):
    """Warm out-of-focus lights far behind, like a restaurant at night."""
    for i in range(n):
        loc = (rng.uniform(-3.5, 3.0), rng.uniform(3.5, 7.0), rng.uniform(0.6, 3.2))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.05, 0.11), location=loc)
        em = bpy.data.materials.new(f'bokeh{i}')
        em.use_nodes = True
        nt = em.node_tree
        for nd in list(nt.nodes):
            if nd.type != 'OUTPUT_MATERIAL':
                nt.nodes.remove(nd)
        e = nt.nodes.new('ShaderNodeEmission')
        e.inputs['Color'].default_value = P.lin(rng.choice(['#ffb35c', '#ffd28a', '#ff9a3c', '#ffe2b0']))
        e.inputs['Strength'].default_value = rng.uniform(5, 12)
        nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs[0])
        bpy.context.object.data.materials.append(em)
        bpy.context.object.visible_diffuse = False
        bpy.context.object.visible_glossy = False


def main():
    out = sys.argv[1]
    kw = dict(a.split('=') for a in sys.argv[2:])
    frames = int(kw.get('frames', 40))
    W, H = int(kw.get('w', 720)), int(kw.get('h', 1280))
    samples = int(kw.get('samples', 32))
    first, last = int(kw.get('first', 0)), int(kw.get('last', frames - 1))
    todo = [int(v) for v in kw['only'].split(',')] if 'only' in kw else range(first, last + 1)
    os.makedirs(out, exist_ok=True)

    sc = P.reset()
    sc.render.use_persistent_data = True
    sc.view_settings.exposure = 0.0
    P.world_hdri('lebombo_1k.hdr', 0.3, rot=2.6, bg='#070504')
    pz = P.Pizza('vegx', 7, wedge=(TC - HALF, TC + HALF))
    pie = pz.build('pie')
    sl = pz.build('slice')
    bread = P.mat_simple('bread_cut', '#efd6a6', 0.8, 0.3, (1, 0.8, 0.5), 0.0)
    wall_mats = [bread, pz.mat('sauce'), pz.mat('cheese')]
    pie += [cut_wall(pz, TC - HALF, 'wall_a', wall_mats), cut_wall(pz, TC + HALF, 'wall_b', wall_mats)]
    sl += [cut_wall(pz, TC - HALF, 'swall_a', wall_mats), cut_wall(pz, TC + HALF, 'swall_b', wall_mats)]
    P.serving_board()
    P.board('slate', size=60.0, z=-0.074)

    # the slice hangs off a pivot at its crust end
    p0 = Vector((math.cos(TC) * PIVOT_R, math.sin(TC) * PIVOT_R, 0.06))
    pivot = bpy.data.objects.new('pivot', None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = p0
    bpy.context.view_layer.update()
    for ob in sl:
        ob.parent = pivot
        ob.matrix_parent_inverse = pivot.matrix_world.inverted()

    # strands: (pie point, slice point, radius) pairs along both cuts and around the tip
    rng = random.Random(11)
    anchors = []
    for side in (-1, 1):
        t = TC + side * HALF
        for k in range(10):
            r = rng.uniform(0.06, 0.74)
            x, y = r * math.cos(t), r * math.sin(t)
            z = float(pz.cheese_h(np.array([x]), np.array([y]))[0]) - 0.003
            # pie side sits just outside the slice's edge, slice side just inside
            n_out = Vector((math.cos(t + side * math.pi / 2), math.sin(t + side * math.pi / 2), 0)) * 0.008
            anchors.append((Vector((x, y, z)) + n_out, Vector((x, y, z)) - n_out, rng.uniform(0.006, 0.019)))
    for k in range(14):
        r = rng.uniform(0.0, 0.2)
        t = TC + rng.uniform(-HALF, HALF) * 0.7
        x, y = r * math.cos(t), r * math.sin(t)
        z = float(pz.cheese_h(np.array([x]), np.array([y]))[0]) - 0.003
        back = Vector((-math.cos(TC), -math.sin(TC), 0)) * rng.uniform(0.02, 0.08)
        anchors.append((Vector((x, y, z)) + back, Vector((x, y, z)), rng.uniform(0.008, 0.026)))
    smat = mat_strand()
    strands = [strand_obj(f'strand{i}', smat) for i in range(len(anchors))]

    # light: the key comes from behind the slice so the strands glow
    P.area_light('back', (0.5, 3.6, 1.6), (0, 0.3, 0.4), 1100, 1.8, '#ffd29a')
    P.area_light('key', (-2.3, -1.5, 2.5), (0, 0.4, 0.5), 420, 2.4, '#fff0dc')
    P.area_light('rim', (2.5, 2.0, 1.0), (0, 0.4, 0.4), 320, 1.2, '#ffc27a')
    P.area_light('fill', (1.4, -3.2, 1.0), (0, 0.0, 0.3), 70, 3.0, '#ffe5c8')
    bokeh(random.Random(5))

    target = (0.0, 0.32, 0.5)
    loc = P.aim(20, 2.15, target, 14)
    focus = Vector((0.0, 0.12, 0.3))
    cam = P.camera(loc, target, lens=56, dof=(focus - Vector(loc)).length, fstop=5.6)
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.sensor_width = 36

    axis = Vector((math.cos(TC + math.pi / 2), math.sin(TC + math.pi / 2), 0))
    out_dir = Vector((math.cos(TC), math.sin(TC), 0))
    for f in todo:
        u = ease(f / max(1, frames - 1))
        pivot.location = p0 + out_dir * (0.12 * u) + Vector((0, 0, 0.86 * u))
        pivot.rotation_mode = 'AXIS_ANGLE'
        pivot.rotation_axis_angle = (math.radians(-40) * u, axis.x, axis.y, axis.z)
        bpy.context.view_layer.update()
        M = pivot.matrix_world @ Matrix.Translation(-p0)
        for (a, b, r0), ob in zip(anchors, strands):
            B = M @ b
            L = (B - a).length
            L0 = 0.014
            thin = max(0.16, math.sqrt(L0 / max(L, L0)))
            sag = 0.24 * L * (0.4 + 0.6 * u)
            pts = ob.data.splines[0].points
            n = len(pts)
            for i, pt in enumerate(pts):
                s = i / (n - 1)
                p = a.lerp(B, s)
                p.z -= sag * 4 * s * (1 - s) * (0.3 if L < 0.05 else 1.0)
                wob = 0.01 * math.sin(s * math.pi * 2 + r0 * 900) * u
                p.x += wob
                pt.co = (p.x, p.y, p.z, 1.0)
                end = abs(2 * s - 1) ** 1.6
                pt.radius = r0 * (thin * (0.55 + 0.45 * end) + 0.6 * end * (1 - thin))
            ob.hide_render = L < 0.004
        P.render(os.path.join(out, f'pull_{f:03d}.exr'), W, H, samples)
        print('frame', f, 'done', flush=True)


if __name__ == '__main__':
    main()
