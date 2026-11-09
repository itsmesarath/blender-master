# Scripting guide (Blender 5.2)

## Data API first
| Task | Data API | Avoid |
|---|---|---|
| create a mesh | `bpy.data.meshes.new` + `from_pydata` or `bmesh` | `bpy.ops.mesh.primitive_*` in loops |
| link to a collection | `collection.objects.link(obj)` | relying on the active collection |
| set a transform | `obj.location = ...`, `obj.matrix_world = ...` | `bpy.ops.transform.*` |
| add a modifier | `obj.modifiers.new(name, type)` | `bpy.ops.object.modifier_add` |
| material slot | `obj.data.materials.append(mat)` | `bpy.ops.object.material_slot_add` |
| delete | `bpy.data.objects.remove(obj, do_unlink=True)` | `bpy.ops.object.delete` |
| keyframe | `obj.keyframe_insert(path, frame=...)` or channelbag F-curves | timeline operators |

## When an operator is needed
```python
with bpy.context.temp_override(active_object=obj, selected_objects=[obj], object=obj):
    bpy.ops.object.modifier_apply(modifier="Bevel")
```
- Check `bpy.ops.x.y.poll()` first; a failed poll means the context is wrong.
- Edit-mode operators need an Edit-mode object; prefer `bmesh` on `obj.data` in Object mode.

## Idempotency
```python
def get_or_create_mesh_object(name, coll):
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
        coll.objects.link(obj)
    return obj
```
Generated sets (scatter, arrays): delete everything with the generator's prefix, then rebuild.

## Arguments and exit codes
```python
import sys
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
```
Run with `--python-exit-code 1` so an uncaught exception fails the process.

## Performance
- Batch vertex data with `foreach_set` / `foreach_get` and numpy instead of per-vertex Python.
- Disable undo for big batch jobs in the UI (`bpy.context.preferences.edit.use_global_undo`),
  and restore it after.
- Avoid `bpy.context.view_layer.update()` inside loops; call it once when you need fresh matrices.

## Custom operators (UI tools)
```python
class OBJECT_OT_make_crate(bpy.types.Operator):
    bl_idname = "object.make_crate"
    bl_label = "Make Crate"
    bl_options = {"REGISTER", "UNDO"}
    size: bpy.props.FloatProperty(default=0.6, min=0.05)

    def execute(self, context):
        build_crate(self.size)          # pure function, testable headless
        return {"FINISHED"}
```
Keep the logic in plain functions so headless tests do not need the operator.

## Extensions (packaged add-ons)
- Since 4.2 add-ons are distributed as extensions with a `blender_manifest.toml`
  (id, version, name, maintainer, type "add-on", blender_version_min, license).
- Extensions must be GPL-compatible (GPL-3.0-or-later is the standard licence on the platform).
- Wheels must match the bundled Python (3.13 for 5.x) and every target platform.
- Build: `blender --command extension build`; validate with `blender --command extension validate`.
- Only package or install with the user's explicit approval.

## Debugging checklist
1. Read the full traceback; the last `bpy` line names the property or operator.
2. Check [../../../references/blender-5.2-api-notes.md](../../../references/blender-5.2-api-notes.md).
3. Print `obj.bl_rna.properties.keys()` or `node.inputs.keys()` to discover 5.x names.
4. Reduce to the smallest failing snippet and run it headless.
