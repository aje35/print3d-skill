# Public API Contract: Model Modification (004)

**Branch**: `004-model-modification` | **Date**: 2026-03-14

## New Public Functions

### `modify_mesh`

The primary entry point for all mesh modification operations. Added to `src/print3d_skill/__init__.py` as a public API function.

```python
def modify_mesh(
    mesh_path: str,
    operation: str,
    output_path: str | None = None,
    **params: Any,
) -> ModifyResult:
    """
    Apply a modification operation to an existing mesh.

    Args:
        mesh_path: Path to the input mesh file (STL, OBJ, PLY, 3MF).
        operation: Operation type — "boolean", "scale", "combine", "engrave", "split".
        output_path: Path for the output mesh. If None, auto-generated next to input
                     (e.g., "model.stl" → "model_modified.stl"). Original is never overwritten.
        **params: Operation-specific parameters (see below).

    Returns:
        ModifyResult with output paths, previews, analysis, and warnings.

    Raises:
        FileNotFoundError: If mesh_path does not exist.
        UnsupportedFormatError: If mesh format is not supported.
        ValueError: If operation is unknown or required params are missing.
        MeshLoadError: If mesh cannot be loaded.
        CapabilityUnavailable: If required tool is not available (e.g., OpenSCAD for text).
    """
```

### Operation-Specific Parameters

#### Boolean (`operation="boolean"`)

```python
modify_mesh(
    mesh_path="model.stl",
    operation="boolean",
    boolean_type="difference",         # "union", "difference", "intersection"
    tool_mesh_path="other.stl",        # OR use tool_primitive params below
    # --- OR primitive specification ---
    primitive_type="cylinder",          # "cylinder", "box", "sphere", "cone"
    primitive_dimensions={"diameter": 6.0, "height": 20.0},
    primitive_position=(25.0, 10.0, 0.0),
    primitive_orientation=(0.0, 0.0, 0.0),
)
```

#### Scale (`operation="scale"`)

```python
# Uniform
modify_mesh("model.stl", operation="scale", scale_mode="uniform", factor=1.2)

# Non-uniform
modify_mesh("model.stl", operation="scale", scale_mode="non_uniform",
            factors={"x": 1.0, "y": 1.0, "z": 1.5})

# Dimension-targeted
modify_mesh("model.stl", operation="scale", scale_mode="dimension_target",
            target_axis="x", target_value_mm=50.0, proportional=True)
```

#### Combine (`operation="combine"`)

```python
modify_mesh(
    mesh_path="base.stl",
    operation="combine",
    other_mesh_paths=["handle.stl", "knob.stl"],
    alignment="top",          # "center", "top", "bottom", "front", "back", "left", "right"
    offset=(0.0, 0.0, 5.0),  # Additional translation in mm
)
```

#### Engrave (`operation="engrave"`)

```python
modify_mesh(
    mesh_path="case.stl",
    operation="engrave",
    text="v2.1",
    text_mode="engrave",       # "engrave" or "emboss"
    font="Liberation Sans",
    font_size=8.0,             # mm
    depth=0.6,                 # mm
    surface="top",             # "top", "bottom", "front", "back", "left", "right"
    text_position=(0.0, 0.0),  # 2D offset on surface in mm
)
```

#### Split (`operation="split"`)

```python
modify_mesh(
    mesh_path="large_model.stl",
    operation="split",
    split_axis="z",
    split_offset_mm=50.0,
    add_alignment=True,
    pin_diameter=4.0,
    pin_height=6.0,
    pin_clearance=0.3,
)
```

## Mode Router Integration

Modify mode is accessible via the existing router:

```python
from print3d_skill import route

result = route(
    "modify",
    mesh_path="model.stl",
    operation="boolean",
    boolean_type="difference",
    primitive_type="cylinder",
    primitive_dimensions={"diameter": 6.0, "height": 20.0},
    primitive_position=(25.0, 10.0, 0.0),
)
# Returns ModeResponse(mode="modify", status="success", data=ModifyResult)
```

## Return Type Contract

`ModifyResult` fields guaranteed for all operations:

| Field | Type | Always present |
|-------|------|---------------|
| `operation` | `ModifyOperation` | Yes |
| `input_mesh_path` | `str` | Yes |
| `output_mesh_paths` | `list[str]` | Yes (1 element for most ops, 2+ for split) |
| `before_preview_path` | `str` | Yes |
| `after_preview_paths` | `list[str]` | Yes (1 per output mesh) |
| `analysis_report` | `MeshAnalysisReport` | Yes |
| `warnings` | `list[str]` | Yes (may be empty) |
| `feature_warnings` | `list[FeatureWarning]` | Yes (populated only for scale ops) |
| `bbox_before` | `BoundingBox` | Yes |
| `bbox_after` | `BoundingBox` | Yes |
| `vertex_count_before` | `int` | Yes |
| `vertex_count_after` | `int` | Yes |
| `face_count_before` | `int` | Yes |
| `face_count_after` | `int` | Yes |
| `alignment_features` | `list[AlignmentFeature]` | Yes (populated only for split ops) |
| `repair_performed` | `bool` | Yes |

## Error Contract

All errors return `ModeResponse(status="error", message=<description>)` when accessed via the router, or raise exceptions when using `modify_mesh()` directly.

| Scenario | Exception | ModeResponse message pattern |
|----------|-----------|------------------------------|
| Input file missing | `FileNotFoundError` | "Input mesh not found: {path}" |
| Unsupported format | `UnsupportedFormatError` | "Unsupported format: {ext}" |
| Invalid operation | `ValueError` | "Unknown operation: {op}" |
| Missing params | `ValueError` | "Operation '{op}' requires: {params}" |
| Boolean produces empty mesh | No exception | warning in `warnings` list |
| Repair failed (pre-boolean) | No exception | status="error", "Mesh repair failed..." |
| OpenSCAD not available (text) | `CapabilityUnavailable` | "Text operations require OpenSCAD" |
| Non-intersecting split plane | No exception | warning + status="error" |
