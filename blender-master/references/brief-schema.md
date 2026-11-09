# Project brief format (`brief/brief.json`)

JSON, so both the planning scripts (plain Python) and Blender's bundled Python can read it with no
extra packages. Template: `templates/project_brief.json`.

```json
{
  "schema": "blender-master/brief@1",
  "project": "perfume-packshot",
  "request": "the user's words, verbatim",
  "type": {"primary": "product_shot", "modifiers": [], "scores": {"product_shot": 13}},
  "deliverables": [{"kind": "still", "res": [1920, 1080], "cameras": ["CAM_hero", "CAM_front"]}],
  "units": "metric_m",
  "style": {"look": "clean commercial"},
  "budget": {"tris": 3000, "render_minutes_per_frame": 5},
  "facts": {"subject_prefix": "GEO_bottle_", "subject_size": [0.07, 0.07, 0.13], "hero_camera": "CAM_hero"},
  "assumptions": ["bottle 7 cm wide, 13 cm tall"],
  "questions": [],
  "execution_mode": "headless",
  "parts": [
    {
      "id": "P02-model", "role": "model", "subskill": "modeling-topology", "routed_via": "primary",
      "depends_on": ["P01-blockout"], "mode": "headless", "goal": "lathed glass body + cap",
      "ops": [{"op": "lathe", "args": {"name": "GEO_bottle_glass", "profile": [[0, 0], [0.03, 0]]}}],
      "acceptance": [{"check": "bounds_size", "args": {"objects": "GEO_bottle_", "target": [0.07, 0.07, 0.13], "tol": 0.05},
                      "desc": "subject matches brief size"}],
      "preview": {"cameras": ["CAM_hero"], "samples": 16, "res": [480, 270], "contact_sheet": false}
    }
  ]
}
```

## Fields

| Field | Meaning |
|---|---|
| `type` | recognition result; `modifiers` add roles |
| `deliverables` | what the user receives: `still`, `frames`, `export`, `blend` |
| `facts` | numbers every part may use. Common keys: `subject_prefix`, `subject_proxy`, `subject_size` [x,y,z] m, `size_tol`, `ground_z`, `hero_camera`, `cameras`, `resolution`, `tri_budget`, `min_quad_ratio`, `allow_ngons`, `closed_meshes`, `frame_objects`, `frame_margin`, `min_fill`, `exposure` (overrides for the exposure check), `transparent` |
| `assumptions` | every default you chose instead of asking |
| `questions` | open questions; a non-empty list on a part that needs the answer means ASK first |
| `parts[].ops` | ordered calls into the sub-skill's `scripts/ops.py` `OPS` table |
| `parts[].acceptance` | checks from [checks.md](checks.md); every part needs at least one |
| `parts[].preview` | cameras and quality of the per-part preview; `false` to skip |
| `parts[].mode` | `headless`, `live_mcp` or `manual` |
| `parts[].status` | set by the planner: `needs_agent_input` when ops are still missing |

## params.json (what the agent writes)

`plan_project.py` merges a params file into the default decomposition:

```json
{
  "project": "slug",
  "facts": {...},
  "assumptions": [...],
  "skip_roles": ["retopo"],
  "add_roles": ["edit"],
  "type_override": {"primary": "interior", "modifiers": []},
  "roles": {
    "model": {"goal": "...", "ops": [...], "acceptance_extra": [...], "acceptance_override": [...], "preview": {...}}
  }
}
```

`add_roles` appends roles the project type does not include (for example an `edit` pass that
cuts rendered frames into an MP4 for a product shot); `skip_roles` removes roles.


## Part ids and dependency graph

Ids are `P<nn>-<role>` in role order. Dependencies come from the role graph in
[taxonomy.md](taxonomy.md), restricted to the roles present. The runner executes in topological
order on one evolving file: "parallel" parts simply have no edge between them, so their order
does not matter.

## Spatial brief (multi-object projects)

Written by blockout-spatial-brief into `brief/`:

- `spatial_brief.md`: one row per proxy (size, base position, pinned note) and the camera list.
- `cameras.json`: name, lens, type, location, rotation of every camera.
- The `.blend` itself: `PRX_*` proxies with a `brief_note` custom property, `CAM_*` hero cameras,
  `REV_review` Grease Pencil object with a `REVIEW` layer (red material = fix/remove, green = add).
- Optional `refs/` folder: reference images named by the part they belong to
  (`refs/P02-model_side.png`), so each reference has a clear scope.
