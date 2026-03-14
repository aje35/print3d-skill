"""Modify mode data models: requests, results, enums, and parameter blocks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from print3d_skill.models.analysis import MeshAnalysisReport
from print3d_skill.models.mesh import BoundingBox

# --- Enums ---


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


# --- Request Models ---


@dataclass
class ToolPrimitive:
    """A parametrically defined shape for boolean operations."""

    primitive_type: PrimitiveType
    dimensions: dict[str, float]
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def validate(self) -> None:
        """Validate dimensions match the primitive type."""
        required: dict[PrimitiveType, set[str]] = {
            PrimitiveType.CYLINDER: {"diameter", "height"},
            PrimitiveType.BOX: {"width", "depth", "height"},
            PrimitiveType.SPHERE: {"diameter"},
            PrimitiveType.CONE: {"bottom_diameter", "top_diameter", "height"},
        }
        needed = required.get(self.primitive_type, set())
        missing = needed - set(self.dimensions.keys())
        if missing:
            raise ValueError(
                f"Primitive type '{self.primitive_type.value}' requires "
                f"dimensions: {sorted(missing)}"
            )


@dataclass
class BooleanParams:
    """Parameters for a boolean operation."""

    boolean_type: BooleanType
    tool_mesh_path: str | None = None
    tool_primitive: ToolPrimitive | None = None

    def validate(self) -> None:
        """Exactly one of tool_mesh_path or tool_primitive must be set."""
        has_path = self.tool_mesh_path is not None
        has_prim = self.tool_primitive is not None
        if has_path == has_prim:
            raise ValueError(
                "BooleanParams requires exactly one of "
                "'tool_mesh_path' or 'tool_primitive'"
            )
        if self.tool_primitive:
            self.tool_primitive.validate()


@dataclass
class ScaleParams:
    """Parameters for a scaling operation."""

    mode: ScaleMode
    factor: float | None = None
    factors: dict[str, float] | None = None
    target_axis: str | None = None
    target_value_mm: float | None = None
    proportional: bool = True

    def validate(self) -> None:
        """Validate that required fields match the scale mode."""
        if self.mode == ScaleMode.UNIFORM:
            if self.factor is None:
                raise ValueError("ScaleMode.UNIFORM requires 'factor'")
        elif self.mode == ScaleMode.NON_UNIFORM:
            if self.factors is None:
                raise ValueError("ScaleMode.NON_UNIFORM requires 'factors'")
        elif self.mode == ScaleMode.DIMENSION_TARGET:
            if self.target_axis is None or self.target_value_mm is None:
                raise ValueError(
                    "ScaleMode.DIMENSION_TARGET requires "
                    "'target_axis' and 'target_value_mm'"
                )


@dataclass
class CombineParams:
    """Parameters for combining/aligning models."""

    other_mesh_paths: list[str] = field(default_factory=list)
    alignment: str = "center"
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class TextParams:
    """Parameters for text engraving or embossing."""

    text: str = ""
    mode: TextMode = TextMode.ENGRAVE
    font: str = "Liberation Sans"
    font_size: float = 10.0
    depth: float = 0.6
    surface: SurfaceFace = SurfaceFace.TOP
    position: tuple[float, float] = (0.0, 0.0)

    def validate(self) -> None:
        """Validate text parameters."""
        if not self.text:
            raise ValueError("TextParams.text must be non-empty")
        if self.depth <= 0:
            raise ValueError("TextParams.depth must be > 0")


@dataclass
class SplitParams:
    """Parameters for splitting a model."""

    axis: str = "z"
    offset_mm: float = 0.0
    add_alignment: bool = True
    pin_diameter: float = 4.0
    pin_height: float = 6.0
    pin_clearance: float = 0.3

    def validate(self) -> None:
        """Validate split parameters."""
        if self.axis not in ("x", "y", "z"):
            raise ValueError(
                f"SplitParams.axis must be 'x', 'y', or 'z', got '{self.axis}'"
            )


@dataclass
class ModifyRequest:
    """Complete request for a Modify mode operation."""

    mesh_path: str
    operation: ModifyOperation
    output_path: str | None = None
    boolean_params: BooleanParams | None = None
    scale_params: ScaleParams | None = None
    combine_params: CombineParams | None = None
    text_params: TextParams | None = None
    split_params: SplitParams | None = None

    def validate(self) -> None:
        """Validate that operation matches populated params block."""
        op_to_params: dict[ModifyOperation, str] = {
            ModifyOperation.BOOLEAN: "boolean_params",
            ModifyOperation.SCALE: "scale_params",
            ModifyOperation.COMBINE: "combine_params",
            ModifyOperation.ENGRAVE: "text_params",
            ModifyOperation.SPLIT: "split_params",
        }
        attr = op_to_params.get(self.operation)
        if attr and getattr(self, attr) is None:
            raise ValueError(
                f"Operation '{self.operation.value}' requires '{attr}' to be set"
            )
        params = getattr(self, attr) if attr else None
        if params and hasattr(params, "validate"):
            params.validate()
        if self.output_path and self.output_path == self.mesh_path:
            raise ValueError(
                "output_path must differ from mesh_path (non-destructive output)"
            )


# --- Result Models ---


@dataclass
class FeatureWarning:
    """Warning about a feature affected by modification."""

    feature_type: str
    original_dimension_mm: float
    new_dimension_mm: float
    standard_match: str | None
    message: str


@dataclass
class AlignmentFeature:
    """An alignment pin or hole added at a split boundary."""

    alignment_type: AlignmentType
    position: tuple[float, float, float]
    diameter: float
    height: float
    clearance: float
    part_index: int


@dataclass
class ModifyResult:
    """Result of a modification operation."""

    operation: ModifyOperation
    input_mesh_path: str
    output_mesh_paths: list[str]
    before_preview_path: str
    after_preview_paths: list[str]
    analysis_report: MeshAnalysisReport
    warnings: list[str]
    feature_warnings: list[FeatureWarning]
    bbox_before: BoundingBox
    bbox_after: BoundingBox
    vertex_count_before: int
    vertex_count_after: int
    face_count_before: int
    face_count_after: int
    alignment_features: list[AlignmentFeature] = field(default_factory=list)
    repair_performed: bool = False
