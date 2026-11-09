import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402
import bm_verify  # noqa: E402


def body():
    ctx = H.make_ctx(project="gn_test", subskill="geometry-nodes")
    bm_scene.clear_scene()
    G = H.ops("geometry-nodes")
    bm_mesh.plane("GEO_ground", (10, 10))
    bm_mesh.cylinder("GEO_src_tree", 0.2, 1.5, 8)
    G.scatter(ctx, "forest", "GEO_ground", "GEO_src_tree", density=2.0, seed=3)
    ok, v = H.check(ctx, "gn_instances", target="GEO_forest", min_count=120, max_count=280)
    H.expect("scatter_count_density", ok, v, "about 200 on 100 m2")
    ok, v = H.check(ctx, "gn_input_changes", target="GEO_forest", input="Seed", value=11)
    H.expect("seed_changes_layout", ok, v)
    G.set_param(ctx, "GEO_forest", "Density", 0.5)
    ok, v = H.check(ctx, "gn_instances", target="GEO_forest", min_count=25, max_count=75)
    H.expect("density_input", ok, v)
    H.expect("source_hidden", bpy.data.objects["GEO_src_tree"].hide_render)

    bm_mesh.box("GEO_src_lamp", (0.2, 0.2, 4.0))
    G.instance_row(ctx, "lamps", "GEO_src_lamp", count=6, spacing=5.0, start=(-12.5, -6, 0))
    ok, v = H.check(ctx, "gn_instances", target="GEO_lamps", min_count=6, max_count=6)
    H.expect("row_count", ok, v)

    G.building_block(ctx, "city", rows=3, cols=4, lot=8, gap=4, height_min=6, height_max=30, seed=2)
    city = bpy.data.objects["GEO_city"]
    lo, hi = bm_verify.world_bounds(city)
    H.expect("city_on_ground", abs(lo.z) < 1e-4, lo.z)
    H.expect("city_heights", 6 <= hi.z <= 30.01, hi.z)
    H.expect("city_footprint", abs((hi - lo).x - (4 * 8 + 3 * 4)) < 1e-3, (hi - lo).x, 44)
    S = H.ops("materials-shading")
    S.material(ctx, "bldg", "concrete")
    S.assign(ctx, "bldg", ["GEO_city"])
    bpy.context.view_layer.update()
    evm = city.evaluated_get(bpy.context.evaluated_depsgraph_get())
    H.expect("gn_material_applies", city.material_slots[0].link == "OBJECT"
             and city.material_slots[0].material.name == "MAT_bldg", [s.link for s in city.material_slots])
    H.expect("gn_eval_has_polys", len(evm.data.polygons) > 0)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = city.evaluated_get(dg)
    H.expect("height_attribute", "height_factor" in ev.data.attributes, list(ev.data.attributes.keys())[:12])
    ok, v = H.check(ctx, "gn_input_changes", target="GEO_city", input="Rows", value=5)
    H.expect("rows_input", ok, v)

    bm_mesh.box("GEO_src_window", (1.2, 0.1, 1.4), (0, 0, -0.7))
    G.facade(ctx, "front", "GEO_src_window", floors=5, bays=4)
    ok, v = H.check(ctx, "gn_evaluates", objects="GEO_")
    H.expect("all_evaluate", ok, v)
    G.apply_nodes(ctx, "GEO_city")
    H.expect("applied", not city.modifiers and len(city.data.vertices) == 12 * 8, len(city.data.vertices))


H.run(body)
