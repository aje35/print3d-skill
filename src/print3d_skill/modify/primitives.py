"""Primitive shape generation for boolean operands.

Uses trimesh.creation for core-tier primitive generation (no OpenSCAD needed).
"""

from __future__ import annotations

import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

from print3d_skill.models.modify import PrimitiveType, ToolPrimitive


def create_cylinder(diameter: float, height: float) -> trimesh.Trimesh:
    """Create a cylinder centered on the origin, aligned to Z axis."""
    return trimesh.creation.cylinder(
        radius=diameter / 2.0, height=height, sections=32
    )


def create_box(width: float, depth: float, height: float) -> trimesh.Trimesh:
    """Create a box centered on the origin."""
    return trimesh.creation.box(extents=[width, depth, height])


def create_sphere(diameter: float) -> trimesh.Trimesh:
    """Create a sphere centered on the origin."""
    return trimesh.creation.icosphere(subdivisions=3, radius=diameter / 2.0)


def create_cone(
    bottom_diameter: float, top_diameter: float, height: float
) -> trimesh.Trimesh:
    """Create a cone/frustum centered on the origin, aligned to Z axis."""
    if top_diameter < 1e-6:
        # True cone
        return trimesh.creation.cone(radius=bottom_diameter / 2.0, height=height, sections=32)
    # Frustum: use cylinder with varying radius
    # trimesh doesn't have a direct frustum, so build via revolution
    r_bottom = bottom_diameter / 2.0
    r_top = top_diameter / 2.0
    # Create a linearly-interpolated profile and revolve
    n_sections = 32
    angles = np.linspace(0, 2 * np.pi, n_sections, endpoint=False)
    vertices = []
    faces = []
    # Bottom ring + top ring
    for h_idx, (h, r) in enumerate([(0, r_bottom), (height, r_top)]):
        for a in angles:
            vertices.append([r * np.cos(a), r * np.sin(a), h - height / 2])
    vertices = np.array(vertices)
    # Build faces between bottom and top rings
    for i in range(n_sections):
        i_next = (i + 1) % n_sections
        b0 = i
        b1 = i_next
        t0 = n_sections + i
        t1 = n_sections + i_next
        faces.append([b0, b1, t1])
        faces.append([b0, t1, t0])
    # Cap bottom
    center_b = len(vertices)
    vertices = np.vstack([vertices, [[0, 0, -height / 2]]])
    for i in range(n_sections):
        i_next = (i + 1) % n_sections
        faces.append([center_b, i_next, i])
    # Cap top
    center_t = len(vertices)
    vertices = np.vstack([vertices, [[0, 0, height / 2]]])
    for i in range(n_sections):
        i_next = (i + 1) % n_sections
        faces.append([center_t, n_sections + i, n_sections + i_next])

    return trimesh.Trimesh(vertices=vertices, faces=np.array(faces), process=True)


def create_primitive(spec: ToolPrimitive) -> trimesh.Trimesh:
    """Create a mesh from a ToolPrimitive specification.

    Generates the primitive, applies orientation (Euler angles in degrees),
    then translates to position.
    """
    spec.validate()
    dims = spec.dimensions

    if spec.primitive_type == PrimitiveType.CYLINDER:
        mesh = create_cylinder(dims["diameter"], dims["height"])
    elif spec.primitive_type == PrimitiveType.BOX:
        mesh = create_box(dims["width"], dims["depth"], dims["height"])
    elif spec.primitive_type == PrimitiveType.SPHERE:
        mesh = create_sphere(dims["diameter"])
    elif spec.primitive_type == PrimitiveType.CONE:
        mesh = create_cone(dims["bottom_diameter"], dims["top_diameter"], dims["height"])
    else:
        raise ValueError(f"Unknown primitive type: {spec.primitive_type}")

    # Apply orientation (Euler angles XYZ in degrees)
    if any(a != 0.0 for a in spec.orientation):
        rot = Rotation.from_euler("xyz", spec.orientation, degrees=True)
        transform = np.eye(4)
        transform[:3, :3] = rot.as_matrix()
        mesh.apply_transform(transform)

    # Apply translation
    if any(p != 0.0 for p in spec.position):
        mesh.apply_translation(list(spec.position))

    return mesh
