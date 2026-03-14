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
