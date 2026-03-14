"""Modify mode: standalone mesh modification operations.

Public API: modify_mesh()
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np
import trimesh

from print3d_skill.analysis import analyze_mesh
from print3d_skill.exceptions import MeshLoadError, UnsupportedFormatError
from print3d_skill.models.mesh import BoundingBox
from print3d_skill.models.modify import (
    BooleanParams,
    BooleanType,
    CombineParams,
    ModifyOperation,
    ModifyRequest,
    ModifyResult,
    PrimitiveType,
    ScaleMode,
    ScaleParams,
    SplitParams,
    SurfaceFace,
    TextMode,
    TextParams,
    ToolPrimitive,
)

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {"stl", "3mf", "obj", "ply"}


def _detect_format(path: str) -> str:
    """Detect mesh format from file extension."""
    ext = Path(path).suffix.lower().lstrip(".")
    if ext in SUPPORTED_FORMATS:
        return ext
    raise UnsupportedFormatError(
        f"Unsupported file format '.{ext}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
    )


def _load_mesh(path: str) -> trimesh.Trimesh:
    """Load a mesh from file."""
    try:
        mesh = trimesh.load(path, force="mesh")
    except Exception as e:
        raise MeshLoadError(f"Failed to load mesh '{path}': {e}") from e
    if not hasattr(mesh, "faces") or len(mesh.faces) == 0:
        raise MeshLoadError(f"Mesh '{path}' has no faces (empty mesh)")
    return mesh


def _get_bbox(mesh: trimesh.Trimesh) -> BoundingBox:
    """Extract BoundingBox from a trimesh mesh."""
    verts = np.asarray(mesh.vertices)
    return BoundingBox(
        min_point=tuple(verts.min(axis=0).tolist()),
        max_point=tuple(verts.max(axis=0).tolist()),
    )


def generate_output_path(
    input_path: str,
    operation: ModifyOperation,
    output_path: str | None = None,
    part_label: str | None = None,
) -> str:
    """Generate output path for a modification result.

    Rules:
    - If output_path provided, use it (must differ from input).
    - Otherwise, auto-generate: model.stl -> model_modified.stl
    - For split: model.stl -> model_bottom.stl / model_top.stl
    - If file exists, append _001, _002, etc.
    """
    if output_path:
        return output_path

    p = Path(input_path)
    ext = p.suffix

    if operation == ModifyOperation.SPLIT and part_label:
        stem = f"{p.stem}_{part_label}"
    else:
        stem = f"{p.stem}_modified"

    candidate = str(p.parent / f"{stem}{ext}")

    # Ensure we never overwrite the input
    if candidate == input_path:
        stem = f"{stem}_out"
        candidate = str(p.parent / f"{stem}{ext}")

    # Handle existing files with incrementing suffix
    if os.path.exists(candidate):
        counter = 1
        while os.path.exists(candidate):
            candidate = str(p.parent / f"{stem}_{counter:03d}{ext}")
            counter += 1

    return candidate


def _build_request_from_kwargs(
    mesh_path: str,
    operation: str,
    output_path: str | None = None,
    **params: object,
) -> ModifyRequest:
    """Build a ModifyRequest from keyword arguments."""
    try:
        op = ModifyOperation(operation)
    except ValueError:
        raise ValueError(
            f"Unknown operation: '{operation}'. "
            f"Valid: {[o.value for o in ModifyOperation]}"
        )

    request = ModifyRequest(mesh_path=mesh_path, operation=op, output_path=output_path)

    if op == ModifyOperation.BOOLEAN:
        boolean_type = params.get("boolean_type", "union")
        tool_mesh_path = params.get("tool_mesh_path")

        tool_primitive = None
        prim_type = params.get("primitive_type")
        if prim_type:
            tool_primitive = ToolPrimitive(
                primitive_type=PrimitiveType(prim_type),
                dimensions=params.get("primitive_dimensions", {}),
                position=params.get("primitive_position", (0.0, 0.0, 0.0)),
                orientation=params.get("primitive_orientation", (0.0, 0.0, 0.0)),
            )

        request.boolean_params = BooleanParams(
            boolean_type=BooleanType(boolean_type),
            tool_mesh_path=str(tool_mesh_path) if tool_mesh_path else None,
            tool_primitive=tool_primitive,
        )

    elif op == ModifyOperation.SCALE:
        scale_mode = params.get("scale_mode", "uniform")
        request.scale_params = ScaleParams(
            mode=ScaleMode(scale_mode),
            factor=params.get("factor"),
            factors=params.get("factors"),
            target_axis=params.get("target_axis"),
            target_value_mm=params.get("target_value_mm"),
            proportional=params.get("proportional", True),
        )

    elif op == ModifyOperation.COMBINE:
        request.combine_params = CombineParams(
            other_mesh_paths=params.get("other_mesh_paths", []),
            alignment=params.get("alignment", "center"),
            offset=params.get("offset", (0.0, 0.0, 0.0)),
        )

    elif op == ModifyOperation.ENGRAVE:
        text_mode_val = params.get("text_mode", "engrave")
        surface_val = params.get("surface", "top")
        request.text_params = TextParams(
            text=params.get("text", ""),
            mode=TextMode(text_mode_val),
            font=params.get("font", "Liberation Sans"),
            font_size=params.get("font_size", 10.0),
            depth=params.get("depth", 0.6),
            surface=SurfaceFace(surface_val),
            position=params.get("text_position", (0.0, 0.0)),
        )

    elif op == ModifyOperation.SPLIT:
        request.split_params = SplitParams(
            axis=params.get("split_axis", "z"),
            offset_mm=params.get("split_offset_mm", 0.0),
            add_alignment=params.get("add_alignment", True),
            pin_diameter=params.get("pin_diameter", 4.0),
            pin_height=params.get("pin_height", 6.0),
            pin_clearance=params.get("pin_clearance", 0.3),
        )

    return request


def modify_mesh(
    mesh_path: str,
    operation: str,
    output_path: str | None = None,
    **params: object,
) -> ModifyResult:
    """Apply a modification operation to an existing mesh.

    Args:
        mesh_path: Path to the input mesh file (STL, OBJ, PLY, 3MF).
        operation: Operation type - "boolean", "scale", "combine", "engrave", "split".
        output_path: Path for the output mesh. If None, auto-generated.
        **params: Operation-specific parameters.

    Returns:
        ModifyResult with output paths, previews, analysis, and warnings.

    Raises:
        FileNotFoundError: If mesh_path does not exist.
        UnsupportedFormatError: If mesh format is not supported.
        ValueError: If operation is unknown or required params are missing.
        MeshLoadError: If mesh cannot be loaded.
        CapabilityUnavailable: If required tool is not available.
    """
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Input mesh not found: {mesh_path}")

    fmt = _detect_format(mesh_path)
    request = _build_request_from_kwargs(mesh_path, operation, output_path, **params)
    request.validate()

    # Load input mesh and capture before-state
    mesh_before = _load_mesh(mesh_path)
    bbox_before = _get_bbox(mesh_before)
    vert_count_before = len(mesh_before.vertices)
    face_count_before = len(mesh_before.faces)

    # Dispatch to operation handler
    op = ModifyOperation(operation)
    if op == ModifyOperation.BOOLEAN:
        from print3d_skill.modify.boolean import execute_boolean

        result_mesh, warnings, repair_performed = execute_boolean(
            mesh_before, request.boolean_params
        )
        output_paths = [generate_output_path(mesh_path, op, request.output_path)]
        result_mesh.export(output_paths[0], file_type=fmt)
        feature_warnings = []
        alignment_features = []

    elif op == ModifyOperation.SCALE:
        from print3d_skill.modify.features import detect_standard_holes
        from print3d_skill.modify.scale import execute_scale

        result_mesh, warnings = execute_scale(mesh_before, request.scale_params)
        output_paths = [generate_output_path(mesh_path, op, request.output_path)]
        result_mesh.export(output_paths[0], file_type=fmt)
        feature_warnings = detect_standard_holes(mesh_before, request.scale_params)
        repair_performed = False
        alignment_features = []

    elif op == ModifyOperation.COMBINE:
        from print3d_skill.modify.combine import execute_combine

        result_mesh, warnings = execute_combine(mesh_before, request.combine_params)
        output_paths = [generate_output_path(mesh_path, op, request.output_path)]
        result_mesh.export(output_paths[0], file_type=fmt)
        feature_warnings = []
        repair_performed = False
        alignment_features = []

    elif op == ModifyOperation.ENGRAVE:
        from print3d_skill.modify.text import execute_text

        result_mesh, warnings = execute_text(mesh_before, request.text_params)
        output_paths = [generate_output_path(mesh_path, op, request.output_path)]
        result_mesh.export(output_paths[0], file_type=fmt)
        feature_warnings = []
        repair_performed = False
        alignment_features = []

    elif op == ModifyOperation.SPLIT:
        from print3d_skill.modify.split import execute_split

        parts, warnings, alignment_features = execute_split(
            mesh_before, request.split_params
        )
        output_paths = []
        labels = ["bottom", "top"] if len(parts) == 2 else [str(i) for i in range(len(parts))]
        for i, (part, label) in enumerate(zip(parts, labels)):
            part_path = generate_output_path(mesh_path, op, None, part_label=label)
            part.export(part_path, file_type=fmt)
            output_paths.append(part_path)
        result_mesh = parts[0]  # Primary output for analysis
        feature_warnings = []
        repair_performed = False

    else:
        raise ValueError(f"Unknown operation: '{operation}'")

    # Post-modification metrics
    bbox_after = _get_bbox(result_mesh)

    # Run comparison rendering
    from print3d_skill.modify.comparison import render_before_after, render_multiple_after

    preview_dir = str(Path(output_paths[0]).parent)
    stem = Path(mesh_path).stem

    if len(output_paths) == 1:
        before_preview, after_preview = render_before_after(
            mesh_path, output_paths[0], preview_dir, stem
        )
        after_previews = [after_preview]
    else:
        before_preview, after_previews = render_multiple_after(
            mesh_path, output_paths, preview_dir, stem
        )

    # Run post-modification analysis (F2)
    analysis = analyze_mesh(output_paths[0])

    return ModifyResult(
        operation=op,
        input_mesh_path=str(Path(mesh_path).resolve()),
        output_mesh_paths=[str(Path(p).resolve()) for p in output_paths],
        before_preview_path=before_preview,
        after_preview_paths=after_previews,
        analysis_report=analysis,
        warnings=warnings,
        feature_warnings=feature_warnings,
        bbox_before=bbox_before,
        bbox_after=bbox_after,
        vertex_count_before=vert_count_before,
        vertex_count_after=len(result_mesh.vertices),
        face_count_before=face_count_before,
        face_count_after=len(result_mesh.faces),
        alignment_features=alignment_features,
        repair_performed=repair_performed if op == ModifyOperation.BOOLEAN else False,
    )
