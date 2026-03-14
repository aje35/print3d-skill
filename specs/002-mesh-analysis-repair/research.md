# Research: Mesh Analysis & Repair

**Feature**: 002-mesh-analysis-repair
**Date**: 2026-03-14

## R1: Trimesh Defect Detection APIs

**Decision**: Use trimesh's built-in mesh properties and methods for all 10 defect types except self-intersection.

**Rationale**: trimesh (already a core dependency) provides direct access to most mesh quality metrics through properties on the `Trimesh` object. This avoids adding new dependencies.

**Findings**:

| Defect Type | trimesh API | Notes |
|-------------|-------------|-------|
| Non-manifold edges | `mesh.edges` analysis — edges appearing in >2 faces | Compute from `mesh.edges_sorted` + face-edge mapping |
| Non-manifold vertices | `mesh.faces` adjacency analysis | Check vertex face fans for connectivity |
| Boundary edges / holes | `mesh.edges` appearing in only 1 face; `mesh.outline()` | `mesh.is_watertight` is the aggregate check |
| Inconsistent normals | `mesh.face_normals` + `mesh.face_adjacency` | Check adjacent faces for winding consistency |
| Self-intersecting faces | Not built into trimesh | See R3 below |
| Degenerate triangles | Compute from face areas: `mesh.area_faces` | Faces with area < epsilon are degenerate |
| Duplicate vertices | `mesh.vertices` distance comparison | `mesh.merge_vertices()` does this; pre-check via tolerance |
| Duplicate faces | `mesh.faces_unique` / sorted face comparison | Compare sorted vertex index tuples |
| Excessive polygon count | `len(mesh.faces)` vs configurable threshold | Trivial check |
| Non-watertight shells | `mesh.is_watertight` per shell after `mesh.split()` | `mesh.split()` separates disconnected bodies |

**Alternatives considered**:
- PyMeshLab: More comprehensive analysis but heavy dependency, GPL-licensed — conflicts with constitution Principle I
- Open3D: Strong mesh analysis but large install footprint, not pip-only on all platforms

## R2: Trimesh Repair Capabilities

**Decision**: Use trimesh's `repair` module and mesh methods for all repair strategies.

**Rationale**: trimesh provides built-in repair functions that cover all required strategies. No additional dependencies needed.

**Findings**:

| Repair Strategy | trimesh API | Notes |
|-----------------|-------------|-------|
| Hole filling | `trimesh.repair.fill_holes(mesh)` | Fan triangulation; handles simple and complex holes |
| Normal reconciliation | `trimesh.repair.fix_normals(mesh)` + `trimesh.repair.fix_winding(mesh)` | Reconciles winding order and outward orientation |
| Vertex merging | `mesh.merge_vertices(merge_tex=True, merge_norm=True)` | Merges vertices within default tolerance |
| Degenerate removal | `mesh.remove_degenerate_faces()` | Removes zero-area and near-zero-area faces |
| Duplicate face removal | `mesh.remove_duplicate_faces()` | Removes exact duplicate faces |
| Mesh decimation | `mesh.simplify_quadric_decimation(face_count)` | Quadric error metric; preserves shape |

**Vertex merge tolerance**: trimesh's `merge_vertices()` uses a default tolerance based on the mesh's extent. For our configurable tolerance (FR-020, default 1e-8), we'll need to use `mesh.merge_vertices(merge_tex=True)` and may need to manipulate `mesh.vertices` directly with a custom tolerance via `trimesh.grouping.merge_vertices_hash()`.

## R3: Self-Intersection Detection

**Decision**: Use face-pair bounding box overlap pre-filtering + triangle-triangle intersection tests via numpy vectorized operations. Mark as "warning" severity with best-effort detection.

**Rationale**: Neither trimesh nor manifold3d provides a direct self-intersection API. Full O(n^2) triangle-triangle tests are infeasible for large meshes. The practical approach is:

1. Build an R-tree or spatial hash of face bounding boxes (trimesh provides `mesh.triangles` for this)
2. Find candidate intersecting pairs via bounding box overlap
3. Test only candidate pairs with Moller-Trumbore triangle-triangle intersection
4. For meshes >100K faces, sample a subset and report "potential self-intersections detected (sampled)"

**Performance**: For 500K faces, R-tree filtering reduces candidates from 250B pairs to ~10K–100K. Triangle-triangle tests on candidates complete in <5s.

**Alternatives considered**:
- manifold3d: Can detect non-manifold conditions but not self-intersections specifically
- fcl (Flexible Collision Library): Good but requires system-level install on some platforms — violates Principle VI
- PyMeshLab: Has self-intersection detection but GPL-licensed

## R4: PLY Format Support

**Decision**: Add PLY to SUPPORTED_FORMATS. trimesh supports PLY natively.

**Rationale**: trimesh loads PLY files via `trimesh.load()` with automatic format detection. The only change needed is adding `"ply"` to the `SUPPORTED_FORMATS` set in `renderer.py` and handling PLY in the format detection logic.

**Findings**: trimesh uses the `plyfile` package (BSD license) as an optional dependency for PLY support. It's pip-installable and already commonly installed alongside trimesh.

## R5: 3MF and STL Export

**Decision**: Use trimesh's `mesh.export()` for both STL (binary) and 3MF export.

**Rationale**: The existing test fixtures already demonstrate that trimesh supports both formats:
- `mesh.export(path, file_type="stl")` — binary STL
- `mesh.export(path, file_type="3mf")` — 3MF format

Both are pip-only (no system packages). 3MF support uses trimesh's built-in exchange module.

## R6: Multi-Body Mesh Handling

**Decision**: Use `mesh.split()` to separate disconnected shells, analyze each independently, then optionally recombine.

**Rationale**: trimesh's `split()` method separates a mesh into connected components (shells). Each shell can be analyzed independently for defects. The repair pipeline processes each shell, then the results are aggregated into a single report.

**Findings**:
- `mesh.split()` returns a list of `Trimesh` objects
- `trimesh.util.concatenate(meshes)` recombines shells after repair
- For single-body meshes, `mesh.split()` returns a list of length 1 — no special handling needed

## R7: Mesh Health Score Calculation

**Decision**: Health score is a float 0.0–1.0 derived from weighted defect counts.

**Rationale**: A simple numeric score enables threshold-based classification (print-ready/repairable/severely-damaged) and gives users an at-a-glance quality indicator.

**Calculation**:
- Start at 1.0 (perfect)
- Subtract weighted penalties per defect type:
  - Critical defects (non-manifold, holes, non-watertight): -0.1 per affected face/edge, capped at -0.6
  - Warning defects (normals, self-intersections): -0.05 per affected element, capped at -0.3
  - Info defects (degenerate, duplicate, excessive poly): -0.01 per affected element, capped at -0.1
- Floor at 0.0
- Classification: ≥0.8 = print-ready, 0.3–0.8 = repairable, <0.3 = severely-damaged

This maps approximately to the >50% critical defect threshold from the spec's clarification.
