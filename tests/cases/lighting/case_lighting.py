import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import math  # noqa: E402

import bm_checks  # noqa: E402
import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402


def scene(ctx):
    bm_scene.clear_scene()
    bm_mesh.box("GEO_floor", (4, 4, 0.02), (0, 0, -0.02))
    bm_mesh.sphere("GEO_ball", 0.25, 32, 16, (0, 0, 0))
    S = H.ops("materials-shading")
    S.material(ctx, "clay", "clay")
    S.assign(ctx, "clay", "GEO_")


def body():
    ctx = H.make_ctx(project="light_test", facts={"hero_camera": "CAM_hero"}, subskill="lighting-cameras")
    L = H.ops("lighting-cameras")
    scene(ctx)
    L.camera(ctx, "CAM_hero", 50, "three_quarter", objects="GEO_ball", fill=0.75)
    L.world(ctx, "studio", strength=0.3)
    L.three_point(ctx, objects="GEO_ball", camera="CAM_hero")
    ok, v = H.check(ctx, "lights_exist", min_count=3)
    H.expect("three_lights", ok, v)
    ok, v = H.check(ctx, "camera_frames", camera="CAM_hero", objects="GEO_ball")
    H.expect("framed", ok, v)
    ok, v = H.check(ctx, "exposure", camera="CAM_hero", res=[160, 90], samples=8)
    H.expect("exposure_ok", ok, v)
    H.data("exposure", v)

    # overexpose, the fixer must bring it back within range in <= 3 rounds
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.data.energy *= 40
    ok, v = H.check(ctx, "exposure", camera="CAM_hero", res=[160, 90], samples=8)
    H.expect("overexposure_detected", not ok, v)
    fixed = False
    for attempt in range(1, 4):
        ctx.attempt = attempt
        L.FIXES["exposure"](ctx, {"camera": "CAM_hero", "res": [160, 90], "samples": 8}, attempt)
        ok, v = H.check(ctx, "exposure", camera="CAM_hero", res=[160, 90], samples=8)
        if ok:
            fixed = True
            break
    H.expect("exposure_fixed", fixed, v)

    # autofit camera too close -> dolly fix; hand-placed camera -> SKIP
    cam = bpy.data.objects["CAM_hero"]
    cam.location = cam.location * 0.15
    ok, v = H.check(ctx, "camera_frames", camera="CAM_hero", objects="GEO_ball")
    H.expect("too_close_detected", not ok, v)
    msg = L.FIXES["camera_frames"](ctx, {"camera": "CAM_hero", "objects": "GEO_ball"}, 1)
    ok, v = H.check(ctx, "camera_frames", camera="CAM_hero", objects="GEO_ball")
    H.expect("dolly_fix", ok, [msg, v])
    L.camera(ctx, "CAM_hand", 50, location=(0.2, -0.3, 0.1), target=(0, 0, 0.25))
    msg = L.FIXES["camera_frames"](ctx, {"camera": "CAM_hand", "objects": "GEO_ball"}, 1)
    H.expect("hand_camera_respected", str(msg).startswith("SKIP"), msg)

    # turntable is a seamless loop
    L.turntable(ctx, "CAM_hero", "GEO_ball", frames=24)
    import bm_anim
    piv = bpy.data.objects["CTRL_orbit"]
    a0 = bm_anim.value_at(piv, "rotation_euler", 2, 1)
    a24 = bm_anim.value_at(piv, "rotation_euler", 2, 25)
    H.expect("turntable_full_turn", abs(a24 - a0 - 2 * math.pi) < 1e-4, a24 - a0, 2 * math.pi)
    sc = bpy.context.scene
    H.expect("turntable_range", (sc.frame_start, sc.frame_end) == (1, 24), [sc.frame_start, sc.frame_end])
    L.depth_of_field(ctx, "CAM_hero", "GEO_ball", 2.8)
    H.expect("dof_focus_empty", cam.data.dof.use_dof and cam.data.dof.focus_object is not None)

    # other rigs build without errors
    L.softbox_studio(ctx, objects="GEO_ball", camera="CAM_hero")
    L.sun(ctx, 30, 40)
    L.world(ctx, "sky", sun_elevation=30)
    L.practical(ctx, "LGT_lamp", (1, 1, 1))
    H.expect("rigs_built", bpy.data.objects.get("LGT_sun") is not None and bpy.data.objects.get("LGT_lamp") is not None)


H.run(body)
