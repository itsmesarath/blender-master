# blender-master

An open agent skill that lets a coding agent plan, build and check **Blender 5.2** projects end
to end. You give it a one-line request ("a game-ready sci-fi crate for Unity", "a packshot of a
perfume bottle", "a 3-second ad for a smart speaker"). It plans the project, builds it one part
at a time with Blender's own Python API, measures each part against numeric checks, and hands back
renders, versioned `.blend` files, exports and a QA report.

It uses the open [Agent Skills](https://agentskills.io) format (a folder with a `SKILL.md`), so
any agent that loads skills can use it. Blender runs on your machine; nothing is uploaded.

> Status: `0.2.0-dev`. The coordinator and all 22 sub-skills are implemented, and each one has
> its own headless Blender test. Six example projects pass end to end on Blender 5.2.3,
> including a full character pipeline. 2D Grease Pencil animation and asset management are
> still on the backlog.

## Contents
- [Install](#install)
- [How it works](#how-it-works)
- [Sub-skills](#sub-skills)
- [Examples](#examples)
- [Running it yourself](#running-it-yourself)
- [Limits and untested areas](#limits-and-untested-areas)
- [Safety](#safety)
- [Contributing and licence](#contributing-and-licence)

## Install

Requirements: [Blender 5.2](https://www.blender.org/download/) for building and checking, and
Python 3.10+ for the planning scripts. There are no Python packages to install.

```
git clone https://github.com/itsmesarath/blender-master.git blender-master-repo && cd blender-master-repo
```

| Agent | Command | Installs to |
|---|---|---|
| Claude Code (user-wide) | `./install.sh` | `~/.claude/skills/blender-master` |
| Cursor (this project) | `./install.sh --cursor` (run from your project folder) | `.cursor/skills/blender-master` |
| Any other skills-aware agent | `./install.sh --dir PATH` | `PATH/blender-master` |
| Windows (PowerShell) | `.\install.ps1 [-Cursor] [-Dir PATH] [-Flat]` | same as above |

- Add `--flat` to also expose each sub-skill as its own top-level skill (symlinks). This is
  useful for agents that do not follow links between skills.
- An existing install is moved to `blender-master.bak.<timestamp>` and never deleted.
- For agents without skill support, point them at `blender-master/SKILL.md` as instructions and
  let them run the scripts in `blender-master/scripts/`.

Tell the agent where Blender lives, either with `BLENDER_BIN=/path/to/blender` or by putting
`blender` on your `PATH`. Then just ask it for something made in Blender.

## How it works

The top-level `SKILL.md` is a **coordinator**. It never builds a whole project in one go:

```
INTAKE -> RECOGNISE -> DECOMPOSE -> ROUTE -> EXECUTE + VERIFY (per part) -> FINAL QA -> DELIVER
```

1. **Intake.** It reads the request and asks at most three questions, and only those that change
   the plan (deliverable, style, real size, target engine). Everything else becomes a written
   assumption.
2. **Recognise.** It scores the request against 15 project types, such as product shot, game
   asset, interior, character, procedural system, simulation or stylised. It picks one primary
   type plus modifiers.
3. **Decompose.** It writes a project brief:
   - facts in real units;
   - a spatial blockout with real-scale stand-ins and named cameras;
   - a dependency graph of parts (blockout, model, UV, materials, rig, render and so on).

   Every part carries **numeric acceptance checks**, such as size within 5%, no n-gons, UVs
   inside 0-1, no clipped exposure, or an encoded video with 84 frames and an audio track.
4. **Route.** Each part goes to one focused sub-skill, and the agent reads only the sub-skills
   it needs.
5. **Execute and verify.** It works one part at a time, in one of three modes:
   - **headless**: one Blender process per part, working on a copy;
   - **live**: through an MCP connection to your open Blender, with your approval for each
     chunk of code;
   - **manual**: numbered click-paths for you to follow.

   After each part it runs the checks, applies up to 3 automatic fixes, renders a preview and
   looks at it. It then saves a versioned file, or stops and shows you the failing numbers.
6. **Final QA and delivery.** It re-runs every check on the final file and builds a contact
   sheet and `qa_report.md`. Exports are re-imported to prove they are intact.

Everything is written to a project folder (`brief/`, `reports/`, `previews/`, `blend/`,
`renders/`, `exports/`), so an interrupted job resumes where it stopped.

## Sub-skills

| Sub-skill | Covers |
|---|---|
| blockout-spatial-brief | real-scale stand-ins, named shot cameras, review marks, the spatial brief |
| modeling-topology | hard-surface and organic base meshes, bevels and insets, rooms, lathes, skin-modifier figures |
| sculpting | dense copies, voxel remesh, multires, detail passes, symmetry |
| retopology | shrinkwrap fit, quad remesh, level-of-detail chains, surface-distance check |
| uv-texturing-baking | seams, unwrap, packing, texel density, normal/AO/colour bakes |
| materials-shading | PBR presets, procedural wood/concrete/worn paint, zones, baked texture wiring |
| npr-stylized | toon bands, outlines, line art, Freestyle, painterly compositor finishes |
| hair-fur | groomed hair curves by region, fur, hair shading |
| rigging-body | humanoid armature, IK legs/arms, skin weights, attachments, Rigify start |
| rigging-face | shape keys by region, left/right splits, control empties, drivers |
| animation | keyframes and poses, cycles, noise, path follow, NLA, baking |
| physics-simulation | rigid bodies, cloth and clothing, soft bodies, particles, smoke, liquid, baking |
| scene-environment | terrain, streets, modular kits, prop scattering, proxy swaps |
| geometry-nodes | scatter, instance rows, building blocks, facades, exposed inputs |
| lighting-cameras | worlds, three-point and studio lights, sun/sky, interiors, cameras, depth of field |
| product-shots | studio sweeps, turntables, motion beats, cloth reveals, logos, end cards |
| render-compositing | engine presets, samples, denoise, compositor, deliverable renders |
| video-editing | sequencer cuts, titles, sound, transitions, H.264/AAC MP4 |
| scripting-automation | bpy scripts, batch jobs, add-on skeletons, the 5.x API linter |
| qa-review | final re-checks, contact sheets, paint-over review, QA report |
| export-interchange | FBX / glTF / USD / Alembic presets for engines, re-import round-trip |
| live-control-mcp | driving an open Blender through MCP, one approved chunk at a time |

Routing rules and fallbacks: [blender-master/references/routing.md](blender-master/references/routing.md).
Check catalogue: [blender-master/references/checks.md](blender-master/references/checks.md).

## Examples

Each example is text only: the request, the parameters an agent would write, and a walk-through.

| Example | What it shows |
|---|---|
| [01 product packshot](examples/01-product-packshot/README.md) | lathed glass bottle, studio lights, two cameras |
| [02 game prop crate](examples/02-game-prop-crate/README.md) | hard-surface modelling, UVs, worn paint, FBX + glTF export |
| [03 small interior](examples/03-small-interior/README.md) | room shell with a window, furniture, daylight plus a practical lamp |
| [04 character full run](examples/04-character-full-run/README.md) | sculpt, retopo, bake, hair, face and body rig, animation, FBX round-trip |
| [05 procedural city block](examples/05-procedural-city-block/README.md) | geometry-nodes buildings, scatter, street, terrain |
| [06 product ad shot](examples/06-product-ad-shot/README.md) | cloth reveal, rigid bodies, logo, end card, MP4 edit |

## Running it yourself

```
export BLENDER_BIN=/path/to/blender-5.2.3-linux-x64/blender
N=01-product-packshot
python3 blender-master/scripts/plan_project.py --request "$(cat examples/$N/request.txt)" \
    --params examples/$N/params.json --out out/$N
python3 blender-master/scripts/run_project.py --brief out/$N/brief/brief.json --out out/$N
```

The results land in `out/$N/`:
- `renders/`;
- `brief/qa_report.md`;
- `reports/<part>.json` (every check with its measured value);
- `previews/`;
- `blend/<project>_v###.blend`;
- `exports/`.

In normal use the agent writes `params.json` after reading the routed sub-skills. The examples
ship ready-made ones so the pipeline also runs without an agent.

Tests:
```
python3 -m pytest -m "not slow"   # unit, format, lint and per-sub-skill Blender tests (~1 min)
python3 -m pytest -m slow         # the six example projects end to end (~5 min on 4 cores)
python3 tools/scrub_scan.py       # leaked references, private paths, secrets, link allow-list
```

## Limits and untested areas
- **Supported Blender:** 5.2 LTS, tested on 5.2.3 (Linux). 5.0 and 5.1 run with a warning.
  Older versions are refused because the scripts rely on 5.x APIs: the node-group compositor,
  layered actions, Geometry Nodes `properties.inputs` and the new sequencer names.
- **Automated tests:** CPU-only Cycles. These are **not** covered:
  - GPU rendering and the EEVEE look (including the EEVEE toon mode and Line Art strokes in a
    final render);
  - interactive tools (sculpt strokes, hand grooming, weight painting, add-on buttons such as
    Rigify generation);
  - live MCP sessions (their code templates are linted but not run against a server);
  - imports inside game engines (Unreal, Unity, Godot).

  Reports mark these as untested.
- **Visual quality:** the examples are previs and test quality, not finished art. The checks
  prove a part is correct (sizes, topology, weights, frames, files), not that it is beautiful.
  The agent still looks at every preview, and so should you.
- **Simulations** are baked at modest resolutions for speed. Raise the quality settings for
  final work.

## Safety
Blender runs Python with your user permissions. The skill:
- works on copies and saves versioned files, and never overwrites your `.blend`;
- keeps MCP approvals on, shows the code for each live chunk first, and connects only to
  localhost;
- never installs add-ons, extensions or pip packages, never auto-runs scripts embedded in
  files, and never uses paid services, asset stores or render farms without an explicit yes;
- never asks for, stores or prints API keys;
- confirms the intended depiction for cultural, religious or real-person subjects.

Details: [SECURITY.md](SECURITY.md) and
[blender-master/references/safety.md](blender-master/references/safety.md).

## Contributing and licence
See [CONTRIBUTING.md](CONTRIBUTING.md). All guidance and code must be original, and the scrub
scan enforces this.

MIT, see [LICENSE](LICENSE). Blender is a trademark of the Blender Foundation. This project is
not affiliated with or endorsed by it.
