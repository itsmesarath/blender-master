"""rigging-face ops: regional shape keys (move, rotate about a pivot, inflate) with soft falloff,
left/right splits, corrective combination keys, face control objects, and drivers that map a
control's channel to a key value (clamped 0-1) - plus checks that keys and drivers work."""
from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

import bm_checks
import bm_scene


def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    return o


def _falloff(d, r):
    t = max(0.0, 1.0 - d / r)
    return t * t * (3 - 2 * t)


def _basis(o):
    if o.data.shape_keys is None:
        o.shape_key_add(name="Basis", from_mix=False)
    return o.data.shape_keys.key_blocks["Basis"]


def region_key(ctx, mesh, name, center, radius, offset=None, rotate=None, inflate=0.0, side=None,
               mirror=False, squash=None, below=None, snap=True):
    """Shape key ``name`` deforming a soft sphere around ``center``.
    offset: (dx, dy, dz) move; rotate: (axis 'X'|'Y'|'Z', degrees, pivot) e.g. a jaw hinge;
    inflate: along normals; side 'L'/'R' limits to x>0 / x<0; mirror adds the mirrored region;
    squash: (axis, factor) flattens toward the centre (lids closing); below: only verts under z;
    snap moves ``center`` onto the nearest basis vertex so a rough guess still hits the surface."""
    o = _obj(mesh)
    basis = _basis(o)
    if snap:
        center = min((d.co for d in basis.data), key=lambda p: (p - Vector(center)).length_squared).copy()
    kb = o.data.shape_keys.key_blocks.get(name) or o.shape_key_add(name=name, from_mix=False)
    kb.relative_key = basis
    c = Vector(center)
    centers = [c] + ([Vector((-c.x, c.y, c.z))] if mirror and abs(c.x) > 1e-6 else [])
    rot = None
    if rotate:
        axis, deg, pivot = rotate
        rot = (Matrix.Rotation(math.radians(deg), 4, axis), Vector(pivot))
    n = 0
    for i, v in enumerate(o.data.vertices):
        p = basis.data[i].co
        if side == "L" and p.x < -1e-6 or side == "R" and p.x > 1e-6:
            kb.data[i].co = p
            continue
        if below is not None and p.z > below:
            kb.data[i].co = p
            continue
        w, sgn = 0.0, 1
        for k, cc in enumerate(centers):
            wk = _falloff((p - cc).length, radius)
            if wk > w:
                w, sgn = wk, (1 if k == 0 else -1)
        if w <= 0:
            kb.data[i].co = p
            continue
        q = p.copy()
        if offset:
            q += Vector((offset[0] * sgn, offset[1], offset[2])) * w
        if rot:
            m, piv = rot
            r = piv + (m @ (p - piv))
            q += (r - p) * w
        if inflate:
            q += v.normal * inflate * w
        if squash:
            ax, f = squash
            ai = "XYZ".index(ax)
            cc = centers[0 if sgn > 0 else 1]
            q[ai] = q[ai] + (cc[ai] - q[ai]) * (1 - f) * w
        kb.data[i].co = q
        n += 1
    kb.value = 0.0
    return f"{o.name}: key {name} moves {n} verts"


def split_lr(ctx, mesh, key, blend=0.01, remove_source=False):
    """Make <key>_L and <key>_R from a symmetric key, cross-fading over ``blend`` metres at x=0."""
    o = _obj(mesh)
    kbs = o.data.shape_keys.key_blocks
    src, basis = kbs[key], kbs["Basis"]
    for side, sgn in (("L", 1), ("R", -1)):
        nm = f"{key}_{side}"
        kb = kbs.get(nm) or o.shape_key_add(name=nm, from_mix=False)
        kb.relative_key = basis
        for i in range(len(basis.data)):
            b = basis.data[i].co
            x = b.x * sgn
            w = 1.0 if x >= blend else 0.0 if x <= -blend else (x + blend) / (2 * blend)
            kb.data[i].co = b + (src.data[i].co - b) * w
    if remove_source:
        o.shape_key_remove(src)
    return f"{o.name}: {key} split into _L/_R"


def face_control(ctx, name, location, size=0.015, parent=None):
    """Small control object (empty) the animator moves; drivers read its local location.
    rigging-body ``bind_extras`` later parents it to the head bone."""
    if not name.startswith("CTRL_"):
        name = "CTRL_" + name
    bm_scene.remove_object(name)
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "SPHERE"
    e.empty_display_size = size
    e.location = location
    bm_scene.link_exclusive(e)
    if parent:
        e.parent = bpy.data.objects[parent]
    e.lock_rotation = (True, True, True)
    e.lock_scale = (True, True, True)
    return f"{name} at {tuple(round(x, 3) for x in location)}"


def drive(ctx, mesh, key, control, channel="LOC_Z", full=0.02, space="TRANSFORM_SPACE", bone=None):
    """Driver: key value = clamp(channel / full, 0, 1); a negative ``full`` maps downward moves.
    TRANSFORM_SPACE reads the control's own channels (what the animator keys), so it keeps
    working after the control is parented to the head. ``bone`` drives from a pose bone of
    armature ``control`` (use LOCAL_SPACE for bones)."""
    o = _obj(mesh)
    kb = o.data.shape_keys.key_blocks[key]
    path = f'key_blocks["{key}"].value'
    o.data.shape_keys.driver_remove(path)
    fc = o.data.shape_keys.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED"
    var = d.variables.new()
    var.name = "c"
    var.type = "TRANSFORMS"
    t = var.targets[0]
    t.id = _obj(control)
    if bone:
        t.bone_target = bone
    t.transform_type = channel
    t.transform_space = space
    ctl = _obj(control)
    src = ctl.pose.bones[bone] if bone else ctl
    ax = "XYZ".index(channel[-1])
    attr = {"LOC": "location", "ROT": "rotation_euler", "SCA": "scale"}[channel[:3]]
    rest = round(getattr(src, attr)[ax], 6)
    # rest value subtracted, so the control can sit anywhere; simple expression: no Python needed
    d.expression = f"min(max((c - {rest}) / {full}, 0), 1)" if rest else f"min(max(c / {full}, 0), 1)"
    kb.slider_max = 1.0
    return f"{key} <- {control}.{channel} (full at {full})"


def combo_key(ctx, mesh, name, keys, offset=None, center=None, radius=0.03, inflate=0.0):
    """Corrective key that turns on only when all ``keys`` are on (value = product of their
    values). Copies the source keys' driver variables, because a driver on a shape key that
    reads other keys of the same Key datablock forms a dependency cycle and stops evaluating."""
    import re
    o = _obj(mesh)
    if center is not None:
        region_key(ctx, mesh, name, center, radius, offset=offset, inflate=inflate)
    sk = o.data.shape_keys
    src = {fc.data_path: fc for fc in (sk.animation_data.drivers if sk.animation_data else [])}
    path = f'key_blocks["{name}"].value'
    sk.driver_remove(path)
    fc = sk.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED"
    terms = []
    for i, k in enumerate(keys):
        sfc = src.get(f'key_blocks["{k}"].value')
        if sfc is None:
            raise ValueError(f"key {k!r} has no driver yet: drive it before making the combo")
        expr = sfc.driver.expression
        for var in sfc.driver.variables:
            nv = d.variables.new()
            nv.name = f"k{i}_{var.name}"
            nv.type = var.type
            for a, b in zip(var.targets, nv.targets):
                if var.type == "SINGLE_PROP":
                    b.id_type = a.id_type
                b.id = a.id
                b.data_path = a.data_path
                b.bone_target = a.bone_target
                b.transform_type = a.transform_type
                b.transform_space = a.transform_space
            expr = re.sub(rf"\b{re.escape(var.name)}\b", nv.name, expr)
        terms.append(f"({expr})")
    d.expression = " * ".join(terms)
    return f"{name} = {' * '.join(keys)}"


@bm_checks.register("shape_keys_valid")
def _shape_keys_valid(ctx, objects="GEO_", min_keys=1, max_move=0.2):
    res, ok = {}, True
    for o in bm_checks.select(objects):
        sk = o.data.shape_keys
        if sk is None:
            continue
        basis = sk.key_blocks[0]
        info = {}
        for kb in sk.key_blocks[1:]:
            mv = max(((a.co - b.co).length for a, b in zip(kb.data, basis.data)), default=0.0)
            info[kb.name] = round(mv, 4)
            ok = ok and 1e-5 < mv <= max_move and kb.relative_key == basis
        res[o.name] = info
        ok = ok and len(info) >= min_keys
    return ok and bool(res), res, f">= {min_keys} keys, each moves 0 < d <= {max_move} m", \
        "" if res else "no shape keys"


@bm_checks.register("drivers_resolve")
def _drivers_resolve(ctx, objects="GEO_"):
    """Every driver valid, targets exist, and moving each driver's control changes the value."""
    res, ok, n = {}, True, 0
    for o in bm_checks.select(objects):
        sk = o.data.shape_keys
        if not sk or not sk.animation_data:
            continue
        for fc in sk.animation_data.drivers:
            n += 1
            d = fc.driver
            probs = []
            if not d.is_valid:
                probs.append("invalid expression")
            for var in d.variables:
                for t in var.targets[:1 if var.type in ("SINGLE_PROP", "TRANSFORMS") else 2]:
                    if t.id is None:
                        probs.append(f"{var.name}: no target")
            tvs = [v for v in d.variables if v.type == "TRANSFORMS"]
            tv = tvs[0] if len(tvs) == 1 else None   # combos (products) need all controls on
            if tv is not None and tv.targets[0].id is not None and not probs:
                ctl = tv.targets[0].id
                ch = tv.targets[0].transform_type
                before = _value(o, fc)
                ax = "XYZ".index(ch[-1]) if ch.startswith("LOC") else None
                if ax is not None:
                    old = ctl.location[ax]
                    changed = False
                    for delta in (0.05, -0.05):
                        ctl.location[ax] = old + delta
                        changed = changed or abs(_value(o, fc) - before) > 1e-4
                    ctl.location[ax] = old
                    bpy.context.view_layer.update()
                    if not changed:
                        probs.append("control does not change value")
            res[fc.data_path] = probs or "ok"
            ok = ok and not probs
    return ok and n > 0, res, "all drivers resolve and respond", "" if n else "no drivers"


def _value(o, fc):
    bpy.context.view_layer.update()
    path = fc.data_path
    name = path.split('"')[1]
    return o.data.shape_keys.key_blocks[name].value


OPS = {"region_key": region_key, "split_lr": split_lr, "face_control": face_control, "drive": drive,
       "combo_key": combo_key}
FIXES = {}
