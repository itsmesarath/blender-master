"""Compositor helpers for Blender 5.x.

5.x model: the compositor is a node-group data-block assigned to ``scene.compositing_node_group``;
the final image goes to a Group Output node with an ``Image`` output socket (there is no
Composite node and no per-scene node tree property). Many node options are input sockets now.
"""
from __future__ import annotations

import bpy


def ensure_tree(scene=None, name: str = "COMP_main", reset: bool = False):
    """Return (tree, render_layers_node, group_output_node), creating a minimal pass-through tree."""
    scene = scene or bpy.context.scene
    tree = scene.compositing_node_group
    if tree is None or reset:
        tree = bpy.data.node_groups.get(name) or bpy.data.node_groups.new(name, "CompositorNodeTree")
        scene.compositing_node_group = tree
    if reset:
        tree.nodes.clear()
    if not any(i.in_out == "OUTPUT" and i.name == "Image" for i in tree.interface.items_tree
               if i.item_type == "SOCKET"):
        tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = next((n for n in tree.nodes if n.bl_idname == "CompositorNodeRLayers"), None) or tree.nodes.new("CompositorNodeRLayers")
    out = next((n for n in tree.nodes if n.bl_idname == "NodeGroupOutput"), None) or tree.nodes.new("NodeGroupOutput")
    rl.location, out.location = (-600, 0), (600, 0)
    if not out.inputs["Image"].is_linked:
        tree.links.new(rl.outputs["Image"], out.inputs["Image"])
    return tree, rl, out


def _feed(tree, out_node):
    """Socket currently feeding the group output Image input."""
    link = out_node.inputs["Image"].links[0] if out_node.inputs["Image"].is_linked else None
    return link.from_socket if link else None


def add_denoise(scene=None, prefilter: str = "Accurate"):
    """Render Layers -> Denoise (image + albedo + normal) -> Group Output. Cycles only.

    Turns on the view layer's denoising data passes; the scene must be re-rendered afterwards.
    Use either this or Cycles' own render denoiser, not both.
    """
    scene = scene or bpy.context.scene
    vl = scene.view_layers[0]
    vl.cycles.denoising_store_passes = True
    tree, rl, out = ensure_tree(scene)
    dn = next((n for n in tree.nodes if n.bl_idname == "CompositorNodeDenoise"), None) or tree.nodes.new("CompositorNodeDenoise")
    dn.location = (-150, 0)
    dn.inputs["Prefilter"].default_value = prefilter
    tree.links.new(rl.outputs["Image"], dn.inputs["Image"])
    if "Denoising Albedo" in rl.outputs:
        tree.links.new(rl.outputs["Denoising Albedo"], dn.inputs["Albedo"])
        tree.links.new(rl.outputs["Denoising Normal"], dn.inputs["Normal"])
    tree.links.new(dn.outputs["Image"], out.inputs["Image"])
    return dn


def add_mist(scene=None, start: float = 2.0, depth: float = 20.0, color=(0.7, 0.78, 0.9, 1.0), amount: float = 0.6):
    """Blend a flat haze colour over the image using the Mist pass."""
    scene = scene or bpy.context.scene
    vl = scene.view_layers[0]
    vl.use_pass_mist = True
    if scene.world is None:
        scene.world = bpy.data.worlds.new("WLD_main")
    scene.world.mist_settings.start = start
    scene.world.mist_settings.depth = depth
    tree, rl, out = ensure_tree(scene)
    src = _feed(tree, out) or rl.outputs["Image"]
    mul = tree.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = amount
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    mix.location, mul.location = (300, 0), (100, -200)
    tree.links.new(rl.outputs["Mist"], mul.inputs[0])
    tree.links.new(mul.outputs[0], mix.inputs["Factor"])
    tree.links.new(src, mix.inputs[6])            # A (colour)
    mix.inputs[7].default_value = color           # B (colour)
    tree.links.new(mix.outputs[2], out.inputs["Image"])
    return mix


def add_glare(scene=None, kind: str = "Fog Glow", threshold: float = 1.0, strength: float = 0.5):
    scene = scene or bpy.context.scene
    tree, rl, out = ensure_tree(scene)
    src = _feed(tree, out) or rl.outputs["Image"]
    g = tree.nodes.new("CompositorNodeGlare")
    g.inputs["Type"].default_value = kind
    g.inputs["Threshold"].default_value = threshold
    g.inputs["Strength"].default_value = strength
    g.location = (350, 150)
    tree.links.new(src, g.inputs["Image"])
    tree.links.new(g.outputs["Image"], out.inputs["Image"])
    return g


def chain_types(scene=None) -> list[str]:
    """Node types from Render Layers to Group Output along the Image path (for checks)."""
    scene = scene or bpy.context.scene
    tree = scene.compositing_node_group
    if tree is None:
        return []
    out = next((n for n in tree.nodes if n.bl_idname == "NodeGroupOutput"), None)
    chain, node = [], out
    while node is not None:
        chain.append(node.bl_idname)
        linked = [i for i in node.inputs if i.is_linked and i.type in {"RGBA", "VECTOR"}]
        img_in = next((i for i in linked if i.name in {"Image", "A"}), linked[0] if linked else None)
        node = img_in.links[0].from_node if img_in else None
    return list(reversed(chain))
