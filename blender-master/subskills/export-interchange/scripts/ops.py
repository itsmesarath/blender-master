"""export-interchange ops: pre-export prep, preset exports, and a round-trip check that
re-imports each file in a separate clean Blender process and compares it to the source."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import bpy

import bm_checks
import bm_export
import bm_verify

HERE = os.path.dirname(os.path.abspath(__file__))


def prepare(ctx, objects="GEO_", apply_scale=True, apply_rotation=False, triangulate=False):
    """Apply scale (and optionally rotation) so engines read true sizes; optional Triangulate
    modifier (kept live; the exporter evaluates it) for engines that must match Blender's split."""
    objs = bm_checks.select(objects)
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(o in objs)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]
        if apply_scale or apply_rotation:
            bpy.ops.object.transform_apply(location=False, rotation=apply_rotation, scale=apply_scale)
    if triangulate:
        for o in objs:
            if not any(m.type == "TRIANGULATE" for m in o.modifiers):
                m = o.modifiers.new("EXPORT_tri", "TRIANGULATE")
                m.keep_custom_normals = True
    rep = bm_export.pre_export_report(objs)
    ctx.report.data["pre_export"] = rep
    return f"prepared {len(objs)} objects; issues: { {k: v for k, v in rep.items() if v} }"


def _with_rigs(objs):
    """Add the armatures that deform the chosen meshes, so a character exports with its rig."""
    out = list(objs)
    for o in objs:
        rigs = [m.object for m in o.modifiers if m.type == "ARMATURE" and m.object]
        if o.parent and o.parent.type == "ARMATURE":
            rigs.append(o.parent)
        for r in rigs:
            if r not in out:
                out.append(r)
    return out


def export(ctx, preset="ue5_fbx", objects="GEO_", filename=None, include_rigs=True, **overrides):
    objs = bm_checks.select(objects)
    if include_rigs:
        objs = _with_rigs(objs)
    scene = bpy.context.scene
    scene.frame_set(scene.frame_start)  # sizes compare in the rest/first-frame pose
    name = filename or f"{ctx.brief['project']}_{preset}"
    path = bm_export.export(preset, ctx.path("exports", name), objs, **overrides)
    src = bm_export.summary(objs)
    lo, hi = bm_verify.bounds_of(objs)
    src["size"] = [round(v, 4) for v in (hi - lo)]
    manifest = ctx.path("exports", "manifest.json")
    data = json.load(open(manifest)) if os.path.exists(manifest) else {}
    data[os.path.basename(path)] = {"preset": preset, "source": src}
    json.dump(data, open(manifest, "w"), indent=2)
    ctx.report.artefact(path, "export")
    return f"{preset} -> {os.path.basename(path)}"


def roundtrip(path, blender=None, timeout=300):
    """Import ``path`` into an empty factory scene in a fresh Blender and return its summary."""
    blender = blender or bpy.app.binary_path
    out = path + ".roundtrip.json"
    cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1", "--python",
           os.path.join(HERE, "roundtrip_check.py"), "--", path, out]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(f"round-trip import failed: {proc.stderr[-400:]}")
    return json.load(open(out))


@bm_checks.register("roundtrip_match")
def _roundtrip_match(ctx, size_tol=0.01):
    manifest = os.path.join(ctx.out_dir, "exports", "manifest.json")
    if not os.path.exists(manifest):
        return False, None, "manifest", "no exports recorded"
    data = json.load(open(manifest))
    res, ok = {}, True
    for fname, info in data.items():
        src = info["source"]
        got = roundtrip(os.path.join(ctx.out_dir, "exports", fname))
        problems = []
        if got["meshes"] < 1:
            problems.append("no meshes")
        if info["preset"] != "alembic" and got["materials"] < src["materials"]:
            problems.append(f"materials {got['materials']}<{src['materials']}")
        if got["armatures"] < src["armatures"]:
            problems.append("armature lost")
        if got["shape_keys"] < src["shape_keys"]:
            problems.append("shape keys lost")
        if src.get("animated") and not got.get("animated") and info["preset"] not in ("usd", "alembic"):
            # USD preset skips animation; Alembic carries it as a cache, not an action
            problems.append("animation lost")
        if any(abs(a - b) > size_tol * max(b, 1e-3) for a, b in zip(sorted(got["size"]), sorted(src["size"]))):
            problems.append(f"size {got['size']} vs {src['size']}")
        res[fname] = problems or "ok"
        ok = ok and not problems
    return ok, res, "every file re-imports with meshes, materials, rig, keys and size intact", ""


OPS = {"prepare": prepare, "export": export}
FIXES = {}
