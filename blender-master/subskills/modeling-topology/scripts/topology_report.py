"""Topology report for one or more meshes.

Run inside Blender:
  blender -b file.blend --python topology_report.py -- --objects GEO_ [--out report.json]

Prints JSON: per object quads / tris / ngons, pole counts by valence, boundary and
non-manifold edges, loose parts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "lib")))

import bm_checks  # noqa: E402
import bm_verify  # noqa: E402


def report(selector: str) -> dict:
    out = {}
    for obj in bm_checks.select(selector):
        out[obj.name] = {"faces": bm_verify.face_stats(obj), "poles": bm_verify.poles(obj),
                         "manifold": bm_verify.manifold_report(obj)}
    return out


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", default="GEO_")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    data = report(a.objects)
    text = json.dumps(data, indent=2, default=str)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
