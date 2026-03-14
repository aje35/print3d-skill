"""Create mode: parametric CAD generation pipeline.

Provides session-based OpenSCAD code compilation, rendering,
printability validation, and export infrastructure.
"""

from __future__ import annotations

import os
import shutil

import trimesh

from print3d_skill.exceptions import CapabilityUnavailable, DesignError
from print3d_skill.export.formats import export_to_formats
from print3d_skill.models.create import (
    CreateConfig,
    CreateResult,
    CreateSession,
    DesignExport,
    DesignRequest,
    GeneratedDesign,
    PrintabilityReport,
)

from .bosl2 import detect_bosl2
from .compiler import compile_and_render
from .printability import validate_printability as _validate_printability
from .session import create_session, increment_iteration, next_iteration_paths


def start_session(
    request: DesignRequest,
    config: CreateConfig | None = None,
) -> CreateSession:
    """Initialize a design session with a working directory for iterations.

    Validates that OpenSCAD is available and detects BOSL2 if preferred.

    Args:
        request: The user's design specification.
        config: Pipeline configuration. Uses defaults if None.

    Returns:
        A new CreateSession ready for submit_iteration() calls.

    Raises:
        CapabilityUnavailable: OpenSCAD is not installed.
    """
    if config is None:
        config = CreateConfig()

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

    bosl2_available = False
    if config.bosl2_preferred:
        bosl2_available = detect_bosl2()

    return create_session(request, config, bosl2_available)


def submit_iteration(
    session: CreateSession,
    scad_code: str,
    changes: str | None = None,
) -> GeneratedDesign:
    """Submit OpenSCAD code for compilation and rendering.

    Each call produces a versioned .scad file, compiles it to STL,
    and renders a multi-angle preview PNG.

    Args:
        session: Active design session from start_session().
        scad_code: OpenSCAD source code for this iteration.
        changes: Description of changes from previous iteration.

    Returns:
        GeneratedDesign with compile status, mesh path, preview path.

    Raises:
        DesignError: Session expired or max iterations exceeded.
    """
    if not session._active:
        raise DesignError("Session is no longer active")

    if session.iteration >= session.config.max_iterations:
        raise DesignError(
            f"Maximum iterations ({session.config.max_iterations}) exceeded"
        )

    scad_path, stl_path, preview_path = next_iteration_paths(session)
    iteration = increment_iteration(session)

    result = compile_and_render(
        session=session,
        scad_code=scad_code,
        scad_path=scad_path,
        stl_path=stl_path,
        preview_path=preview_path,
        iteration=iteration,
        changes=changes,
    )

    session.iterations.append(result)
    return result


def create_design(
    request: DesignRequest,
    config: CreateConfig | None = None,
) -> CreateResult:
    """Set up the Create mode infrastructure and return a CreateResult.

    This validates OpenSCAD availability, detects BOSL2, and checks
    the description for minimum viability. It does NOT generate code
    itself — the caller (agent) provides code via submit_iteration().

    Args:
        request: The design specification with description and constraints.
        config: Pipeline configuration. Uses defaults if None.

    Returns:
        CreateResult with status and guidance message.
    """
    if config is None:
        config = CreateConfig()

    # Check OpenSCAD availability first
    if not shutil.which("openscad"):
        return CreateResult(
            status="error",
            message=(
                "OpenSCAD is not installed. Install it to use Create mode: "
                "brew install openscad (macOS), apt install openscad (Ubuntu), "
                "choco install openscad (Windows)"
            ),
        )

    # Check for vague descriptions
    desc = request.description.strip()
    if len(desc) < 10 or not any(
        kw in desc.lower()
        for kw in [
            "box", "bracket", "mount", "stand", "holder", "case", "clip",
            "hook", "shelf", "plate", "cover", "frame", "ring", "tube",
            "cylinder", "sphere", "gear", "hinge", "knob", "handle",
            "spacer", "washer", "funnel", "tray", "slot", "channel",
            "wall", "base", "support", "enclosure", "adapter", "connector",
            "round", "square", "flat", "tall", "wide", "thick", "thin",
            "mm", "cm", "inch",
        ]
    ):
        return CreateResult(
            status="error",
            message=(
                "Description is too vague to generate geometry. "
                "Please include: what shape/type of part, approximate "
                "dimensions, and intended purpose."
            ),
        )

    # Detect BOSL2
    bosl2_available = False
    if config.bosl2_preferred:
        bosl2_available = detect_bosl2()

    bosl2_msg = ""
    if config.bosl2_preferred:
        if bosl2_available:
            bosl2_msg = " BOSL2 library detected — use rounded boxes, threads, gears."
        else:
            bosl2_msg = " BOSL2 not installed — use native OpenSCAD primitives only."

    return CreateResult(
        status="success",
        message=f"Create mode ready. Use start_session() to begin.{bosl2_msg}",
    )


def export_design(
    session: CreateSession,
    output_dir: str | None = None,
) -> DesignExport:
    """Export the final approved design as STL, 3MF, and .scad source.

    Copies the .scad source file and exports STL/3MF via trimesh.
    Runs printability validation on the final mesh.

    Args:
        session: Active design session with at least one successful iteration.
        output_dir: Directory for output files. Uses session working dir if None.

    Returns:
        DesignExport with paths to all exported files.

    Raises:
        DesignError: No successful iterations to export.
    """
    # Find the last successful iteration
    successful = [d for d in session.iterations if d.compile_success]
    if not successful:
        raise DesignError("No successful iterations to export")

    final = successful[-1]
    out_dir = output_dir or session.working_dir
    os.makedirs(out_dir, exist_ok=True)

    # Copy .scad source
    scad_dest = os.path.join(out_dir, "design.scad")
    shutil.copy2(final.scad_path, scad_dest)

    # Export mesh formats via trimesh
    mesh = trimesh.load(final.mesh_path, force="mesh")
    mesh_paths = export_to_formats(
        mesh=mesh,
        output_dir=out_dir,
        stem="design",
        formats=session.config.export_formats,
    )

    # Run printability validation
    printability = None
    stl_path = mesh_paths.get("stl", final.mesh_path)
    try:
        printability = _validate_printability(stl_path, session.config)
    except Exception:
        pass  # Non-fatal: export succeeds even if validation fails

    session._active = False

    return DesignExport(
        scad_path=scad_dest,
        mesh_paths=mesh_paths,
        preview_path=final.preview_path or "",
        printability_report=printability,
        total_iterations=session.iteration,
        design_request=session.request,
        final_design=final,
    )


def validate_printability(
    mesh_path: str,
    config: CreateConfig | None = None,
) -> PrintabilityReport:
    """Validate a mesh against FDM printability rules.

    Runs wall thickness, overhang, bridge, and bed adhesion checks.

    Args:
        mesh_path: Path to a compiled mesh file (STL, 3MF, OBJ, PLY).
        config: Thresholds for validation rules. Uses defaults if None.

    Returns:
        PrintabilityReport with warnings and pass/fail status.

    Raises:
        FileNotFoundError: mesh_path does not exist.
    """
    return _validate_printability(mesh_path, config)
