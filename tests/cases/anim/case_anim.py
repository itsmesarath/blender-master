import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import json  # noqa: E402

import bm_mesh  # noqa: E402
from mathutils import Vector  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="anim_test", subskill="animation")
    bm_scene.clear_scene()
    M, R, F, A = H.ops("modeling-topology"), H.ops("rigging-body"), H.ops("rigging-face"), H.ops("animation")
    A.frame_range(ctx, 1, 48, 24)
    M.skin_figure(ctx, "GEO_char_body", height=1.8)
    J = json.loads(bpy.data.objects["GEO_char_body"]["joints"])
    R.armature_from_joints(ctx, "GEO_char_body")
    R.bind(ctx, "GEO_char_body", "RIG_char")
    A.wave(ctx, "RIG_char", "rotation_euler", index=0, amplitude=4, period=48, bone="spine", degrees=True)
    A.pose_keys(ctx, "RIG_char", {1: {"upper_arm_R": [0, 0, 0]}, 12: {"upper_arm_R": [0, 0, -70]},
                                  24: {"upper_arm_R": [0, 0, -70]}, 36: {"upper_arm_R": [0, 0, 0]},
                                  49: {"upper_arm_R": [0, 0, 0]}})
    A.wave(ctx, "RIG_char", "rotation_euler", index=2, amplitude=25, period=12, start=12, cycles=1,
           bone="forearm_R", degrees=True)
    ok, v = H.check(ctx, "anim_present", objects=["RIG_char"], min_curves=3)
    H.expect("present", ok, v)
    ok, v = H.check(ctx, "loop_ok", objects=["RIG_char"])
    H.expect("loops", ok, v)
    ok, v = H.check(ctx, "no_pops", objects=["RIG_char"])
    H.expect("smooth", ok, v)
    # a pop is detected
    bm_mesh.box("GEO_ball", (0.2, 0.2, 0.2), (2, 0, 0))
    A.keyframes(ctx, "GEO_ball", "location", [[1, [2, 0, 0]], [24, [2, 0, 1]], [25, [2, 0, 4]], [48, [2, 0, 4.2]]],
                interpolation="LINEAR")
    ok, v = H.check(ctx, "no_pops", objects=["GEO_ball"])
    H.expect("pop_detected", not ok, v)
    ok, _ = H.check(ctx, "loop_ok", objects=["GEO_ball"])
    H.expect("non_loop_detected", not ok)
    # follow path + nla
    bm_mesh.box("GEO_car", (0.4, 0.8, 0.3))
    A.follow_path(ctx, "GEO_car", [(0, 0, 0), (3, 2, 0), (6, 0, 0), (9, -2, 0)], frames=(1, 48))
    bpy.context.scene.frame_set(48)
    end = bpy.data.objects["GEO_car"].matrix_world.translation
    H.expect("path_end", (end - Vector((9, -2, 0))).length < 0.05, tuple(end))
    bpy.context.scene.frame_set(1)
    H.expect("nla", "NLA" in A.nla_push(ctx, "GEO_ball"))
    # driven face key baked for export
    F.region_key(ctx, "GEO_char_body", "jaw_open", (0, J["head"][1] - 0.1, J["head"][2] - 0.03), 0.06,
                 offset=(0, 0, -0.01))
    F.face_control(ctx, "jaw", (0, -0.3, J["head"][2] - 0.06))
    F.drive(ctx, "GEO_char_body", "jaw_open", "CTRL_jaw", full=-0.02)
    A.keyframes(ctx, "CTRL_jaw", "location", [[1, J["head"][2] - 0.06], [12, J["head"][2] - 0.08], [24, J["head"][2] - 0.06]],
                index=2)
    A.bake_shape_keys(ctx, "GEO_char_body", remove_drivers=True)
    sk = bpy.data.objects["GEO_char_body"].data.shape_keys
    import bm_anim
    vals = [fc.evaluate(12) for fc in bm_anim.fcurves(sk)]
    H.expect("baked_keys", vals and abs(vals[0] - 1.0) < 1e-3, vals)


H.run(body)
