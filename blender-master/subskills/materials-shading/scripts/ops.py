"""materials-shading ops: Principled-based presets (5.x socket names), procedural textures that
need no image files, assignment by name or prefix, and per-face-slot assignment."""
from __future__ import annotations

import bpy

import bm_checks

# Principled BSDF input values per preset. Colours are linear RGB.
PRESETS = {
    "clay":           {"Base Color": (0.6, 0.6, 0.6, 1), "Roughness": 0.6},
    "plastic_gloss":  {"Base Color": (0.8, 0.1, 0.1, 1), "Roughness": 0.18, "Coat Weight": 0.3, "Coat Roughness": 0.05},
    "plastic_matte":  {"Base Color": (0.5, 0.5, 0.5, 1), "Roughness": 0.55},
    "rubber":         {"Base Color": (0.03, 0.03, 0.03, 1), "Roughness": 0.75},
    "metal_polished": {"Base Color": (0.9, 0.9, 0.92, 1), "Metallic": 1.0, "Roughness": 0.08},
    "metal_brushed":  {"Base Color": (0.85, 0.85, 0.87, 1), "Metallic": 1.0, "Roughness": 0.3, "Anisotropic": 0.6},
    "metal_gold":     {"Base Color": (1.0, 0.72, 0.33, 1), "Metallic": 1.0, "Roughness": 0.15},
    "metal_painted":  {"Base Color": (0.15, 0.3, 0.45, 1), "Metallic": 0.0, "Roughness": 0.4, "Coat Weight": 0.5},
    "glass_clear":    {"Base Color": (1, 1, 1, 1), "Transmission Weight": 1.0, "Roughness": 0.0, "IOR": 1.5},
    "glass_tinted":   {"Base Color": (0.85, 0.65, 0.4, 1), "Transmission Weight": 1.0, "Roughness": 0.02, "IOR": 1.5},
    "liquid_water":   {"Base Color": (1, 1, 1, 1), "Transmission Weight": 1.0, "Roughness": 0.0, "IOR": 1.33},
    "ceramic":        {"Base Color": (0.9, 0.88, 0.85, 1), "Roughness": 0.25, "Coat Weight": 0.6, "Coat Roughness": 0.1},
    "fabric":         {"Base Color": (0.35, 0.4, 0.5, 1), "Roughness": 0.85, "Sheen Weight": 0.3, "Sheen Roughness": 0.5},
    "paper_backdrop": {"Base Color": (0.8, 0.8, 0.8, 1), "Roughness": 0.9},
    "plaster":        {"Base Color": (0.75, 0.72, 0.68, 1), "Roughness": 0.9},
    "skin_basic":     {"Base Color": (0.8, 0.6, 0.5, 1), "Roughness": 0.45, "Subsurface Weight": 0.25,
                       "Subsurface Radius": (1.0, 0.35, 0.2), "Subsurface Scale": 0.01},
    "emissive":       {"Base Color": (0, 0, 0, 1), "Emission Color": (1.0, 0.85, 0.6, 1), "Emission Strength": 5.0},
    "wood":           {"Roughness": 0.45, "_procedural": "wood"},
    "concrete":       {"Roughness": 0.8, "_procedural": "concrete"},
    "worn_metal":     {"Metallic": 1.0, "_procedural": "worn_metal"},
}


def _principled(mat):
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return bsdf


def _set(bsdf, key, value):
    if key not in bsdf.inputs:
        raise KeyError(f"Principled BSDF has no input {key!r} in this Blender version")
    sock = bsdf.inputs[key]
    if isinstance(value, (tuple, list)) and len(value) == 3 and len(sock.default_value) == 4:
        value = (*value, 1.0)
    sock.default_value = value


def _wood(nt, bsdf, color_a=(0.28, 0.14, 0.06, 1), color_b=(0.55, 0.33, 0.16, 1), scale=6.0, axis="X",
          boards=None, board_width=0.14, board_length=1.2, board_variation=0.35):
    """Straight grain: thin dark lines along one object axis (bands with gentle distortion), broken
    up by a stretched noise so boards do not look printed, plus a fine bump. ``boards`` (default on
    for X/Y floors and decks) splits the surface into staggered planks: each plank gets its own
    tint and grain offset, with thin dark seams."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    stretch = {"X": (0.15, 1.0, 1.0), "Y": (1.0, 0.15, 1.0), "Z": (1.0, 1.0, 0.15)}.get(axis, (0.15, 1.0, 1.0))
    mapping.inputs["Scale"].default_value = stretch
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = {"X": "Y", "Y": "X", "Z": "X"}.get(axis, "Y")   # lines run along the axis
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 1.2
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 1.5
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale * 0.6
    noise.inputs["Detail"].default_value = 6.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.inputs["Factor"].default_value = 0.45
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = color_a
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = color_b
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.04
    nt.links.new(tc.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], mix.inputs[2])      # float A
    nt.links.new(noise.outputs["Fac"], mix.inputs[3])     # float B
    grain = mix.outputs[0]
    if boards is None:
        boards = axis in ("X", "Y") and board_width > 0
    if boards:
        # planks: brick texture in object space, bricks run along the grain axis
        bmap = nt.nodes.new("ShaderNodeMapping")
        bmap.inputs["Rotation"].default_value = (0, 0, 0 if axis == "X" else 1.5708)
        brick = nt.nodes.new("ShaderNodeTexBrick")
        brick.offset = 0.5
        brick.offset_frequency = 1
        brick.squash = 1.0
        brick.inputs["Scale"].default_value = 1.0
        brick.inputs["Brick Width"].default_value = board_length
        brick.inputs["Row Height"].default_value = board_width
        brick.inputs["Mortar Size"].default_value = 0.002
        brick.inputs["Mortar Smooth"].default_value = 0.2
        brick.inputs["Bias"].default_value = 0.0
        brick.inputs["Color1"].default_value = (0.0, 0.0, 0.0, 1)
        brick.inputs["Color2"].default_value = (1.0, 1.0, 1.0, 1)
        brick.inputs["Mortar"].default_value = (0.0, 0.0, 0.0, 1)
        nt.links.new(tc.outputs["Object"], bmap.inputs["Vector"])
        nt.links.new(bmap.outputs["Vector"], brick.inputs["Vector"])
        # each plank samples the grain at a random offset so lines do not continue across seams
        jitter = nt.nodes.new("ShaderNodeVectorMath")
        jitter.operation = "MULTIPLY_ADD"
        jitter.inputs[1].default_value = (13.7, 7.3, 3.1)
        nt.links.new(brick.outputs["Color"], jitter.inputs[0])
        nt.links.new(mapping.outputs["Vector"], jitter.inputs[2])
        nt.links.new(jitter.outputs[0], wave.inputs["Vector"])
        nt.links.new(jitter.outputs[0], noise.inputs["Vector"])
        wave.inputs["Distortion"].default_value = 2.5
        mix.inputs["Factor"].default_value = 0.55
        tone = nt.nodes.new("ShaderNodeMath")              # per-plank random value -0.5..0.5
        tone.operation = "SUBTRACT"
        tone.inputs[1].default_value = 0.5
        nt.links.new(brick.outputs["Color"], tone.inputs[0])
        amt = nt.nodes.new("ShaderNodeMath")
        amt.operation = "MULTIPLY"
        amt.inputs[1].default_value = board_variation
        nt.links.new(tone.outputs[0], amt.inputs[0])
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        add.use_clamp = True
        nt.links.new(grain, add.inputs[0])
        nt.links.new(amt.outputs[0], add.inputs[1])
        seam = nt.nodes.new("ShaderNodeMath")             # darken seams (brick Fac = 1 in mortar)
        seam.operation = "MULTIPLY"
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(brick.outputs["Fac"], inv.inputs[1])
        nt.links.new(add.outputs[0], seam.inputs[0])
        nt.links.new(inv.outputs[0], seam.inputs[1])
        grain = seam.outputs[0]
        bump.inputs["Strength"].default_value = 0.08
    nt.links.new(grain, ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(grain, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

def _concrete(nt, bsdf, color_a=(0.32, 0.31, 0.3, 1), color_b=(0.52, 0.5, 0.48, 1), scale=12.0):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = color_a
    ramp.color_ramp.elements[1].color = color_b
    rough = nt.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.65
    rough.inputs["To Max"].default_value = 0.95
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def _worn_metal(nt, bsdf, paint=(0.12, 0.25, 0.38, 1), metal=(0.55, 0.55, 0.57, 1), wear=0.3,
                paint_roughness=0.55):
    """Painted metal with procedural wear. ``wear`` is the amount of bare metal (0 = new paint,
    1 = heavily worn): a large-scale noise decides where wear may appear and a fine noise breaks
    it into chips. Bare metal is metallic and glossier; paint stays rough and dielectric."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    big = nt.nodes.new("ShaderNodeTexNoise")
    big.inputs["Scale"].default_value = 3.0
    big.inputs["Detail"].default_value = 4.0
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 28.0
    fine.inputs["Detail"].default_value = 10.0
    fine.inputs["Roughness"].default_value = 0.7
    both = nt.nodes.new("ShaderNodeMath")
    both.operation = "MULTIPLY"
    nt.links.new(tc.outputs["Object"], big.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    nt.links.new(big.outputs["Fac"], both.inputs[0])
    nt.links.new(fine.outputs["Fac"], both.inputs[1])
    thr = max(0.05, 0.42 - 0.22 * max(0.0, min(1.0, wear)))   # product of two ~0.5 noises
    mask = nt.nodes.new("ShaderNodeValToRGB")
    mask.color_ramp.elements[0].position = thr
    mask.color_ramp.elements[1].position = min(thr + 0.02, 1.0)
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs[6].default_value = paint
    col.inputs[7].default_value = metal
    rough = nt.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = paint_roughness
    rough.inputs["To Max"].default_value = 0.3
    nt.links.new(both.outputs[0], mask.inputs["Fac"])
    nt.links.new(mask.outputs["Color"], col.inputs["Factor"])
    nt.links.new(col.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(mask.outputs["Color"], bsdf.inputs["Metallic"])
    nt.links.new(mask.outputs["Color"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])


PROCEDURAL = {"wood": _wood, "concrete": _concrete, "worn_metal": _worn_metal}


def material(ctx, name, preset="clay", overrides=None, color=None, procedural_args=None):
    """Create or rebuild MAT_<name> from a preset. ``color`` sets Base Color (or the paint colour
    for procedural presets that accept one)."""
    if not name.startswith("MAT_"):
        name = "MAT_" + name
    if preset not in PRESETS:
        raise ValueError(f"preset must be one of {sorted(PRESETS)}")
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt = mat.node_tree                     # 5.x: node tree exists on creation, no use_nodes
    for n in [n for n in nt.nodes if n.bl_idname not in ("ShaderNodeOutputMaterial", "ShaderNodeBsdfPrincipled")]:
        nt.nodes.remove(n)
    bsdf = _principled(mat)
    vals = dict(PRESETS[preset])
    proc = vals.pop("_procedural", None)
    for k, v in vals.items():
        _set(bsdf, k, v)
    if proc:
        PROCEDURAL[proc](nt, bsdf, **(procedural_args or {}))
    if color is not None and not proc:
        _set(bsdf, "Base Color", color)
    for k, v in (overrides or {}).items():
        _set(bsdf, k, v)
    base = bsdf.inputs["Base Color"].default_value
    mat.diffuse_color = (base[0], base[1], base[2], 1.0)    # viewport colour follows the look
    mat["preset"] = preset
    return f"{name} ({preset})"


def assign(ctx, material, targets, slot=None, replace=True):
    """Assign MAT_<material> to objects (names list or prefix). replace=True clears other slots."""
    if not material.startswith("MAT_"):
        material = "MAT_" + material
    mat = bpy.data.materials[material]
    objs = bm_checks.select(targets)
    if not objs:
        raise ValueError(f"no mesh objects match {targets!r}")
    for o in objs:
        if replace:
            # clearing slots resets face material indices; keep them so later slots still land
            idx = [p.material_index for p in o.data.polygons]
            o.data.materials.clear()
            o.data.materials.append(mat)
            o.data.polygons.foreach_set("material_index", idx)
        elif slot is not None and slot < len(o.material_slots):
            o.material_slots[slot].material = mat
        else:
            o.data.materials.append(mat)
        if any(m.type == "NODES" for m in o.modifiers):
            # geometry generated by nodes carries its own (empty) material list; object-linked
            # slots apply to whatever the modifier outputs
            for i, s in enumerate(o.material_slots):
                m = o.data.materials[i]
                s.link = "OBJECT"
                s.material = m
    return f"{material} -> {[o.name for o in objs]}"


def assign_by_normal(ctx, target, material, direction=(0, 0, 1), min_dot=0.7):
    """Add a material slot and give it to faces facing ``direction`` (e.g. a label band or a top)."""
    from mathutils import Vector
    if not material.startswith("MAT_"):
        material = "MAT_" + material
    o = bpy.data.objects[target]
    mat = bpy.data.materials[material]
    if mat.name not in [m.name for m in o.data.materials if m]:
        o.data.materials.append(mat)
    idx = [m.name if m else None for m in o.data.materials].index(mat.name)
    d = Vector(direction).normalized()
    n = 0
    for p in o.data.polygons:
        if p.normal.dot(d) >= min_dot:
            p.material_index = idx
            n += 1
    return f"{material} on {n} faces of {target}"


def assign_band(ctx, target, material, z_min, z_max):
    """Give faces whose centre lies between z_min and z_max (object space) their own material."""
    if not material.startswith("MAT_"):
        material = "MAT_" + material
    o = bpy.data.objects[target]
    mat = bpy.data.materials[material]
    if mat.name not in [m.name for m in o.data.materials if m]:
        o.data.materials.append(mat)
    idx = [m.name if m else None for m in o.data.materials].index(mat.name)
    n = 0
    for p in o.data.polygons:
        if z_min <= p.center.z <= z_max:
            p.material_index = idx
            n += 1
    return f"{material} band on {n} faces"


def assign_box(ctx, target, material, box_min, box_max):
    """Give faces whose centre lies inside an axis-aligned box (object space) their own material:
    clothing zones on a single body mesh, labels, trims."""
    from mathutils import Vector
    if not material.startswith("MAT_"):
        material = "MAT_" + material
    o = bpy.data.objects[target]
    mat = bpy.data.materials[material]
    if mat.name not in [m.name for m in o.data.materials if m]:
        o.data.materials.append(mat)
    idx = [m.name if m else None for m in o.data.materials].index(mat.name)
    lo, hi = Vector(box_min), Vector(box_max)
    n = 0
    for p in o.data.polygons:
        c = p.center
        if all(lo[i] <= c[i] <= hi[i] for i in range(3)):
            p.material_index = idx
            n += 1
    return f"{material}: {n} faces of {target}"


def use_textures(ctx, material, textures, ao_strength=1.0):
    """Wire image files into MAT_<material>: ``textures`` maps diffuse/basecolor, roughness,
    normal, ao, emit to paths (relative paths resolve inside the project output folder)."""
    import os
    import bm_textures
    if not material.startswith("MAT_"):
        material = "MAT_" + material
    mat = bpy.data.materials[material]
    nodes = {}
    for i, (kind, path) in enumerate(textures.items()):
        full = path if os.path.isabs(path) else ctx.path(path)
        if not os.path.exists(full):
            raise FileNotFoundError(full)
        cs = bm_textures.COLORSPACE.get(kind, "Non-Color")
        nodes[kind] = bm_textures.image_node(mat, full, f"TEX_{kind}", cs, (-900, -300 * i))
    return f"{material}: wired {bm_textures.wire(mat, nodes, ao_strength)}"


OPS = {"material": material, "assign_box": assign_box, "use_textures": use_textures, "assign": assign, "assign_by_normal": assign_by_normal, "assign_band": assign_band}
FIXES = {}
