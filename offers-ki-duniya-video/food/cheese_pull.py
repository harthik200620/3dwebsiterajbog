"""The cheese pull: a slice lifted out of the pie, mozzarella stretching between them.

python3 food/cheese_pull.py <out_dir> [frames=60] [w=864] [h=1536] [samples=28] [first=0] [last=59]
                            [only=0,20,39] [matte=1]

Writes linear EXRs (pull_000.exr ...) for food/grade.py and, with matte=1, an alpha
matte of the slice and its strands (matte_000.png) so type can sit behind the slice.

Each frame is rendered on its own:
- the slice is lifted by its crust and bends under its own weight, more towards the tip,
  the way a hot slice flops (its meshes are bent vertex by vertex, its toppings ride along);
- every strand is rebuilt from its two anchors: thick ropes and thin threads, some flat
  like ribbons, thinning as they stretch (volume stays constant), sagging by their weight,
  and snapping into two hanging tails once stretched past their limit.
The slice is one of the eight the pie is pre-cut into, so its edges follow the cut grooves.
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
SLICE_LEN = 0.96
N_PTS = 24                    # points per strand


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
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = P.noise_tex(nt, 60.0, 4, 0.5, 0.0, tc.outputs['Object'])
    col = P.mix_rgb(nt, fac=nz.outputs['Fac'], a_col='#f6d98a', b_col='#eebd5c')
    nt.links.new(col, b.inputs['Base Color'])
    b.inputs['Subsurface Weight'].default_value = 0.9
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.62, 0.25)
    b.inputs['Subsurface Scale'].default_value = 0.025
    b.inputs['Roughness'].default_value = 0.2
    b.inputs['Coat Weight'].default_value = 0.5
    b.inputs['Coat Roughness'].default_value = 0.04
    b.inputs['Specular IOR Level'].default_value = 0.6
    bp = P.bump(nt, nz.outputs['Fac'], 0.15, 0.003)
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def ribbon_profile():
    """A flattened circle: the cross-section of a strand that has stretched into a sheet."""
    cu = bpy.data.curves.new('ribbon_profile', 'CURVE')
    cu.dimensions = '2D'
    sp = cu.splines.new('POLY')
    n = 12
    sp.points.add(n - 1)
    for k in range(n):
        a = k / n * math.tau
        sp.points[k].co = (math.cos(a) * 1.6, math.sin(a) * 0.32, 0, 1)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new('ribbon_profile', cu)
    bpy.context.collection.objects.link(ob)
    ob.hide_render = True
    return ob


def strand_obj(name, mat, profile=None):
    """Two splines: the strand itself, and a second tail used once it snaps."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    if profile is not None:
        cu.bevel_mode = 'OBJECT'
        cu.bevel_object = profile
    else:
        cu.bevel_depth = 1.0
        cu.bevel_resolution = 3
    cu.use_fill_caps = True
    for _ in range(2):
        sp = cu.splines.new('POLY')
        sp.points.add(N_PTS - 1)
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    return ob


def ease(u):
    return u * u * (3 - 2 * u)


def bokeh(rng, n=11):
    """Warm out-of-focus lights far behind, like a restaurant at night."""
    out = []
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
        out.append(bpy.context.object)
    return out


class Bend:
    """The slice flops: the bend angle grows towards the tip as theta(d) = tip * (d / L) ** 1.7,
    where d is the distance from the crust along the slice. Points keep their height above the
    slice's mid-plane, measured along the bent normal."""

    def __init__(self, origin, v_tip, side):
        self.O, self.v, self.w = Vector(origin), Vector(v_tip), Vector(side)
        self.z = Vector((0, 0, 1))
        self.set(0.0)

    def set(self, tip_angle):
        self.tip = tip_angle
        d = np.linspace(0, 1.3, 1301)
        th = tip_angle * np.clip(d / SLICE_LEN, 0, None) ** 1.7
        dd = d[1] - d[0]
        s = np.concatenate([[0], np.cumsum((np.cos(th[1:]) + np.cos(th[:-1])) / 2 * dd)])
        z = -np.concatenate([[0], np.cumsum((np.sin(th[1:]) + np.sin(th[:-1])) / 2 * dd)])
        self._tab = (d, th, s, z)

    def _look(self, d):
        dtab, th, s, z = self._tab
        dc = np.clip(d, 0, None)
        return np.interp(dc, dtab, th), np.interp(dc, dtab, s) + np.minimum(d, 0), np.interp(dc, dtab, z)

    def points(self, co):
        """co: (n, 3) rest positions -> bent rest positions."""
        rel = co - np.array(self.O)
        d = rel @ np.array(self.v)
        w = rel @ np.array(self.w)
        h = rel[:, 2]
        th, s, z = self._look(d)
        v, wv = np.array(self.v), np.array(self.w)
        out = (np.array(self.O)[None, :] + v[None, :] * (s + h * np.sin(th))[:, None] + wv[None, :] * w[:, None]
               + np.array([0, 0, 1.0])[None, :] * (z + h * np.cos(th))[:, None])
        return out

    def frame(self, q):
        """The rigid transform a small object at rest position q follows."""
        rel = Vector(q) - self.O
        d = rel.dot(self.v)
        th, s, z = (float(a[0]) for a in self._look(np.array([d])))
        p = Vector(self.points(np.array([list(q)]))[0])
        t_axis = self.v * math.cos(th) - self.z * math.sin(th)
        n_axis = self.v * math.sin(th) + self.z * math.cos(th)
        Mb = Matrix((t_axis, self.w, n_axis)).transposed()
        Mr = Matrix((self.v, self.w, self.z)).transposed()
        R = (Mb @ Mr.transposed()).to_4x4()
        return Matrix.Translation(p) @ R @ Matrix.Translation(-Vector(q))


def render_matte(path, W, H, keep):
    """Alpha matte of the slice and its strands: everything else is a holdout."""
    sc = bpy.context.scene
    saved = []
    for ob in sc.objects:
        if ob.type in ('MESH', 'CURVE') and ob not in keep:
            saved.append((ob, ob.is_holdout))
            ob.is_holdout = True
    prev = (sc.render.film_transparent, sc.cycles.samples, sc.cycles.use_denoising, sc.cycles.max_bounces,
            sc.render.image_settings.file_format, sc.render.image_settings.color_mode, sc.render.image_settings.color_depth)
    sc.render.film_transparent = True
    sc.cycles.samples = 12
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 0
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for ob, v in saved:
        ob.is_holdout = v
    (sc.render.film_transparent, sc.cycles.samples, sc.cycles.use_denoising, sc.cycles.max_bounces,
     sc.render.image_settings.file_format, sc.render.image_settings.color_mode, sc.render.image_settings.color_depth) = prev


def main():
    out = sys.argv[1]
    kw = dict(a.split('=') for a in sys.argv[2:])
    frames = int(kw.get('frames', 60))
    W, H = int(kw.get('w', 864)), int(kw.get('h', 1536))
    samples = int(kw.get('samples', 28))
    first, last = int(kw.get('first', 0)), int(kw.get('last', frames - 1))
    todo = [int(v) for v in kw['only'].split(',')] if 'only' in kw else range(first, last + 1)
    want_matte = kw.get('matte', '1') == '1'
    os.makedirs(out, exist_ok=True)

    sc = P.reset()
    sc.render.use_persistent_data = True
    sc.view_settings.exposure = 0.0
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
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

    out_dir = Vector((math.cos(TC), math.sin(TC), 0))
    axis = Vector((math.cos(TC + math.pi / 2), math.sin(TC + math.pi / 2), 0))
    bend = Bend((p0.x, p0.y, pz.base), -out_dir, axis)
    # the slice's own meshes bend vertex by vertex; shared meshes (toppings, herbs) ride as rigid pieces
    soft, rigid = [], []
    for ob in sl:
        # the slice's own meshes are built in world space at rest; toppings and herbs are placed objects
        if ob.type == 'MESH' and ob.name.startswith(('crust_', 'sauce_', 'cheese_', 'swall_')):
            co = np.zeros(len(ob.data.vertices) * 3)
            ob.data.vertices.foreach_get('co', co)
            soft.append((ob, co.reshape(-1, 3).copy()))
        else:
            rigid.append((ob, ob.matrix_basis.copy()))

    # strands: (pie point, slice point, radius, snap length, flat?) in rest coordinates
    rng = random.Random(11)
    anchors = []
    def logr(a, b):
        return math.exp(rng.uniform(math.log(a), math.log(b)))
    for k in range(26):                          # around the tip, where the slice leaves the pie last
        rs = rng.uniform(0.0, 0.24)
        ts = TC + rng.uniform(-HALF, HALF) * 0.8 * (1 - rs * 1.5)
        b = Vector((rs * math.cos(ts), rs * math.sin(ts), 0))
        if rng.random() < 0.55:                  # to the other slices' tips
            rp, tp = rng.uniform(0.01, 0.14), TC + math.pi + rng.uniform(-1.3, 1.3)
        else:                                    # to the cut edges near the centre
            side = rng.choice((-1, 1))
            rp, tp = rng.uniform(0.03, 0.26), TC + side * (HALF + rng.uniform(0.04, 0.2))
        a = Vector((rp * math.cos(tp), rp * math.sin(tp), 0))
        r0 = rng.uniform(0.022, 0.034) if k < 4 else logr(0.003, 0.02)
        anchors.append([a, b, r0, rng.uniform(0.45, 1.6), rng.random() < 0.3])
    for side in (-1, 1):                         # along both cut edges, thicker towards the tip
        t = TC + side * HALF
        for k in range(9):
            r = 0.06 + 0.6 * rng.random() ** 1.6
            n_out = Vector((math.cos(t + side * math.pi / 2), math.sin(t + side * math.pi / 2), 0))
            base = Vector((r * math.cos(t), r * math.sin(t), 0))
            anchors.append([base + n_out * 0.012, base - n_out * 0.01, logr(0.003, 0.014), rng.uniform(0.3, 1.2), rng.random() < 0.35])
    for an in anchors:                           # sit both ends in the cheese surface
        for j in (0, 1):
            p = an[j]
            p.z = float(pz.cheese_h(np.array([p.x]), np.array([p.y]))[0]) - 0.003
    smat = mat_strand()
    prof = ribbon_profile()
    strands = [strand_obj(f'strand{i}', smat, prof if an[4] else None) for i, an in enumerate(anchors)]
    wiggle = [(rng.uniform(0, math.tau), rng.uniform(1.0, 2.5), rng.uniform(-0.6, 0.6)) for _ in anchors]

    # light: the key comes from behind the slice so the strands glow
    P.area_light('back', (0.5, 3.6, 1.6), (0, 0.3, 0.4), 1100, 1.8, '#ffd29a')
    P.area_light('key', (-2.3, -1.5, 2.5), (0, 0.4, 0.5), 420, 2.4, '#fff0dc')
    P.area_light('rim', (2.5, 2.0, 1.0), (0, 0.4, 0.4), 320, 1.2, '#ffc27a')
    P.area_light('fill', (1.4, -3.2, 1.0), (0, 0.0, 0.3), 70, 3.0, '#ffe5c8')
    bokeh(random.Random(5))

    def set_tail(sp, start, down, length, r0):
        for i, pt in enumerate(sp.points):
            s = i / (N_PTS - 1)
            p = start + down * (length * s)
            p.z -= 0.35 * length * s * s
            pt.co = (p.x, p.y, p.z, 1.0)
            pt.radius = r0 * (0.9 - 0.45 * s + 0.5 * math.exp(-((s - 1) / 0.12) ** 2))

    def hide_spline(sp, at):
        for pt in sp.points:
            pt.co = (at.x, at.y, at.z, 1.0)
            pt.radius = 0.0

    for f in todo:
        u = ease(f / max(1, frames - 1))
        # camera: a slow push in as the slice rises
        target = Vector((0.0, 0.3 + 0.02 * u, 0.5 + 0.06 * u))
        loc = P.aim(19 - 2 * u, 1.92 - 0.12 * u, tuple(target), 14)
        cam = bpy.context.scene.camera
        if cam is None:
            focus = Vector((0.0, 0.12, 0.32))
            cam = P.camera(loc, tuple(target), lens=58, dof=(focus - Vector(loc)).length, fstop=5.0)
            cam.data.sensor_fit = 'HORIZONTAL'
            cam.data.sensor_width = 36
        cam.location = loc
        cam.rotation_euler = (target - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        cam.data.dof.focus_distance = (Vector((0.0, 0.1 + 0.06 * u, 0.3 + 0.18 * u)) - Vector(loc)).length

        pivot.location = p0 + out_dir * (0.1 * u) + Vector((0, 0, 0.9 * u))
        pivot.rotation_mode = 'AXIS_ANGLE'
        pivot.rotation_axis_angle = (math.radians(-28) * u, axis.x, axis.y, axis.z)
        bend.set(1.0 * u)
        for ob, co0 in soft:
            ob.data.vertices.foreach_set('co', bend.points(co0).ravel())
            ob.data.update()
        for ob, m0 in rigid:
            ob.matrix_basis = bend.frame(m0.to_translation()) @ m0
        bpy.context.view_layer.update()
        M = pivot.matrix_world @ Matrix.Translation(-p0)

        for (a, b, r0, snap, flat), ob, (ph, fq, lat) in zip(anchors, strands, wiggle):
            B = M @ Vector(bend.points(np.array([list(b)]))[0])
            L = (B - a).length
            sp0, sp1 = ob.data.splines[0], ob.data.splines[1]
            if L < 0.004:
                hide_spline(sp0, a); hide_spline(sp1, a)
                ob.hide_render = True
                continue
            ob.hide_render = False
            if L > snap:                         # snapped: a tail hangs from each end
                tail = min(0.22, 0.1 + 0.08 * r0 / 0.01)
                set_tail(sp0, a, (B - a).normalized() * 0.4 + Vector((0, 0, -0.6)), tail * 0.6, r0 * 0.9)
                set_tail(sp1, B, (a - B).normalized() * 0.25 + Vector((0, 0, -0.75)), tail, r0)
                continue
            hide_spline(sp1, B)
            thin = max(0.12, math.sqrt(0.016 / max(L, 0.016)))
            sag = (0.1 + 5.0 * r0) * L * (0.5 + 0.5 * u)
            perp = (B - a).cross(Vector((0, 0, 1)))
            perp = perp.normalized() if perp.length > 1e-6 else Vector((1, 0, 0))
            for i, pt in enumerate(sp0.points):
                s = i / (N_PTS - 1)
                p = a.lerp(B, s)
                p.z -= sag * 4 * s * (1 - s)
                p += perp * (0.012 * L * (math.sin(s * math.pi * fq + ph) + lat) * s * (1 - s) * 4)
                pt.co = (p.x, p.y, p.z, 1.0)
                neck = max(math.exp(-s / 0.07), math.exp(-(1 - s) / 0.07))
                pt.radius = r0 * (thin + (1 - thin) * neck) * (0.55 if flat else 1.0)
                pt.tilt = (ph + s * fq * 2.0) if flat else 0.0

        P.render(os.path.join(out, f'pull_{f:03d}.exr'), W, H, samples)
        if want_matte:
            render_matte(os.path.join(out, f'matte_{f:03d}.png'), W, H, set(sl) | set(strands))
        print('frame', f, 'done', flush=True)


if __name__ == '__main__':
    main()
