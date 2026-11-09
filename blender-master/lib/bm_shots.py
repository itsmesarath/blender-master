"""Look step for live sessions: viewport screenshot when a window exists, render fallback headless."""
from __future__ import annotations

import bpy

import bm_render


def look(path: str, camera=None) -> dict:
    """Save an image of the current state. Returns {path, method}."""
    wm = bpy.context.window_manager
    if not bpy.app.background and wm.windows:
        win = wm.windows[0]
        try:
            with bpy.context.temp_override(window=win):
                bpy.ops.screen.screenshot(filepath=path)
            return {"path": path, "method": "screen_screenshot"}
        except Exception as exc:  # fall through to a render
            print(f"[blender-master] screenshot failed ({exc}); rendering instead")
    bm_render.render_still(path, camera)
    return {"path": path, "method": "render_fallback"}
