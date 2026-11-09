import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="env_test", subskill="scene-environment")
    bm_scene.clear_scene()
    E, B = H.ops("scene-environment"), H.ops("blockout-spatial-brief")
    E.terrain(ctx, "GEO_terrain", size=(60, 60), resolution=48, height=5, flat_radius=10, seed=2)
    t = bpy.data.objects["GEO_terrain"]
    centre = [v.co.z for v in t.data.vertices if v.co.length < 9]
    rim = [abs(v.co.z) for v in t.data.vertices if v.co.length > 25]
    H.expect("flat_set", max(abs(z) for z in centre) < 1e-6, max(centre))
    H.expect("hills", max(rim) > 0.5, max(rim))
    E.street(ctx, "main", length=30, location=(40, 0, 0))
    H.expect("street_parts", all(f"GEO_main_{p}" in bpy.data.objects for p in ("road", "walk_L", "walk_R", "lines")))
    E.modular_kit(ctx, "kit", grid=2.0, height=3.0)
    E.kit_layout(ctx, [["floor", 0, 0, 0], ["floor", 1, 0, 0], ["wall", 0, 0, 0], ["wall", 1, 0, 0],
                       ["wall", 0, 0, 90], ["pillar", 0, 0, 0]], name="room")
    walls = [o for o in bpy.data.objects if o.name.startswith("GEO_room_wall")]
    H.expect("linked_copies", len({o.data.name for o in walls}) == 1 and len(walls) == 3)
    bm_mesh.cylinder("GEO_src_rock", 0.3, 0.4, 8, location=(0, -80, 0))
    E.scatter_props(ctx, "GEO_terrain", "GEO_src_rock", name="rocks", density=0.02, seed=1)
    ok, v = H.check(ctx, "gn_instances", target="GEO_rocks", min_count=30, max_count=120)
    H.expect("scatter", ok, v)
    B.proxy(ctx, "PRX_tree", size=(1, 1, 4), location=(5, 5, 0), note="tree")
    bm_mesh.cylinder("GEO_src_trunk", 0.2, 2.0, 8, location=(0, -90, 0))
    E.swap_proxy(ctx, "PRX_tree", "GEO_src_trunk", name="GEO_tree_01")
    bpy.context.view_layer.update()
    tr = bpy.data.objects["GEO_tree_01"]
    H.expect("swap_fits", abs(tr.dimensions.z - 4.0) < 0.01, tr.dimensions.z)
    # z-fight: two coplanar boxes
    bm_mesh.box("GEO_zf_a", (1, 1, 1), (60, 0, 0))
    bm_mesh.box("GEO_zf_b", (1, 1, 1), (60.5, 0, 0))
    bpy.context.view_layer.update()
    ok, v = H.check(ctx, "no_zfight", objects=["GEO_zf_a", "GEO_zf_b"])
    H.expect("zfight_found", not ok, v)
    ok, v = H.check(ctx, "no_zfight", objects=["GEO_main_road", "GEO_main_walk_L", "GEO_main_lines"])
    H.expect("street_clean", ok, v)
    B.camera(ctx, "CAM_hero", lens=35, view="three_quarter", objects=["GEO_room_wall_002", "GEO_room_wall_003"], fill=0.6)
    ok, v = H.check(ctx, "camera_coverage", camera="CAM_hero", objects="GEO_room_", min_fraction=0.8)
    H.expect("coverage", ok, v)


H.run(body)
