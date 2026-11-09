"""Export presets and pre-export checks.

Engine targets are expressed as operator keyword sets. Engine-side import has to be verified in
the engine itself; the round-trip here only proves the file is complete from Blender's side.
"""
from __future__ import annotations

import os

import bpy

import bm_verify

PRESETS = {
    # Unreal: cm units are handled by the engine when the file is in metres with unit scale 1.
    "ue5_fbx": {"op": "fbx", "ext": ".fbx", "kw": dict(
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", axis_forward="-Y", axis_up="Z",
        add_leaf_bones=False, use_tspace=True, mesh_smooth_type="FACE", use_mesh_modifiers=True,
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, use_armature_deform_only=True,
        object_types={"MESH", "ARMATURE", "EMPTY"}, path_mode="COPY", embed_textures=False)},
    "unity_fbx": {"op": "fbx", "ext": ".fbx", "kw": dict(
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Z", axis_up="Y",
        bake_space_transform=True, add_leaf_bones=False, use_tspace=True, mesh_smooth_type="FACE",
        object_types={"MESH", "ARMATURE", "EMPTY"})},
    "godot_gltf": {"op": "gltf", "ext": ".glb", "kw": dict(
        export_format="GLB", export_yup=True, export_apply=True, export_tangents=True,
        export_animations=True)},
    "gltf_web": {"op": "gltf", "ext": ".glb", "kw": dict(
        export_format="GLB", export_yup=True, export_apply=True, export_animations=True,
        export_image_format="AUTO")},
    "usd": {"op": "usd", "ext": ".usdc", "kw": dict(
        export_materials=True, export_uvmaps=True, export_normals=True, generate_preview_surface=True,
        export_animation=False, relative_paths=True)},
    "alembic": {"op": "abc", "ext": ".abc", "kw": dict(
        uvs=True, normals=True, export_hair=True, apply_subdiv=False)},
}


def pre_export_report(objects) -> dict:
    """Problems that usually break engine imports."""
    issues = {"unapplied_scale": [], "negative_scale": [], "no_material": [], "ngons": [], "no_uv": []}
    for o in objects:
        if o.type != "MESH":
            continue
        if not bm_verify.scale_applied(o):
            issues["unapplied_scale"].append(o.name)
        if bm_verify.negative_scale(o):
            issues["negative_scale"].append(o.name)
        if not o.material_slots or any(s.material is None for s in o.material_slots):
            issues["no_material"].append(o.name)
        if bm_verify.face_stats(o)["ngons"]:
            issues["ngons"].append(o.name)
        if not o.data.uv_layers:
            issues["no_uv"].append(o.name)
    return issues


def _select_only(objects):
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    for o in objects:
        o.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def export(preset: str, path: str, objects=None, **overrides) -> str:
    p = PRESETS[preset]
    if not path.endswith(p["ext"]):
        path = os.path.splitext(path)[0] + p["ext"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    kw = dict(p["kw"], **overrides)
    if objects is not None:
        _select_only(list(objects))
    sel = objects is not None
    if p["op"] == "fbx":
        bpy.ops.export_scene.fbx(filepath=path, use_selection=sel, **kw)
    elif p["op"] == "gltf":
        bpy.ops.export_scene.gltf(filepath=path, use_selection=sel, **kw)
    elif p["op"] == "usd":
        bpy.ops.wm.usd_export(filepath=path, selected_objects_only=sel, **kw)
    elif p["op"] == "abc":
        bpy.ops.wm.alembic_export(filepath=path, selected=sel, **kw)
    return path


def import_file(path: str) -> list:
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".fbx":
        bpy.ops.wm.fbx_import(filepath=path)
    elif ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext in {".usd", ".usdc", ".usda"}:
        bpy.ops.wm.usd_import(filepath=path)
    elif ext == ".abc":
        bpy.ops.wm.alembic_import(filepath=path)
    else:
        raise ValueError(ext)
    return [o for o in bpy.data.objects if o not in before]


def summary(objects) -> dict:
    meshes = [o for o in objects if o.type == "MESH"]
    mats = {s.material.name.split(".")[0] for o in meshes for s in o.material_slots if s.material}
    return {
        "meshes": len(meshes),
        "polys": sum(len(o.data.polygons) for o in meshes),
        "materials": len(mats),
        "armatures": sum(1 for o in objects if o.type == "ARMATURE"),
        "shape_keys": sum(len(o.data.shape_keys.key_blocks) for o in meshes if o.data.shape_keys),
        "animated": sum(1 for o in objects if o.animation_data and o.animation_data.action),
    }
