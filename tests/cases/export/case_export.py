import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import json  # noqa: E402

import bm_checks  # noqa: E402
import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="exp_test", subskill="export-interchange")
    bm_scene.clear_scene()
    S = H.ops("materials-shading")
    M = H.ops("modeling-topology")
    E = H.ops("export-interchange")
    M.box(ctx, "GEO_prop_body", (0.6, 0.4, 0.3))
    M.panel_inset(ctx, "GEO_prop_body", thickness=0.04, depth=0.02, inner_material_index=1)
    M.cylinder(ctx, "GEO_prop_knob", 0.05, 0.08, 16, (0, 0, 0.3))
    S.material(ctx, "paint", "metal_painted")
    S.material(ctx, "panel", "plastic_matte")
    S.material(ctx, "knob", "rubber")
    S.assign(ctx, "paint", "GEO_prop_body")
    S.assign(ctx, "panel", "GEO_prop_body", replace=False)
    S.assign(ctx, "knob", "GEO_prop_knob")
    M.uv_quick(ctx, "GEO_prop_")
    # animate the knob so the round-trip has an action to keep
    knob = bpy.data.objects["GEO_prop_knob"]
    knob.keyframe_insert("rotation_euler", index=2, frame=1)
    knob.rotation_euler.z = 1.0
    knob.keyframe_insert("rotation_euler", index=2, frame=24)
    bpy.data.objects["GEO_prop_body"].scale = (1.0, 1.0, 1.0)

    E.prepare(ctx, "GEO_prop_")
    pre = ctx.report.data["pre_export"]
    H.expect("pre_export_clean", not any(pre[k] for k in ("unapplied_scale", "negative_scale", "no_material", "no_uv")), pre)
    H.expect("pre_export_flags_cylinder_caps", pre["ngons"] == ["GEO_prop_knob"], pre["ngons"])
    for preset in ("ue5_fbx", "unity_fbx", "godot_gltf", "gltf_web", "usd", "alembic"):
        E.export(ctx, preset, "GEO_prop_")
    files = sorted(os.listdir(os.path.join(H.OUT, "exports")))
    H.data("files", files)
    H.expect("six_exports", len([f for f in files if "." in f and not f.endswith(".json")]) == 6, files)
    ok, v, exp, det = bm_checks.run(ctx, {"check": "roundtrip_match"})
    H.expect("roundtrip_match", ok, v)

    # a broken export is caught: drop a material from the manifest's file by rewriting it smaller
    man = os.path.join(H.OUT, "exports", "manifest.json")
    data = json.load(open(man))
    name = next(k for k, v in data.items() if v["preset"] == "gltf_web")
    data[name]["source"]["materials"] += 2       # pretend the source had more materials
    json.dump({name: data[name]}, open(man, "w"))
    ok, v, exp, det = bm_checks.run(ctx, {"check": "roundtrip_match"})
    H.expect("roundtrip_detects_loss", not ok, v)


H.run(body)
