---
name: blender-master
description: Plans and builds Blender 5.2 projects end to end. Use when the user asks for anything made in Blender (a model, prop, product shot, interior, environment, character, procedural system, simulation, render, export, or a bpy script) or wants to drive Blender live through MCP. It recognises the project type, writes a brief with a part list and measurable checks, routes each part to a focused sub-skill, runs it headless, through MCP or as manual steps, verifies every part with numeric checks and preview renders, then does final QA and export.
license: MIT
compatibility: Blender 5.2 LTS (tested 5.2.3, bundled Python 3.13). Helper scripts need Blender on the machine; the planning scripts need only Python 3.10+.
metadata:
  version: "0.2.0-dev"
  blender: "5.2"
---

# blender-master

A coordinator. It never builds a whole project in one go. It turns a request into small parts with
checks, hands each part to the right sub-skill, and proves each part works before moving on.

```
INTAKE -> RECOGNISE -> DECOMPOSE -> ROUTE -> EXECUTE + VERIFY (per part) -> FINAL QA -> DELIVER
```

Everything is written into a project folder (`<project>/brief/`, `reports/`, `previews/`,
`blend/`, `renders/`, `exports/`), so work resumes cleanly after a crash or in a new session.

## 1. Intake

Read: the request, any reference images or files, the target use (still, clip, game asset, print,
web), the Blender version (`blender --version`), and whether a live Blender is reachable via MCP.

Ask only what changes the plan, at most 3 questions in one message:
deliverable, style, real-world size when it matters, target engine/platform for exports.
Everything else gets a sensible default that you write into the brief as an assumption.

## 2. Recognise

Score the request against the 15 project types in [references/taxonomy.md](references/taxonomy.md)
(signals and default parts; machine-readable copy in `references/taxonomy.json`):

character, creature/furry, hard-surface prop, product/ad shot, environment, architecture/interior,
procedural system, VFX/simulation, motion graphics, stylised/NPR, game asset, rigging only,
look-dev/render only, scripting/automation, 2D/Grease Pencil.

Pick one primary type plus modifiers (e.g. *prop + game export*). If the top two types are close
**and** would give different part lists, ask one question; otherwise state the assumption.
`python scripts/recognize.py "<request>"` prints the scores.

## 3. Decompose

Write the project brief ([references/brief-schema.md](references/brief-schema.md),
template `templates/project_brief.json`):

- **facts**: sizes in metres, subject object prefix, hero camera, resolution, budgets.
- **spatial brief** for anything with more than one object: real-scale proxies, named hero
  cameras, a note pinned to every proxy, and a review layer (red = fix/remove, green = add).
- **parts**: a dependency graph. Each part has a role, a sub-skill, `depends_on`, its ops, and
  **acceptance checks that are numbers**, plus one visual check from a hero camera.

DAG rules: a part starts only when its dependencies PASS. Topology freezes before UVs, shape keys
and rigging. Geometry freezes before lighting polish. Scale is applied before physics and export.

`python scripts/plan_project.py --request "..." --params params.json --out <project>` fills in the
type, default parts, routing, dependencies and default checks; you supply facts and ops in
`params.json` after reading the routed sub-skills.

## 4. Route

Use [references/routing.md](references/routing.md). All 22 sub-skills are core:

| Part (role) | Sub-skill |
|---|---|
| Blockout, layout, hero cameras, review layer (`blockout`) | [blockout-spatial-brief](subskills/blockout-spatial-brief/SKILL.md) |
| Polygon modelling: hard-surface, organic base meshes, rooms (`model`) | [modeling-topology](subskills/modeling-topology/SKILL.md) |
| Sculpt detail, multires, voxel remesh, symmetry (`sculpt`) | [sculpting](subskills/sculpting/SKILL.md) |
| Retopology, shrinkwrap fit, quad remesh, LODs (`retopo`) | [retopology](subskills/retopology/SKILL.md) |
| UV seams, unwrap, packing, texel density, baking (`uv`, `bake`) | [uv-texturing-baking](subskills/uv-texturing-baking/SKILL.md) |
| PBR and procedural materials, texture wiring (`materials`) | [materials-shading](subskills/materials-shading/SKILL.md) |
| Toon, outlines, line art, painterly finishes (`npr`) | [npr-stylized](subskills/npr-stylized/SKILL.md) |
| Hair, fur, grooming with curves (`hair`) | [hair-fur](subskills/hair-fur/SKILL.md) |
| Body rig, IK, skinning, weights (`rig_body`) | [rigging-body](subskills/rigging-body/SKILL.md) |
| Face shape keys, controls, drivers (`rig_face`) | [rigging-face](subskills/rigging-face/SKILL.md) |
| Keyframes, cycles, noise, paths, NLA (`animation`) | [animation](subskills/animation/SKILL.md) |
| Rigid bodies, cloth and clothing, soft bodies, particles, smoke, liquid (`simulation`) | [physics-simulation](subskills/physics-simulation/SKILL.md) |
| Terrain, streets, modular kits, set dressing (`environment`) | [scene-environment](subskills/scene-environment/SKILL.md) |
| Geometry-nodes generators, scattering, instancing (`procedural`) | [geometry-nodes](subskills/geometry-nodes/SKILL.md) |
| Lights, world, cameras, lenses, depth of field (`lighting`) | [lighting-cameras](subskills/lighting-cameras/SKILL.md) |
| Studio packshots, turntables, reveals, logo and end cards (`product`) | [product-shots](subskills/product-shots/SKILL.md) |
| Engines, samples, passes, compositor, output (`render`) | [render-compositing](subskills/render-compositing/SKILL.md) |
| Sequencer cut, titles, sound, MP4 encode (`edit`) | [video-editing](subskills/video-editing/SKILL.md) |
| bpy scripts, generators, batch jobs, add-ons (`script`) | [scripting-automation](subskills/scripting-automation/SKILL.md) |
| Checks, contact sheets, paint-over review, QA report (`qa`) | [qa-review](subskills/qa-review/SKILL.md) |
| FBX / glTF / USD / Alembic, engine presets, round-trip (`export`) | [export-interchange](subskills/export-interchange/SKILL.md) |
| Driving a live Blender through MCP (`live`) | [live-control-mcp](subskills/live-control-mcp/SKILL.md) |

Planned for later: 2D Grease Pencil animation and asset management; those roles route to a
fallback, and the brief says so. Use `add_roles` / `skip_roles` in params to add a part a type
does not include (for example an `edit` pass for a product clip) or drop one.

Read a sub-skill's `SKILL.md` only when a part is routed to it.

## 5. Execute and verify, one part at a time

Choose the mode per part ([references/execution-modes.md](references/execution-modes.md)):

- **Headless** (default with a shell and Blender): `python scripts/run_project.py --brief
  <project>/brief/brief.json --out <project>`. One Blender process per part, on a copy.
- **Live MCP**: the user watches their own Blender. One small code chunk per object or system,
  then look, then verify. See live-control-mcp.
- **Manual**: numbered click-paths with exact values, for hand work (sculpt strokes, grooming,
  weight touch-ups) or when the user wants to learn.

Mixed modes are normal. Per part ([references/verify-loop.md](references/verify-loop.md)):

1. Run the ops.
2. Run the acceptance checks (bounds, overlaps, normals, n-gons, material slots, framing,
   exposure, output files...). Catalogue: [references/checks.md](references/checks.md).
3. **FIX**: apply the automatic fixer for a failed check, re-check. At most 3 rounds.
4. Render a preview from the hero camera and **look at it** against the part's goal.
5. **PASS** -> versioned save `<project>_v###.blend` and the report `reports/<part>.json`.
   **ASK** -> stop dependants and show the user the preview and the exact failing numbers.
   Never loosen a check silently to make it pass; if a threshold was wrong, change it in the
   brief and say why.

## 6. Final QA and delivery

Run the qa-review part last: every earlier check again on the final file, generic hygiene checks,
a contact sheet, `brief/qa_report.md`. Then export if the brief asks (export-interchange does a
re-import round-trip). Deliver: renders, the versioned .blend, exports, the QA report, and a list
of anything untested (GPU look, engine import, modal tools).

## 7. Safety (always)

Full rules: [references/safety.md](references/safety.md).

- Show generated code and get the host's approval before it runs in the user's own Blender.
- Work on copies. Never overwrite the user's file; save `_v001`, `_v002`... and checkpoint before
  destructive steps (apply, boolean, remesh, join, decimate).
- No installing add-ons, extensions, pip packages or downloaded scripts, no auto-run of scripts
  in untrusted files, and no MCP socket beyond localhost without an explicit yes.
- No paid services (AI generators, asset stores, render farms) and no API keys without an
  explicit yes for that use. Never print or store secrets.
- For cultural, religious or real-person subjects, confirm the intended depiction in the brief.

## Reference map

- Blender 5.x API changes that break older scripts: [references/blender-5.2-api-notes.md](references/blender-5.2-api-notes.md)
- Names, prefixes, collections, units: [references/naming-conventions.md](references/naming-conventions.md)
- Shared Python helpers (run inside Blender): `lib/bm_*.py`, described in [references/lib.md](references/lib.md)
- Worked text examples: `examples/` at the repository root
