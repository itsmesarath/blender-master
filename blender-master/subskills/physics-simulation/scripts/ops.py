"""physics-simulation ops: rigid bodies, cloth (presets, pin groups, pressure), collisions,
soft bodies, particles, low-resolution smoke/liquid domains, garments cut from a body mesh for
character clothing, cache baking - and checks that simulations move, stay bounded and settle."""
from __future__ import annotations

import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

import bm_checks
import bm_scene


def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    return o


def _objs(sel):
    if isinstance(sel, str) and not sel.endswith("_") and sel != "*":
        return [_obj(sel)]
    out = bm_checks.select(sel)
    if not out:
        raise KeyError(f"no mesh objects match {sel!r}")
    return out


def _override(o):
    return bpy.context.temp_override(object=o, active_object=o, selected_objects=[o],
                                     selected_editable_objects=[o])


# ------------------------------------------------------------------ rigid bodies
def rigid_world(ctx, substeps=10, iterations=10, frame_start=None, frame_end=None):
    sc = bpy.context.scene
    if sc.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    w = sc.rigidbody_world
    w.substeps_per_frame = substeps
    w.solver_iterations = iterations
    w.point_cache.frame_start = frame_start or sc.frame_start
    w.point_cache.frame_end = frame_end or sc.frame_end
    if w.collection is None:
        w.collection = bpy.data.collections.get("RigidBodyWorld") or bpy.data.collections.new("RigidBodyWorld")
    return f"rigid world {w.point_cache.frame_start}-{w.point_cache.frame_end}, {substeps} substeps"


PRIMITIVE_SHAPES = {"BOX", "SPHERE", "CAPSULE", "CYLINDER", "CONE"}


def _center_origin(o):
    """Primitive collision shapes are centred on the object origin; move the origin to the
    bounds centre (geometry stays put) so a base-origin mesh does not sink into the floor."""
    bpy.context.view_layer.update()   # fresh matrix_world for just-created objects
    vs = o.data.vertices
    if not vs:
        return
    lo = Vector((min(v.co.x for v in vs), min(v.co.y for v in vs), min(v.co.z for v in vs)))
    hi = Vector((max(v.co.x for v in vs), max(v.co.y for v in vs), max(v.co.z for v in vs)))
    c = (lo + hi) / 2
    if c.length < 1e-6:
        return
    o.data.transform(Matrix.Translation(-c))
    o.matrix_world = o.matrix_world @ Matrix.Translation(c)


def rigid_body(ctx, targets, kind="ACTIVE", shape="CONVEX_HULL", mass=1.0, friction=0.5, bounciness=0.1,
               margin=0.001, animated=False, damping=0.05):
    """ACTIVE bodies fall and collide; PASSIVE are static colliders (floor, product).
    ``animated`` passive bodies follow their keyframes (a pushing hand, a moving lid).
    Primitive shapes re-centre the origin on the bounds first (they are centred on the origin)."""
    if bpy.context.scene.rigidbody_world is None:
        rigid_world(ctx)
    objs = _objs(targets)
    for o in objs:
        if shape in PRIMITIVE_SHAPES:
            _center_origin(o)
        if o.rigid_body is None:
            with _override(o):
                bpy.ops.rigidbody.object_add(type=kind)
        rb = o.rigid_body
        rb.type = kind
        rb.collision_shape = shape
        rb.mass = mass
        rb.friction = friction
        rb.restitution = bounciness
        rb.collision_margin = margin
        rb.use_margin = True
        rb.kinematic = animated
        rb.linear_damping = rb.angular_damping = damping
    return f"{len(objs)} {kind.lower()} rigid bodies ({shape})"


# ------------------------------------------------------------------ cloth
CLOTH = {  # mass kg/m2-ish, tension/compression, shear, bending, air
    "cotton": dict(mass=0.3, tension=15, shear=5, bending=0.5, air=1.0),
    "silk": dict(mass=0.15, tension=5, shear=5, bending=0.05, air=1.0),
    "denim": dict(mass=1.0, tension=40, shear=40, bending=10, air=1.0),
    "leather": dict(mass=0.4, tension=80, shear=80, bending=150, air=1.0),
    "rubber": dict(mass=3.0, tension=15, shear=15, bending=25, air=1.0),
    "flag": dict(mass=0.2, tension=10, shear=8, bending=0.2, air=2.0),
}


def pin_group(ctx, target, name="pin", z_above=None, z_below=None, box_min=None, box_max=None):
    """Vertex group of vertices above/below a height or inside a box (object space): the cloth
    pin group (waistband, flag pole edge, curtain rail)."""
    o = _obj(target)
    vg = o.vertex_groups.get(name) or o.vertex_groups.new(name=name)
    idx = []
    for v in o.data.vertices:
        c = v.co
        if z_above is not None and c.z < z_above:
            continue
        if z_below is not None and c.z > z_below:
            continue
        if box_min is not None and not all(box_min[i] <= c[i] <= box_max[i] for i in range(3)):
            continue
        idx.append(v.index)
    vg.add(idx, 1.0, "REPLACE")
    return f"{target}: {len(idx)} verts in {name}"


def cloth(ctx, target, preset="cotton", pin=None, quality=6, self_collision=False, pressure=0.0,
          thickness=0.005, shrink=0.0, frame_start=None, frame_end=None):
    """Cloth on ``target`` with a material preset; ``pin`` = vertex group held in place
    (it then follows the object's parent/armature); ``pressure`` > 0 inflates closed meshes."""
    o = _obj(target)
    m = next((x for x in o.modifiers if x.type == "CLOTH"), None) or o.modifiers.new("Cloth", "CLOTH")
    s, c = m.settings, m.collision_settings
    p = CLOTH[preset]
    s.quality = quality
    s.mass = p["mass"]
    s.tension_stiffness = s.compression_stiffness = p["tension"]
    s.shear_stiffness = p["shear"]
    s.bending_stiffness = p["bending"]
    s.air_damping = p["air"]
    s.shrink_min = shrink
    if pin:
        s.vertex_group_mass = pin
        s.pin_stiffness = 1.0
    if pressure:
        s.use_pressure = True
        s.uniform_pressure_force = pressure
    c.distance_min = thickness
    c.use_self_collision = self_collision
    sc = bpy.context.scene
    m.point_cache.frame_start = frame_start or sc.frame_start
    m.point_cache.frame_end = frame_end or sc.frame_end
    return f"{target}: {preset} cloth, quality {quality}" + (f", pinned by {pin}" if pin else "")


def collision(ctx, targets, thickness=0.005, friction=5.0, damping=0.1):
    """Make objects collide with cloth, soft bodies and particles."""
    objs = _objs(targets)
    for o in objs:
        m = next((x for x in o.modifiers if x.type == "COLLISION"), None) or o.modifiers.new("Collision", "COLLISION")
        cs = o.collision
        cs.thickness_outer = thickness
        cs.cloth_friction = friction
        cs.damping = damping
    return f"{len(objs)} colliders"


def soft_body(ctx, target, goal=0.7, stiffness=0.5, friction=0.5, goal_group=None):
    """Jiggle and squash (bellies, jelly, antennae): goal holds the shape, lower = floppier."""
    o = _obj(target)
    m = next((x for x in o.modifiers if x.type == "SOFT_BODY"), None) or o.modifiers.new("Softbody", "SOFT_BODY")
    s = m.settings
    s.use_goal = goal > 0
    s.goal_default = goal
    s.goal_spring = stiffness
    s.goal_friction = friction
    if goal_group:
        s.vertex_group_goal = goal_group
    s.use_edges = True
    s.use_stiff_quads = True
    return f"{target}: soft body goal {goal}"


def garment_from_body(ctx, body, name, box_min, box_max, offset=0.012, pin_z_above=None, thickness=0.004,
                      preset="cotton", collide_body=True):
    """Character clothing from the body itself: copy the faces inside a box (shirt, skirt,
    sleeve), push them out by ``offset``, optionally pin the top (waistband) and make it cloth
    colliding with the body. Simple, robust garments for headless runs; tailored clothes are
    modelled from patterns (see reference)."""
    b = _obj(body)
    if not name.startswith("GEO_"):
        name = "GEO_" + name
    bm = bmesh.new()
    bm.from_mesh(b.data)
    lo, hi = Vector(box_min), Vector(box_max)
    drop = [f for f in bm.faces if not all(lo[i] <= f.calc_center_median()[i] <= hi[i] for i in range(3))]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * offset
    bm_scene.remove_object(name)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    o = bpy.data.objects.new(name, me)
    bm_scene.link_exclusive(o)
    o.matrix_world = b.matrix_world.copy()
    if pin_z_above is not None:
        pin_group(ctx, name, "pin", z_above=pin_z_above)
    sol = o.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = 1.0
    if preset:
        cloth(ctx, name, preset, pin="pin" if pin_z_above is not None else None, thickness=thickness)
        o.modifiers.move(o.modifiers.find("Solidify"), len(o.modifiers) - 1)
    if collide_body:
        collision(ctx, [b.name], thickness=thickness)
    return f"{name}: {len(me.polygons)} faces from {body}"


# ------------------------------------------------------------------ particles and fluids
def particles(ctx, emitter, count=500, frame_start=1, frame_end=24, lifetime=50, velocity=1.0, random=0.3,
              instance=None, size=0.05, size_random=0.3, gravity=1.0, seed=0):
    """Emitter particles (sparks, confetti, dust, debris); ``instance`` renders an object per
    particle (hidden source)."""
    o = _obj(emitter)
    ps_mod = next((m for m in o.modifiers if m.type == "PARTICLE_SYSTEM"), None)
    if ps_mod is None:
        o.modifiers.new("Particles", "PARTICLE_SYSTEM")
        ps_mod = o.modifiers[-1]
    ps = ps_mod.particle_system
    st = ps.settings
    st.count = count
    st.frame_start, st.frame_end = frame_start, frame_end
    st.lifetime = lifetime
    st.normal_factor = velocity
    st.factor_random = random
    st.particle_size = size
    st.size_random = size_random
    st.effector_weights.gravity = gravity
    ps.seed = seed
    if instance:
        src = _obj(instance)
        st.render_type = "OBJECT"
        st.instance_object = src
        src.hide_render = True
    return f"{emitter}: {count} particles {frame_start}-{frame_end}"


def fluid(ctx, kind="smoke", emitter=None, domain_size=(2, 2, 2), domain_location=(0, 0, 1), resolution=32,
          frame_end=None, name="FX_fluid_domain"):
    """Low-resolution gas or liquid for previews and stylized shots: a domain box plus an
    emitter (flow). Raise resolution only for the final bake (cost grows with its cube)."""
    sc = bpy.context.scene
    import bm_mesh
    bm_scene.remove_object(name)
    d = bm_mesh.box(name, domain_size, (domain_location[0], domain_location[1], domain_location[2] - domain_size[2] / 2))
    dm = d.modifiers.new("Fluid", "FLUID")
    dm.fluid_type = "DOMAIN"
    ds = dm.domain_settings
    ds.domain_type = "GAS" if kind == "smoke" else "LIQUID"
    ds.resolution_max = resolution
    ds.cache_frame_start = sc.frame_start
    ds.cache_frame_end = frame_end or sc.frame_end
    ds.cache_directory = ctx.path("cache", "fluid")
    ds.cache_type = "ALL"
    if kind == "liquid":
        ds.use_mesh = True
    if emitter:
        e = _obj(emitter)
        fm = next((m for m in e.modifiers if m.type == "FLUID"), None) or e.modifiers.new("Fluid", "FLUID")
        fm.fluid_type = "FLOW"
        fs = fm.flow_settings
        fs.flow_type = "SMOKE" if kind == "smoke" else "LIQUID"
        fs.flow_behavior = "INFLOW" if kind == "smoke" else "GEOMETRY"
        if kind == "liquid":
            e.hide_render = True
    return f"{name}: {kind} domain res {resolution}"


def bake(ctx, frame_end=None):
    """Bake every cache (rigid bodies, cloth, soft bodies, particles) into the .blend and any
    fluid domain to its cache folder, so later parts and renders read the same result."""
    sc = bpy.context.scene
    if frame_end:
        sc.frame_end = frame_end
    msgs = []
    fluids = [o for o in sc.objects if any(m.type == "FLUID" and m.fluid_type == "DOMAIN" for m in o.modifiers)]
    for d in fluids:
        os.makedirs(next(m for m in d.modifiers if m.type == "FLUID").domain_settings.cache_directory, exist_ok=True)
        with _override(d):
            bpy.ops.fluid.bake_all()
        msgs.append(f"fluid {d.name}")
    with bpy.context.temp_override(scene=sc):
        bpy.ops.ptcache.free_bake_all()
        bpy.ops.ptcache.bake_all(bake=True)
    msgs.append("point caches")
    sc.frame_set(sc.frame_start)
    return "baked " + ", ".join(msgs)


# ------------------------------------------------------------------ checks
def _snap(objs, frame):
    sc = bpy.context.scene
    sc.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for o in objs:
        ev = o.evaluated_get(dg)
        pts = [ev.matrix_world @ v.co for v in ev.data.vertices] if ev.type == "MESH" and ev.data else \
            [ev.matrix_world.translation.copy()]
        if not pts:
            pts = [ev.matrix_world.translation.copy()]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        out[o.name] = (lo, hi, pts)
    return out


@bm_checks.register("sim_moved")
def _sim_moved(ctx, objects="GEO_", frame=None, min_move=0.01):
    sc = bpy.context.scene
    objs = bm_checks.select(objects)
    if not objs:
        return False, None, "simulated objects", "none"
    a = _snap(objs, sc.frame_start)
    b = _snap(objs, frame or sc.frame_end)
    sc.frame_set(sc.frame_start)
    res = {}
    for o in objs:
        pa, pb = a[o.name][2], b[o.name][2]
        if len(pa) == len(pb):
            mv = max((x - y).length for x, y in zip(pa, pb))
        else:
            mv = ((a[o.name][0] + a[o.name][1]) / 2 - (b[o.name][0] + b[o.name][1]) / 2).length
        res[o.name] = round(mv, 4)
    moved = sum(1 for v in res.values() if v >= min_move)
    return moved == len(res), res, f"every object moves >= {min_move} m", ""


@bm_checks.register("no_explosion")
def _no_explosion(ctx, objects="GEO_", max_growth=3.0, floor_z=None, max_height=50.0):
    """Bounds stay finite, do not grow beyond ``max_growth`` x their start size, nothing falls
    through the floor or flies away."""
    sc = bpy.context.scene
    objs = bm_checks.select(objects)
    res, ok = {}, True
    start = _snap(objs, sc.frame_start)
    for f in sorted({(sc.frame_start + sc.frame_end) // 2, sc.frame_end}):
        snap = _snap(objs, f)
        for o in objs:
            lo0, hi0, _ = start[o.name]
            lo, hi, _p = snap[o.name]
            size0 = max((hi0 - lo0).length, 1e-3)
            growth = (hi - lo).length / size0
            finite = all(math.isfinite(c) for c in (*lo, *hi))
            below = floor_z is not None and lo.z < floor_z - 0.05
            far = max(abs(c) for c in (*lo, *hi)) > max_height
            bad = (not finite) or growth > max_growth or below or far
            if bad:
                res[f"{o.name}@{f}"] = {"growth": round(growth, 2), "below_floor": below, "far": far}
            ok = ok and not bad
    sc.frame_set(sc.frame_start)
    return ok and bool(objs), res or "ok", f"growth <= {max_growth}x, finite, above floor", ""


@bm_checks.register("sim_settled")
def _sim_settled(ctx, objects="GEO_", tail=3, max_speed=0.02):
    """Rigid bodies come to rest by the end (per-frame motion over the last frames)."""
    sc = bpy.context.scene
    objs = bm_checks.select(objects)
    e = sc.frame_end
    a, b = _snap(objs, e - tail), _snap(objs, e)
    sc.frame_set(sc.frame_start)
    res = {o.name: round((((a[o.name][0] + a[o.name][1]) - (b[o.name][0] + b[o.name][1])) / 2).length / tail, 4)
           for o in objs}
    bad = {k: v for k, v in res.items() if v > max_speed}
    return not bad, bad or "settled", f"speed <= {max_speed} m/frame at the end", ""


OPS = {"rigid_world": rigid_world, "rigid_body": rigid_body, "pin_group": pin_group, "cloth": cloth,
       "collision": collision, "soft_body": soft_body, "garment_from_body": garment_from_body,
       "particles": particles, "fluid": fluid, "bake": bake}
FIXES = {}
