"""geometry-nodes ops: procedural node groups built from Python with exposed inputs - surface
scatter, instance rows, building blocks with per-instance attributes, facades - plus input
setting through the 5.2 ``mod.properties.inputs`` API and evaluation checks."""
from __future__ import annotations

import math

import bpy

import bm_checks
import bm_gn
import bm_scene


# ------------------------------------------------------------------ node helpers
class Tree:
    """Small builder: interface sockets, nodes, links. Socket refs are (node, name or index)."""

    def __init__(self, name, inputs=()):
        old = bpy.data.node_groups.get(name)
        if old is not None:
            bpy.data.node_groups.remove(old)
        self.ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
        self.ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        self.ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        for sname, stype, default, lo, hi in inputs:
            s = self.ng.interface.new_socket(sname, in_out="INPUT", socket_type=stype)
            if default is not None:
                s.default_value = default
            if lo is not None:
                s.min_value = lo
            if hi is not None:
                s.max_value = hi
        self.gin = self.node("NodeGroupInput", (-800, 0))
        self.gout = self.node("NodeGroupOutput", (800, 0))

    def node(self, idname, loc=(0, 0), **props):
        n = self.ng.nodes.new(idname)
        n.location = loc
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, a_sock, b, b_sock):
        out = a.outputs[a_sock]
        inp = b.inputs[b_sock]
        self.ng.links.new(out, inp)

    def value(self, node, sock, v):
        node.inputs[sock].default_value = v


def _host(name):
    """Empty mesh object that carries the node modifier."""
    if not name.startswith("GEO_"):
        name = "GEO_" + name
    bm_scene.remove_object(name)
    obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bm_scene.link_exclusive(obj)
    return obj


def _attach(obj, tree):
    mod = obj.modifiers.new("GN", "NODES")
    mod.node_group = tree.ng
    return mod


def _source(name):
    """Hide an object used only as instance source or surface reference from renders."""
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    o["gn_source"] = True
    return o


def _random(t, loc, lo, hi, seed_link=None, dtype="FLOAT", seed=0):
    r = t.node("FunctionNodeRandomValue", loc, data_type=dtype)
    socks = [s for s in r.inputs if s.enabled]
    named = {s.name: s for s in socks}
    named["Min"].default_value = lo
    named["Max"].default_value = hi
    named["Seed"].default_value = seed
    if seed_link is not None:
        t.ng.links.new(seed_link, named["Seed"])
    out = next(s for s in r.outputs if s.enabled)
    return r, named, out


# ------------------------------------------------------------------ ops
def scatter(ctx, name, surface, instance, density=10.0, seed=0, scale_min=0.8, scale_max=1.2,
            random_rotation=True, hide_sources=True):
    """Scatter ``instance`` over ``surface`` (points per square metre). Exposed inputs: Density,
    Seed, Scale Min, Scale Max."""
    surf, inst = _source(surface), _source(instance)
    t = Tree(f"GN_{name}_scatter", [("Density", "NodeSocketFloat", float(density), 0.0, 10000.0),
                                     ("Seed", "NodeSocketInt", int(seed), None, None),
                                     ("Scale Min", "NodeSocketFloat", float(scale_min), 0.0, None),
                                     ("Scale Max", "NodeSocketFloat", float(scale_max), 0.0, None)])
    si = t.node("GeometryNodeObjectInfo", (-600, 200), transform_space="RELATIVE")
    si.inputs["Object"].default_value = surf
    ii = t.node("GeometryNodeObjectInfo", (-600, -200), transform_space="ORIGINAL")
    ii.inputs["Object"].default_value = inst
    dist = t.node("GeometryNodeDistributePointsOnFaces", (-300, 200))
    t.link(si, "Geometry", dist, "Mesh")
    t.link(t.gin, "Density", dist, "Density")
    t.link(t.gin, "Seed", dist, "Seed")
    iop = t.node("GeometryNodeInstanceOnPoints", (100, 100))
    t.link(dist, "Points", iop, "Points")
    t.link(ii, "Geometry", iop, "Instance")
    r, named, out = _random(t, (-150, -150), 0.8, 1.2, seed_link=t.gin.outputs["Seed"])
    t.ng.links.new(t.gin.outputs["Scale Min"], named["Min"])
    t.ng.links.new(t.gin.outputs["Scale Max"], named["Max"])
    t.ng.links.new(out, iop.inputs["Scale"])
    if random_rotation:
        rz, nz, oz = _random(t, (-150, -400), 0.0, 2 * math.pi, seed_link=None, seed=int(seed) + 7)
        comb = t.node("ShaderNodeCombineXYZ", (0, -400))
        t.ng.links.new(oz, comb.inputs["Z"])
        e2r = t.node("FunctionNodeEulerToRotation", (100, -400))
        t.link(comb, "Vector", e2r, "Euler")
        t.link(e2r, "Rotation", iop, "Rotation")
    t.link(iop, "Instances", t.gout, "Geometry")
    host = _host(name)
    _attach(host, t)
    if hide_sources:
        inst.hide_render = True
        inst.hide_viewport = True
    return f"{host.name}: scatter {instance} on {surface} density={density}"


def instance_row(ctx, name, instance, count=8, spacing=4.0, start=(0, 0, 0), direction=(1, 0, 0), hide_sources=True):
    """A straight row of instances (street lamps, posts, columns). Exposed: Count, Spacing."""
    inst = _source(instance)
    t = Tree(f"GN_{name}_row", [("Count", "NodeSocketInt", int(count), 1, 10000),
                                 ("Spacing", "NodeSocketFloat", float(spacing), 0.0, None)])
    line = t.node("GeometryNodeMeshLine", (-500, 100))
    line.inputs["Start Location"].default_value = start
    t.link(t.gin, "Count", line, "Count")
    vm = t.node("ShaderNodeVectorMath", (-700, -100), operation="SCALE")
    vm.inputs[0].default_value = direction
    t.ng.links.new(t.gin.outputs["Spacing"], vm.inputs["Scale"])
    t.link(vm, "Vector", line, "Offset")
    ii = t.node("GeometryNodeObjectInfo", (-500, -200), transform_space="ORIGINAL")
    ii.inputs["Object"].default_value = inst
    iop = t.node("GeometryNodeInstanceOnPoints", (0, 0))
    t.link(line, "Mesh", iop, "Points")
    t.link(ii, "Geometry", iop, "Instance")
    t.link(iop, "Instances", t.gout, "Geometry")
    host = _host(name)
    _attach(host, t)
    if hide_sources:
        inst.hide_render = True
        inst.hide_viewport = True
    return f"{host.name}: row of {count} x {instance}"


def building_block(ctx, name, rows=4, cols=4, lot=8.0, gap=4.0, height_min=6.0, height_max=30.0, seed=1,
                   realize=True):
    """Grid of box buildings with random heights. Each building stores a 0-1 ``height_factor``
    named attribute for shaders (Attribute node, name height_factor). Exposed: Rows, Columns,
    Height Min, Height Max, Seed."""
    t = Tree(f"GN_{name}_block", [("Rows", "NodeSocketInt", int(rows), 1, 200),
                                   ("Columns", "NodeSocketInt", int(cols), 1, 200),
                                   ("Height Min", "NodeSocketFloat", float(height_min), 0.1, None),
                                   ("Height Max", "NodeSocketFloat", float(height_max), 0.1, None),
                                   ("Seed", "NodeSocketInt", int(seed), None, None)])
    step = lot + gap
    grid = t.node("GeometryNodeMeshGrid", (-500, 200))
    # grid size = (n-1) * step so points sit on lot centres
    for axis, sock in (("Columns", "Size X"), ("Rows", "Size Y")):
        sub = t.node("ShaderNodeMath", (-700, 200), operation="SUBTRACT")
        t.ng.links.new(t.gin.outputs[axis], sub.inputs[0])
        sub.inputs[1].default_value = 1.0
        mul = t.node("ShaderNodeMath", (-600, 200), operation="MULTIPLY")
        t.link(sub, 0, mul, 0)
        mul.inputs[1].default_value = step
        t.link(mul, 0, grid, sock)
    t.link(t.gin, "Columns", grid, "Vertices X")
    t.link(t.gin, "Rows", grid, "Vertices Y")
    pts = t.node("GeometryNodeMeshToPoints", (-300, 200))
    t.link(grid, "Mesh", pts, "Mesh")
    cube = t.node("GeometryNodeMeshCube", (-500, -200))
    cube.inputs["Size"].default_value = (lot, lot, 1.0)
    lift = t.node("GeometryNodeTransform", (-300, -200))
    lift.inputs["Translation"].default_value = (0, 0, 0.5)     # base at z = 0
    t.link(cube, "Mesh", lift, "Geometry")
    iop = t.node("GeometryNodeInstanceOnPoints", (0, 100))
    t.link(pts, "Points", iop, "Points")
    t.link(lift, "Geometry", iop, "Instance")
    fac_r, fac_named, fac = _random(t, (-300, -450), 0.0, 1.0, seed_link=t.gin.outputs["Seed"])
    # height = min + fac * (max - min)
    rng = t.node("ShaderNodeMath", (-150, -550), operation="SUBTRACT")
    t.ng.links.new(t.gin.outputs["Height Max"], rng.inputs[0])
    t.ng.links.new(t.gin.outputs["Height Min"], rng.inputs[1])
    ma = t.node("ShaderNodeMath", (0, -500), operation="MULTIPLY_ADD")
    t.ng.links.new(fac, ma.inputs[0])
    t.link(rng, 0, ma, 1)
    t.ng.links.new(t.gin.outputs["Height Min"], ma.inputs[2])
    comb = t.node("ShaderNodeCombineXYZ", (150, -500))
    comb.inputs["X"].default_value = 1.0
    comb.inputs["Y"].default_value = 1.0
    t.link(ma, 0, comb, "Z")
    t.link(comb, "Vector", iop, "Scale")
    store = t.node("GeometryNodeStoreNamedAttribute", (300, 100), data_type="FLOAT", domain="INSTANCE")
    store.inputs["Name"].default_value = "height_factor"
    t.link(iop, "Instances", store, "Geometry")
    t.ng.links.new(fac, store.inputs["Value"])
    last = store
    if realize:
        real = t.node("GeometryNodeRealizeInstances", (500, 100))
        t.link(store, "Geometry", real, "Geometry")
        last = real
    t.link(last, 0, t.gout, "Geometry")
    host = _host(name)
    _attach(host, t)
    return f"{host.name}: {rows}x{cols} buildings {height_min}-{height_max} m"


def facade(ctx, name, window, width=12.0, height=15.0, floors=5, bays=4, depth=0.3, hide_sources=True):
    """Flat facade wall (facing -Y) with ``window`` instanced on a floors x bays grid. Exposed:
    Floors, Bays."""
    win = _source(window)
    t = Tree(f"GN_{name}_facade", [("Floors", "NodeSocketInt", int(floors), 1, 200),
                                    ("Bays", "NodeSocketInt", int(bays), 1, 200)])
    wall = t.node("GeometryNodeMeshCube", (-400, 300))
    wall.inputs["Size"].default_value = (width, depth, height)
    wall_t = t.node("GeometryNodeTransform", (-200, 300))
    wall_t.inputs["Translation"].default_value = (0, 0, height / 2)
    t.link(wall, "Mesh", wall_t, "Geometry")
    grid = t.node("GeometryNodeMeshGrid", (-400, 0))
    grid.inputs["Size X"].default_value = width * (1 - 1.0 / max(bays, 1))
    grid.inputs["Size Y"].default_value = height * (1 - 1.0 / max(floors, 1))
    t.link(t.gin, "Bays", grid, "Vertices X")
    t.link(t.gin, "Floors", grid, "Vertices Y")
    stand = t.node("GeometryNodeTransform", (-200, 0))
    stand.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    stand.inputs["Translation"].default_value = (0, -depth / 2, height / 2)
    t.link(grid, "Mesh", stand, "Geometry")
    pts = t.node("GeometryNodeMeshToPoints", (0, 0))
    t.link(stand, "Geometry", pts, "Mesh")
    ii = t.node("GeometryNodeObjectInfo", (0, -250), transform_space="ORIGINAL")
    ii.inputs["Object"].default_value = win
    iop = t.node("GeometryNodeInstanceOnPoints", (200, 0))
    t.link(pts, "Points", iop, "Points")
    t.link(ii, "Geometry", iop, "Instance")
    join = t.node("GeometryNodeJoinGeometry", (500, 100))
    t.link(iop, "Instances", join, "Geometry")
    t.link(wall_t, "Geometry", join, "Geometry")
    t.link(join, "Geometry", t.gout, "Geometry")
    host = _host(name)
    _attach(host, t)
    if hide_sources:
        win.hide_render = True
        win.hide_viewport = True
    return f"{host.name}: facade {floors} floors x {bays} bays"


def set_param(ctx, target, name, value):
    """Set an exposed input by its display name on the target's node modifier."""
    obj = bpy.data.objects[target]
    mod = next(m for m in obj.modifiers if m.type == "NODES")
    bm_gn.set_input(mod, name, value)
    obj.update_tag()
    return f"{target}.{name} = {value}"


def apply_nodes(ctx, target):
    """Bake the node result into real mesh data (for export or hand editing). Irreversible on this
    object: a checkpoint should exist."""
    import bm_io
    obj = bpy.data.objects[target]
    bm_io.checkpoint(ctx.path("blend", "checkpoints"), f"{ctx.part_id}_apply_{target}")
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = obj.data
    obj.modifiers.clear()
    obj.data = mesh
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return f"{target}: applied ({len(mesh.vertices)} verts)"


OPS = {"scatter": scatter, "instance_row": instance_row, "building_block": building_block, "facade": facade,
       "set_param": set_param, "apply_nodes": apply_nodes}
FIXES = {}


# ------------------------------------------------------------------ checks
def evaluated_stats(obj):
    """(vertex count of evaluated mesh incl. realized geometry, instance count)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    verts = len(ev.data.vertices) if ev.type == "MESH" and ev.data else 0
    inst = sum(1 for i in dg.object_instances if i.is_instance and i.parent and i.parent.original == obj)
    return verts, inst


def fingerprint(obj):
    """Counts plus position sums: changes when layout changes even if counts do not."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    vsum = 0.0
    if ev.type == "MESH" and ev.data:
        vsum = sum(v.co.x + 2 * v.co.y + 3 * v.co.z for v in ev.data.vertices)
    isum = sum(i.matrix_world.translation.x + 2 * i.matrix_world.translation.y for i in dg.object_instances
               if i.is_instance and i.parent and i.parent.original == obj)
    v, n = evaluated_stats(obj)
    return [v, n, round(vsum, 3), round(isum, 3)]


@bm_checks.register("gn_evaluates")
def _gn_evaluates(ctx, objects="GEO_"):
    objs = [o for o in bm_checks.select(objects, mesh_only=False) if any(m.type == "NODES" for m in o.modifiers)]
    res = {o.name: evaluated_stats(o) for o in objs}
    empty = [n for n, (v, i) in res.items() if v == 0 and i == 0]
    return bool(objs) and not empty, res, "every node object yields geometry", f"empty: {empty}" if empty else ""


@bm_checks.register("gn_instances")
def _gn_instances(ctx, target, min_count=1, max_count=10 ** 7):
    v, i = evaluated_stats(bpy.data.objects[target])
    return min_count <= i <= max_count, i, [min_count, max_count], ""


@bm_checks.register("gn_input_changes")
def _gn_input_changes(ctx, target, input, value):
    """Changing an exposed input changes the result (and the old value is restored)."""
    obj = bpy.data.objects[target]
    mod = next(m for m in obj.modifiers if m.type == "NODES")
    before = fingerprint(obj)
    old = bm_gn.get_input(mod, input)
    bm_gn.set_input(mod, input, value)
    obj.update_tag()
    after = fingerprint(obj)
    bm_gn.set_input(mod, input, old)
    obj.update_tag()
    return before != after, {"before": before, "after": after}, "result changes", input
