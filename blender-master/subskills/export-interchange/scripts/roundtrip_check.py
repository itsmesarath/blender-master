"""Import one exported file into an empty scene and write a JSON summary.
blender -b --factory-startup --python roundtrip_check.py -- <file> <out.json>
Sizes are compared axis-sorted, so a Y-up file still matches its Z-up source."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "lib"))

import bpy  # noqa: E402

import bm_export  # noqa: E402
import bm_verify  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
src, out = args[0], args[1]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
objs = bm_export.import_file(src)
bpy.context.view_layer.update()
summary = bm_export.summary(objs)
meshes = [o for o in objs if o.type == "MESH"]
lo, hi = bm_verify.bounds_of(meshes)
summary["size"] = [round(v, 4) for v in (hi - lo)]
summary["file"] = os.path.basename(src)
with open(out, "w") as f:
    json.dump(summary, f, indent=2)
print("roundtrip", summary)
