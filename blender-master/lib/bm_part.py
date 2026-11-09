"""Part runtime: executes one part of a project brief inside Blender and writes its report.

Called by ``scripts/part_entry.py`` (which the coordinator's runner launches as
``blender -b [input.blend] --factory-startup --python-exit-code 1 --python part_entry.py -- ...``).

Flow per part: ops -> acceptance checks -> up to 3 automatic fix rounds -> PASS or ASK
-> preview render(s) -> versioned save -> JSON report.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

import bpy

import bm_checks
import bm_io
import bm_render
import bm_report
import bm_version

MAX_FIX_ROUNDS = 3


class Ctx:
    def __init__(self, brief, part, out_dir, attempt, report, skill_root):
        self.brief, self.part, self.out_dir = brief, part, out_dir
        self.part_id, self.attempt, self.report = part["id"], attempt, report
        self.skill_root = skill_root
        self.facts = brief.get("facts", {})

    def path(self, *parts) -> str:
        p = os.path.join(self.out_dir, *parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p


def load_subskill(skill_root: str, name: str):
    path = os.path.join(skill_root, "subskills", name, "scripts", "ops.py")
    if not os.path.exists(path):
        raise FileNotFoundError(f"sub-skill {name!r} has no scripts/ops.py (is it implemented yet?)")
    mod_name = "ops_" + name.replace("-", "_")
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def evaluate(ctx, items) -> None:
    ctx.report.reset_checks()
    for item in items:
        ok, value, expected, detail = bm_checks.run(ctx, item)
        ctx.report.check(item["check"], ok, value, expected, item.get("desc", detail) or detail)


def run_part(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--part", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skill-root", required=True)
    ap.add_argument("--attempt", type=int, default=1)
    a = ap.parse_args(bm_report.script_args(argv))

    brief = json.load(open(a.brief))
    part = next(p for p in brief["parts"] if p["id"] == a.part)
    rep = bm_report.Report(part["id"], part["subskill"], a.attempt)
    ctx = Ctx(brief, part, a.out, a.attempt, rep, a.skill_root)
    report_path = os.path.join(a.out, "reports", f"{part['id']}.json")
    status = "PASS"
    try:
        bm_version.require_blender()
        mod = load_subskill(a.skill_root, part["subskill"])
        for op in part.get("ops", []):
            fn = mod.OPS.get(op["op"])
            if fn is None:
                raise KeyError(f"{part['subskill']} has no op {op['op']!r}; known: {sorted(mod.OPS)}")
            result = fn(ctx, **op.get("args", {}))
            rep.note(f"{op['op']}: {result}")
        bpy.context.view_layer.update()
        items = part.get("acceptance", [])
        evaluate(ctx, items)
        rounds = 0
        while rep.failed() and rounds < MAX_FIX_ROUNDS:
            applied = False
            for c in rep.failed():
                item = next(i for i in items if i["check"] == c["name"])
                fixer = getattr(mod, "FIXES", {}).get(c["name"]) or bm_checks.FIXES.get(c["name"])
                if fixer:
                    msg = str(fixer(ctx, item.get("args", {}), rounds + 1))
                    rep.fix(f"round {rounds + 1} {c['name']}: {msg}")
                    applied = applied or not msg.startswith("SKIP")
            if not applied:
                rep.note("no automatic fix available for: " + ", ".join(c["name"] for c in rep.failed()))
                break
            rounds += 1
            bpy.context.view_layer.update()
            evaluate(ctx, items)
        rep.data["fix_rounds"] = rounds
        if rep.failed():
            status = "ASK"
            rep.data["question"] = ("Part %s still fails %s after %d fix round(s). Review the preview and "
                                    "decide: adjust the brief, accept, or fix by hand." %
                                    (part["id"], [c["name"] for c in rep.failed()], rounds))
        _previews(ctx, part)
        blend = bm_io.versioned_save(os.path.join(a.out, "blend"), brief["project"])
        rep.artefact(blend, "blend")
        rep.data["blend"] = blend
    except Exception as exc:
        rep.error(exc)
        status = "ERROR"
    rep.data["status"] = status
    return rep.finish(report_path)


def _previews(ctx, part) -> None:
    pv = part.get("preview", {"cameras": ["CAM_hero"]})
    if not pv:
        return
    scene = bpy.context.scene
    cams = [c for c in pv.get("cameras", []) if c in bpy.data.objects]
    if not cams and scene.camera is not None:
        cams = [scene.camera.name]
    with bm_render.preview_scope(scene):
        bm_render.preview_settings(samples=pv.get("samples", 16), res=tuple(pv.get("res", (480, 270))),
                                   transparent=scene.render.film_transparent)
        for cam in cams:
            p = bm_render.render_still(ctx.path("previews", f"{ctx.part_id}_{cam}.png"), cam)
            ctx.report.artefact(p, "preview")
        if pv.get("contact_sheet"):
            import bm_checks as C
            objs = C.select(pv.get("objects", "*"))
            if objs:
                p = bm_render.contact_sheet(objs, ctx.path("previews", f"{ctx.part_id}_sheet.png"), tile=(240, 240))
                ctx.report.artefact(p, "contact_sheet")
