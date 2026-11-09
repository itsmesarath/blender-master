# Chunk templates

Each chunk: a `# SCOPE:` header, at most 60 lines, no shell/network/file deletion, and a final
`print(json.dumps(...))` so the result can be checked. Replace `<...>` values before sending.
All blocks below are linted by `scripts/lint_chunks.py` in CI.

## read_state
```python
# SCOPE: read-only
import bpy, json
sc = bpy.context.scene
objs = []
for o in sc.objects:
    objs.append({"name": o.name, "type": o.type, "dims": [round(v, 3) for v in o.dimensions],
                 "loc": [round(v, 3) for v in o.location], "hidden": o.hide_get()})
print(json.dumps({"blender": bpy.app.version_string, "file": bpy.data.filepath,
                  "dirty": bpy.data.is_dirty, "engine": sc.render.engine,
                  "frame": sc.frame_current, "objects": objs}))
```

## versioned_copy
```python
# SCOPE: file (save a numbered copy next to the current file; the original is not overwritten)
import bpy, json, os, re
src = bpy.data.filepath
folder = os.path.dirname(src) if src else bpy.app.tempdir
stem = re.sub(r"_v\d{3}$", "", os.path.splitext(os.path.basename(src))[0] or "untitled")
n = 1
while os.path.exists(os.path.join(folder, f"{stem}_v{n:03d}.blend")):
    n += 1
path = os.path.join(folder, f"{stem}_v{n:03d}.blend")
bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
print(json.dumps({"saved_copy": path}))
```

## create_box_at_size
```python
# SCOPE: GEO_<name>
import bpy, bmesh, json
name, size, loc = "GEO_<name>", (0.6, 0.6, 0.6), (0.0, 0.0, 0.0)
obj = bpy.data.objects.get(name)
if obj is None:
    obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.context.scene.collection.objects.link(obj)
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co.x *= size[0]; v.co.y *= size[1]; v.co.z = (v.co.z + 0.5) * size[2]
bm.to_mesh(obj.data); bm.free()
obj.location = loc
print(json.dumps({"object": name, "dims": [round(v, 3) for v in obj.dimensions]}))
```

## add_bevel_stack
```python
# SCOPE: GEO_<name> (modifiers only)
import bpy, json, math
obj = bpy.data.objects["GEO_<name>"]
bev = obj.modifiers.get("BEVEL") or obj.modifiers.new("BEVEL", "BEVEL")
bev.width, bev.segments, bev.limit_method = 0.006, 2, "ANGLE"
bev.angle_limit = math.radians(30)
bev.harden_normals = True
wn = obj.modifiers.get("WNORMAL") or obj.modifiers.new("WNORMAL", "WEIGHTED_NORMAL")
wn.keep_sharp = True
print(json.dumps({"object": obj.name, "modifiers": [m.type for m in obj.modifiers]}))
```

## material_preset
```python
# SCOPE: MAT_<name>, GEO_<name> (material slots)
import bpy, json
mat = bpy.data.materials.get("MAT_<name>") or bpy.data.materials.new("MAT_<name>")
bsdf = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
bsdf.inputs["Base Color"].default_value = (0.8, 0.1, 0.1, 1.0)
bsdf.inputs["Roughness"].default_value = 0.35
obj = bpy.data.objects["GEO_<name>"]
if mat.name not in [s.material.name for s in obj.material_slots if s.material]:
    obj.data.materials.append(mat)
print(json.dumps({"material": mat.name, "slots": len(obj.material_slots)}))
```

## area_key_light
```python
# SCOPE: LGT_key
import bpy, json
from mathutils import Vector
target, loc = Vector((0, 0, 0.3)), Vector((1.2, -1.2, 1.4))
obj = bpy.data.objects.get("LGT_key")
if obj is None:
    obj = bpy.data.objects.new("LGT_key", bpy.data.lights.new("LGT_key", "AREA"))
    bpy.context.scene.collection.objects.link(obj)
obj.data.energy, obj.data.size = 150.0, 1.0
obj.location = loc
obj.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
print(json.dumps({"light": obj.name, "energy": obj.data.energy}))
```

## verify_sizes
```python
# SCOPE: read-only
import bpy, json
expected = {"GEO_<name>": (0.6, 0.6, 0.6)}
tol = 0.05
rows = {}
for name, exp in expected.items():
    o = bpy.data.objects.get(name)
    if o is None:
        rows[name] = "missing"; continue
    got = [round(v, 4) for v in o.dimensions]
    ok = all(abs(g - e) <= tol * e for g, e in zip(got, exp))
    rows[name] = {"got": got, "pass": ok, "scale_applied": tuple(o.scale) == (1.0, 1.0, 1.0)}
print(json.dumps({"verify_sizes": rows}))
```

## viewport_screenshot
```python
# SCOPE: read-only (writes one PNG to the temp folder)
import bpy, json, os
path = os.path.join(bpy.app.tempdir, "live_view.png")
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
with bpy.context.temp_override(window=win, area=area):
    bpy.ops.screen.screenshot_area(filepath=path)
print(json.dumps({"screenshot": path}))
```
