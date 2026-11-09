"""Version guard and feature flags. Import this first in every script that runs inside Blender."""
from __future__ import annotations

import bpy

TARGET = (5, 2)
TESTED = (5, 2, 3)


class BlenderVersionError(RuntimeError):
    pass


def version() -> tuple[int, int, int]:
    return tuple(bpy.app.version)  # type: ignore[return-value]


def require_blender(minimum: tuple[int, int] = TARGET, allow_old: bool = False) -> tuple[int, int, int]:
    """Refuse below 5.0, warn on 5.0/5.1, pass on 5.2+.

    The skill's scripts use 5.x-only APIs (compositor node groups, layered actions, socket-based
    node options, ``mod.properties.inputs``). Running them on 4.x fails in confusing places, so stop early.
    """
    v = version()
    if v[:2] < (5, 0) and not allow_old:
        raise BlenderVersionError(
            f"blender-master needs Blender 5.x (target {TARGET[0]}.{TARGET[1]}); this is "
            f"{bpy.app.version_string}. Pass allow_old=True only to read old files, not to build.")
    if v[:2] < minimum:
        print(f"[blender-master] WARNING: tested on {'.'.join(map(str, TESTED))}; running "
              f"{bpy.app.version_string}. Some helpers may be missing.")
    return v


def eevee_id() -> str:
    """Engine identifier for EEVEE (renamed back to BLENDER_EEVEE in 5.0)."""
    return "BLENDER_EEVEE" if version()[:2] >= (5, 0) else "BLENDER_EEVEE_NEXT"  # api-lint: ok (4.2-4.5 id)


def has(feature: str) -> bool:
    """Feature flags so callers can branch without hard-coding versions."""
    v = version()[:2]
    flags = {
        "compositor_node_group": v >= (5, 0),
        "layered_actions_only": v >= (5, 0),
        "gn_properties_inputs": v >= (5, 2),
        "boolean_manifold": v >= (5, 0),
        "strips_api": v >= (5, 0),
        "window_screenshot": v >= (5, 2),
    }
    if feature not in flags:
        raise KeyError(feature)
    return flags[feature]
