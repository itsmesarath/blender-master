"""animation ops: frame range and rate, keyframes on any property, pose keys for rigs, wave
cycles, noise, cyclic loops, path following, NLA strips, baking driven shape keys to keyframes
for export - and checks that animation exists, loops cleanly and has no pops."""
from __future__ import annotations

import math

import bpy

import bm_anim
import bm_checks
import bm_scene


def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    return o


def frame_range(ctx, start=1, end=120, fps=24):
    s = bpy.context.scene
    s.frame_start, s.frame_end = start, end
    s.render.fps, s.render.fps_base = fps, 1.0
    s.frame_set(start)
    return f"frames {start}-{end} at {fps} fps"


def keyframes(ctx, target, data_path, keys, index=None, interpolation="BEZIER", bone=None, data=False):
    """keys: [[frame, value], ...] (value may be a list for vector properties, then every
    index is keyed). ``bone`` keys a pose bone channel; ``data`` keys the object's data block
    (e.g. a light's energy, a camera's lens)."""
    o = _obj(target)
    idb = o.data if data else o
    path = f'pose.bones["{bone}"].{data_path}' if bone else data_path
    if bone and data_path.startswith("rotation_euler"):
        o.pose.bones[bone].rotation_mode = "XYZ"
    n = 0
    for frame, value in keys:
        vals = value if isinstance(value, (list, tuple)) else [value]
        idxs = range(len(vals)) if index is None and len(vals) > 1 else [index or 0] * len(vals)
        for i, v in zip(idxs, vals):
            bm_anim.key(idb, path, i, frame, v, interpolation, group=bone)
            n += 1
    return f"{n} keys on {target}{'/' + bone if bone else ''}.{data_path}"


def pose_keys(ctx, rig, poses, interpolation="BEZIER", degrees=True):
    """poses: {frame: {bone: [rx, ry, rz]}} rotations in the bone's local XYZ (degrees)."""
    o = _obj(rig)
    n = 0
    for frame, bones in sorted(poses.items(), key=lambda kv: float(kv[0])):
        for bn, rot in bones.items():
            pb = o.pose.bones[bn]
            pb.rotation_mode = "XYZ"
            for i, a in enumerate(rot):
                bm_anim.key(o, f'pose.bones["{bn}"].rotation_euler', i, float(frame),
                            math.radians(a) if degrees else a, interpolation, group=bn)
                n += 1
    return f"{n} pose keys on {rig}"


def wave(ctx, target, data_path, index=0, amplitude=1.0, period=24, phase=0.0, center=None, start=None,
         cycles=1, bone=None, degrees=False, data=False, loop=None):
    """Sine oscillation keyed at quarter periods (ease in/out): idle sways, breathing, bobbing,
    a waving hand. ``phase`` in periods (0-1). ``loop`` (default: whole cycles starting at the
    scene start) repeats it forever; otherwise it plays ``cycles`` times and holds."""
    o = _obj(target)
    idb = o.data if data else o
    path = f'pose.bones["{bone}"].{data_path}' if bone else data_path
    if bone and "rotation_euler" in data_path:
        o.pose.bones[bone].rotation_mode = "XYZ"
    start = bpy.context.scene.frame_start if start is None else start
    base = idb.path_resolve(path)[index] if center is None else center
    amp = math.radians(amplitude) if degrees else amplitude
    pts = int(cycles * 4)
    for k in range(pts + 1):
        f = start + k * period / 4
        val = base + amp * math.sin(2 * math.pi * (k / 4 + phase))
        bm_anim.key(idb, path, index, f, val, "BEZIER", group=bone)
    fc = next(f for f in bm_anim.fcurves(idb) if f.data_path == path and f.array_index == index)
    for kp in fc.keyframe_points:
        kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    if loop is None:
        loop = float(cycles).is_integer() and start == bpy.context.scene.frame_start
    if loop and not any(m.type == "CYCLES" for m in fc.modifiers):
        fc.modifiers.new("CYCLES")
    fc.update()
    return f"wave on {target}.{path}[{index}] amp {amplitude} period {period}"


def cycle(ctx, target, data=False):
    o = _obj(target)
    bm_anim.make_cyclic(o.data if data else o)
    return f"{target}: cyclic"


def noise(ctx, target, data_path, index=0, strength=0.02, scale=8.0, bone=None):
    """Organic jitter (handheld camera, flicker, idle micro-motion) on top of existing keys."""
    o = _obj(target)
    path = f'pose.bones["{bone}"].{data_path}' if bone else data_path
    bm_anim.add_noise(o, path, index, strength, scale)
    return f"noise on {target}.{path}[{index}]"


def follow_path(ctx, target, points, frames=(1, 120), closed=False, follow=True, name=None):
    """Move ``target`` along a smooth curve through ``points`` between ``frames``."""
    o = _obj(target)
    name = name or f"CTRL_{target.split('_', 1)[-1]}_path"
    bm_scene.remove_object(name)
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("NURBS")
    sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points):
        p.co = (*c, 1.0)
    sp.use_endpoint_u = not closed
    sp.use_cyclic_u = closed
    sp.order_u = min(4, len(points))
    path = bpy.data.objects.new(name, cu)
    bm_scene.link_exclusive(path)
    o.location = (0, 0, 0)
    con = o.constraints.get("FollowPath") or o.constraints.new("FOLLOW_PATH")
    con.name = "FollowPath"
    con.target = path
    con.use_curve_follow = follow
    con.use_fixed_location = True
    con.forward_axis = "TRACK_NEGATIVE_Y"
    con.up_axis = "UP_Z"
    bm_anim.key(o, 'constraints["FollowPath"].offset_factor', 0, frames[0], 0.0, "BEZIER")
    bm_anim.key(o, 'constraints["FollowPath"].offset_factor', 0, frames[1], 1.0 if not closed else 0.999, "BEZIER")
    return f"{target} follows {name} over frames {frames}"


def nla_push(ctx, target, track="base", start=None):
    """Move the active action into an NLA strip (layering, reuse, game clips)."""
    o = _obj(target)
    ad = o.animation_data
    if not ad or not ad.action:
        return "SKIP: no action"
    act = ad.action
    t = ad.nla_tracks.get(track) or ad.nla_tracks.new()
    t.name = track
    s = t.strips.new(act.name, int(start if start is not None else act.frame_range[0]), act)
    ad.action = None
    return f"{target}: {act.name} -> NLA {track} strip {s.name}"


def bake_shape_keys(ctx, mesh, frames=None, step=1, remove_drivers=False):
    """Key every driven shape key at each frame (for FBX/glTF: engines import key animation,
    not drivers)."""
    o = _obj(mesh)
    sk = o.data.shape_keys
    if not sk or not sk.animation_data or not sk.animation_data.drivers:
        return "SKIP: no driven keys"
    s = bpy.context.scene
    f0, f1 = frames or (s.frame_start, s.frame_end)
    names = [fc.data_path.split('"')[1] for fc in sk.animation_data.drivers]
    vals = {n: [] for n in names}
    for f in range(f0, f1 + 1, step):
        s.frame_set(f)
        for n in names:
            vals[n].append((f, sk.key_blocks[n].value))
    if remove_drivers:
        for n in names:
            sk.driver_remove(f'key_blocks["{n}"].value')
    for n, fv in vals.items():
        for f, v in fv:
            bm_anim.key(sk, f'key_blocks["{n}"].value', 0, f, v, "LINEAR")
    s.frame_set(f0)
    return f"baked {len(names)} driven keys over {f0}-{f1}"


# ------------------------------------------------------------------ checks
def _animated(sel):
    out = []
    for o in bm_checks.select(sel, mesh_only=False):
        fcs = bm_anim.fcurves(o)
        if o.data is not None and hasattr(o.data, "shape_keys") and o.data.shape_keys:
            fcs += bm_anim.fcurves(o.data.shape_keys)
        if o.type in {"LIGHT", "CAMERA"}:
            fcs += bm_anim.fcurves(o.data)
        out.append((o, fcs))
    return out


@bm_checks.register("anim_present")
def _anim_present(ctx, objects="*", min_curves=1, min_range=1e-4):
    res = {}
    for o, fcs in _animated(objects):
        moving = 0
        for fc in fcs:
            ks = [kp.co.y for kp in fc.keyframe_points]
            if (ks and max(ks) - min(ks) > min_range) or any(m.type == "NOISE" for m in fc.modifiers):
                moving += 1
        if fcs:
            res[o.name] = moving
    ok = bool(res) and sum(res.values()) >= min_curves
    return ok, res, f">= {min_curves} moving curves", "" if res else "nothing animated"


@bm_checks.register("loop_ok")
def _loop_ok(ctx, objects="*", tol=1e-3):
    """Cyclic loops: each curve's value at frame_end+1 equals frame_start (no hitch)."""
    s = bpy.context.scene
    bad = {}
    for o, fcs in _animated(objects):
        for fc in fcs:
            if any(m.type == "NOISE" for m in fc.modifiers):
                continue
            a, b = fc.evaluate(s.frame_start), fc.evaluate(s.frame_end + 1)
            if abs(a - b) > tol * max(1.0, abs(a)):
                bad[f"{o.name}:{fc.data_path}[{fc.array_index}]"] = round(b - a, 4)
    return not bad, bad, "start and end+1 match", ""


@bm_checks.register_fix("loop_ok")
def _fix_loop(ctx, args, attempt):
    for o, _f in _animated(args.get("objects", "*")):
        bm_anim.make_cyclic(o)
    return "made curves cyclic"


@bm_checks.register("no_pops")
def _no_pops(ctx, objects="*", ratio=6.0, floor=1e-3):
    """Flags frame-to-frame jumps much larger than the curve's typical step (accidental keys,
    flipped rotations)."""
    s = bpy.context.scene
    bad = {}
    for o, fcs in _animated(objects):
        for fc in fcs:
            if any(m.type == "NOISE" for m in fc.modifiers):
                continue
            vals = [fc.evaluate(f) for f in range(s.frame_start, s.frame_end + 1)]
            steps = sorted(abs(b - a) for a, b in zip(vals, vals[1:]))
            if len(steps) < 3:
                continue
            typical = max(steps[len(steps) * 3 // 4], floor)
            if steps[-1] > ratio * typical and steps[-1] > floor * 10:
                bad[f"{o.name}:{fc.data_path}[{fc.array_index}]"] = round(steps[-1], 4)
    return not bad, bad, f"no step > {ratio}x the typical step", ""


OPS = {"frame_range": frame_range, "keyframes": keyframes, "pose_keys": pose_keys, "wave": wave, "cycle": cycle,
       "noise": noise, "follow_path": follow_path, "nla_push": nla_push, "bake_shape_keys": bake_shape_keys}
FIXES = {"loop_ok": _fix_loop}
