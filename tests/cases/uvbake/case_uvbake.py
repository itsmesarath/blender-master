import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="uv_test", subskill="uv-texturing-baking")
    bm_scene.clear_scene()
    M, Mat, U, S = H.ops("modeling-topology"), H.ops("materials-shading"), H.ops("uv-texturing-baking"), H.ops("sculpting")
    M.box(ctx, "GEO_crate", (0.6, 0.6, 0.6))
    M.panel_inset(ctx, "GEO_crate", thickness=0.06, depth=0.03, faces="all", inner_material_index=1)
    U.mark_seams(ctx, "GEO_crate", angle=50)
    U.unwrap(ctx, "GEO_crate", method="angle")
    for name in ("uv_in_bounds", "uv_no_overlap"):
        ok, v = H.check(ctx, name, objects=["GEO_crate"])
        H.expect(f"angle_{name}", ok, v)
    U.unwrap(ctx, "GEO_crate", method="smart")
    ok, v = H.check(ctx, "uv_no_overlap", objects=["GEO_crate"])
    H.expect("smart_no_overlap", ok, v)
    U.texel_report(ctx, "GEO_crate")
    Mat.material(ctx, "paint", preset="metal_painted", color=(0.2, 0.25, 0.1))
    Mat.assign(ctx, "paint", ["GEO_crate"])
    U.bake(ctx, "GEO_crate", maps=("ao",), size=128, samples=8)
    ok, v = H.check(ctx, "bake_nonempty", pattern="textures/GEO_crate_ao.png")
    H.expect("ao_baked", ok, v)
    nt = bpy.data.materials["MAT_paint"].node_tree
    H.expect("ao_wired", any(n.type == "MIX" and n.blend_type == "MULTIPLY" for n in nt.nodes))

    # high -> low normal bake
    bm_mesh.sphere("GEO_ball", 0.5, 24, 12, location=(2, 0, 0.5))
    S.make_high(ctx, "GEO_ball", levels=2)
    S.surface_noise(ctx, "GEO_ball_high", strength=0.02, scale=12, symmetric=False)
    U.unwrap(ctx, "GEO_ball", method="smart")
    Mat.material(ctx, "ball", preset="plastic_matte", color=(0.5, 0.5, 0.5))
    Mat.assign(ctx, "ball", ["GEO_ball"])
    U.bake(ctx, "GEO_ball", maps=("normal",), size=128, high="GEO_ball_high", extrusion=0.05, samples=1)
    ok, v = H.check(ctx, "bake_nonempty", pattern="textures/GEO_ball_normal.png")
    H.expect("normal_baked_detail", ok, v)
    bsdf = next(n for n in bpy.data.materials["MAT_ball"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    H.expect("normal_wired", bsdf.inputs["Normal"].is_linked)
    # deliberately push UVs outside and let the fixer repack
    uv = bpy.data.objects["GEO_ball"].data.uv_layers.active
    for d in uv.data:
        d.uv.x += 0.7
    ok, _ = H.check(ctx, "uv_in_bounds", objects=["GEO_ball"])
    U.FIXES["uv_in_bounds"](ctx, {"objects": ["GEO_ball"]}, 1)
    ok2, v2 = H.check(ctx, "uv_in_bounds", objects=["GEO_ball"])
    H.expect("bounds_fix", (not ok) and ok2, v2)


H.run(body)
