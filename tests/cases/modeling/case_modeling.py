import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402

import bm_verify  # noqa: E402


def body():
    ctx = H.make_ctx(project="model_test", subskill="modeling-topology")
    import bm_scene
    bm_scene.clear_scene()
    M = H.ops("modeling-topology")

    # hard-surface crate: box -> panel inset with its own material index -> bevel stack
    M.box(ctx, "GEO_crate_body", (0.6, 0.6, 0.6))
    M.panel_inset(ctx, "GEO_crate_body", thickness=0.06, depth=0.03, inner_material_index=1)
    M.hs_bevel(ctx, "GEO_crate_body", width=0.006, segments=2)
    o = bpy.data.objects["GEO_crate_body"]
    H.expect("bevel_stack", [m.type for m in o.modifiers][:2] == ["BEVEL", "WEIGHTED_NORMAL"], [m.type for m in o.modifiers])
    H.expect("inner_material_index", any(p.material_index == 1 for p in o.data.polygons))
    ok, v = H.check(ctx, "bounds_size", objects="GEO_crate_body", target=[0.6, 0.6, 0.6], tol=0.01)
    H.expect("crate_size_kept", ok, v)
    ok, v = H.check(ctx, "no_ngons", objects="GEO_crate_body")
    H.expect("crate_no_ngons", ok, v)
    ok, v = H.check(ctx, "manifold", objects="GEO_crate_body")
    H.expect("crate_manifold", ok, v)

    # boolean cut leaves a closed mesh and writes a checkpoint first
    M.box(ctx, "GEO_block", (0.4, 0.4, 0.2), (1.5, 0, 0))
    M.boolean_cut(ctx, "GEO_block", "cylinder", (0.1, 0.1, 0.5), (1.5, 0, 0))
    blk = bpy.data.objects["GEO_block"]
    H.expect("boolean_applied", not blk.modifiers, [m.type for m in blk.modifiers])
    H.expect("boolean_hole", len(blk.data.polygons) > 6, len(blk.data.polygons))
    H.expect("boolean_manifold", bm_verify.manifold_report(blk)["non_manifold_edges"] == 0, bm_verify.manifold_report(blk))
    H.expect("checkpoint_written", os.path.isdir(os.path.join(H.OUT, "blend", "checkpoints"))
             and os.listdir(os.path.join(H.OUT, "blend", "checkpoints")))

    # lathe product
    M.lathe(ctx, "GEO_vase", [(0, 0), (0.05, 0), (0.08, 0.1), (0.04, 0.25), (0.05, 0.3), (0, 0.3)], location=(-1.5, 0, 0))
    ok, v = H.check(ctx, "on_ground", objects="GEO_vase")
    H.expect("lathe_on_ground", ok, v)

    # room shell with an opening + furniture
    M.room_shell(ctx, "GEO_room", 4.0, 3.5, 2.6, openings=[{"wall": "north", "width": 1.2, "height": 1.3, "sill": 0.9}])
    room = bpy.data.objects["GEO_room"]
    H.expect("room_manifold", bm_verify.manifold_report(room)["non_manifold_edges"] == 0, bm_verify.manifold_report(room))
    H.expect("room_normals_out", bm_verify.normals_outward(room))
    H.expect("room_opening_cut", len(room.data.polygons) > 12, len(room.data.polygons))
    for kind in ("bed", "desk", "chair", "shelf", "table", "rug"):
        M.furniture(ctx, kind, location=(0, 0, 0))
        f = bpy.data.objects["GEO_" + kind]
        lo, hi = bm_verify.world_bounds(f)
        H.expect(f"furniture_{kind}_grounded", abs(lo.z) < 1e-4, round(lo.z, 5), 0.0)
        H.expect(f"furniture_{kind}_spread", (hi - lo).x > 0.3, round((hi - lo).x, 3), "> 0.3 (parts not collapsed)")

    M.uv_quick(ctx, "GEO_crate_body")
    ok, v = H.check(ctx, "uv_present", objects="GEO_crate_body")
    H.expect("uv_quick", ok, v)

    # standalone topology report on a saved copy
    path = os.path.join(H.OUT, "model.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    script = os.path.join(H.SKILL, "subskills", "modeling-topology", "scripts", "topology_report.py")
    rep = os.path.join(H.OUT, "topology.json")
    proc = subprocess.run([bpy.app.binary_path, "-b", path, "--factory-startup", "--python-exit-code", "1",
                           "--python", script, "--", "--objects", "GEO_crate_body", "--out", rep],
                          capture_output=True, text=True, timeout=300)
    data = json.load(open(rep)) if os.path.exists(rep) else {}
    H.expect("topology_report", proc.returncode == 0 and "GEO_crate_body" in data, proc.stderr[-300:])
    if data:
        H.data("topology", data["GEO_crate_body"])


H.run(body)
