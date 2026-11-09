import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import json  # noqa: E402

import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="face_test", subskill="rigging-face")
    bm_scene.clear_scene()
    M, F, R = H.ops("modeling-topology"), H.ops("rigging-face"), H.ops("rigging-body")
    M.skin_figure(ctx, "GEO_char_body", height=1.8, subdiv=2)
    o = bpy.data.objects["GEO_char_body"]
    J = json.loads(o["joints"])
    hx, hy, hz = J["head"]
    front = hy - 0.1
    F.region_key(ctx, "GEO_char_body", "jaw_open", (0, front, hz - 0.03), 0.07,
                 rotate=("X", 18, (0, hy, hz + 0.01)), below=hz + 0.0)
    F.region_key(ctx, "GEO_char_body", "smile", (0.035, front, hz), 0.03, offset=(0.006, 0.0, 0.006), mirror=True)
    F.split_lr(ctx, "GEO_char_body", "smile")
    F.region_key(ctx, "GEO_char_body", "brow_up", (0.03, front, hz + 0.05), 0.03, offset=(0, 0, 0.008), mirror=True)
    ok, v = H.check(ctx, "shape_keys_valid", objects=["GEO_char_body"], min_keys=4)
    H.expect("keys_valid", ok, v)
    kb = o.data.shape_keys.key_blocks
    dl = max(abs(a.co.x - b.co.x) for a, b in zip(kb["smile_L"].data, kb["Basis"].data) if a.co.x < -0.01)
    H.expect("split_left_only", dl < 1e-6, dl)
    F.face_control(ctx, "jaw", (0, front - 0.05, hz - 0.06))
    F.face_control(ctx, "mouth_L", (0.05, front - 0.05, hz))
    F.drive(ctx, "GEO_char_body", "jaw_open", "CTRL_jaw", channel="LOC_Z", full=-0.02)
    F.drive(ctx, "GEO_char_body", "smile_L", "CTRL_mouth_L", channel="LOC_Z", full=0.015)
    F.combo_key(ctx, "GEO_char_body", "jaw_smile_fix", ["jaw_open", "smile_L"], center=(0.035, front, hz - 0.01),
                radius=0.02, inflate=0.003)
    ok, v = H.check(ctx, "drivers_resolve", objects=["GEO_char_body"])
    H.expect("drivers", ok, v)
    ctl = bpy.data.objects["CTRL_jaw"]
    ctl.location.z -= 0.01
    bpy.context.view_layer.update()
    H.expect("half_open", abs(kb["jaw_open"].value - 0.5) < 0.05, kb["jaw_open"].value)
    ctl.location.z -= 0.05
    bpy.context.view_layer.update()
    H.expect("clamped", abs(kb["jaw_open"].value - 1.0) < 1e-4, kb["jaw_open"].value)
    bpy.data.objects["CTRL_mouth_L"].location.z += 0.02
    bpy.context.view_layer.update()
    H.expect("combo_on", kb["jaw_smile_fix"].value > 0.99, kb["jaw_smile_fix"].value)
    # face controls follow the head after body rigging
    R.armature_from_joints(ctx, "GEO_char_body")
    R.bind(ctx, "GEO_char_body", "RIG_char")
    R.bind_extras(ctx, "RIG_char", ["CTRL_jaw", "CTRL_mouth_L"], bone="head")
    ok, v = H.check(ctx, "drivers_resolve", objects=["GEO_char_body"])
    H.expect("drivers_after_parenting", ok, v)
    dg = bpy.context.evaluated_depsgraph_get()
    H.expect("keys_survive_armature", len(o.evaluated_get(dg).data.vertices) == len(o.data.vertices))


H.run(body)
