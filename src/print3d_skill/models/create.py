"""Create mode data models for parametric CAD generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from print3d_skill.models.analysis import MeshAnalysisReport


@dataclass
class CreateConfig:
    """Configuration for the Create mode pipeline."""

    max_iterations: int = 5
    nozzle_diameter: float = 0.4
    min_wall_thickness: float = 0.8
    max_overhang_angle: float = 45.0
    max_bridge_distance: float = 10.0
    min_bed_adhesion_area: float = 100.0
    target_material: str = "PLA"
    export_formats: list[str] = field(default_factory=lambda: ["stl", "3mf"])
    render_previews: bool = True
    bosl2_preferred: bool = True


@dataclass
class DesignRequest:
    """The user's input to Create mode."""

    description: str
    dimensions: dict[str, float] = field(default_factory=dict)
    material: str | None = None
    nozzle_diameter: float | None = None
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedDesign:
    """A single iteration of the CAD code generation."""

    iteration: int
    scad_code: str
    scad_path: str
    compile_success: bool
    compile_error: str | None = None
    mesh_path: str | None = None
    preview_path: str | None = None
    analysis_report: MeshAnalysisReport | None = None
    changes_from_previous: str | None = None


@dataclass
class PrintabilityWarning:
    """A single printability rule violation."""

    rule: str
    severity: str
    measured_value: float
    threshold: float
    location: str
    suggestion: str
    affected_face_count: int = 0


@dataclass
class PrintabilityReport:
    """Result of validating a design against FDM printability rules."""

    mesh_path: str
    config: CreateConfig
    warnings: list[PrintabilityWarning] = field(default_factory=list)
    is_printable: bool = True
    total_checks: int = 0
    passed_checks: int = 0
    wall_thickness_min: float | None = None
    max_overhang_angle_found: float | None = None
    max_bridge_distance_found: float | None = None
    bed_adhesion_area: float | None = None


@dataclass
class CreateSession:
    """Active design session with working directory and iteration state."""

    request: DesignRequest
    config: CreateConfig
    working_dir: str
    iteration: int = 0
    iterations: list[GeneratedDesign] = field(default_factory=list)
    bosl2_available: bool = False
    _active: bool = True


@dataclass
class DesignExport:
    """Final output bundle from Create mode."""

    scad_path: str
    mesh_paths: dict[str, str] = field(default_factory=dict)
    preview_path: str = ""
    printability_report: PrintabilityReport | None = None
    total_iterations: int = 0
    design_request: DesignRequest | None = None
    final_design: GeneratedDesign | None = None


@dataclass
class CreateResult:
    """Top-level return value from create_design()."""

    status: str
    message: str
    export: DesignExport | None = None
    iterations: list[GeneratedDesign] = field(default_factory=list)
    printability_report: PrintabilityReport | None = None
