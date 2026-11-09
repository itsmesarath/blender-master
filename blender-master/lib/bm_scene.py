"""Scene hygiene: collections, naming prefixes, units, idempotent creation, orphan purge."""
from __future__ import annotations

import re

import bpy

# Prefix -> collection. Keep in sync with references/naming-conventions.md
PREFIXES = {
    "PRX_": "BLOCKOUT",   # proxy / blockout geometry
    "GEO_": "GEO",        # final geometry
    "LGT_": "LIGHTS",
    "CAM_": "CAMERAS",
    "REF_": "REFS",
    "FX_": "FX",
    "CTRL_": "CONTROLS",
    "RIG_": "RIGS",
    "REV_": "REVIEW",
}
NAME_RE = re.compile(r"^(PRX|GEO|LGT|CAM|REF|FX|CTRL|RIG|REV)_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*(?:\.\d{3})?$")


def ensure_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if coll.name not in parent.children and coll != parent:
        try:
            parent.children.link(coll)
        except RuntimeError:
            pass
    return coll


def collection_for(name: str) -> bpy.types.Collection:
    for pre, coll in PREFIXES.items():
        if name.startswith(pre):
            return ensure_collection(coll)
    return ensure_collection("MISC")


def link_exclusive(obj: bpy.types.Object, coll: bpy.types.Collection | None = None) -> bpy.types.Object:
    """Link obj into exactly one collection (chosen by prefix when coll is None)."""
    coll = coll or collection_for(obj.name)
    for c in list(obj.users_collection):
        if c != coll:
            c.objects.unlink(obj)
    if obj.name not in coll.objects:
        coll.objects.link(obj)
    return obj


def get_or_create_object(name: str, data=None) -> tuple[bpy.types.Object, bool]:
    """Return (object, created). Re-running a step must not duplicate objects."""
    obj = bpy.data.objects.get(name)
    if obj is not None:
        return obj, False
    obj = bpy.data.objects.new(name, data)
    link_exclusive(obj)
    return obj, True


def remove_object(name: str) -> None:
    obj = bpy.data.objects.get(name)
    if obj is None:
        return
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and getattr(data, "users", 1) == 0:
        for coll in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.curves):
            if data.name in coll and coll[data.name] == data:
                coll.remove(data)
                break


def set_units(system: str = "METRIC", scale: float = 1.0, length: str = "METERS") -> None:
    us = bpy.context.scene.unit_settings
    us.system = system
    us.scale_length = scale
    us.length_unit = length


def clear_scene(keep_prefixes: tuple[str, ...] = ()) -> None:
    """Delete every object (except kept prefixes) and purge orphans. For fresh headless builds only."""
    for obj in list(bpy.data.objects):
        if keep_prefixes and obj.name.startswith(keep_prefixes):
            continue
        bpy.data.objects.remove(obj, do_unlink=True)
    purge_orphans()
    bpy.context.view_layer.update()   # drop stale entries from view_layer.objects


def purge_orphans(max_passes: int = 5) -> int:
    removed = 0
    for _ in range(max_passes):
        n = 0
        for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights,
                     bpy.data.curves, bpy.data.images, bpy.data.node_groups, bpy.data.actions,
                     bpy.data.grease_pencils):
            for block in list(coll):
                if block.users == 0 and not block.use_fake_user:
                    coll.remove(block)
                    n += 1
        removed += n
        if n == 0:
            break
    return removed


def bad_names(objects=None) -> list[str]:
    """Objects whose names do not follow PREFIX_Name."""
    objects = bpy.context.scene.objects if objects is None else objects
    return [o.name for o in objects if not NAME_RE.match(o.name)]


def objects_with_prefix(prefix: str, mesh_only: bool = False) -> list[bpy.types.Object]:
    out = [o for o in bpy.context.scene.objects if o.name.startswith(prefix)]
    return [o for o in out if o.type == "MESH"] if mesh_only else out


def set_note(obj: bpy.types.Object, note: str) -> None:
    """Pin a brief note to an object (custom property, survives save and export as extras)."""
    obj["brief_note"] = note
