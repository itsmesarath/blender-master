---
name: qa-review
description: Runs final quality assurance on a Blender 5.2 project or any .blend - re-runs every part's acceptance checks on the final file, adds hygiene checks (names, scale, empty slots, missing textures), renders a four-view contact sheet, runs the red/green paint-over review cycle and writes a QA report with pass/fail per check. Use when the user asks "is it ready", wants a review, a check, a QA report, or before any delivery or export.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Part of blender-master; scripts expect its lib/ on sys.path.
metadata:
  parent: blender-master
  status: core
---

# QA and review

Prove the final file still meets every promise in the brief, and show the evidence.

## Procedure
1. **Re-run every earlier part's acceptance checks** on the final file (`qa_run`). Later parts
   can break earlier ones: a material change shifts exposure, an applied modifier changes size.
2. **Hygiene checks** on top: naming prefixes, applied scale, no empty slots or missing images.
   Add project-type checks from [references/qa-checklists.md](references/qa-checklists.md)
   (e.g. triangle budget and UVs for game assets, framing for every deliverable camera).
3. **Contact sheet**: front, right, top orthographic plus a three-quarter view in one image
   (`brief/qa_contact_sheet.png`). Catches hidden problems the hero camera never shows: missing
   backs, floating parts, stray objects.
4. **Look at every render and the sheet.** Compare against the brief's goal and references.
5. **Paint-over review**: if something is visually wrong, mark it on the review layer (red =
   fix/remove, green = add) with a note, route the fix to the right sub-skill, and re-run QA.
6. **Report**: `brief/qa_report.md` and `.json` with one row per check (part, check, value,
   expected, result), the render list, the contact sheet and known issues.

The QA part passes only when every row passes. Known issues the user accepted go in
`known_issues`, never by deleting a failing check.

## Standalone use on any .blend
```
blender -b scene.blend --factory-startup --python scripts/qa_run.py -- --out qa_out \
    [--prefix GEO_] [--max-tris 5000] [--size 0.6 0.6 0.6] [--brief brief.json]
```
Exit code 0 = all pass, 3 = something failed. Never writes to the input file.
`scripts/contact_sheet.py` renders only the sheet.

## Acceptance (default)
QA report files exist and `qa_all_pass`.

## Scripts
- `scripts/ops.py`: `qa_run` op and the `qa_all_pass` check.
- `scripts/qa_run.py`: standalone QA command.
- `scripts/contact_sheet.py`: four-view sheet for any .blend.
