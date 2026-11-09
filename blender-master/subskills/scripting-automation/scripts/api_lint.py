#!/usr/bin/env python3
"""Static lint for bpy scripts targeting Blender 5.2: flags 4.x-era API use and unsafe habits.

python api_lint.py file_or_dir [...]      exit 0 = clean, 1 = findings
Lines can opt out with a trailing comment:  # api-lint: ok
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RULES = [
    (r"BLENDER_EEVEE_NEXT", "engine id is BLENDER_EEVEE in 5.x"),
    (r"\bscene\.node_tree\b|\bcontext\.scene\.node_tree\b", "compositor: use scene.compositing_node_group (node group data-block)"),
    (r"CompositorNodeComposite", "Composite node removed: end the tree in a Group Output node"),
    (r"\.use_nodes\s*=\s*True", "use_nodes is a deprecated no-op in 5.x: node trees exist on creation"),
    (r"\baction\.fcurves\b|\.action\.fcurves\b", "layered actions: reach F-Curves via the slot's channelbag"),
    (r"\baction\.groups\b", "layered actions: groups live on the channelbag"),
    (r"\bmod(ifier)?\[\s*[\"'](Socket_|Input_)\d+", "GN inputs: use mod.properties.inputs (5.2)"),
    (r"solver\s*=\s*[\"']FAST[\"']", "Boolean solver FAST is called FLOAT"),
    (r"\.sequences(_all)?\b", "VSE: use sequence_editor.strips"),
    (r"frame_final_duration|frame_offset_start|frame_offset_end", "VSE 5.1 names: duration / left_handle_offset / right_handle_offset"),
    (r"\bimport bgl\b", "bgl was removed: use the gpu module"),
    (r"\bbrush\.sculpt_tool\b", "brush.sculpt_tool -> brush.sculpt_brush_type"),
    (r"CompositorNodeMixRGB|CompositorNodeMapRange|CompositorNodeGamma", "use the shared ShaderNodeMix / MapRange / Gamma nodes"),
    (r"rl\.outputs\[\s*[\"']Z[\"']\s*\]", "render pass Z is called Depth"),
    (r"glare_type\s*=|\.variation\s*=", "compositor node options are input sockets now"),
    (r"bpy\.types\.GreasePencilv3|grease_pencils_v3", "GP v3 types are bpy.types.GreasePencil / bpy.data.grease_pencils"),
    (r"\bexec\(|\beval\(", "no exec/eval of generated strings"),
    (r"\bos\.system\(|subprocess\.(call|run|Popen)\(.*shell\s*=\s*True", "no shell execution from scene scripts"),
    (r"save(_as)?_mainfile\((?![^)]*copy\s*=\s*True)", "save a copy or a versioned file; never overwrite the user's .blend"),
    (r"use_scripts_auto_execute\s*=\s*True", "never enable auto-run of scripts in files"),
    (r"addon_install|extensions\.package_install", "installing add-ons needs an explicit user yes"),
]
SKIP_DIRS = {"_output", "out", ".git", "__pycache__"}
COMPILED = [(re.compile(p), msg) for p, msg in RULES]


def lint_text(text: str, name: str = "<chunk>") -> list[str]:
    out = []
    for ln, line in enumerate(text.splitlines(), 1):
        if "api-lint: ok" in line or line.lstrip().startswith("#"):
            continue
        for rx, msg in COMPILED:
            if rx.search(line):
                out.append(f"{name}:{ln}: {msg}")
    return out


def lint_paths(paths) -> list[str]:
    out = []
    for p in paths:
        p = Path(p)
        files = sorted(f for f in p.rglob("*.py") if not SKIP_DIRS & set(f.parts)) if p.is_dir() else [p]
        for f in files:
            if f.name == "api_lint.py":
                continue
            out += lint_text(f.read_text(encoding="utf-8"), str(f))
    return out


if __name__ == "__main__":
    findings = lint_paths(sys.argv[1:] or ["."])
    for f in findings:
        print(f)
    print(f"api-lint: {'FAIL' if findings else 'PASS'} ({len(findings)})")
    sys.exit(1 if findings else 0)
