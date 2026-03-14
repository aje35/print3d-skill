# Data Model: Parametric CAD Generation

**Feature**: 003-parametric-cad
**Date**: 2026-03-14

## Entities

### CreateConfig

Configuration for the Create mode pipeline.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| max_iterations | int | 5 | Maximum compile-render-evaluate iterations |
| nozzle_diameter | float | 0.4 | Nozzle diameter in mm (for printability) |
| min_wall_thickness | float | 0.8 | Minimum wall thickness in mm |
| max_overhang_angle | float | 45.0 | Max overhang angle in degrees |
| max_bridge_distance | float | 10.0 | Max unsupported bridge span in mm |
| min_bed_adhesion_area | float | 100.0 | Minimum bed contact area in mm² |
| target_material | str | "PLA" | Target print material |
| export_formats | list[str] | ["stl", "3mf"] | Mesh export formats |
| render_previews | bool | True | Whether to render previews each iteration |
| bosl2_preferred | bool | True | Prefer BOSL2 modules when available |

### DesignRequest

The user's input to Create mode.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| description | str | Yes | Natural language description of the part |
| dimensions | dict[str, float] | No | Explicit dimensions (e.g., {"width": 50}) |
| material | str | No | Target material (default from config) |
| nozzle_diameter | float | No | Nozzle size (default from config) |
| constraints | dict[str, Any] | No | Additional constraints (max_volume, orientation) |

### GeneratedDesign

A single iteration of the CAD code generation.

| Field | Type | Description |
|-------|------|-------------|
| iteration | int | Iteration number (1-based) |
| scad_code | str | The OpenSCAD source code text |
| scad_path | str | Path to the saved .scad file |
| compile_success | bool | Whether OpenSCAD compiled without errors |
| compile_error | str \| None | Compiler error output (if failed) |
| mesh_path | str \| None | Path to compiled STL (if success) |
| preview_path | str \| None | Path to rendered preview PNG (if success) |
| analysis_report | MeshAnalysisReport \| None | Mesh analysis (if compiled) |
| changes_from_previous | str \| None | Description of what changed |

### PrintabilityWarning

A single printability rule violation.

| Field | Type | Description |
|-------|------|-------------|
| rule | str | Rule identifier (e.g., "min_wall_thickness") |
| severity | str | "error" or "warning" |
| measured_value | float | The actual measured value |
| threshold | float | The threshold that was violated |
| location | str | Description of where the issue is |
| suggestion | str | Actionable fix suggestion with specific numbers |
| affected_face_count | int | Number of faces affected |

### PrintabilityReport

Result of validating a design against FDM printability rules.

| Field | Type | Description |
|-------|------|-------------|
| mesh_path | str | Path to the mesh that was validated |
| config | CreateConfig | Config used for thresholds |
| warnings | list[PrintabilityWarning] | All warnings found |
| is_printable | bool | True if no errors (warnings OK) |
| total_checks | int | Number of checks performed |
| passed_checks | int | Number of checks that passed |
| wall_thickness_min | float \| None | Thinnest wall found (mm) |
| max_overhang_angle_found | float \| None | Steepest overhang (degrees) |
| max_bridge_distance_found | float \| None | Longest bridge (mm) |
| bed_adhesion_area | float \| None | Estimated bed contact area (mm²) |

### DesignExport

Final output bundle from Create mode.

| Field | Type | Description |
|-------|------|-------------|
| scad_path | str | Path to the .scad source file |
| mesh_paths | dict[str, str] | Format → path for exported meshes |
| preview_path | str | Path to the final preview PNG |
| printability_report | PrintabilityReport | Validation results |
| total_iterations | int | How many iterations were needed |
| design_request | DesignRequest | Original request |
| final_design | GeneratedDesign | The approved design iteration |

### CreateResult

Top-level return value from `create_design()`.

| Field | Type | Description |
|-------|------|-------------|
| status | str | "success", "max_iterations_reached", "compile_failed", "error" |
| message | str | Human-readable status message |
| export | DesignExport \| None | Export bundle (if successful) |
| iterations | list[GeneratedDesign] | All iterations attempted |
| printability_report | PrintabilityReport \| None | Final printability check |

## Relationships

```
DesignRequest ──1:1──> CreateResult
CreateResult ──1:N──> GeneratedDesign (iterations list)
CreateResult ──1:1──> DesignExport (if successful)
CreateResult ──1:1──> PrintabilityReport
DesignExport ──1:1──> GeneratedDesign (final)
DesignExport ──1:1──> PrintabilityReport
GeneratedDesign ──1:1──> MeshAnalysisReport (from F2, if compiled)
PrintabilityReport ──1:N──> PrintabilityWarning
```

## State Transitions

### Design Iteration State Machine

```
[start] → generating → compiling → compiled_ok → rendering → rendered
                          ↓                                      ↓
                    compile_failed ──────────────────> [iterate or stop]
                                                         ↓
rendered → evaluating → approved → validating → exporting → [done]
               ↓
           needs_revision → [iterate]
```

### CreateResult Status Values

| Status | Meaning |
|--------|---------|
| success | Design approved, validated, and exported |
| max_iterations_reached | Hit iteration limit, best version exported |
| compile_failed | Could not produce compilable code after all iterations |
| error | Infrastructure failure (OpenSCAD not installed, etc.) |
