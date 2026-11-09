import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import os  # noqa: E402

import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="fluid_test", subskill="physics-simulation")
    bm_scene.clear_scene()
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 8
    P = H.ops("physics-simulation")
    bm_mesh.sphere("FX_smoke_src", 0.15, 12, 6, location=(0, 0, 0.3))
    H.data("fluid", P.fluid(ctx, "smoke", emitter="FX_smoke_src", domain_size=(1, 1, 1.5),
                            domain_location=(0, 0, 0.75), resolution=16))
    H.data("bake", P.bake(ctx))
    cache = ctx.path("cache", "fluid")
    files = [f for _r, _d, fs in os.walk(cache) for f in fs]
    H.expect("fluid_cache_written", len(files) >= 4, len(files))


H.run(body)
