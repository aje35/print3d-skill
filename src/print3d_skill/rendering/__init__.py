"""Rendering pipeline for multi-angle mesh previews.

Public API: render_preview()
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from print3d_skill.exceptions import (
    CapabilityUnavailable,
    RenderTimeoutError,
    ScadCompileError,
)
from print3d_skill.models.preview import MeshSummary, PreviewResult
from print3d_skill.rendering.compositor import compose_preview
from print3d_skill.rendering.renderer import load_mesh


def _compile_scad(scad_path: str, timeout: float) -> str:
    """Compile a .scad file to STL via OpenSCAD CLI.

    Returns path to the temporary STL file.
    Raises CapabilityUnavailable if OpenSCAD is not installed.
    Raises ScadCompileError on syntax/compile errors.
    """
    if not shutil.which("openscad"):
        raise CapabilityUnavailable(
            capability="cad_compilation",
            provider="OpenSCAD",
            install_instructions=(
                "Install OpenSCAD: brew install openscad (macOS), "
                "apt install openscad (Ubuntu), "
                "choco install openscad (Windows)"
            ),
        )

    tmp_dir = tempfile.mkdtemp(prefix="print3d_scad_")
    stl_path = os.path.join(tmp_dir, "compiled.stl")

    try:
        result = subprocess.run(
            ["openscad", "-o", stl_path, scad_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RenderTimeoutError(
            f"OpenSCAD compilation timed out after {timeout}s"
        )

    if result.returncode != 0 or not os.path.exists(stl_path):
        raise ScadCompileError(
            f"OpenSCAD compilation failed:\n{result.stderr}"
        )

    return stl_path


def render_preview(
    mesh_path: str,
    output_path: str,
    resolution: tuple[int, int] = (1600, 1200),
    timeout_seconds: float = 30.0,
) -> PreviewResult:
    """Render a multi-angle preview of a mesh file.

    Accepts STL, 3MF, OBJ mesh files. Also accepts .scad files
    if OpenSCAD CLI is available.

    Returns PreviewResult with the path to the output PNG,
    render metadata, and any warnings (unit mismatch, high
    face count).

    Raises:
        FileNotFoundError: mesh_path does not exist
        MeshLoadError: file is corrupt or unreadable
        UnsupportedFormatError: file format not recognized
        RenderTimeoutError: rendering exceeded timeout_seconds
        ScadCompileError: .scad file has syntax errors (includes
            compiler output in the exception message)
        CapabilityUnavailable: .scad file given but OpenSCAD
            not installed
    """
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    ext = Path(mesh_path).suffix.lower()

    # Handle .scad files: compile to STL first
    actual_mesh_path = mesh_path
    if ext == ".scad":
        actual_mesh_path = _compile_scad(mesh_path, timeout_seconds)

    mesh_file = load_mesh(actual_mesh_path)

    # Run rendering with timeout
    result_holder: list[PreviewResult | None] = [None]
    error_holder: list[Exception | None] = [None]

    def _render() -> None:
        try:
            result_holder[0] = compose_preview(mesh_file, output_path, resolution)
        except Exception as e:
            error_holder[0] = e

    thread = threading.Thread(target=_render)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        # Render timed out — return partial result with mesh info we already have
        return PreviewResult(
            image_path=str(os.path.abspath(output_path)) if os.path.exists(output_path) else "",
            resolution=resolution,
            file_size_bytes=os.path.getsize(output_path) if os.path.exists(output_path) else 0,
            views=[],
            mesh_summary=MeshSummary(
                face_count=mesh_file.face_count,
                vertex_count=mesh_file.vertex_count,
                bounding_box_mm=mesh_file.bounding_box.dimensions,
            ),
            warnings=["Render timed out"],
            render_time_seconds=timeout_seconds,
            timed_out=True,
        )

    if error_holder[0] is not None:
        raise error_holder[0]

    return result_holder[0]  # type: ignore[return-value]
