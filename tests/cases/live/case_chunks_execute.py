import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import contextlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402

DOC = os.path.join(H.SKILL, "subskills", "live-control-mcp", "references", "chunk-templates.md")
NEEDS_UI = {"viewport_screenshot"}


def body():
    text = open(DOC).read()
    blocks = re.findall(r"## (\w+)\n```python\n(.*?)```", text, re.S)
    H.expect("templates_found", len(blocks) >= 6, len(blocks))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H.OUT, "live_test.blend"))  # api-lint: ok (test fixture)
    for name, code in blocks:
        if name in NEEDS_UI:
            continue
        code = code.replace("<name>", "chunk_test")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(compile(code, name, "exec"), {"__name__": "__chunk__"})  # api-lint: ok (test fixture)
        last = buf.getvalue().strip().splitlines()[-1]
        H.expect(f"chunk_{name}_json", isinstance(json.loads(last), dict), last[:200])
    o = bpy.data.objects.get("GEO_chunk_test")
    H.expect("box_created", o is not None and abs(o.dimensions.x - 0.6) < 1e-4)
    H.expect("bevel_stack", o is not None and [m.type for m in o.modifiers] == ["BEVEL", "WEIGHTED_NORMAL"])
    H.expect("versioned_copy_written", os.path.exists(os.path.join(H.OUT, "live_test_v001.blend")))


H.run(body)
