"""qa-review ops: re-run every earlier acceptance check on the final file, add generic scene
hygiene checks, render a contact sheet, write brief/qa_report.md + .json."""
from __future__ import annotations

import json
import os
import time

import bpy

import bm_checks
import bm_part
import bm_render

GENERIC = [  # applied to every project on top of the parts' own checks
    {"check": "names_valid", "desc": "naming convention"},
    {"check": "scale_applied", "args": {"objects": "GEO_"}, "desc": "scale applied"},
    {"check": "materials_filled", "args": {"objects": "GEO_"}, "desc": "no empty material slots"},
]
SKIP_ROLES = {"qa", "export"}
# checks that describe a run, not the final file (they cannot be re-measured later)
RUNTIME_ONLY = {"script_ran", "roundtrip_match", "qa_all_pass"}


def _run_items(ctx, items):
    rows = []
    for it in items:
        ok, value, expected, detail = bm_checks.run(ctx, it)
        rows.append({"check": it["check"], "pass": bool(ok), "desc": it.get("desc", ""), "value": _short(value),
                     "expected": _short(expected), "detail": detail})
    return rows


def _short(v, n=160):
    s = json.dumps(v, default=str)
    return s if len(s) <= n else s[:n] + "..."


def qa_run(ctx, contact_sheet=True, known_issues=()):
    brief = ctx.brief
    table = []
    sc = bpy.context.scene
    sc.frame_set(sc.frame_start)   # geometry checks read the first frame (rest or start pose)
    for part in brief["parts"]:
        if part["role"] in SKIP_ROLES or part.get("mode") == "manual":
            continue
        try:   # the part's sub-skill registers its own checks
            bm_part.load_subskill(ctx.skill_root, part["subskill"])
        except FileNotFoundError:
            pass
        items = [it for it in part.get("acceptance", []) if it["check"] not in RUNTIME_ONLY]
        for row in _run_items(ctx, items):
            table.append({"part": part["id"], **row})
    for row in _run_items(ctx, GENERIC):
        table.append({"part": "generic", **row})
    sheet = None
    if contact_sheet:
        objs = bm_checks.select("GEO_") or bm_checks.select("*")
        if objs:
            with bm_render.preview_scope():
                bm_render.preview_settings(samples=12, res=(240, 240))
                sheet = bm_render.contact_sheet(objs, ctx.path("brief", "qa_contact_sheet.png"), tile=(240, 240))
            ctx.report.artefact(sheet, "contact_sheet")
    rdir = os.path.join(ctx.out_dir, "renders")
    renders = sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []
    passed = all(r["pass"] for r in table)
    result = {"project": brief["project"], "pass": passed, "checked": len(table),
              "failed": [r for r in table if not r["pass"]], "rows": table, "renders": renders,
              "contact_sheet": sheet, "known_issues": list(known_issues),
              "blender": bpy.app.version_string, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(ctx.path("brief", "qa_report.json"), "w") as f:
        json.dump(result, f, indent=2)
    md = [f"# QA report: {brief['project']}", "",
          f"Result: **{'PASS' if passed else 'FAIL'}** ({len(table) - len(result['failed'])}/{len(table)} checks)",
          f"Blender {bpy.app.version_string}", "", "| Part | Check | Result | Value | Note |", "|---|---|---|---|---|"]
    for r in table:
        md.append(f"| {r['part']} | {r['check']} | {'PASS' if r['pass'] else 'FAIL'} | `{r['value']}` | {r['desc']} |")
    md += ["", "## Renders", ""] + [f"- renders/{r}" for r in renders]
    if sheet:
        md += ["", "Contact sheet: brief/qa_contact_sheet.png"]
    md += ["", "## Known issues", ""] + ([f"- {k}" for k in known_issues] or ["- none recorded"])
    with open(ctx.path("brief", "qa_report.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    ctx.qa_result = result
    return f"QA {'PASS' if passed else 'FAIL'} {len(table) - len(result['failed'])}/{len(table)}"


@bm_checks.register("qa_all_pass")
def _qa_all_pass(ctx):
    res = getattr(ctx, "qa_result", None)
    if res is None:
        p = os.path.join(ctx.out_dir, "brief", "qa_report.json")
        res = json.load(open(p)) if os.path.exists(p) else None
    if res is None:
        return False, None, True, "qa_run has not been run"
    return res["pass"], [f"{r['part']}:{r['check']}" for r in res["failed"]], [], f"{res['checked']} checks"


OPS = {"qa_run": qa_run}
FIXES = {}
