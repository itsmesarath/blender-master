import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="mat_test", subskill="materials-shading")
    bm_scene.clear_scene()
    S = H.ops("materials-shading")
    for i, preset in enumerate(sorted(S.PRESETS)):
        S.material(ctx, f"t_{preset}", preset)
        m = bpy.data.materials.get(f"MAT_t_{preset}")
        H.expect(f"preset_{preset}", m is not None and m.node_tree is not None, preset)
    S.material(ctx, "wood_y", "wood", procedural_args={"axis": "Y", "scale": 10})
    S.material(ctx, "red", "plastic_gloss", color=(0.6, 0.02, 0.02), overrides={"Roughness": 0.3})
    bsdf = next(n for n in bpy.data.materials["MAT_red"].node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    H.expect("override_roughness", abs(bsdf.inputs["Roughness"].default_value - 0.3) < 1e-6,
             bsdf.inputs["Roughness"].default_value, 0.3)
    H.expect("color_set", abs(bsdf.inputs["Base Color"].default_value[0] - 0.6) < 1e-6)
    try:
        S.material(ctx, "bad", "clay", overrides={"Not A Socket": 1})
        H.expect("unknown_socket_rejected", False)
    except KeyError:
        H.expect("unknown_socket_rejected", True)

    # face indices survive re-assignment (export round-trips depend on it)
    b = bm_mesh.box("GEO_b", (1, 1, 1))
    S.material(ctx, "body", "metal_painted")
    S.material(ctx, "top", "rubber")
    S.assign(ctx, "body", "GEO_b")
    S.assign_by_normal(ctx, "GEO_b", "top", (0, 0, 1), 0.9)
    tops = [p.index for p in b.data.polygons if p.material_index == 1]
    H.expect("top_faces_assigned", len(tops) == 1, tops)
    S.assign(ctx, "body", "GEO_b", replace=True)
    S.assign(ctx, "top", "GEO_b", replace=False)
    H.expect("indices_preserved", [p.index for p in b.data.polygons if p.material_index == 1] == tops,
             [p.material_index for p in b.data.polygons])
    S.assign_band(ctx, "GEO_b", "red", 0.4, 0.6)
    H.expect("band_slot_added", len(b.material_slots) == 3, len(b.material_slots), 3)
    ok, v = H.check(ctx, "materials_filled", objects="GEO_")
    H.expect("materials_filled", ok, v)

    # an empty slot fails and the fixer fills it with the flagged placeholder
    e = bm_mesh.box("GEO_empty", (0.5, 0.5, 0.5), (2, 0, 0))
    e.data.materials.append(None)
    ok, v = H.check(ctx, "materials_filled", objects="GEO_empty")
    H.expect("empty_slot_detected", not ok, v)
    import bm_checks
    msg = bm_checks.FIXES["materials_filled"](ctx, {"objects": "GEO_empty"}, 1)
    ok, v = H.check(ctx, "materials_filled", objects="GEO_empty")
    H.expect("placeholder_fix", ok and "placeholder" in str(msg).lower(), [msg, v])


H.run(body)
