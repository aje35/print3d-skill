# Public API Contract: Mesh Analysis & Repair

**Feature**: 002-mesh-analysis-repair
**Date**: 2026-03-14

## New Public Functions

These functions will be added to `print3d_skill.__init__` and become part of the public API.

### analyze_mesh()

Analyze a mesh file for defects and produce a structured report.

**Signature**:
```
analyze_mesh(mesh_path: str) -> MeshAnalysisReport
```

**Parameters**:
- `mesh_path`: Absolute or relative path to a mesh file (STL, 3MF, OBJ, PLY)

**Returns**: `MeshAnalysisReport` — structured defect analysis with health classification

**Raises**:
- `FileNotFoundError` — mesh_path does not exist
- `UnsupportedFormatError` — file format not in {stl, 3mf, obj, ply}
- `MeshLoadError` — file is corrupt, truncated, or unreadable
- `MeshAnalysisError` — analysis failed (new exception)

**Behavior**:
1. Load mesh via trimesh, auto-triangulate non-triangular faces
2. Detect unit scale via bounding box heuristics
3. Split into shells if multi-body
4. Run all 10 defect detectors on each shell
5. Aggregate results and compute health score + classification
6. Return structured report

**Idempotent**: Yes — same input always produces same output.

---

### repair_mesh()

Run the full repair pipeline on a mesh file.

**Signature**:
```
repair_mesh(
    mesh_path: str,
    output_path: str | None = None,
    config: RepairConfig | None = None,
) -> RepairSummary
```

**Parameters**:
- `mesh_path`: Path to the input mesh file
- `output_path`: Path for the repaired mesh output. If None, auto-generates based on input path.
- `config`: Optional repair configuration. If None, uses defaults.

**Returns**: `RepairSummary` — what was found, what was fixed, what remains, export paths

**Raises**:
- `FileNotFoundError` — mesh_path does not exist
- `UnsupportedFormatError` — file format not supported
- `MeshLoadError` — file is corrupt or unreadable
- `RepairError` — repair pipeline encountered an unrecoverable error (new exception)

**Behavior**:
1. Load mesh and run initial analysis
2. If print-ready: return summary with no repairs needed
3. Execute repair steps in order: merge vertices → remove degenerates → remove duplicate faces → fill holes → fix normals
4. Render before/after preview at each step (if config.render_previews is True)
5. Re-analyze repaired mesh
6. Export to configured formats
7. Return complete repair summary

**Idempotent**: Yes — running on an already-clean mesh produces no changes.

---

### export_mesh()

Export a mesh to one or more formats.

**Signature**:
```
export_mesh(
    mesh_path: str,
    output_dir: str | None = None,
    formats: list[str] | None = None,
) -> ExportResult
```

**Parameters**:
- `mesh_path`: Path to the mesh file to export
- `output_dir`: Directory for output files. If None, uses the input file's directory.
- `formats`: List of output formats (e.g., ["stl", "3mf"]). If None, defaults to ["stl", "3mf"].

**Returns**: `ExportResult` — paths to exported files + final analysis

**Raises**:
- `FileNotFoundError` — mesh_path does not exist
- `UnsupportedFormatError` — input format not supported
- `MeshLoadError` — file is corrupt or unreadable
- `ExportError` — export failed (new exception)

---

## New Exceptions

Added to `print3d_skill.exceptions`:

| Exception | Parent | When Raised |
|-----------|--------|-------------|
| `MeshAnalysisError` | `Print3DSkillError` | Analysis fails (e.g., mesh has no valid geometry) |
| `RepairError` | `Print3DSkillError` | Repair pipeline encounters unrecoverable error |
| `ExportError` | `Print3DSkillError` | Export fails (e.g., unable to write output file) |

---

## New Public Dataclasses

All importable from `print3d_skill.models`:

- `MeshAnalysisReport`
- `MeshDefect`
- `ShellAnalysis`
- `RepairResult`
- `RepairSummary`
- `RepairConfig`
- `ExportResult`

And enums:
- `DefectType`
- `DefectSeverity`
- `MeshHealthClassification`
- `RepairStrategy`

---

## Updated Fix Mode Handler

The existing `FixHandler` (currently a stub returning `not_implemented`) will be updated to route through the repair pipeline:

```
route("fix", mesh_path="/path/to/mesh.stl") -> ModeResponse
```

The `ModeResponse.data` field will contain the `RepairSummary` when Fix mode is invoked through the router.

---

## Contract Tests

Each public function must have contract tests verifying:

1. **Signature**: Function exists and accepts the documented parameters
2. **Return type**: Returns the documented dataclass type
3. **Error handling**: Raises the documented exceptions for invalid inputs
4. **Idempotency**: analyze_mesh and repair_mesh produce consistent results on repeated calls
