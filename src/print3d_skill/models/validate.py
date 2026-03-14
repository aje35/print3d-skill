"""Data models for G-code validation, slicing, and printing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# --- Enums ---


class ValidationStatus(Enum):
    """Overall outcome of a validation run."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class CheckSeverity(Enum):
    """Severity level for an individual validation check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class CheckCategory(Enum):
    """Category of a validation check for grouping results."""

    TEMPERATURE = "temperature"
    SPEED = "speed"
    RETRACTION = "retraction"
    DIMENSIONS = "dimensions"
    FIRST_LAYER = "first_layer"
    TIME_ESTIMATE = "time_estimate"
    MATERIAL_ESTIMATE = "material_estimate"
    COMPATIBILITY = "compatibility"


class ExtruderType(Enum):
    """Type of extruder for retraction validation."""

    DIRECT_DRIVE = "direct_drive"
    BOWDEN = "bowden"


class PrinterConnectionType(Enum):
    """Type of printer API connection."""

    OCTOPRINT = "octoprint"
    MOONRAKER = "moonraker"
    BAMBU = "bambu"


class PrinterStatus(Enum):
    """Current state of a connected printer."""

    IDLE = "idle"
    PRINTING = "printing"
    PAUSED = "paused"
    ERROR = "error"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"


class SlicerType(Enum):
    """Supported slicer CLI backends."""

    PRUSASLICER = "prusaslicer"
    ORCASLICER = "orcaslicer"


# --- Component dataclasses ---


@dataclass
class TemperatureCommand:
    """A single temperature command extracted from G-code."""

    command: str
    target_temp_c: float
    line_number: int
    layer: int | None = None
    wait: bool = False


@dataclass
class FanCommand:
    """A fan speed change extracted from G-code."""

    command: str
    speed_percent: float
    line_number: int
    layer: int | None = None


@dataclass
class PrintDimensions:
    """Estimated bounding box of print moves (stdlib-only, no numpy)."""

    min_x: float = 0.0
    max_x: float = 0.0
    min_y: float = 0.0
    max_y: float = 0.0
    min_z: float = 0.0
    max_z: float = 0.0

    @property
    def size_x(self) -> float:
        return self.max_x - self.min_x

    @property
    def size_y(self) -> float:
        return self.max_y - self.min_y

    @property
    def size_z(self) -> float:
        return self.max_z - self.min_z


# --- Primary entities ---


@dataclass
class GcodeAnalysis:
    """Structured report from parsing a G-code file."""

    file_path: str = ""
    file_size_bytes: int = 0
    slicer: str | None = None
    hotend_temps: list[TemperatureCommand] = field(default_factory=list)
    bed_temps: list[TemperatureCommand] = field(default_factory=list)
    chamber_temps: list[TemperatureCommand] = field(default_factory=list)
    print_speed_mm_s: float | None = None
    travel_speed_mm_s: float | None = None
    first_layer_speed_mm_s: float | None = None
    retraction_distance_mm: float | None = None
    retraction_speed_mm_s: float | None = None
    z_hop_mm: float | None = None
    layer_height_mm: float | None = None
    first_layer_height_mm: float | None = None
    layer_count: int | None = None
    estimated_time_s: float | None = None
    estimated_filament_mm: float | None = None
    estimated_filament_g: float | None = None
    fan_speeds: list[FanCommand] = field(default_factory=list)
    print_dimensions: PrintDimensions | None = None
    line_count: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationCheck:
    """A single validation check result."""

    category: CheckCategory = CheckCategory.TEMPERATURE
    name: str = ""
    severity: CheckSeverity = CheckSeverity.PASS
    actual_value: str = ""
    expected_range: str = ""
    message: str = ""
    recommendation: str = ""


@dataclass
class ValidationResult:
    """Complete output of validating G-code against profiles."""

    status: ValidationStatus = ValidationStatus.PASS
    gcode_analysis: GcodeAnalysis = field(default_factory=GcodeAnalysis)
    material_profile: str | None = None
    printer_profile: str | None = None
    checks: list[ValidationCheck] = field(default_factory=list)
    summary: str = ""
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# --- Profile dataclasses ---


@dataclass
class MaterialProfile:
    """Reference data for a filament material used in validation."""

    name: str = ""
    hotend_temp_min_c: float = 0.0
    hotend_temp_max_c: float = 0.0
    bed_temp_min_c: float = 0.0
    bed_temp_max_c: float = 0.0
    speed_min_mm_s: float = 0.0
    speed_max_mm_s: float = 0.0
    retraction_direct_drive_mm: float = 0.0
    retraction_bowden_mm: float = 0.0
    retraction_speed_mm_s: float = 0.0
    requires_enclosure: bool = False
    requires_heated_bed: bool = False
    fan_speed_percent: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class PrinterProfile:
    """Reference data for a printer's capabilities."""

    name: str = ""
    build_volume_x_mm: float = 0.0
    build_volume_y_mm: float = 0.0
    build_volume_z_mm: float = 0.0
    max_hotend_temp_c: float = 0.0
    max_bed_temp_c: float = 0.0
    extruder_type: ExtruderType = ExtruderType.DIRECT_DRIVE
    has_heated_bed: bool = True
    has_enclosure: bool = False
    notes: list[str] = field(default_factory=list)


# --- Slicing dataclasses ---


@dataclass
class SliceRequest:
    """Request to slice a model via CLI."""

    model_path: str = ""
    output_path: str | None = None
    slicer: SlicerType | None = None
    printer_profile: str | None = None
    material_profile: str | None = None
    quality_preset: str | None = None
    overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class SliceResult:
    """Result of a slicing operation."""

    gcode_path: str = ""
    slicer_used: SlicerType = SlicerType.PRUSASLICER
    slicer_version: str = ""
    model_path: str = ""
    profiles_used: dict[str, str] = field(default_factory=dict)
    overrides_applied: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# --- Printer dataclasses ---


@dataclass
class PrinterConnection:
    """Configuration for connecting to a printer."""

    name: str = ""
    connection_type: PrinterConnectionType = PrinterConnectionType.OCTOPRINT
    host: str = ""
    port: int | None = None
    api_key: str | None = None
    serial: str | None = None
    access_code: str | None = None


@dataclass
class PrinterInfo:
    """Status information about a connected printer."""

    name: str = ""
    connection_type: PrinterConnectionType = PrinterConnectionType.OCTOPRINT
    status: PrinterStatus = PrinterStatus.UNKNOWN
    hotend_temp_c: float | None = None
    bed_temp_c: float | None = None
    progress_percent: float | None = None
    current_file: str | None = None


@dataclass
class PrintJob:
    """A submission of validated G-code to a printer."""

    printer_name: str = ""
    gcode_path: str = ""
    validation_result: ValidationResult = field(default_factory=ValidationResult)
    submitted: bool = False
    message: str = ""
