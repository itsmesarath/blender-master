"""Layered-action safe animation helpers (Blender 5.x).

In 5.x an Action holds layers -> strips -> channelbags per slot; the old flat F-Curve list on the action is gone.
Always reach F-Curves through the channelbag for the ID's assigned slot.
"""
from __future__ import annotations

import bpy
from bpy_extras import anim_utils


def channelbag(id_block, create: bool = True):
    ad = id_block.animation_data or (id_block.animation_data_create() if create else None)
    if ad is None:
        return None
    if ad.action is None:
        if not create:
            return None
        ad.action = bpy.data.actions.new(f"ACT_{id_block.name}")
    if ad.action_slot is None:
        if not create:
            return None
        slot = ad.action.slots.new(id_type=id_block.id_type, name=id_block.name)
        ad.action_slot = slot
    if create:
        return anim_utils.action_ensure_channelbag_for_slot(ad.action, ad.action_slot)
    return anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)


def fcurves(id_block) -> list:
    cb = channelbag(id_block, create=False)
    return list(cb.fcurves) if cb else []


def ensure_fcurve(id_block, data_path: str, index: int = 0, group: str | None = None):
    cb = channelbag(id_block)
    kw = {"index": index}
    if group:
        kw["group_name"] = group
    return cb.fcurves.ensure(data_path, **kw)


def key(id_block, data_path: str, index: int, frame: float, value: float, interpolation: str = "BEZIER",
        group: str | None = None):
    fc = ensure_fcurve(id_block, data_path, index, group)
    kp = fc.keyframe_points.insert(frame, value, options={"FAST"})
    kp.interpolation = interpolation
    fc.update()
    return kp


def set_interpolation(id_block, interpolation: str = "LINEAR") -> None:
    for fc in fcurves(id_block):
        for kp in fc.keyframe_points:
            kp.interpolation = interpolation


def make_cyclic(id_block, data_path: str | None = None) -> None:
    for fc in fcurves(id_block):
        if data_path and fc.data_path != data_path:
            continue
        if not any(m.type == "CYCLES" for m in fc.modifiers):
            fc.modifiers.new("CYCLES")


def add_noise(id_block, data_path: str, index: int, strength: float = 0.02, scale: float = 8.0):
    fc = ensure_fcurve(id_block, data_path, index)
    if not fc.keyframe_points:   # noise needs a curve to sit on
        fc.keyframe_points.insert(bpy.context.scene.frame_start, id_block.path_resolve(data_path)[index])
    m = fc.modifiers.new("NOISE")
    m.strength, m.scale = strength, scale
    return m


def value_at(id_block, data_path: str, index: int, frame: float) -> float:
    for fc in fcurves(id_block):
        if fc.data_path == data_path and fc.array_index == index:
            return fc.evaluate(frame)
    raise KeyError(f"{data_path}[{index}]")
