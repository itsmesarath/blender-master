"""Template for a standalone headless step. Copy, rename, fill in build() and checks().

blender -b [input.blend] --factory-startup --python-exit-code 1 --python my_step.py -- \
        --out OUTDIR [--param value]

Rules this template enforces: version guard first, arguments after "--", idempotent build
(re-running replaces, never duplicates), data API before operators, a JSON report, and a
versioned copy instead of overwriting any file.
"""
import argparse
import os
import sys

LIB = os.environ.get("BLENDER_MASTER_LIB") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib")
sys.path.insert(0, LIB)

import bpy  # noqa: E402

import bm_io  # noqa: E402
import bm_mesh  # noqa: E402
import bm_report  # noqa: E402
import bm_verify  # noqa: E402
from bm_version import require_blender  # noqa: E402


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--spacing", type=float, default=0.3)
    return ap.parse_args(bm_report.script_args())


def build(a):
    """Example generator: a row of boxes of increasing height. Replace with the real step."""
    names = []
    for i in range(a.count):
        o = bm_mesh.box(f"GEO_step_{i:02d}", (0.2, 0.2, 0.1 + 0.05 * i), (i * a.spacing, 0, 0))
        names.append(o.name)
    return names


def checks(a, rep, names):
    rep.check("count", len([o for o in bpy.data.objects if o.name.startswith("GEO_step_")]) == a.count,
              len(names), a.count, "idempotent: rerun must not add objects")
    tallest = bpy.data.objects[names[-1]]
    lo, hi = bm_verify.world_bounds(tallest)
    rep.check("height", abs((hi.z - lo.z) - (0.1 + 0.05 * (a.count - 1))) < 1e-4, round(hi.z - lo.z, 4))


def main():
    require_blender()
    a = parse()
    rep = bm_report.Report("step", "scripting-automation")
    try:
        names = build(a)
        names = build(a)          # second call proves idempotency
        checks(a, rep, names)
        rep.artefact(bm_io.versioned_save(os.path.join(a.out, "blend"), "step"), "blend")
    except Exception as exc:
        rep.error(exc)
    data = rep.finish(os.path.join(a.out, "reports", "step.json"))
    sys.exit(0 if data["pass"] else 1)


main()
