import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import json  # noqa: E402

import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="hair_test", subskill="hair-fur")
    bm_scene.clear_scene()
    M, F = H.ops("modeling-topology"), H.ops("hair-fur")
    M.skin_figure(ctx, "GEO_char_body", height=1.8)
    body_o = bpy.data.objects["GEO_char_body"]
    head = json.loads(body_o["joints"])["head"]
    F.hair_material(ctx, "hair", melanin=0.85, redness=0.2)
    msg = F.groom(ctx, "char_hair", "GEO_char_body", count=1500, length=0.14,
                  region={"z_min": head[2] - 0.01, "direction": (0, 0.45, 1), "min_dot": 0.15},
                  curl=1.5, curl_radius=0.006, material="hair", seed=4)
    H.data("groom", msg)
    ok, v = H.check(ctx, "curve_count", prefix="GEO_char_hair", min_curves=1500, max_curves=1500)
    H.expect("count", ok, v)
    ok, v = H.check(ctx, "hair_roots_on_surface", prefix="GEO_char_hair")
    H.expect("roots", ok, v)
    ok, v = H.check(ctx, "hair_material", prefix="GEO_char_hair")
    H.expect("material", ok, v)
    hair = bpy.data.objects["GEO_char_hair"]
    pos = [p.vector.z for p in hair.data.position_data]
    H.expect("on_head", min(pos) > 1.35, min(pos))
    H.expect("parented", hair.parent == body_o)

    bm_mesh.sphere("GEO_critter", 0.15, 24, 12, location=(1, 0, 0.15))
    F.fur(ctx, "critter_fur", "GEO_critter", density=20000, length=0.015)
    ok, v = H.check(ctx, "curve_count", prefix="GEO_critter_fur", min_curves=4000)
    H.expect("fur_density", ok, v)


H.run(body)
