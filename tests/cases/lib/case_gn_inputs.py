import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402

import bm_gn  # noqa: E402
import bm_mesh  # noqa: E402


def body():
    obj = bm_mesh.box("GEO_gn", (1, 1, 1))
    ng = bpy.data.node_groups.new("GN_offset", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Height", in_out="INPUT", socket_type="NodeSocketFloat")
    gi, go = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
    tr = ng.nodes.new("GeometryNodeTransform")
    comb = ng.nodes.new("ShaderNodeCombineXYZ")
    ng.links.new(gi.outputs["Geometry"], tr.inputs["Geometry"])
    ng.links.new(gi.outputs["Height"], comb.inputs["Z"])
    ng.links.new(comb.outputs["Vector"], tr.inputs["Translation"])
    ng.links.new(tr.outputs["Geometry"], go.inputs["Geometry"])
    mod = obj.modifiers.new("GN", "NODES")
    mod.node_group = ng
    bm_gn.set_input(mod, "Height", 2.0)
    H.expect("gn_get", abs(bm_gn.get_input(mod, "Height") - 2.0) < 1e-6, bm_gn.get_input(mod, "Height"), 2.0)
    bpy.context.view_layer.update()
    import bm_verify
    lo, hi = bm_verify.world_bounds(obj)
    H.expect("gn_evaluates", abs(lo.z - 2.0) < 1e-4, lo.z, 2.0)


H.run(body)
