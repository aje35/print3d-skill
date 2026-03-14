# Public API Contract: Parametric CAD Generation

**Feature**: 003-parametric-cad
**Date**: 2026-03-14

## New Public Functions

### `create_design(request, config=None) -> CreateResult`

**Module**: `print3d_skill.create`
**Also exported from**: `print3d_skill` (top-level)

```python
def create_design(
    request: DesignRequest,
    config: CreateConfig | None = None,
) -> CreateResult:
```

**Parameters**:
- `request` (DesignRequest): The design specification with natural language
  description and optional dimensions/constraints.
- `config` (CreateConfig | None): Pipeline configuration. Uses defaults if None.

**Returns**: `CreateResult` with status, iterations list, export bundle, and
printability report.

**Raises**:
- `CapabilityUnavailable`: OpenSCAD not installed (required for compilation).
- `DesignError`: Unrecoverable error in the design pipeline.

**Behavior**:
1. Validates that OpenSCAD is available.
2. Detects BOSL2 availability if `config.bosl2_preferred` is True.
3. Returns a `CreateResult` with `status="error"` and guidance message if
   the description is too vague (no shape/size/purpose).
4. The caller (agent) provides the `.scad` code via `submit_iteration()`.
5. The function does NOT generate code itself — it provides the
   compile-render-validate infrastructure.

### `submit_iteration(session, scad_code, changes=None) -> GeneratedDesign`

**Module**: `print3d_skill.create`

```python
def submit_iteration(
    session: CreateSession,
    scad_code: str,
    changes: str | None = None,
) -> GeneratedDesign:
```

**Parameters**:
- `session` (CreateSession): Active design session from `start_session()`.
- `scad_code` (str): OpenSCAD source code for this iteration.
- `changes` (str | None): Description of changes from previous iteration.

**Returns**: `GeneratedDesign` with compile status, mesh path, preview path.

**Raises**:
- `DesignError`: Session is expired or max iterations exceeded.

### `start_session(request, config=None) -> CreateSession`

**Module**: `print3d_skill.create`

```python
def start_session(
    request: DesignRequest,
    config: CreateConfig | None = None,
) -> CreateSession:
```

Initializes a design session with a working directory for iterations.

### `validate_printability(mesh_path, config=None) -> PrintabilityReport`

**Module**: `print3d_skill.create.printability`
**Also exported from**: `print3d_skill` (top-level)

```python
def validate_printability(
    mesh_path: str,
    config: CreateConfig | None = None,
) -> PrintabilityReport:
```

**Parameters**:
- `mesh_path` (str): Path to a compiled mesh file (STL, 3MF, OBJ, PLY).
- `config` (CreateConfig | None): Thresholds for validation rules.

**Returns**: `PrintabilityReport` with warnings and pass/fail status.

**Raises**:
- `FileNotFoundError`: mesh_path does not exist.
- `MeshLoadError`: mesh file is corrupt.

**Behavior**: Runs all 4 printability checks (wall thickness, overhangs,
bridges, bed adhesion) and returns a structured report with actionable
suggestions.

### `export_design(session) -> DesignExport`

**Module**: `print3d_skill.create`

```python
def export_design(
    session: CreateSession,
    output_dir: str | None = None,
) -> DesignExport:
```

Exports the final approved design as STL, 3MF, and .scad source file.

### `detect_bosl2() -> bool`

**Module**: `print3d_skill.create.bosl2`

```python
def detect_bosl2() -> bool:
```

Returns True if BOSL2 is installed and available to OpenSCAD.
Result is cached after first call.

## New Exceptions

### `DesignError`

```python
class DesignError(Print3DSkillError):
    """Raised when the design pipeline encounters an unrecoverable error."""
```

### `PrintabilityError`

```python
class PrintabilityError(Print3DSkillError):
    """Raised when printability validation cannot be performed."""
```

## Updated Functions

### `route("create", ...)` — Create mode handler

The Create mode handler accepts these kwargs:
- `description` (str): Natural language description
- `dimensions` (dict, optional): Explicit dimensions
- `material` (str, optional): Target material
- `config` (CreateConfig, optional): Pipeline configuration

Returns `ModeResponse` with `CreateResult` as data.

## Type Exports

All new types are importable from `print3d_skill.models`:

```python
from print3d_skill.models import (
    CreateConfig,
    CreateResult,
    CreateSession,
    DesignExport,
    DesignRequest,
    GeneratedDesign,
    PrintabilityReport,
    PrintabilityWarning,
)
```

## Idempotency Contract

- `validate_printability()` on a print-ready mesh returns a report with
  `is_printable=True` and empty warnings list.
- `detect_bosl2()` returns a cached boolean — multiple calls are cheap.

## Error Hierarchy

```
Print3DSkillError
├── CapabilityUnavailable   (OpenSCAD not installed)
├── ScadCompileError        (existing, .scad syntax errors)
├── DesignError             (new, design pipeline failures)
├── PrintabilityError       (new, validation infrastructure errors)
├── MeshLoadError           (existing, corrupt mesh)
└── ExportError             (existing, export failures)
```
