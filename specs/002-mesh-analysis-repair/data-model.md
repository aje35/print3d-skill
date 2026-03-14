# Data Model: Mesh Analysis & Repair

**Feature**: 002-mesh-analysis-repair
**Date**: 2026-03-14

## Entities

### DefectType (Enum)

Enumeration of all detectable mesh defect types.

| Value | Severity | Description |
|-------|----------|-------------|
| `non_manifold_edges` | critical | Edges shared by more than 2 faces |
| `non_manifold_vertices` | critical | Vertices where face fan is disconnected |
| `boundary_edges` | critical | Edges belonging to only 1 face (holes) |
| `non_watertight` | critical | Shell is not a closed volume |
| `inconsistent_normals` | warning | Face normals not consistently outward-facing |
| `self_intersecting` | warning | Faces that penetrate other faces |
| `degenerate_faces` | info | Zero-area or near-zero-area triangles |
| `duplicate_vertices` | info | Vertices within merge tolerance of each other |
| `duplicate_faces` | info | Identical face index triples |
| `excessive_poly_count` | info | Face count above configurable threshold |

### DefectSeverity (Enum)

| Value | Meaning |
|-------|---------|
| `critical` | Prevents slicing/printing; must be repaired |
| `warning` | May cause print issues; should be repaired |
| `info` | Cosmetic or optimization opportunity; optional repair |

### MeshHealthClassification (Enum)

| Value | Criteria |
|-------|----------|
| `print_ready` | Zero critical defects (health score ≥ 0.8) |
| `repairable` | Critical defects affecting ≤50% of faces/edges (score 0.3–0.8) |
| `severely_damaged` | Critical defects affecting >50% of faces/edges (score < 0.3) |

### MeshDefect

A single detected defect instance.

| Field | Type | Description |
|-------|------|-------------|
| `defect_type` | DefectType | Which defect was detected |
| `severity` | DefectSeverity | How severe the defect is |
| `count` | int | Number of affected elements (faces, edges, or vertices) |
| `affected_indices` | list[int] | Indices of affected elements in the mesh |
| `description` | str | Human-readable description of the defect |

### ShellAnalysis

Per-shell analysis for multi-body meshes.

| Field | Type | Description |
|-------|------|-------------|
| `shell_index` | int | Index of this shell (0-based) |
| `vertex_count` | int | Number of vertices in this shell |
| `face_count` | int | Number of faces in this shell |
| `bounding_box` | BoundingBox | Bounding box of this shell (reuses existing model) |
| `is_watertight` | bool | Whether this shell is watertight |
| `defects` | list[MeshDefect] | Defects found in this shell |

### MeshAnalysisReport

The complete analysis result.

| Field | Type | Description |
|-------|------|-------------|
| `mesh_path` | str | Path to the analyzed mesh file |
| `format` | str | Detected file format |
| `detected_units` | str | Detected unit scale (mm, inches, meters, unknown) |
| `vertex_count` | int | Total vertex count |
| `face_count` | int | Total face count |
| `bounding_box` | BoundingBox | Overall bounding box |
| `shell_count` | int | Number of disconnected shells |
| `shells` | list[ShellAnalysis] | Per-shell analysis (empty if single-body) |
| `defects` | list[MeshDefect] | Aggregate defect list across all shells |
| `health_score` | float | 0.0–1.0 composite health score |
| `classification` | MeshHealthClassification | Overall health classification |
| `is_triangulated` | bool | Whether non-triangular faces were auto-triangulated on load |

### RepairStrategy (Enum)

| Value | Targets DefectType |
|-------|--------------------|
| `merge_vertices` | duplicate_vertices |
| `remove_degenerates` | degenerate_faces |
| `fill_holes` | boundary_edges, non_watertight |
| `fix_normals` | inconsistent_normals |
| `remove_duplicates` | duplicate_faces |
| `decimate` | excessive_poly_count |

### RepairResult

Outcome of a single repair step.

| Field | Type | Description |
|-------|------|-------------|
| `strategy` | RepairStrategy | Which repair strategy was applied |
| `defect_type` | DefectType | Which defect type this targeted |
| `success` | bool | Whether the repair succeeded |
| `elements_affected` | int | Number of elements changed |
| `description` | str | What was done |
| `before_preview_path` | str or None | Path to before preview image |
| `after_preview_path` | str or None | Path to after preview image |

### RepairSummary

Aggregate result of the full repair pipeline.

| Field | Type | Description |
|-------|------|-------------|
| `mesh_path` | str | Path to original mesh |
| `initial_analysis` | MeshAnalysisReport | Analysis before repair |
| `final_analysis` | MeshAnalysisReport | Analysis after repair |
| `repairs` | list[RepairResult] | Each repair step performed |
| `total_defects_found` | int | Total defects in initial analysis |
| `total_defects_fixed` | int | Defects resolved by repair |
| `remaining_defects` | list[MeshDefect] | Defects that couldn't be auto-repaired |
| `export_paths` | dict[str, str] | Format → file path for exported files |
| `classification_changed` | bool | Whether health classification improved |
| `severely_damaged_warning` | str or None | Warning text if mesh was severely damaged |

### RepairConfig

User-configurable parameters.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vertex_merge_tolerance` | float | 1e-8 | Distance threshold for merging duplicate vertices |
| `degenerate_area_threshold` | float | 1e-10 | Area below which a face is considered degenerate |
| `max_poly_count` | int | 1_000_000 | Face count above which "excessive" is reported |
| `decimation_target` | int or None | None | Target face count for decimation (None = skip) |
| `export_formats` | list[str] | ["stl", "3mf"] | Which formats to export |
| `output_dir` | str or None | None | Output directory (None = same as input) |
| `render_previews` | bool | True | Whether to render before/after previews |

### ExportResult

Output of the export step.

| Field | Type | Description |
|-------|------|-------------|
| `paths` | dict[str, str] | Format → absolute file path for each exported file |
| `repair_summary` | RepairSummary or None | Repair summary if repair was performed |
| `analysis_report` | MeshAnalysisReport | Final analysis of exported mesh |

## Relationships

```
RepairConfig ──configures──> Pipeline
MeshAnalysisReport ──contains──> list[MeshDefect]
MeshAnalysisReport ──contains──> list[ShellAnalysis]
ShellAnalysis ──contains──> list[MeshDefect]
RepairSummary ──contains──> MeshAnalysisReport (initial + final)
RepairSummary ──contains──> list[RepairResult]
ExportResult ──contains──> RepairSummary (optional)
ExportResult ──contains──> MeshAnalysisReport
```

## State Transitions

```
Mesh file on disk
    │
    ▼ load + auto-triangulate
Loaded mesh (MeshFile)
    │
    ▼ analyze
MeshAnalysisReport
    │
    ├── classification: print_ready → skip to export
    │
    ├── classification: repairable → enter repair pipeline
    │
    └── classification: severely_damaged → enter repair pipeline (with warning)
            │
            ▼ repair pipeline (ordered steps)
            ┌─ merge_vertices
            ├─ remove_degenerates
            ├─ remove_duplicates
            ├─ fill_holes
            └─ fix_normals
                │
                ▼ re-analyze
            MeshAnalysisReport (post-repair)
                │
                ▼ export
            ExportResult
```
