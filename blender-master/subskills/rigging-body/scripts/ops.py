"""rigging-body ops: armatures from stored joints or a bone spec, bone collections (DEF, CTRL,
MCH), two-bone IK with poles that keep the rest pose, skinning (automatic heat weights with a
distance-based fallback), weight cleanup, rigid attachments to bones, an optional Rigify
metarig, and deformation checks."""
from __future__ import annotations

import json
import math

import bpy
from mathutils import Matrix, Vector

import bm_checks
import bm_scene

# (bone, head joint, tail joint, parent). Matches modeling-topology skin_figure joints.
HUMANOID = [
    ("hips", "pelvis", "spine", "root"),
    ("spine", "spine", "chest", "hips"),
    ("chest", "chest", "neck", "spine"),
    ("neck", "neck", "head", "chest"),
    ("head", "head", "head_top", "neck"),
] + [b for s in "LR" for b in (
    (f"thigh_{s}", f"hip_{s}", f"knee_{s}", "hips"),
    (f"shin_{s}", f"knee_{s}", f"ankle_{s}", f"thigh_{s}"),
    (f"foot_{s}", f"ankle_{s}", f"toe_{s}", f"shin_{s}"),
    (f"clavicle_{s}", f"clav_{s}", f"shoulder_{s}", "chest"),
    (f"upper_arm_{s}", f"shoulder_{s}", f"elbow_{s}", f"clavicle_{s}"),
    (f"forearm_{s}", f"elbow_{s}", f"wrist_{s}", f"upper_arm_{s}"),
    (f"hand_{s}", f"wrist_{s}", f"hand_{s}", f"forearm_{s}"),
)]
LIMBS = {  # IK end bone -> (chain length, pole direction in rig space)
    "forearm_L": (2, (0, 1, 0)), "forearm_R": (2, (0, 1, 0)),
    "shin_L": (2, (0, -1, 0)), "shin_R": (2, (0, -1, 0)),
}


def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    return o


def _mode(o, mode):
    vl = bpy.context.view_layer
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for x in vl.objects:
        if x is not None:
            x.select_set(x == o)
    vl.objects.active = o
    if mode != "OBJECT":
        bpy.ops.object.mode_set(mode=mode)


def _collection(arm, name):
    return arm.collections.get(name) or arm.collections.new(name)


def armature_from_joints(ctx, mesh, name="RIG_char", spec=None, joints=None):
    """Armature whose deform bones run between stored joints (``joints`` JSON on ``mesh``,
    written by skin_figure) following ``spec`` [(bone, head joint, tail joint, parent)].
    Adds a ``root`` bone at the ground; deform bones go to the DEF collection."""
    m = _obj(mesh)
    J = {k: Vector(v) for k, v in (joints or json.loads(m["joints"])).items()}
    for s in "LR":  # clavicle start near the neck base, derived when missing
        if f"clav_{s}" not in J and f"shoulder_{s}" in J and "chest" in J:
            sh = J[f"shoulder_{s}"]
            J[f"clav_{s}"] = Vector((sh.x * 0.15, sh.y, sh.z))
    spec = spec or HUMANOID
    bm_scene.remove_object(name)
    arm = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, arm)
    bm_scene.link_exclusive(rig)
    rig.matrix_world = m.matrix_world.copy()
    rig.show_in_front = True
    _mode(rig, "EDIT")
    eb = arm.edit_bones
    root = eb.new("root")
    root.head = Vector((J.get("pelvis", Vector()).x, 0, 0))
    root.tail = root.head + Vector((0, 0.25, 0))
    root.use_deform = False
    for bname, h, t, parent in spec:
        b = eb.new(bname)
        b.head, b.tail = J[h], J[t]
        if (b.tail - b.head).length < 1e-4:
            b.tail = b.head + Vector((0, 0, 0.05))
        if parent:
            b.parent = eb[parent]
            b.use_connect = (eb[parent].tail - b.head).length < 1e-4
    # roll: limbs bend around their local X; align X to world X (arms/legs) for clean IK
    for b in eb:
        b.align_roll(Vector((0, -1, 0)) if abs(b.vector.normalized().z) < 0.7 else Vector((0, -1, 0)))
    _mode(rig, "OBJECT")
    d = _collection(arm, "DEF")
    c = _collection(arm, "CTRL")
    _collection(arm, "MCH")
    for b in arm.bones:
        (c if b.name == "root" else d).assign(b)
    rig["rig_spec"] = json.dumps(spec)
    return f"{name}: {len(arm.bones)} bones"


def _signed(u, v, n):
    a = u.angle(v, 0.0)
    return -a if n.dot(u.cross(v)) < 0 else a


def ik_limbs(ctx, rig="RIG_char", limbs=None, pole_distance=0.4):
    """Two-bone IK on each limb end bone with a CTRL target at its tail and a pole in
    ``direction``. Pole angle is computed so the rest pose does not move."""
    r = _obj(rig)
    arm = r.data
    limbs = limbs or {k: v for k, v in LIMBS.items() if k in arm.bones}
    _mode(r, "EDIT")
    eb = arm.edit_bones
    made = {}
    for end, (chain, pdir) in limbs.items():
        b = eb[end]
        base = b
        for _ in range(chain - 1):
            base = base.parent
        tgt = eb.new(f"CTRL_ik_{end}")
        tgt.head = b.tail.copy()
        tgt.tail = b.tail + Vector((0, 0.08, 0)) if b.vector.normalized().z < -0.7 else b.tail + b.vector.normalized() * 0.08
        tgt.parent = eb["root"]
        tgt.use_deform = False
        mid = (base.head + b.tail) / 2
        pole = eb.new(f"CTRL_pole_{end}")
        pole.head = mid + Vector(pdir) * pole_distance
        pole.tail = pole.head + Vector((0, 0, 0.05))
        pole.parent = eb["root"]
        pole.use_deform = False
        n = base.vector.normalized()
        pole_normal = (b.tail - base.head).cross(pole.head - base.head)
        proj = pole_normal.cross(base.vector)
        made[end] = (base.name, tgt.name, pole.name, _signed(base.x_axis, proj, n))
    _mode(r, "OBJECT")
    cc = _collection(arm, "CTRL")
    for end, (_base, tname, pname, angle) in made.items():
        for nm in (tname, pname):
            cc.assign(arm.bones[nm])
            arm.collections["DEF"].unassign(arm.bones[nm]) if "DEF" in arm.collections else None
        pb = r.pose.bones[end]
        con = pb.constraints.get("IK") or pb.constraints.new("IK")
        con.target, con.subtarget = r, tname
        con.pole_target, con.pole_subtarget = r, pname
        con.pole_angle = angle
        con.chain_count = 2
        if _chain_offset(r, end, chain) > 1e-3:   # analytic angle off (near-straight chain): search
            con.pole_angle = _search_pole(r, end, chain, con)
    return f"IK on {list(made)}"


def _chain_offset(r, end, chain):
    bpy.context.view_layer.update()
    pb = r.pose.bones[end]
    worst = 0.0
    for _ in range(chain):
        worst = max(worst, (pb.tail - pb.bone.tail_local).length, (pb.head - pb.bone.head_local).length)
        pb = pb.parent
    return worst


def _search_pole(r, end, chain, con):
    best = (1e9, 0.0)
    for deg in range(-180, 180, 5):
        con.pole_angle = math.radians(deg)
        best = min(best, (_chain_offset(r, end, chain), con.pole_angle))
    step = math.radians(2.5)
    for _ in range(12):
        a0 = best[1]
        for a in (a0 - step, a0 + step):
            con.pole_angle = a
            best = min(best, (_chain_offset(r, end, chain), a))
        step /= 2
    return best[1]


def _deform_bones(rig):
    return [b for b in rig.data.bones if b.use_deform]


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
    return (p - (a + ab * t)).length


def distance_weights(mesh_obj, rig, falloff=2.0, limit=3):
    """Fallback skinning: inverse-distance weights to the nearest deform bone segments."""
    bones = _deform_bones(rig)
    mw = rig.matrix_world
    segs = [(b.name, mw @ b.head_local, mw @ b.tail_local) for b in bones]
    for b in bones:
        if b.name not in mesh_obj.vertex_groups:
            mesh_obj.vertex_groups.new(name=b.name)
        else:
            mesh_obj.vertex_groups[b.name].remove(range(len(mesh_obj.data.vertices)))
    for v in mesh_obj.data.vertices:
        p = mesh_obj.matrix_world @ v.co
        ds = sorted(((max(_seg_dist(p, a, c), 1e-4), n) for n, a, c in segs))[:limit]
        ws = [(1.0 / d ** falloff, n) for d, n in ds]
        tot = sum(w for w, _ in ws)
        for w, n in ws:
            if w / tot > 0.02:
                mesh_obj.vertex_groups[n].add([v.index], w / tot, "REPLACE")


def bind(ctx, mesh, rig="RIG_char", method="auto"):
    """Skin ``mesh`` to ``rig``. auto: heat-diffusion weights (falls back to distance weights for
    any vertex left unweighted); distance: inverse-distance weights only; envelope: bone envelopes."""
    m, r = _obj(mesh), _obj(rig)
    note = method
    if method in ("auto", "envelope"):
        vl = bpy.context.view_layer
        for x in vl.objects:
            if x is not None:
                x.select_set(x in (m, r))
        vl.objects.active = r
        bpy.ops.object.parent_set(type="ARMATURE_AUTO" if method == "auto" else "ARMATURE_ENVELOPE")
    else:
        m.parent = r
        m.matrix_parent_inverse = r.matrix_world.inverted()
        mod = next((x for x in m.modifiers if x.type == "ARMATURE"), None) or m.modifiers.new("Armature", "ARMATURE")
        mod.object = r
        distance_weights(m, r)
    names = {b.name for b in _deform_bones(r)}
    idx = {g.index for g in m.vertex_groups if g.name in names}
    empty = [v.index for v in m.data.vertices if not any(g.group in idx and g.weight > 0 for g in v.groups)]
    if method == "auto" and len(empty) > 0.02 * len(m.data.vertices):
        distance_weights(m, r)
        note = "auto failed on %d verts -> distance weights" % len(empty)
    clean_weights(ctx, mesh, limit=4)
    mod = next(x for x in m.modifiers if x.type == "ARMATURE")
    mod.use_deform_preserve_volume = True
    # armature modifier after shape keys is implicit; keep it first in the stack
    while m.modifiers[0] != mod:
        with bpy.context.temp_override(object=m):
            bpy.ops.object.modifier_move_up(modifier=mod.name)
    return f"{m.name} bound to {r.name} ({note})"


def clean_weights(ctx, mesh, limit=4, min_weight=0.01):
    """Per vertex: drop tiny weights, keep the ``limit`` largest deform weights, normalise."""
    m = _obj(mesh)
    groups = {g.index: g for g in m.vertex_groups}
    rig = next((x.object for x in m.modifiers if x.type == "ARMATURE" and x.object), None)
    deform = {b.name for b in _deform_bones(rig)} if rig else {g.name for g in m.vertex_groups}
    for v in m.data.vertices:
        ws = [(g.weight, g.group) for g in v.groups if groups[g.group].name in deform]
        ws.sort(reverse=True)
        keep = [(w, gi) for w, gi in ws[:limit] if w >= min_weight] or ws[:1]
        tot = sum(w for w, _ in keep) or 1.0
        keep_idx = {gi for _, gi in keep}
        for w, gi in ws:
            if gi in keep_idx:
                groups[gi].add([v.index], w / tot, "REPLACE")
            else:
                groups[gi].remove([v.index])
    return f"{m.name}: weights limited to {limit} and normalised"


def bind_extras(ctx, rig="RIG_char", objects=(), bone="head"):
    """Rigid attachment (hair, eyes, hats, held props, face controls) to one bone, keeping
    their world placement."""
    r = _obj(rig)
    done = []
    bpy.context.view_layer.update()  # fresh matrix_world for just-created objects
    for o in bm_checks.select(objects, mesh_only=False) if isinstance(objects, str) else [bpy.data.objects[n] for n in objects]:
        mw = o.matrix_world.copy()
        pb = r.pose.bones[bone]
        # a bone parent sits at the bone's tail: world = rig @ pose matrix @ (0, length, 0)
        pmat = r.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))
        o.parent = r
        o.parent_type = "BONE"
        o.parent_bone = bone
        o.matrix_parent_inverse = pmat.inverted()
        o.matrix_basis = mw
        done.append(o.name)
    bpy.context.view_layer.update()
    return f"attached {done} to {bone}"


def rigify_metarig(ctx, name="RIG_meta", height=1.8):
    """Optional: add the Rigify human metarig to fit by hand and generate in the UI (needs the
    bundled Rigify add-on enabled)."""
    import addon_utils
    addon_utils.enable("rigify", default_set=True)
    bpy.ops.object.armature_human_metarig_add()
    o = bpy.context.object
    o.name = name
    s = height / max(o.dimensions.z, 1e-6)
    o.scale = (s, s, s)
    return f"{name}: metarig with {len(o.data.bones)} bones (fit, then Generate Rig)"


class _no_action:
    """Mute the rig's action (and constraints' targets stay) so test poses are not overridden
    by keyframes when the check runs on an animated file."""

    def __init__(self, rig):
        self.rig = rig
        self.ad = rig.animation_data
        self.act = self.ad.action if self.ad else None
        self.slot = self.ad.action_slot if self.ad else None

    def __enter__(self):
        if self.act is not None:
            self.ad.action = None
        return self

    def __exit__(self, *exc):
        if self.act is not None:
            self.ad.action = self.act
            if self.slot is not None:
                self.ad.action_slot = self.slot
        bpy.context.view_layer.update()


def _pose_sample(rig, bones_rot):
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    for bn, rot in bones_rot.items():
        if bn in rig.pose.bones:
            rig.pose.bones[bn].rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.update()


DEFAULT_POSE = {"thigh_L": (-40, 0, 0), "shin_L": (60, 0, 0), "forearm_R": (0, 0, 50),
                "upper_arm_L": (0, 0, -30), "head": (10, 0, 20), "spine": (10, 0, 0)}


@bm_checks.register("weights_valid")
def _weights_valid(ctx, objects="GEO_", max_influences=4, tol=0.01):
    res, ok = {}, True
    for m in bm_checks.select(objects):
        rig = next((x.object for x in m.modifiers if x.type == "ARMATURE" and x.object), None)
        if rig is None:
            continue
        deform = {b.name for b in _deform_bones(rig)}
        idx = {g.index for g in m.vertex_groups if g.name in deform}
        unw = over = badsum = 0
        for v in m.data.vertices:
            ws = [g.weight for g in v.groups if g.group in idx and g.weight > 0]
            unw += not ws
            over += len(ws) > max_influences
            badsum += bool(ws) and abs(sum(ws) - 1) > tol
        res[m.name] = {"unweighted": unw, "over_limit": over, "not_normalised": badsum}
        ok = ok and unw == over == badsum == 0
    return ok and bool(res), res, f"every vertex weighted, <= {max_influences} influences, sums 1", \
        "" if res else "no skinned meshes"


@bm_checks.register_fix("weights_valid")
def _fix_weights(ctx, args, attempt):
    for m in bm_checks.select(args.get("objects", "GEO_")):
        if any(x.type == "ARMATURE" for x in m.modifiers):
            if attempt > 1:
                rig = next(x.object for x in m.modifiers if x.type == "ARMATURE")
                distance_weights(m, rig)
            clean_weights(ctx, m.name, args.get("max_influences", 4))
    return "cleaned weights" + (" after distance re-weight" if attempt > 1 else "")


@bm_checks.register("pose_deform_ok")
def _pose_deform_ok(ctx, objects="GEO_", rig="RIG_char", pose=None, max_stretch=3.0):
    """Pose test: the mesh follows the bones (verts move), nothing explodes (edge stretch)."""
    r = bpy.data.objects.get(rig)
    if r is None:
        return False, None, rig, "rig missing"
    meshes = [m for m in bm_checks.select(objects) if any(x.type == "ARMATURE" and x.object == r for x in m.modifiers)]
    if not meshes:
        return False, None, "skinned meshes", "none bound to the rig"
    with _no_action(r):
        return _pose_deform_body(r, meshes, pose, max_stretch)


def _pose_deform_body(r, meshes, pose, max_stretch):
    _pose_sample(r, {})
    dg = bpy.context.evaluated_depsgraph_get()
    rest = {m.name: [v.co.copy() for v in m.evaluated_get(dg).data.vertices] for m in meshes}
    _pose_sample(r, pose or DEFAULT_POSE)
    dg = bpy.context.evaluated_depsgraph_get()
    res, ok = {}, True
    for m in meshes:
        me = m.evaluated_get(dg).data
        moved = sum(1 for a, v in zip(rest[m.name], me.vertices) if (a - v.co).length > 1e-3)
        worst = 0.0
        for e in m.data.edges:
            a, b = e.vertices
            l0 = (rest[m.name][a] - rest[m.name][b]).length
            l1 = (me.vertices[a].co - me.vertices[b].co).length
            if l0 > 1e-6:
                worst = max(worst, l1 / l0)
        finite = all(math.isfinite(c) for v in me.vertices for c in v.co)
        res[m.name] = {"moved": moved, "max_stretch": round(worst, 3), "finite": finite}
        ok = ok and moved > 0 and worst <= max_stretch and finite
    _pose_sample(r, {})
    return ok, res, f"mesh follows pose, edge stretch <= {max_stretch}", ""


@bm_checks.register("ik_rest_stable")
def _ik_rest(ctx, rig="RIG_char", tol=0.002):
    r = bpy.data.objects.get(rig)
    if r is None:
        return False, None, rig, "rig missing"
    with _no_action(r):
        _pose_sample(r, {})
        worst, bad = 0.0, []
        for pb in r.pose.bones:
            d = (r.matrix_world @ pb.tail - r.matrix_world @ pb.bone.tail_local).length
            if d > tol:
                bad.append(pb.name)
            worst = max(worst, d)
    return not bad, {"max_offset": round(worst, 5), "moved": bad}, f"rest pose unchanged by IK (<= {tol} m)", ""


OPS = {"armature_from_joints": armature_from_joints, "ik_limbs": ik_limbs, "bind": bind,
       "clean_weights": clean_weights, "bind_extras": bind_extras, "rigify_metarig": rigify_metarig}
FIXES = {"weights_valid": _fix_weights}
