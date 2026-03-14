# Data Model: Core Infrastructure

**Feature**: 001-core-infrastructure
**Date**: 2026-03-14

## Entities

### MeshFile

Represents a loaded 3D model with extracted metadata.

| Field | Type | Description |
|-------|------|-------------|
| path | str | Absolute path to the source file |
| format | str | Detected format: "stl", "3mf", "obj" |
| vertices | ndarray | Nx3 array of vertex coordinates |
| faces | ndarray | Mx3 array of face indices |
| face_count | int | Number of faces |
| vertex_count | int | Number of vertices |
| bounding_box | BoundingBox | Min/max coordinates in each axis |
| detected_units | str | Heuristic: "mm", "inches", "meters", "unknown" |
| unit_warning | str or None | Warning message if unit mismatch detected |
| file_size_bytes | int | Size of source file on disk |

**Identity**: Uniquely identified by `path`.

**Validation**:
- `face_count` must be > 0 (empty mesh is an error)
- `vertices` and `faces` must be finite (no NaN/inf)
- `format` must be one of the supported formats

### BoundingBox

Axis-aligned bounding box of a mesh.

| Field | Type | Description |
|-------|------|-------------|
| min_point | tuple[float, float, float] | (x_min, y_min, z_min) |
| max_point | tuple[float, float, float] | (x_max, y_max, z_max) |
| dimensions | tuple[float, float, float] | (width, depth, height) |
| max_dimension | float | Largest of width/depth/height |

### PreviewResult

Output of the rendering pipeline.

| Field | Type | Description |
|-------|------|-------------|
| image_path | str | Path to the output PNG file |
| resolution | tuple[int, int] | Image dimensions (width, height) |
| file_size_bytes | int | Size of PNG file |
| views | list[ViewAngle] | The four rendered view angles |
| mesh_summary | MeshSummary | Quick stats about the rendered mesh |
| warnings | list[str] | Any warnings (unit mismatch, high face count) |
| render_time_seconds | float | Time taken to produce the image |
| timed_out | bool | Whether the render was aborted by timeout |

### ViewAngle

Camera configuration for one panel of the composite preview.

| Field | Type | Description |
|-------|------|-------------|
| name | str | "front", "side", "top", "isometric" |
| elevation | float | Camera elevation in degrees |
| azimuth | float | Camera azimuth in degrees |

Standard angles:
- front: elevation=0, azimuth=0
- side: elevation=0, azimuth=90
- top: elevation=90, azimuth=0
- isometric: elevation=35, azimuth=45

### ToolCapability

A named capability that the system can provide.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Capability identifier (e.g., "boolean_operations") |
| description | str | Human-readable description |
| tier | str | "core" or "extended" |
| provider_name | str or None | Name of the provider offering this, if available |
| is_available | bool | Whether the capability is currently usable |
| install_instructions | str or None | How to install the missing tool (if unavailable) |

**Identity**: Uniquely identified by `name`.

### ToolProvider

A wrapper around an external tool.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Provider identifier (e.g., "trimesh", "openscad") |
| capabilities | list[str] | Capability names this provider offers |
| tier | str | "core" or "extended" |
| is_available | bool | Whether the tool is detected and usable |
| version | str or None | Detected version of the tool, if available |
| detection_method | str | How availability is checked (e.g., "import", "shutil.which") |
| install_instructions | str | How to install the tool if missing |

**Identity**: Uniquely identified by `name`.

**State transitions**:
- `unknown` → `available` (on first detection, tool found)
- `unknown` → `unavailable` (on first detection, tool not found)
- `available` ↔ `unavailable` (on refresh, if tool installed/removed)

### KnowledgeFile

A structured knowledge file with metadata for filtering.

| Field | Type | Description |
|-------|------|-------------|
| path | str | Path to the YAML file |
| metadata | KnowledgeMetadata | Filterable metadata from the file |
| data | dict | The knowledge content (structure varies by type) |

### KnowledgeMetadata

Metadata section of a knowledge file, used for query matching.

| Field | Type | Description |
|-------|------|-------------|
| type | str | One of: "tolerance_table", "material_properties", "decision_tree", "design_rules" |
| topic | str | Free-text topic identifier |
| modes | list[str] | Applicable modes (empty = all modes) |
| materials | list[str] | Applicable materials (empty = all materials) |
| printers | list[str] | Applicable printers (empty = all printers) |
| version | str | Schema version for migration |

**Matching rules** (AND with wildcards):
- A query field matches if: the file's list contains the query value,
  OR the file's list is empty (meaning "applies to all").
- All specified query fields must match (AND).
- Unspecified query fields are wildcards (always match).

### KnowledgeQuery

Context descriptor for filtering the knowledge base.

| Field | Type | Description |
|-------|------|-------------|
| mode | str or None | Active workflow mode (None = any) |
| material | str or None | Target material (None = any) |
| printer | str or None | Target printer (None = any) |
| problem_type | str or None | Type of problem being solved (None = any) |

### WorkflowMode

Enumeration of the five operating modes.

| Value | Description |
|-------|-------------|
| create | Design new models from scratch |
| fix | Diagnose and repair broken meshes |
| modify | Alter existing models |
| diagnose | Analyze print failures from photos |
| validate | Review G-code and slicer settings |

### ModeResponse

Response from a workflow handler.

| Field | Type | Description |
|-------|------|-------------|
| mode | str | Which mode handled the request |
| status | str | "success", "error", "not_implemented" |
| message | str | Human-readable response |
| data | dict or None | Mode-specific result data |

### SystemInfo

Output of the capability summary command (FR-023).

| Field | Type | Description |
|-------|------|-------------|
| package_version | str | Installed version of print3d-skill |
| python_version | str | Python version |
| capabilities | list[ToolCapability] | All capabilities and their status |
| core_available | bool | Whether all core capabilities work |
| extended_available | list[str] | Which extended capabilities are available |
| missing_extended | list[str] | Which extended capabilities are missing |

## Relationships

```text
MeshFile ──renders-to──→ PreviewResult
                          ├── contains ViewAngle (4)
                          └── contains MeshSummary

ToolRegistry ──manages──→ ToolProvider (many)
                            └── provides ToolCapability (many)

KnowledgeQuery ──filters──→ KnowledgeFile (many)
                              └── has KnowledgeMetadata

Router ──dispatches-to──→ WorkflowMode ──returns──→ ModeResponse
```
