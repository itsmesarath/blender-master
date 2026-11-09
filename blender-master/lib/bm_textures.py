"""Wire image maps (baked or painted) into a Principled BSDF material."""
from __future__ import annotations

import os

import bpy

COLORSPACE = {"diffuse": "sRGB", "basecolor": "sRGB", "emit": "sRGB", "combined": "sRGB"}


def image_node(mat, path_or_image, label, colorspace=None, location=(-900, 0)):
    nt = mat.node_tree
    img = path_or_image
    if isinstance(path_or_image, str):
        img = bpy.data.images.load(os.path.abspath(path_or_image), check_existing=True)
    if colorspace:
        img.colorspace_settings.name = colorspace
    n = nt.nodes.get(label) or nt.nodes.new("ShaderNodeTexImage")
    n.name = n.label = label
    n.image = img
    n.location = location
    return n


def wire(mat, nodes: dict, ao_strength: float = 1.0) -> list[str]:
    """``nodes``: map name -> image node. Known maps: diffuse/basecolor, roughness, normal, ao,
    emit. Returns the list of wired maps."""
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return []
    L = nt.links
    done = []
    col = nodes.get("diffuse") or nodes.get("basecolor")
    if col is not None:
        L.new(col.outputs["Color"], bsdf.inputs["Base Color"])
        done.append("basecolor")
    if "roughness" in nodes:
        L.new(nodes["roughness"].outputs["Color"], bsdf.inputs["Roughness"])
        done.append("roughness")
    if "emit" in nodes:
        L.new(nodes["emit"].outputs["Color"], bsdf.inputs["Emission Color"])
        done.append("emit")
    if "normal" in nodes:
        nm = nt.nodes.get("NORMAL_map") or nt.nodes.new("ShaderNodeNormalMap")
        nm.name = "NORMAL_map"
        nm.location = (-400, -500)
        L.new(nodes["normal"].outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        done.append("normal")
    if "ao" in nodes:
        base = bsdf.inputs["Base Color"]
        src = base.links[0].from_socket if base.links else None
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.location = (-250, 200)
        mix.inputs[0].default_value = ao_strength
        if src is not None:
            L.new(src, mix.inputs[6])
        else:
            mix.inputs[6].default_value = base.default_value
        L.new(nodes["ao"].outputs["Color"], mix.inputs[7])
        L.new(mix.outputs[2], base)
        done.append("ao")
    return done
