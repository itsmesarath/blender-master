"""Mesh construction with real dimensions baked into the data (object scale stays 1).

Positions use the *base centre* convention: ``location`` is the centre of the object's bottom
face, so ``z=0`` means "standing on the ground".
"""
from __future__ import annotations

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import bm_scene


def _finish(name, bm, location=(0, 0, 0), rotation=(0, 0, 0), smooth=False, replace=True):
    if replace:
        bm_scene.remove_object(name)
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    obj = bpy.data.objects.new(name, me)
    bm_scene.link_exclusive(obj)
    obj.location = location
    obj.rotation_euler = rotation
    return obj


def box(name, size=(1, 1, 1), location=(0, 0, 0), rotation=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector((0, 0, size[2] / 2)), verts=bm.verts)
    return _finish(name, bm, location, rotation)


def cylinder(name, radius=0.5, depth=1.0, segments=32, location=(0, 0, 0), rotation=(0, 0, 0), smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    bmesh.ops.translate(bm, vec=Vector((0, 0, depth / 2)), verts=bm.verts)
    obj = _finish(name, bm, location, rotation, smooth)
    return obj


def sphere(name, radius=0.5, segments=32, rings=16, location=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    bmesh.ops.translate(bm, vec=Vector((0, 0, radius)), verts=bm.verts)
    return _finish(name, bm, location, smooth=True)


def plane(name, size=(2, 2), location=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=Vector((size[0], size[1], 1)), verts=bm.verts)
    return _finish(name, bm, location)


def lathe(name, profile, segments=48, location=(0, 0, 0), smooth=True):
    """Revolve a (radius, z) profile around Z. Points with radius 0 close the shape at the axis.

    The profile runs bottom to top. The result is a closed, manifold, outward-facing mesh with
    triangle fans only where the profile touches the axis.
    """
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    res = bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                         angle=math.tau, steps=segments, use_merge=True, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    # Faces collapsed at the axis become triangles; drop any zero-area leftovers
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(name, bm, location, smooth=smooth)


def join_parts(name, parts, location=(0, 0, 0)):
    """Join several mesh objects into one object (consumes the parts)."""
    bm = bmesh.new()
    for p in parts:
        tmp = p.data.copy()
        tmp.transform(p.matrix_basis)      # matrix_world is stale until a depsgraph update
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        bm_scene.remove_object(p.name)
    bmesh.ops.translate(bm, vec=-Vector(location), verts=bm.verts)
    return _finish(name, bm, location)
