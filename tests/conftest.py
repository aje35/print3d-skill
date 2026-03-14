"""Shared pytest fixtures for print3d-skill tests.

Generates test mesh files programmatically via trimesh so tests
don't depend on binary fixtures checked into the repo.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest
import trimesh


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to the tests/fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def tmp_output_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Temporary directory for test output files."""
    return tmp_path_factory.mktemp("output")


@pytest.fixture(scope="session")
def cube_stl(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a minimal valid STL cube mesh."""
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    path = tmp_path_factory.mktemp("meshes") / "cube.stl"
    mesh.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def simple_obj(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a simple OBJ mesh (icosphere)."""
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=15.0)
    path = tmp_path_factory.mktemp("meshes") / "simple.obj"
    mesh.export(str(path), file_type="obj")
    return path


@pytest.fixture(scope="session")
def colored_3mf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a 3MF mesh with vertex colors."""
    mesh = trimesh.creation.box(extents=[30, 20, 10])
    # Assign face colors
    mesh.visual.face_colors = np.random.randint(
        50, 255, size=(len(mesh.faces), 4), dtype=np.uint8
    )
    path = tmp_path_factory.mktemp("meshes") / "colored.3mf"
    mesh.export(str(path), file_type="3mf")
    return path


@pytest.fixture(scope="session")
def corrupt_stl(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a truncated/corrupt STL file."""
    path = tmp_path_factory.mktemp("meshes") / "corrupt.stl"
    # Write a valid STL header but truncate the data
    with open(path, "wb") as f:
        f.write(b"\x00" * 80)  # 80-byte header
        f.write(struct.pack("<I", 100))  # claim 100 faces
        f.write(b"\x00" * 10)  # but only write 10 bytes of data
    return path


@pytest.fixture(scope="session")
def tiny_mesh(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a mesh with very small dimensions (likely meters, not mm)."""
    mesh = trimesh.creation.box(extents=[0.02, 0.03, 0.01])
    path = tmp_path_factory.mktemp("meshes") / "tiny.stl"
    mesh.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def large_mesh(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a high-poly sphere (>100K faces) for performance tests."""
    mesh = trimesh.creation.icosphere(subdivisions=6, radius=50.0)
    path = tmp_path_factory.mktemp("meshes") / "large_mesh.stl"
    mesh.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def sample_scad(fixtures_dir: Path) -> Path:
    """Path to a simple OpenSCAD source file."""
    path = fixtures_dir / "sample.scad"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '// Simple test cube\n'
            'cube([20, 20, 20], center=true);\n'
        )
    return path


@pytest.fixture(scope="session")
def mesh_with_holes(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a sphere mesh with faces removed to create boundary edges (holes)."""
    mesh = trimesh.creation.icosphere(subdivisions=2)
    faces = np.delete(mesh.faces, [0, 1, 2, 3], axis=0)
    normals = np.delete(mesh.face_normals, [0, 1, 2, 3], axis=0)
    mesh_holed = trimesh.Trimesh(
        vertices=mesh.vertices,
        faces=faces,
        face_normals=normals,
        process=False,
    )
    path = tmp_path_factory.mktemp("meshes") / "mesh_with_holes.stl"
    mesh_holed.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def mesh_with_bad_normals(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a box mesh with ~30% of face windings flipped."""
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    faces = mesh.faces.copy()
    num_to_flip = max(1, int(len(faces) * 0.3))
    rng = np.random.default_rng(42)
    flip_indices = rng.choice(len(faces), size=num_to_flip, replace=False)
    for idx in flip_indices:
        faces[idx] = [faces[idx][0], faces[idx][2], faces[idx][1]]
    mesh_bad = trimesh.Trimesh(
        vertices=mesh.vertices, faces=faces, process=False
    )
    path = tmp_path_factory.mktemp("meshes") / "mesh_with_bad_normals.stl"
    mesh_bad.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def mesh_with_duplicate_vertices(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Generate a box mesh with near-duplicate vertices (within merge tolerance)."""
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    verts = mesh.vertices.copy()
    faces = mesh.faces.copy()
    num_to_dup = min(4, len(verts))
    dup_verts = verts[:num_to_dup] + 1e-9
    new_indices_start = len(verts)
    verts = np.vstack([verts, dup_verts])
    # Remap some faces to reference the duplicated vertices
    for i in range(min(num_to_dup, len(faces))):
        for j in range(3):
            if faces[i][j] < num_to_dup:
                faces[i][j] = new_indices_start + faces[i][j]
    mesh_dup = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    path = tmp_path_factory.mktemp("meshes") / "mesh_with_duplicate_vertices.stl"
    mesh_dup.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def mesh_with_degenerate_faces(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Generate a box mesh with appended zero-area (degenerate) faces."""
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    verts = mesh.vertices.copy()
    faces = mesh.faces.copy()
    # Append degenerate faces where all three vertices are the same point
    degen_faces = np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2]])
    faces = np.vstack([faces, degen_faces])
    mesh_degen = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    path = tmp_path_factory.mktemp("meshes") / "mesh_with_degenerate_faces.stl"
    mesh_degen.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def mesh_with_duplicate_faces(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Generate a box mesh with some faces duplicated."""
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    verts = mesh.vertices.copy()
    faces = mesh.faces.copy()
    # Duplicate the first 4 faces
    dup_faces = faces[:4].copy()
    faces = np.vstack([faces, dup_faces])
    mesh_dupf = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    path = tmp_path_factory.mktemp("meshes") / "mesh_with_duplicate_faces.stl"
    mesh_dupf.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def mesh_non_manifold(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a non-manifold mesh (an edge shared by 3 faces)."""
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    verts = mesh.vertices.copy()
    faces = mesh.faces.copy()
    # Add a new vertex offset from the mesh
    new_vertex = np.array([[0.0, 0.0, 15.0]])
    new_vert_idx = len(verts)
    verts = np.vstack([verts, new_vertex])
    # Create a triangle sharing an existing edge (vertices 0-1) with a new point,
    # making that edge shared by 3 faces (non-manifold).
    extra_face = np.array([[faces[0][0], faces[0][1], new_vert_idx]])
    faces = np.vstack([faces, extra_face])
    mesh_nm = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    path = tmp_path_factory.mktemp("meshes") / "mesh_non_manifold.stl"
    mesh_nm.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def mesh_multi_body(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a mesh with two separate, non-connected bodies."""
    box_a = trimesh.creation.box(extents=[10, 10, 10])
    box_b = trimesh.creation.box(extents=[10, 10, 10])
    box_b.apply_translation([30, 30, 30])
    combined = trimesh.util.concatenate([box_a, box_b])
    path = tmp_path_factory.mktemp("meshes") / "mesh_multi_body.stl"
    combined.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def mesh_self_intersecting(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Generate a self-intersecting mesh from two overlapping boxes."""
    box_a = trimesh.creation.box(extents=[20, 20, 20])
    box_b = trimesh.creation.box(extents=[20, 20, 20])
    box_b.apply_translation([10, 10, 10])  # Overlap by half
    combined = trimesh.util.concatenate([box_a, box_b])
    path = tmp_path_factory.mktemp("meshes") / "mesh_self_intersecting.stl"
    combined.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def clean_mesh(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a known-good watertight box mesh."""
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    path = tmp_path_factory.mktemp("meshes") / "clean.stl"
    mesh.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def mesh_ply(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a simple mesh in PLY format for format testing."""
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    path = tmp_path_factory.mktemp("meshes") / "mesh.ply"
    mesh.export(str(path), file_type="ply")
    return path


# --- Modify mode fixtures ---


@pytest.fixture(scope="session")
def box_with_known_dims(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a box mesh with known exact dimensions (40x30x20 mm)."""
    mesh = trimesh.creation.box(extents=[40, 30, 20])
    path = tmp_path_factory.mktemp("meshes") / "box_40x30x20.stl"
    mesh.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def tall_box_stl(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a tall box for split testing (40x40x100 mm)."""
    mesh = trimesh.creation.box(extents=[40, 40, 100])
    path = tmp_path_factory.mktemp("meshes") / "tall_box.stl"
    mesh.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def cylinder_stl(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a cylinder mesh for combine/boolean testing."""
    mesh = trimesh.creation.cylinder(radius=10, height=30, sections=32)
    path = tmp_path_factory.mktemp("meshes") / "cylinder.stl"
    mesh.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def sphere_stl(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a sphere mesh for boolean testing."""
    mesh = trimesh.creation.icosphere(subdivisions=3, radius=15.0)
    path = tmp_path_factory.mktemp("meshes") / "sphere.stl"
    mesh.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def mesh_with_screw_holes(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a box with M3 clearance holes (3.4mm diameter) for feature detection."""
    base = trimesh.creation.box(extents=[40, 30, 10])
    # Create M3 clearance holes (3.4mm diameter) — boolean subtract cylinders
    try:
        import manifold3d

        m_base = manifold3d.Manifold.of_trimesh(base)
        # Two M3 holes at known positions
        for x_pos in [10.0, -10.0]:
            hole = trimesh.creation.cylinder(radius=1.7, height=20.0, sections=32)
            hole.apply_translation([x_pos, 0, 0])
            m_hole = manifold3d.Manifold.of_trimesh(hole)
            m_base = m_base - m_hole
        result_mesh = m_base.to_trimesh()
        mesh = trimesh.Trimesh(
            vertices=result_mesh.vert_properties[:, :3],
            faces=result_mesh.tri_verts,
        )
    except Exception:
        # Fallback: use plain box if manifold3d fails
        mesh = base
    path = tmp_path_factory.mktemp("meshes") / "box_with_m3_holes.stl"
    mesh.export(str(path), file_type="stl")
    return path


@pytest.fixture(scope="session")
def second_box_stl(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a second box mesh for combine testing (20x20x20 mm)."""
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    path = tmp_path_factory.mktemp("meshes") / "second_box.stl"
    mesh.export(str(path), file_type="stl")
    return path
