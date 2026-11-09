# Execution modes

| Mode | Use when | How | What you can verify |
|---|---|---|---|
| **Headless** (default) | agent has a shell and a Blender binary; reproducible builds; CI | `run_project.py` launches one `blender -b <copy> --factory-startup --python-exit-code 1 --python part_entry.py -- ...` per part | every numeric check + rendered previews |
| **Live MCP** | user has Blender open with an MCP add-on and wants to watch or steer | small code chunks through the MCP tool, one object or system at a time; see `subskills/live-control-mcp` | scene queries, viewport screenshots, the same checks run as chunks |
| **Manual** | no shell or MCP; the user wants to learn; or the step is hand art | numbered click-path for the Blender 5.2 UI with exact values; the user reports back or sends a screenshot | user screenshots; re-run checks on the saved file if you receive it |

Mixed is normal: headless blockout -> manual sculpt -> headless UVs and export.

## Headless details

```
python blender-master/scripts/plan_project.py --request "..." --params params.json --out proj
python blender-master/scripts/run_project.py  --brief proj/brief/brief.json --out proj [--blender PATH]
```

- Blender is found from `--blender`, `$BLENDER_BIN`, then `PATH`.
- `--factory-startup` ignores user preferences and add-ons, so results do not depend on the machine.
- Each part opens the previous PASS version (`blend/<project>_v###.blend`) and saves a new one.
  To start from the user's file use `--input-blend file.blend`: it is copied first and the
  original is never written.
- A crash is retried from the same input up to 3 attempts; a part that ends ASK or ERROR blocks
  the parts that depend on it.
- Outputs: `reports/<part>.json`, `previews/`, `renders/`, `exports/`, `brief/qa_report.md`,
  `run_summary.json`, `run_log.txt`.
- CPU Cycles renders previews everywhere. EEVEE also works in background mode where a GPU or
  software OpenGL is available; check with a tiny render before relying on it.

## Choosing per part

- Anything procedural, measurable, or repeated: headless.
- Anything the user must see while it happens (layout decisions, look-dev with taste calls): live.
- Brush work, combing, weight touch-up, artistic sculpting: manual, with headless checks after.

## Manual-mode step format

```
Step 3 of 7: bevel the crate edges
1. Select GEO_crate_body. Properties > Modifiers > Add Modifier > Generate > Bevel.
2. Amount 0.006 m, Segments 2, Limit Method Angle 40 deg, Harden Normals on.
3. Add Modifier > Normals > Weighted Normal, Keep Sharp on.
Check: edges show a thin highlight in the viewport; send a screenshot of the hero camera view.
```
