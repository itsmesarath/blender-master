import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_scene  # noqa: E402
import bm_verify  # noqa: E402


def body():
    ctx = H.make_ctx(project="retopo_test", subskill="retopology")
    bm_scene.clear_scene()
    M, S, R = H.ops("modeling-topology"), H.ops("sculpting"), H.ops("retopology")
    M.skin_figure(ctx, "GEO_char_body", height=1.8)
    S.make_high(ctx, "GEO_char_body", levels=2)
    S.inflate(ctx, "GEO_char_body_high", (0.0, -0.1, 1.25), 0.12, 0.015)
    ok, v = H.check(ctx, "surface_distance", low="GEO_char_body", high="GEO_char_body_high", max_mean=0.002)
    R.shrinkwrap_fit(ctx, "GEO_char_body", "GEO_char_body_high")
    ok2, v2 = H.check(ctx, "surface_distance", low="GEO_char_body", high="GEO_char_body_high", max_mean=0.002)
    H.expect("fit_improves", ok2 and v2["GEO_char_body"]["mean"] < v["GEO_char_body"]["mean"], v, v2)
    H.expect("hidden_high", bpy.data.objects["GEO_char_body_high"].hide_render)
    H.expect("still_quads", bm_verify.face_stats(bpy.data.objects["GEO_char_body"])["quad_ratio"] == 1.0)

    bm_mesh_sphere = H.ops("modeling-topology")
    import bm_mesh
    bm_mesh.sphere("GEO_blob_high", 1.0, 64, 32)
    S.surface_noise(ctx, "GEO_blob_high", strength=0.05, scale=2.0, symmetric=False)
    msg = R.quad_remesh(ctx, "GEO_blob_high", "GEO_blob", faces=800)
    blob = bpy.data.objects["GEO_blob"]
    H.data("quad_remesh", msg)
    H.expect("remesh_budget", 300 < len(blob.data.polygons) < 2000, len(blob.data.polygons))
    ok, v = H.check(ctx, "quad_ratio", objects=["GEO_blob"], min_ratio=0.85)
    H.expect("remesh_quads", ok, v)
    ok, v = H.check(ctx, "surface_distance", low="GEO_blob", high="GEO_blob_high", max_mean=0.02)
    H.expect("remesh_close", ok, v)
    R.lod_chain(ctx, "GEO_blob", ratios=(0.5, 0.2))
    def tris(o):   # LODs are triangulated by collapse decimation: compare triangle counts
        o.data.calc_loop_triangles()
        return len(o.data.loop_triangles)
    l0 = tris(blob)
    l1, l2 = (tris(bpy.data.objects[f"GEO_blob_LOD{i}"]) for i in (1, 2))
    H.expect("lods_shrink", l0 > l1 > l2, (l0, l1, l2))
    del bm_mesh_sphere


H.run(body)
