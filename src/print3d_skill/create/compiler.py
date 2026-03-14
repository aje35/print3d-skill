"""OpenSCAD compilation and rendering wrapper for create sessions."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from print3d_skill.exceptions import CapabilityUnavailable
from print3d_skill.models.create import CreateSession, GeneratedDesign
from print3d_skill.rendering import render_preview


def compile_and_render(
    session: CreateSession,
    scad_code: str,
    scad_path: str,
    stl_path: str,
    preview_path: str,
    iteration: int,
    changes: str | None = None,
) -> GeneratedDesign:
    """Compile OpenSCAD code to STL and render a multi-angle preview.

    Saves the .scad code to *scad_path*, compiles via OpenSCAD CLI to
    produce *stl_path*, then renders a preview PNG to *preview_path*.

    If compilation fails the error is captured and returned in the
    GeneratedDesign with ``compile_success=False``.

    Args:
        session: The active design session.
        scad_code: OpenSCAD source code text.
        scad_path: Where to write the .scad file.
        stl_path: Expected STL output path.
        preview_path: Where to write the preview PNG.
        iteration: Current iteration number (1-based).
        changes: Description of changes from previous iteration.

    Returns:
        GeneratedDesign with compile status, paths, and optional analysis.
    """
    # Save .scad source
    with open(scad_path, "w") as f:
        f.write(scad_code)

    # Compile .scad → STL
    compile_success, compile_error, actual_stl = _compile_scad_to_path(
        scad_path, stl_path
    )

    if not compile_success:
        return GeneratedDesign(
            iteration=iteration,
            scad_code=scad_code,
            scad_path=scad_path,
            compile_success=False,
            compile_error=compile_error,
            changes_from_previous=changes,
        )

    # Render preview
    rendered_preview: str | None = None
    if session.config.render_previews:
        try:
            render_preview(actual_stl, preview_path)
            rendered_preview = preview_path
        except Exception:
            # Render failure is non-fatal — we still have the STL
            rendered_preview = None

    return GeneratedDesign(
        iteration=iteration,
        scad_code=scad_code,
        scad_path=scad_path,
        compile_success=True,
        mesh_path=actual_stl,
        preview_path=rendered_preview,
        changes_from_previous=changes,
    )


def _compile_scad_to_path(
    scad_path: str,
    stl_path: str,
    timeout: float = 60.0,
) -> tuple[bool, str | None, str]:
    """Compile a .scad file to STL, placing output at *stl_path*.

    Returns:
        Tuple of (success, error_message_or_None, stl_path).
    """
    openscad = shutil.which("openscad")
    if openscad is None:
        raise CapabilityUnavailable(
            capability="cad_compilation",
            provider="OpenSCAD",
            install_instructions=(
                "Install OpenSCAD: brew install openscad (macOS), "
                "apt install openscad (Ubuntu), "
                "choco install openscad (Windows)"
            ),
        )

    try:
        result = subprocess.run(
            [openscad, "-o", stl_path, scad_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"OpenSCAD compilation timed out after {timeout}s", stl_path

    if result.returncode != 0 or not os.path.exists(stl_path):
        error_msg = result.stderr.strip() if result.stderr else "Unknown compile error"
        return False, error_msg, stl_path

    # Check STL file isn't empty (zero-volume geometry)
    if os.path.getsize(stl_path) == 0:
        return False, "Compilation produced empty geometry (zero volume)", stl_path

    return True, None, stl_path
