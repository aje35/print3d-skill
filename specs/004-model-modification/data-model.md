# Data Model: Model Modification (004)

**Branch**: `004-model-modification` | **Date**: 2026-03-14

## New Dataclasses

All new dataclasses live in `src/print3d_skill/models/modify.py`. Follow existing patterns: `from __future__ import annotations`, type hints with `| None`, `field(default_factory=...)` for mutable defaults.

### Enums

```python
class ModifyOperation(str, Enum):
    """Types of modification operations."""
    BOOLEAN = "boolean"
    SCALE = "scale"
    COMBINE = "combine"
    ENGRAVE = "engrave"
    SPLIT = "split"

class BooleanType(str, Enum):
    """Boolean operation types."""
    UNION = "union"
    DIFFERENCE = "difference"
    INTERSECTION = "intersection"

class ScaleMode(str, Enum):
    """Scaling modes."""
    UNIFORM = "uniform"
    NON_UNIFORM = "non_uniform"
    DIMENSION_TARGET = "dimension_target"

class TextMode(str, Enum):
    """Text operation types."""
    ENGRAVE = "engrave"
    EMBOSS = "emboss"

class PrimitiveType(str, Enum):
    """Primitive shape types for boolean operands."""
    CYLINDER = "cylinder"
    BOX = "box"
    SPHERE = "sphere"
    CONE = "cone"

class AlignmentType(str, Enum):
    """Alignment feature types for split operations."""
    PIN = "pin"
    HOLE = "hole"

class SurfaceFace(str, Enum):
    """Named faces of a bounding box for positioning."""
    TOP = "top"
    BOTTOM = "bottom"
    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
```

### Request Models

```python
@dataclass
class ToolPrimitive:
    """A parametrically defined shape for boolean operations."""
    primitive_type: PrimitiveType
    # Dimensions (interpretation depends on primitive_type):
    #   CYLINDER: diameter, height (centered on origin, aligned to Z)
    #   BOX: width (X), depth (Y), height (Z)
    #   SPHERE: diameter
    #   CONE: bottom_diameter, top_diameter, height
    dimensions: dict[str, float]
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0)  # Euler angles (degrees)


@dataclass
class BooleanParams:
    """Parameters for a boolean operation."""
    boolean_type: BooleanType
    tool_mesh_path: str | None = None  # Path to second mesh (if using a file)
    tool_primitive: ToolPrimitive | None = None  # Primitive spec (if generating)
    # Exactly one of tool_mesh_path or tool_primitive must be provided.


@dataclass
class ScaleParams:
    """Parameters for a scaling operation."""
    mode: ScaleMode
    factor: float | None = None  # For UNIFORM (e.g., 1.2 = 120%)
    factors: dict[str, float] | None = None  # For NON_UNIFORM (e.g., {"x": 1.0, "z": 1.5})
    target_axis: str | None = None  # For DIMENSION_TARGET (e.g., "x")
    target_value_mm: float | None = None  # For DIMENSION_TARGET (e.g., 50.0)
    proportional: bool = True  # For DIMENSION_TARGET: scale other axes proportionally


@dataclass
class CombineParams:
    """Parameters for combining/aligning models."""
    other_mesh_paths: list[str]  # One or more meshes to combine with the target
    alignment: str = "center"  # "center", "top", "bottom", "front", "back", "left", "right"
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)  # Additional offset (X, Y, Z) in mm


@dataclass
class TextParams:
    """Parameters for text engraving or embossing."""
    text: str
    mode: TextMode = TextMode.ENGRAVE
    font: str = "Liberation Sans"  # OpenSCAD-compatible font name
    font_size: float = 10.0  # Font size in mm
    depth: float = 0.6  # Engraving depth or embossing height in mm
    surface: SurfaceFace = SurfaceFace.TOP  # Target surface
    position: tuple[float, float] = (0.0, 0.0)  # 2D offset on the target surface (mm)


@dataclass
class SplitParams:
    """Parameters for splitting a model."""
    axis: str = "z"  # "x", "y", or "z" — the normal axis of the cutting plane
    offset_mm: float = 0.0  # Position along the axis where the cut occurs
    add_alignment: bool = True  # Whether to add alignment pins/holes
    pin_diameter: float = 4.0  # Alignment pin diameter in mm
    pin_height: float = 6.0  # Alignment pin height in mm
    pin_clearance: float = 0.3  # Hole clearance around pin in mm


@dataclass
class ModifyRequest:
    """Complete request for a Modify mode operation."""
    mesh_path: str  # Path to the input mesh
    operation: ModifyOperation
    output_path: str | None = None  # If None, auto-generated alongside input
    # Exactly one of the following param blocks will be populated:
    boolean_params: BooleanParams | None = None
    scale_params: ScaleParams | None = None
    combine_params: CombineParams | None = None
    text_params: TextParams | None = None
    split_params: SplitParams | None = None
```

### Result Models

```python
@dataclass
class FeatureWarning:
    """Warning about a feature affected by modification."""
    feature_type: str  # e.g., "screw_hole", "thread", "mounting_hole"
    original_dimension_mm: float
    new_dimension_mm: float
    standard_match: str | None  # e.g., "M3 clearance hole" or None
    message: str  # Human-readable warning


@dataclass
class AlignmentFeature:
    """An alignment pin or hole added at a split boundary."""
    alignment_type: AlignmentType
    position: tuple[float, float, float]
    diameter: float
    height: float
    clearance: float  # 0.0 for pins, configured value for holes
    part_index: int  # Which split part this feature belongs to (0 or 1)


@dataclass
class ModifyResult:
    """Result of a modification operation."""
    operation: ModifyOperation
    input_mesh_path: str
    output_mesh_paths: list[str]  # One for most ops, multiple for split
    before_preview_path: str
    after_preview_paths: list[str]  # One per output mesh
    analysis_report: MeshAnalysisReport  # From F2, run on primary output
    warnings: list[str]  # General warnings (repair performed, empty result, etc.)
    feature_warnings: list[FeatureWarning]  # Scaling feature preservation warnings
    bbox_before: BoundingBox
    bbox_after: BoundingBox
    vertex_count_before: int
    vertex_count_after: int
    face_count_before: int
    face_count_after: int
    # Split-specific fields
    alignment_features: list[AlignmentFeature]  # Empty for non-split operations
    # Boolean-specific
    repair_performed: bool = False  # True if auto-repair ran before boolean
```

### Relationships to Existing Models

```text
ModifyRequest
  ├── uses → MeshAnalysisReport (from models/analysis.py) — post-mod validation
  ├── uses → BoundingBox (from models/mesh.py) — before/after dimensions
  ├── uses → PreviewResult (from models/preview.py) — rendering
  └── produces → ModifyResult

ModifyResult
  ├── contains → MeshAnalysisReport — validation of output mesh
  ├── contains → BoundingBox — before/after bounding boxes
  ├── contains → FeatureWarning[] — scaling warnings
  └── contains → AlignmentFeature[] — split alignment features

ModifyHandler (modes/modify.py)
  ├── accepts → ModifyRequest (via **context kwargs)
  ├── returns → ModeResponse (from models/mode.py)
  │                └── data = ModifyResult
  ├── calls → analyze_mesh() (F2) for post-modification validation
  ├── calls → repair_mesh() (F2) for pre-boolean repair
  └── calls → render_preview() (F1) for before/after rendering
```

### Validation Rules

- `ModifyRequest.operation` must match the populated params block (e.g., `BOOLEAN` requires `boolean_params` to be non-None).
- `BooleanParams` must have exactly one of `tool_mesh_path` or `tool_primitive` set (not both, not neither).
- `ScaleParams.factor` required when `mode=UNIFORM`; `factors` required when `mode=NON_UNIFORM`; `target_axis` + `target_value_mm` required when `mode=DIMENSION_TARGET`.
- `SplitParams.axis` must be one of "x", "y", "z".
- `TextParams.text` must be non-empty.
- `TextParams.depth` must be > 0.
- `ToolPrimitive.dimensions` keys depend on `primitive_type`: CYLINDER requires "diameter" and "height"; BOX requires "width", "depth", "height"; SPHERE requires "diameter"; CONE requires "bottom_diameter", "top_diameter", "height".
- `ModifyRequest.mesh_path` must point to an existing file in a supported format (STL, OBJ, PLY, 3MF).
- `ModifyRequest.output_path` must differ from `mesh_path` (non-destructive output, FR-039).

### State Transitions

None — Modify mode is stateless (FR-037). Each operation is a standalone call with no session. No lifecycle management.
