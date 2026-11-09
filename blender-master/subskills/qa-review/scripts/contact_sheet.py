"""Four-view contact sheet (front, right, top, three-quarter) of any .blend.

blender -b scene.blend --factory-startup --python contact_sheet.py -- --out sheet.png [--objects GEO_]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "lib"))

import bm_checks  # noqa: E402
import bm_render  # noqa: E402
import bm_report  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--objects", default="GEO_")
ap.add_argument("--tile", type=int, default=320)
a = ap.parse_args(bm_report.script_args())
objs = bm_checks.select(a.objects)
if not objs:
    sys.exit(f"no objects match {a.objects!r}")
with bm_render.preview_scope():
    bm_render.preview_settings(samples=12, res=(a.tile, a.tile))
    print("contact sheet:", bm_render.contact_sheet(objs, os.path.abspath(a.out), tile=(a.tile, a.tile)))
