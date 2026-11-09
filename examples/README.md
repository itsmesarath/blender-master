# Examples (text only)

Each folder holds the one-line request (`request.txt`), the parameters an agent would write
after recognition (`params.json`: facts, assumptions and ops per part) and a walk-through
(`README.md`: parts, checks and what to look at). No `.blend` files or
renders are stored; run an example to produce them in the ignored `out/` folder.

| Example | Recognised as | Parts |
|---|---|---|
| [01-product-packshot](01-product-packshot/README.md) | product shot | blockout, model, materials, product (studio lights, DOF), render, QA |
| [02-game-prop-crate](02-game-prop-crate/README.md) | game asset (hard-surface prop) | blockout, model, UV, materials, lighting, render, QA, export (FBX + glTF) |
| [03-small-interior](03-small-interior/README.md) | interior | blockout, model, materials, lighting, render, QA |
| [04-character-full-run](04-character-full-run/README.md) | character (type pinned) | blockout, skin-modifier body, sculpt, retopo, UV, normal + AO bake, zoned materials, hair, face rig, body rig with leg IK, wave animation, lighting, render, QA, FBX export + re-import |
| [05-procedural-city-block](05-procedural-city-block/README.md) | environment + procedural | blockout, terrain and street, instance sources, geometry-nodes buildings / tree scatter / lamp row, materials, sun and sky, render, QA |
| [06-product-ad-shot](06-product-ad-shot/README.md) | product shot + simulation, `add_roles: [edit]` | blockout, model, materials, rigid-body pebbles, studio + cloth reveal + logo + end card, frame renders, sequencer cut to MP4 with a generated tone, QA |

```
export BLENDER_BIN=/path/to/blender
N=01-product-packshot
python3 blender-master/scripts/plan_project.py --request "$(cat examples/$N/request.txt)" \
    --params examples/$N/params.json --out out/$N
python3 blender-master/scripts/run_project.py --brief out/$N/brief/brief.json --out out/$N
```
