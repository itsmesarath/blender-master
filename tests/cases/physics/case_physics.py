import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="sim_test", subskill="physics-simulation")
    bm_scene.clear_scene()
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 40
    M, P = H.ops("modeling-topology"), H.ops("physics-simulation")
    bm_mesh.box("GEO_floor", (6, 6, 0.1), (0, 0, -0.1))
    for i in range(4):
        bm_mesh.box(f"GEO_cube_{i}", (0.3, 0.3, 0.3), (0.2 * i - 0.3, 0.05 * i, 1.0 + 0.45 * i))
    P.rigid_world(ctx, frame_end=40)
    P.rigid_body(ctx, ["GEO_floor"], kind="PASSIVE", shape="BOX")
    P.rigid_body(ctx, "GEO_cube_", kind="ACTIVE", shape="BOX", mass=2.0)
    # cloth: a sheet dropping onto a sphere
    bm_mesh.sphere("GEO_ball", 0.4, 24, 12, location=(3, 0, 0))
    bm_mesh.plane("GEO_sheet", (1.6, 1.6), (3, 0, 1.3))
    sheet = bpy.data.objects["GEO_sheet"]
    import bmesh
    bmo = bmesh.new()
    bmo.from_mesh(sheet.data)
    bmesh.ops.subdivide_edges(bmo, edges=bmo.edges[:], cuts=20, use_grid_fill=True)
    bmo.to_mesh(sheet.data)
    bmo.free()
    P.cloth(ctx, "GEO_sheet", preset="cotton", quality=4)
    P.collision(ctx, ["GEO_ball", "GEO_floor"])
    # character garment
    M.skin_figure(ctx, "GEO_char_body", height=1.8)
    body_o = bpy.data.objects["GEO_char_body"]
    body_o.location.x = -3
    bpy.context.view_layer.update()
    H.data("garment", P.garment_from_body(ctx, "GEO_char_body", "char_skirt", (-0.3, -1, 0.6), (0.3, 1, 1.0),
                                          offset=0.02, pin_z_above=0.95))
    sk = bpy.data.objects["GEO_char_skirt"]
    H.expect("garment_pinned", "pin" in sk.vertex_groups and sk.modifiers[0].type == "CLOTH",
             [m.type for m in sk.modifiers])
    H.data("bake", P.bake(ctx))
    ok, v = H.check(ctx, "sim_moved", objects="GEO_cube_")
    H.expect("cubes_fell", ok, v)
    ok, v = H.check(ctx, "no_explosion", objects="GEO_cube_", floor_z=0.0)
    H.expect("cubes_bounded", ok, v)
    ok, v = H.check(ctx, "sim_settled", objects="GEO_cube_", max_speed=0.03)
    H.expect("cubes_settled", ok, v)
    ok, v = H.check(ctx, "sim_moved", objects=["GEO_sheet"])
    H.expect("cloth_fell", ok, v)
    ok, v = H.check(ctx, "no_explosion", objects=["GEO_sheet", "GEO_char_skirt"], floor_z=-0.01)
    H.expect("cloth_bounded", ok, v)
    sc.frame_set(40)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = sheet.evaluated_get(dg)
    zmax = max((ev.matrix_world @ v.co).z for v in ev.data.vertices)
    H.expect("draped_on_ball", 0.7 < zmax < 0.95, zmax)
    sc.frame_set(1)
    # cache survives save + reload (later parts open the saved file)
    path = ctx.path("blend", "sim.blend")
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    bpy.ops.wm.open_mainfile(filepath=path)
    ok, v = H.check(ctx, "sim_moved", objects="GEO_cube_")
    H.expect("cache_persists", ok, v)
    P2 = H.ops("physics-simulation")
    bm_mesh.box("GEO_emitter", (0.2, 0.2, 0.2), (6, 0, 0.2))
    P2.particles(ctx, "GEO_emitter", count=50, frame_start=1, frame_end=10)
    H.expect("particles", bpy.data.objects["GEO_emitter"].particle_systems[0].settings.count == 50)


H.run(body)
