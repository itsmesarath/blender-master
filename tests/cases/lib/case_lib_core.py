import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402

import math  # noqa: E402

import bm_anim  # noqa: E402
import bm_compositor  # noqa: E402
import bm_io  # noqa: E402
import bm_mesh  # noqa: E402
import bm_render  # noqa: E402
import bm_scene  # noqa: E402
import bm_verify  # noqa: E402
import bm_version  # noqa: E402


def body():
    v = bm_version.require_blender()
    H.expect("version_5_2_plus", v >= (5, 2, 0), list(v), ">= 5.2")
    H.expect("eevee_id", bm_version.eevee_id() == "BLENDER_EEVEE", bm_version.eevee_id())

    bm_scene.clear_scene()
    H.expect("scene_cleared", len(bpy.data.objects) == 0, len(bpy.data.objects), 0)

    # primitives are base-centred at real size
    b = bm_mesh.box("GEO_box", (0.4, 0.3, 0.2), (1, 0, 0))
    lo, hi = bm_verify.world_bounds(b)
    H.expect("box_on_ground", abs(lo.z) < 1e-6, lo.z, 0.0)
    ok, size = bm_verify.size_within([b], (0.4, 0.3, 0.2), 0.001)
    H.expect("box_size", ok, size, [0.4, 0.3, 0.2])
    H.expect("box_collection", b.users_collection[0].name == "GEO", b.users_collection[0].name, "GEO")
    H.expect("box_manifold", bm_verify.manifold_report(b)["non_manifold_edges"] == 0, bm_verify.manifold_report(b))
    H.expect("box_normals_out", bm_verify.normals_outward(b))
    again, created = bm_scene.get_or_create_object("GEO_box")
    H.expect("get_or_create_idempotent", again == b and not created)

    prof = [(0.0, 0.0), (0.03, 0.0), (0.035, 0.08), (0.012, 0.1), (0.012, 0.12), (0.0, 0.12)]
    lathe = bm_mesh.lathe("GEO_lathe", prof, 32, (-1, 0, 0))
    ok, size = bm_verify.size_within([lathe], (0.07, 0.07, 0.12), 0.02)
    H.expect("lathe_size", ok, size, [0.07, 0.07, 0.12])
    H.expect("lathe_manifold", bm_verify.manifold_report(lathe)["non_manifold_edges"] == 0, bm_verify.manifold_report(lathe))

    # overlap detection
    c = bm_mesh.box("GEO_overlap", (0.2, 0.2, 0.2), (1.1, 0, 0.05))
    hits = bm_verify.overlaps([b, c, lathe])
    H.expect("overlap_found", any({"GEO_box", "GEO_overlap"} == set(h) for h in hits), hits)
    bm_scene.remove_object("GEO_overlap")
    H.expect("no_overlap_after_remove", not bm_verify.overlaps([b, lathe]))

    # scale and floating detection
    b.scale = (2, 1, 1)
    H.expect("scale_detected", not bm_verify.scale_applied(b))
    b.scale = (1, 1, 1)
    f = bm_mesh.box("GEO_float", (0.1, 0.1, 0.1), (0, 2, 0.5))
    H.expect("floating_detected", "GEO_float" in bm_verify.floating([b, lathe, f]), bm_verify.floating([b, lathe, f]))
    bm_scene.remove_object("GEO_float")

    # naming
    bpy.data.objects.new("Cube.001", None)
    bpy.context.scene.collection.objects.link(bpy.data.objects["Cube.001"])
    H.expect("bad_name_found", "Cube.001" in bm_scene.bad_names(), bm_scene.bad_names())
    bpy.data.objects.remove(bpy.data.objects["Cube.001"])

    # layered-action keyframing
    e = bpy.data.objects.new("CTRL_spin", None)
    bpy.context.scene.collection.objects.link(e)
    bm_anim.key(e, "rotation_euler", 2, 1, 0.0, "LINEAR")
    bm_anim.key(e, "rotation_euler", 2, 25, math.pi, "LINEAR")
    bm_anim.make_cyclic(e)
    mid = bm_anim.value_at(e, "rotation_euler", 2, 13)
    H.expect("anim_linear_mid", abs(mid - math.pi / 2) < 1e-3, mid, math.pi / 2)
    H.expect("anim_channelbag", len(bm_anim.fcurves(e)) == 1, len(bm_anim.fcurves(e)), 1)
    H.expect("anim_cyclic", any(m.type == "CYCLES" for m in bm_anim.fcurves(e)[0].modifiers))

    # compositor chain on the 5.x node-group compositor
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    bm_compositor.ensure_tree(sc, reset=True)
    bm_compositor.add_denoise(sc)
    bm_compositor.add_glare(sc)
    chain = bm_compositor.chain_types(sc)
    H.expect("compositor_chain", chain[-1:] == ["NodeGroupOutput"] and "CompositorNodeDenoise" in chain, chain)

    # preview render is not black, and settings are restored
    cam_data = bpy.data.cameras.new("CAM_test")
    cam = bpy.data.objects.new("CAM_test", cam_data)
    bm_scene.link_exclusive(cam)
    cam.location = (0.6, -2.5, 1.0)
    cam.rotation_euler = (math.radians(75), 0, math.radians(12))
    sun = bpy.data.objects.new("LGT_sun", bpy.data.lights.new("LGT_sun", "SUN"))
    bm_scene.link_exclusive(sun)
    sc.world = sc.world or bpy.data.worlds.new("WLD_test")
    sc.render.resolution_x = 1234
    with bm_render.preview_scope(sc):
        bm_render.preview_settings(sc, samples=4, res=(160, 90))
        p = bm_render.render_still(os.path.join(H.OUT, "preview.png"), cam)
    st = bm_verify.image_stats(p)
    H.expect("preview_not_black", st["mean"] > 0.02, st["mean"], "> 0.02")
    H.expect("preview_size", (st["width"], st["height"]) == (160, 90), [st["width"], st["height"]])
    H.expect("settings_restored", sc.render.resolution_x == 1234, sc.render.resolution_x, 1234)

    sheet = bm_render.contact_sheet([b, lathe], os.path.join(H.OUT, "sheet.png"), tile=(96, 96))
    H.expect("contact_sheet", os.path.exists(sheet) and bm_verify.image_stats(sheet)["width"] == 192, sheet)

    # versioned saves never overwrite
    d = os.path.join(H.OUT, "blend")
    p1 = bm_io.versioned_save(d, "proj")
    p2 = bm_io.versioned_save(d, "proj")
    H.expect("versioned_save", p1.endswith("proj_v001.blend") and p2.endswith("proj_v002.blend"), [p1, p2])
    H.expect("open_file_unchanged", bpy.data.filepath == "", bpy.data.filepath, "")


H.run(body)
