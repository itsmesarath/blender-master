import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="rig_test", subskill="rigging-body")
    bm_scene.clear_scene()
    M, R = H.ops("modeling-topology"), H.ops("rigging-body")
    M.skin_figure(ctx, "GEO_char_body", height=1.8)
    H.data("armature", R.armature_from_joints(ctx, "GEO_char_body"))
    rig = bpy.data.objects["RIG_char"]
    H.expect("collections", {"DEF", "CTRL", "MCH"} <= {c.name for c in rig.data.collections})
    R.ik_limbs(ctx, "RIG_char")
    ok, v = H.check(ctx, "ik_rest_stable", rig="RIG_char")
    H.expect("ik_rest", ok, v)
    H.data("bind", R.bind(ctx, "GEO_char_body", "RIG_char"))
    ok, v = H.check(ctx, "weights_valid", objects=["GEO_char_body"])
    H.expect("weights", ok, v)
    ok, v = H.check(ctx, "pose_deform_ok", objects=["GEO_char_body"], rig="RIG_char")
    H.expect("pose", ok, v)
    # IK target moves the hand
    pb = rig.pose.bones["CTRL_ik_forearm_L"]
    w0 = (rig.matrix_world @ rig.pose.bones["forearm_L"].tail).copy()
    pb.location = (0, 0.15, 0.1)
    bpy.context.view_layer.update()
    w1 = rig.matrix_world @ rig.pose.bones["forearm_L"].tail
    H.expect("ik_follows", (w1 - w0).length > 0.05, (w1 - w0).length)
    pb.location = (0, 0, 0)
    # rigid attachment
    bm_mesh.sphere("GEO_char_hat", 0.12, 16, 8, location=(0, 0, 1.75))
    R.bind_extras(ctx, "RIG_char", ["GEO_char_hat"], bone="head")
    hat = bpy.data.objects["GEO_char_hat"]
    H.expect("hat_stays", abs(hat.matrix_world.translation.z - 1.75) < 1e-3, tuple(hat.matrix_world.translation))
    rig.pose.bones["head"].rotation_mode = "XYZ"
    rig.pose.bones["head"].rotation_euler = (0, 0.8, 0)  # twist about the bone axis = head turn
    bpy.context.view_layer.update()
    H.expect("hat_follows", abs(hat.matrix_world.translation.z - 1.75) < 0.05 and
             hat.matrix_world.to_euler().z > 0.5, tuple(hat.matrix_world.to_euler()))
    rig.pose.bones["head"].rotation_euler = (0, 0, 0)
    # distance fallback on a simple tube
    bm_mesh.cylinder("GEO_tube", 0.1, 1.0, 16, location=(2, 0, 0))
    H.expect("distance_bind", "distance" in R.bind(ctx, "GEO_tube", "RIG_char", method="distance"))
    ok, v = H.check(ctx, "weights_valid", objects=["GEO_tube"])
    H.expect("distance_weights_valid", ok, v)
    H.expect("rigify_metarig", "metarig" in R.rigify_metarig(ctx, "RIG_meta"))


H.run(body)
