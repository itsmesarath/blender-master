---
name: blockout-spatial-brief
description: Turns a Blender request into a real-scale blockout with named hero cameras, a note pinned to every proxy, a red/green review layer and a written spatial brief. Use at the start of any multi-object scene, layout, environment, product shot or prop before detailed modelling, or when the user says layout, blockout, composition or camera placement.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Part of blender-master; scripts expect its lib/ on sys.path.
metadata:
  parent: blender-master
  status: core
---

# Blockout and spatial brief

Decide **where things are, how big they are, and what the camera sees** before anyone models
detail. A blockout is cheap to change; a finished model in the wrong place is not.

## Inputs -> outputs
- In: the project brief (`facts.subject_size`, deliverable cameras, resolution), optional reference
  images in `brief/refs/`.
- Out: `PRX_*` proxies at real size with `brief_note` properties, `CAM_*` cameras, a ground at
  z = 0, the `REV_review` Grease Pencil layer, `brief/spatial_brief.md`, `brief/cameras.json`.

## Procedure
1. **Scene setup** (`setup_scene`): metric units, frame range, standard collections. Clears the
   factory cube, camera and light.
2. **Proxies** (`proxy`): one per object a viewer would name. Size is the full extent in metres;
   location is the centre of the base. Use the simplest shape that reads (box, cylinder, sphere,
   plane). Every proxy gets a one-line note: what it is and anything that must be true about it
   ("label faces camera", "door opens inward").
3. **Ground** (`ground`) for props and products, or the floor of a room.
4. **Hero cameras** (`camera`): a named view (`three_quarter`, `front`, `low_hero`, `high`,
   `top`, ...) auto-fitted to the proxies, or an explicit `location` + `target`. Choose the lens
   by subject (see [references/blockout-guide.md](references/blockout-guide.md)). The hero camera
   becomes the scene camera. Auto-fitted cameras are tagged `autofit` so later fixers may dolly
   them; hand-placed ones are never moved automatically.
5. **Resolution** (`resolution`) from the deliverable: aspect ratio changes composition, so set it
   before judging the frame.
6. **Review layer** (`review_layer`, `review_mark`): red strokes mark fix/remove, green mark add.
   Each stroke stores a note. Later parts answer every stroke in their report.
7. **Write the spatial brief** (`write_spatial_brief`) and check the hero preview.

## Acceptance (default)
Proxies exist, each has a `brief_note`, hero cameras exist, names follow the prefixes, and the
subject proxy matches `facts.subject_size` within 5 %. Look at the preview: is the subject where
the request implies, at a believable scale against the ground and other objects?

## Pitfalls
- Scaling an object instead of setting its size: proxies are built at size with scale 1.
- Picking the camera after modelling: detail ends up where the camera never looks.
- Cameras inside walls in interiors: give an explicit location inside the room.
- A blockout with no human-scale reference: add a 1.75 m `PRX_scale_figure` if size is doubtful.

## Manual mode
Add > Mesh > Cube, then N panel > Item > Dimensions (not Scale). Object Properties > Custom
Properties > New, name `brief_note`. Add > Camera, Numpad 0 to view, View > Navigation > Fly or
"Lock Camera to View" to frame. Add > Grease Pencil > Blank, rename `REV_review`.

## Scripts
- `scripts/ops.py`: `setup_scene`, `proxy`, `ground`, `camera`, `resolution`, `review_layer`,
  `review_mark`, `write_spatial_brief`.
