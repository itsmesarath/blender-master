import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import json  # noqa: E402


def body():
    ctx = H.make_ctx(project="blockout_test", facts={"hero_camera": "CAM_hero"}, subskill="blockout-spatial-brief")
    B = H.ops("blockout-spatial-brief")
    B.setup_scene(ctx)
    B.proxy(ctx, "PRX_table", "box", (1.2, 0.7, 0.75), (0, 0, 0), note="dining table")
    B.proxy(ctx, "lamp", "cylinder", (0.3, 0.3, 0.5), (0.3, 0, 0.75), note="lamp on the table")
    B.ground(ctx)
    B.camera(ctx, "CAM_hero", 50, "three_quarter", objects="PRX_")
    B.camera(ctx, "front", 85, "front", objects="PRX_table")
    B.resolution(ctx, (1280, 720))
    B.review_layer(ctx)
    B.review_mark(ctx, [(0, -0.5, 1.0), (0.2, -0.5, 1.1), (0.4, -0.5, 1.0)], "red", "lamp too tall")
    B.review_mark(ctx, [(-0.5, 0, 0.8), (-0.4, 0, 0.9)], "green", "add a vase")
    B.write_spatial_brief(ctx)
    B.proxy(ctx, "PRX_table", "box", (1.2, 0.7, 0.75), note="dining table")   # idempotent re-run

    H.expect("one_table", sum(o.name.startswith("PRX_table") for o in bpy.data.objects) == 1)
    H.expect("prefix_added", "PRX_lamp" in bpy.data.objects)
    ok, v = H.check(ctx, "custom_prop", objects="PRX_", key="brief_note")
    H.expect("notes_on_every_proxy", ok, v)
    ok, v = H.check(ctx, "cameras_exist", names=["CAM_hero", "CAM_front"])
    H.expect("cameras_exist", ok, v)
    ok, v = H.check(ctx, "camera_frames", camera="CAM_hero", objects=["PRX_table", "PRX_lamp"])
    H.expect("hero_frames_proxies", ok, v)
    H.expect("hero_is_scene_camera", bpy.context.scene.camera.name == "CAM_hero", bpy.context.scene.camera.name)
    H.expect("autofit_tagged", bool(bpy.data.objects["CAM_hero"].get("autofit")))
    ok, v = H.check(ctx, "bounds_size", objects="PRX_table", target=[1.2, 0.7, 0.75], tol=0.01)
    H.expect("table_size", ok, v)
    rev = bpy.data.objects["REV_review"]
    strokes = rev.data.layers["REVIEW"].frames[0].drawing.strokes
    H.expect("review_strokes", len(strokes) == 2, len(strokes), 2)
    notes = json.loads(rev["review_notes"])
    H.expect("review_notes", [n["kind"] for n in notes] == ["red", "green"], notes)
    H.expect("review_hidden_in_render", rev.hide_render)
    md = open(ctx.path("brief", "spatial_brief.md")).read()
    cams = json.load(open(ctx.path("brief", "cameras.json")))
    H.expect("spatial_brief_lists_proxies", "PRX_table" in md and "PRX_lamp" in md)
    H.expect("cameras_json", {c["name"] for c in cams} >= {"CAM_hero", "CAM_front"}, cams)
    ok, v = H.check(ctx, "names_valid")
    H.expect("names_valid", ok, v)


H.run(body)
