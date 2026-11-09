# Topology guide

## Vocabulary
- **Edge loop**: a ring of edges that continues through four-way vertices. Loops control where a
  surface can bend and where subdivision keeps detail.
- **Pole**: a vertex with 3 edges (N-pole) or 5+ edges (E-pole). Unavoidable where loop
  directions change; keep them on flat, non-bending areas.
- **Support loop**: an extra loop near an edge so subdivision keeps it crisp.

## General rules
1. Model the big shapes with the fewest polygons that hold the silhouette; add loops only where
   shape or deformation needs them.
2. Keep polygons roughly even in size across a surface that deforms; stretching shows in
   shading and in weights.
3. Quads everywhere a surface subdivides or deforms. Triangles are fine on flat, rigid, hidden
   areas and in game meshes after export triangulation.
4. Avoid n-gons on curved surfaces; on perfectly flat faces of a render-only prop they are fine.
5. Check shading in the viewport with a glossy matcap: pinching shows bad poles and uneven loops.

## Organic base meshes (characters, creatures)
- **Eyes and mouth**: concentric rings around each opening, at least 3 rings, so lids and lips
  can open and close. The outer mouth ring continues up the side of the nose into the brow area,
  defining the cheek fold.
- **Nose bridge**: loops flow from the brow ring down the bridge and wrap the nostrils.
- **Joints** (elbows, knees, fingers): 3 loops across the bend, the middle one slightly wider
  on the outside of the bend so volume holds when it folds.
- **Shoulders and hips**: loops follow the direction of rotation; place poles in front of or
  behind the joint, not on top of it.
- **Limbs**: give connecting pieces matching edge counts (e.g. 8 or 12 around an arm and the
  matching opening in the torso) so they join with quads.
- **Hands**: model fingers as boxes with 3-4 loops per segment; the palm has a pole where the
  thumb branches.
- Mirror (clip on) while building; apply mirror before asymmetry work.

## Hard surface
- **Bevel + weighted normals**: angle-limited bevel on the modifier stack, Weighted Normal after
  it (keep sharp on), smooth by angle at ~30 deg. Gives crisp highlights with low geometry.
- **Booleans**: FLOAT solver is fast but needs clean, non-coplanar input; EXACT handles
  overlaps; MANIFOLD is fastest on closed meshes. Keep cutters as hidden `TMP_` objects until
  the design is final, then apply on a checkpoint.
- **Panel lines**: inset + push in, or a thin boolean groove. Give the recess its own material
  slot so it shows in renders, not only in silhouette.
- **Holes on curved surfaces**: match the cylinder segment count to the surrounding loops, or
  cut and then clean up with dissolve/merge.
- **Auto-merge** on bevel and merge operators helps remove stray vertices after booleans.

## Architecture
- Walls have real thickness (100-200 mm). The room is one closed shell; openings go fully
  through. Floors and ceilings can be part of the shell or separate slabs.
- Keep window frames, doors and skirting as separate objects for material and visibility control.
- Avoid coplanar faces between floor and furniture bases (z-fighting): furniture sits *on* z = 0.

## Products
- Turned shapes (bottles, cups): `lathe` a profile; wall thickness by adding an inner profile.
- Caps and lids are separate objects with a hairline gap (0.2-0.5 mm) so the seam reads.
- Use a slightly larger bevel than looks right in the viewport: highlights in close-ups sell it.

## Game meshes
- Budget triangles by screen size; spend them on the silhouette.
- Remove hidden faces (bottoms that touch the ground, inside of joined parts).
- Hard edges = UV seams + split normals; weighted normals avoid many hard edges.
- Apply scale and rotation; pivot at the base centre or the hinge.
