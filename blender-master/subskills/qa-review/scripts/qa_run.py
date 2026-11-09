"""Standalone QA on any .blend (works without a project brief).

blender -b scene.blend --factory-startup --python qa_run.py -- --out qa_out [--brief brief.json]
           [--prefix GEO_] [--max-tris N] [--size X Y Z]

Exit code 0 when every check passes, 3 when something fails (so CI and agents can branch).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "lib"))

import bm_part  # noqa: E402
import bm_report  # noqa: E402
import bm_version  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--brief")
    ap.add_argument("--prefix", default="GEO_")
    ap.add_argument("--max-tris", type=int)
    ap.add_argument("--size", nargs=3, type=float)
    a = ap.parse_args(bm_report.script_args())
    bm_version.require_blender()
    if a.brief:
        brief = json.load(open(a.brief))
    else:
        acc = [{"check": "objects_exist", "args": {"prefix": a.prefix}},
               {"check": "manifold", "args": {"objects": a.prefix}},
               {"check": "normals_outward", "args": {"objects": a.prefix}},
               {"check": "no_overlaps", "args": {"objects": a.prefix}},
               {"check": "no_floating", "args": {"objects": a.prefix}}]
        if a.max_tris:
            acc.append({"check": "tri_budget", "args": {"objects": a.prefix, "max_tris": a.max_tris}})
        if a.size:
            acc.append({"check": "bounds_size", "args": {"objects": a.prefix, "target": a.size}})
        brief = {"project": "qa", "facts": {}, "parts": [{"id": "P00-scene", "role": "model", "subskill": "qa-review",
                                                          "acceptance": acc}]}
    part = {"id": "QA", "role": "qa", "subskill": "qa-review"}
    rep = bm_report.Report("QA", "qa-review")
    ctx = bm_part.Ctx(brief, part, a.out, 1, rep, os.path.join(HERE, "..", "..", ".."))
    mod = bm_part.load_subskill(ctx.skill_root, "qa-review")
    print(mod.qa_run(ctx))
    sys.exit(0 if ctx.qa_result["pass"] else 3)


main()
