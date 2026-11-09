---
name: scripting-automation
description: Writes, lints and tests Blender 5.2 Python (bpy) scripts - generators, batch jobs, custom operators, headless pipelines and add-on/extension scaffolds - with idempotent re-runs, 5.x API checks and safe file handling. Use when the user wants a script, automation, batch processing, a custom tool or operator, or when a part needs code that no other sub-skill provides.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3, bundled Python 3.13). Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Scripting and automation

Deliver Blender Python that runs headless on the first try, can run twice without making a mess,
and does not touch anything outside its job.

## Procedure
1. **Spec**: inputs, outputs, what "done" looks like as a check (counts, sizes, files).
2. **Find the API**: prefer the data API (`bpy.data`, object/mesh properties, `bmesh`) over
   operators. Operators depend on context (active object, mode, area) and break headless. When an
   operator is the only way, set the context explicitly (`with bpy.context.temp_override(...)`)
   and select only what it should act on.
3. **Write it idempotent**: get-or-create by name, remove-and-rebuild generated objects, never
   "add another". Start from `scripts/part_script_template.py`.
4. **Guard the version**: `bm_version.require_blender((5, 0))` at the top.
5. **Lint**: `python scripts/api_lint.py <file>` flags 4.x-era API use (engine id, compositor,
   layered actions, GN inputs, VSE strips, removed modules) and unsafe habits (exec/eval, shell
   calls, overwriting saves, enabling auto-run, installing add-ons).
6. **Test headless**: `blender -b --factory-startup --python-exit-code 1 --python script.py -- args`.
   Run it twice; the second run must produce the same scene (same object count and names).
7. **Report**: write a JSON report with `bm_report.Report` and exit non-zero on failure.

Patterns, operator context, add-on and extension scaffolds:
[references/scripting-guide.md](references/scripting-guide.md).

## Running a script as a project part
`run_script(path, args)` executes a `.py` inside the part's Blender session. Only files inside
the project folder are allowed and they are linted first; the `script_ran` check passes only if
it finished without an exception.

## Rules
- No `exec`/`eval` of generated strings, no shell commands, no network calls in scene scripts.
- Write only inside the project folder; save with `copy=True` or versioned names.
- No installing add-ons, extensions or pip packages without an explicit yes for that package.
- Keep scripts small: one job per file; shared helpers go in a module.

## Scripts
- `scripts/api_lint.py`: static checker (exit 1 on findings; `# api-lint: ok` to waive a line).
- `scripts/part_script_template.py`: idempotent script skeleton with a report.
- `scripts/ops.py`: `run_script` op and the `script_ran` check.
