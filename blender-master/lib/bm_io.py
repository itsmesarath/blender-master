"""Safe file handling: never overwrite the user's file; versioned saves; checkpoints."""
from __future__ import annotations

import os
import re
import shutil

import bpy

VER_RE = re.compile(r"^(?P<stem>.+?)_v(?P<n>\d{3})\.blend$")


def next_version_path(directory: str, stem: str) -> str:
    os.makedirs(directory, exist_ok=True)
    n = 0
    for f in os.listdir(directory):
        m = VER_RE.match(f)
        if m and m.group("stem") == stem:
            n = max(n, int(m.group("n")))
    return os.path.join(directory, f"{stem}_v{n + 1:03d}.blend")


def versioned_save(directory: str, stem: str, compress: bool = True) -> str:
    """Save a copy as <stem>_v###.blend (next free number). The open file name is unchanged."""
    path = next_version_path(directory, stem)
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True, compress=compress, relative_remap=True)
    return path


def open_duplicate(src: str, work_dir: str | None = None) -> str:
    """Copy src to <name>_work.blend and open the copy. The original is never written."""
    work_dir = work_dir or os.path.dirname(os.path.abspath(src))
    base = os.path.splitext(os.path.basename(src))[0]
    dst = os.path.join(work_dir, f"{base}_work.blend")
    if os.path.abspath(dst) == os.path.abspath(src):
        raise RuntimeError("refusing to open the original as the work file")
    shutil.copy2(src, dst)
    bpy.ops.wm.open_mainfile(filepath=dst)
    return dst


def checkpoint(directory: str, label: str) -> str:
    """Quick copy before a destructive step (apply modifiers, remesh, join, decimate)."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"checkpoint_{re.sub(r'[^A-Za-z0-9_-]', '_', label)}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True, compress=True)
    return path
