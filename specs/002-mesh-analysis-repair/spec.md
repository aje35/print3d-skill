# Feature Specification: Mesh Analysis & Repair

**Feature Branch**: `002-mesh-analysis-repair`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Implement the Fix mode: the ability to load a mesh from any common source, automatically diagnose geometry defects, apply repairs, and export a clean printable file — with visual verification at every step."

## Clarifications

### Session 2026-03-14

- Q: When the system loads a mesh containing quad or polygon faces (OBJ, PLY), what should it do? → A: Auto-triangulate all non-triangular faces on load silently as a normalization step.
- Q: What criteria separate "repairable" from "severely-damaged"? → A: "Severely-damaged" when >50% of faces or edges are affected by critical defects — the mesh lacks enough valid structure to repair.
- Q: Should the pipeline attempt repair on severely-damaged meshes or refuse? → A: Attempt best-effort repair but flag the classification prominently in the repair summary as a warning that results may be incomplete.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Analyze Mesh Defects (Priority: P1)

A user has a mesh file (STL, 3MF, OBJ, or PLY) from any source — a Thingiverse download, an AI-generated model, a 3D scan, or a CAD export. They want to know what's wrong with it before attempting to print. The skill loads the file, runs a comprehensive defect analysis, and produces a structured report listing every issue found, categorized by severity (critical, warning, info).

**Why this priority**: Analysis is the foundation — every other Fix mode capability depends on accurate defect detection. Without analysis, repair is blind. This story alone delivers immediate value: users can understand what's wrong with their mesh even before any repairs are implemented.

**Independent Test**: Can be fully tested by loading known-defective mesh files and verifying the analysis report correctly identifies all planted defects with accurate severity classifications.

**Acceptance Scenarios**:

1. **Given** a mesh file with non-manifold edges, **When** the user runs analysis, **Then** the report lists non-manifold edges as a critical defect with the count and affected edge locations.
2. **Given** a mesh file with inverted normals on some faces, **When** the user runs analysis, **Then** the report lists inconsistent normals as a warning with the count of inverted faces.
3. **Given** a clean, watertight mesh with no defects, **When** the user runs analysis, **Then** the report shows zero defects and marks the mesh as print-ready.
4. **Given** a mesh file in an unsupported format (e.g., STEP), **When** the user attempts analysis, **Then** the system reports the format is not supported and lists accepted formats.
5. **Given** a multi-body mesh (multiple shells in one file), **When** the user runs analysis, **Then** the report analyzes each shell independently and reports per-shell and aggregate defect summaries.

---

### User Story 2 - Repair Mesh Defects (Priority: P2)

A user has a mesh with known defects (identified via analysis) and wants the skill to automatically fix them. The skill applies appropriate repair strategies for each defect type in priority order — critical defects first, then warnings — and produces a repaired mesh. Each repair step includes a before/after visual preview so the agent can verify the fix didn't introduce new problems.

**Why this priority**: Repair is the core value proposition of Fix mode — analysis alone tells users what's wrong, but repair actually solves the problem. This depends on US1 (analysis) to know what to fix.

**Independent Test**: Can be fully tested by providing meshes with specific known defects, running repair, and verifying the output mesh passes re-analysis with zero critical defects and that visual previews are generated at each repair step.

**Acceptance Scenarios**:

1. **Given** a mesh with boundary edge holes, **When** the user runs repair, **Then** holes are filled using appropriate triangulation and the repaired mesh has no boundary edges.
2. **Given** a mesh with inconsistent normals, **When** the user runs repair, **Then** normals are reconciled to face outward consistently and the repaired mesh passes normal consistency checks.
3. **Given** a mesh with duplicate vertices closer than the merge tolerance, **When** the user runs repair, **Then** vertices are merged and the vertex count decreases without changing visual geometry.
4. **Given** a mesh with degenerate (zero-area) triangles, **When** the user runs repair, **Then** degenerate faces are removed and the face count decreases without creating new holes.
5. **Given** an already-clean mesh, **When** the user runs repair, **Then** the mesh is returned unchanged (idempotent behavior) with a report indicating no repairs were needed.
6. **Given** a mesh with multiple defect types, **When** the user runs repair, **Then** repairs are applied in priority order (critical first) and each step generates a before/after preview.

---

### User Story 3 - End-to-End Repair Pipeline (Priority: P3)

A user wants to hand the skill a broken mesh and get back a clean, printable file with minimal interaction. The skill runs the full pipeline: load → analyze → prioritized repairs → re-analyze to confirm → visual verification → export. The user receives the repaired mesh file plus a summary of what was found and what was fixed.

**Why this priority**: This is the composed workflow that ties US1 and US2 together into the seamless experience described in the project vision. It depends on both analysis and repair being solid.

**Independent Test**: Can be fully tested by providing a mesh with multiple defects, running the pipeline end-to-end, and verifying the exported mesh is clean, the repair summary is accurate, and before/after previews were generated.

**Acceptance Scenarios**:

1. **Given** a defective mesh file path and an output path, **When** the user invokes the repair pipeline, **Then** the system produces a repaired file at the output path plus a structured repair summary.
2. **Given** a mesh where some defects cannot be auto-repaired, **When** the pipeline completes, **Then** the repair summary clearly lists what was fixed, what remains unfixed, and why.
3. **Given** a mesh exported as STL, **When** the user requests 3MF export, **Then** the repaired mesh is exported in the requested format.
4. **Given** a mesh file, **When** the pipeline runs, **Then** multi-angle before/after preview images are rendered and included in the result.

---

### User Story 4 - Mesh Repair Knowledge & Guidance (Priority: P4)

The knowledge system is populated with mesh repair domain knowledge: diagnostic decision trees (symptom → cause → repair strategy), slicer error message mappings (what "non-manifold" means in Bambu Studio vs PrusaSlicer vs Cura), and common defect patterns by source type (Thingiverse downloads, AI-generated meshes, 3D scans, CAD exports, terrain models). An agent can query this knowledge to explain defects to users and choose repair strategies.

**Why this priority**: Knowledge content enriches the user experience but is not required for the core analysis/repair mechanics. It can be populated incrementally.

**Independent Test**: Can be fully tested by querying the knowledge system with Fix mode context and verifying relevant decision trees, error mappings, and defect pattern data are returned.

**Acceptance Scenarios**:

1. **Given** a query for Fix mode knowledge about non-manifold edges, **When** the knowledge system is queried, **Then** it returns a decision tree mapping the symptom to likely causes and repair strategies.
2. **Given** a query about slicer error messages, **When** the knowledge system is queried, **Then** it returns mappings showing how different slicers (Bambu Studio, PrusaSlicer, Cura) report the same underlying mesh defect.
3. **Given** a query about defect patterns for a specific source type (e.g., "thingiverse"), **When** the knowledge system is queried, **Then** it returns the most common defects found in meshes from that source with recommended repair approaches.

---

### Edge Cases

- What happens when a mesh file is empty (zero vertices/faces)?
- What happens when a mesh file is corrupted or truncated mid-write?
- What happens when a mesh has extremely high polygon count (>5M faces)?
- What happens when a mesh uses non-standard units (inches, meters) and the system needs to detect scale?
- What happens when hole filling would create self-intersecting geometry?
- What happens when a multi-body mesh has shells that intersect each other?
- What happens when vertex merging at the configured tolerance would collapse thin features?
- What happens when a repair step fixes one defect but introduces another?
- What happens when the input mesh is a point cloud (vertices only, no faces)?

## Requirements *(mandatory)*

### Functional Requirements

**Mesh Loading**:

- **FR-001**: System MUST accept STL (binary and ASCII), 3MF, OBJ, and PLY file formats for analysis and repair.
- **FR-002**: System MUST detect likely unit scale (millimeters vs inches vs meters) based on bounding box heuristics and report the detected scale.
- **FR-003**: System MUST handle multi-body meshes (multiple disconnected shells in one file) by analyzing each shell independently.
- **FR-004**: System MUST reject unsupported formats with a clear error listing accepted formats.
- **FR-005**: System MUST handle corrupted or truncated files gracefully with a descriptive error rather than an unhandled exception.
- **FR-005a**: System MUST auto-triangulate any non-triangular faces (quads, n-gons) on load as a silent normalization step. All downstream analysis and repair operations assume triangular meshes.

**Defect Analysis**:

- **FR-006**: System MUST detect and report non-manifold edges (edges shared by more than 2 faces) with severity "critical".
- **FR-007**: System MUST detect and report non-manifold vertices (vertices where the face fan is not a single connected component) with severity "critical".
- **FR-008**: System MUST detect and report boundary edges / holes (edges belonging to only one face) with severity "critical".
- **FR-009**: System MUST detect and report inverted or inconsistent face normals with severity "warning".
- **FR-010**: System MUST detect and report self-intersecting faces with severity "warning".
- **FR-011**: System MUST detect and report degenerate triangles (zero-area or near-zero-area faces) with severity "info".
- **FR-012**: System MUST detect and report duplicate vertices (vertices within a configurable merge tolerance) with severity "info".
- **FR-013**: System MUST detect and report duplicate faces with severity "info".
- **FR-014**: System MUST detect and report excessive polygon count (above a configurable threshold) with severity "info".
- **FR-015**: System MUST detect and report non-watertight shells with severity "critical".
- **FR-016**: System MUST produce a structured analysis report containing: per-defect-type counts, severity levels, affected element indices, and an overall mesh health score.
- **FR-017**: System MUST classify the overall mesh as "print-ready" (zero critical defects), "repairable" (critical defects affecting ≤50% of faces/edges), or "severely-damaged" (critical defects affecting >50% of faces/edges — insufficient valid structure for automated repair).

**Repair Strategies**:

- **FR-018**: System MUST fill boundary edge holes using fan triangulation for simple holes and planar fill for complex holes.
- **FR-019**: System MUST reconcile inconsistent normals to face outward uniformly.
- **FR-020**: System MUST merge duplicate vertices within a configurable tolerance (default: 1e-8).
- **FR-021**: System MUST remove degenerate (zero-area) triangles without creating new holes.
- **FR-022**: System MUST support mesh decimation to reduce polygon count to a configurable target while preserving overall shape.
- **FR-023**: Each repair step MUST render a before/after multi-angle preview for visual verification by the agent.

**Repair Pipeline**:

- **FR-024**: System MUST execute repairs in a defined priority order: merge vertices → remove degenerates → fill holes → reconcile normals → final validation.
- **FR-025**: System MUST re-analyze the mesh after all repairs to confirm defects are resolved.
- **FR-025a**: Pipeline MUST attempt best-effort repair on meshes classified as "severely-damaged", but MUST include a prominent warning in the repair summary that results may be incomplete due to extensive damage.
- **FR-026**: Pipeline MUST be idempotent — running it on an already-clean mesh MUST produce no changes and report "no repairs needed".
- **FR-027**: Pipeline MUST produce a structured repair summary listing: defects found, repairs applied, defects remaining (if any), and reason for any unresolved defects.

**Export**:

- **FR-028**: System MUST export repaired meshes in STL format (binary).
- **FR-029**: System MUST export repaired meshes in 3MF format.
- **FR-030**: System MUST include the repair summary as part of the export result.

**Knowledge Content**:

- **FR-031**: Knowledge system MUST contain mesh repair decision trees mapping symptoms to likely causes and repair strategies.
- **FR-032**: Knowledge system MUST contain slicer error message mappings showing how Bambu Studio, PrusaSlicer, and Cura report common mesh defects.
- **FR-033**: Knowledge system MUST contain common defect patterns organized by mesh source type (Thingiverse downloads, AI-generated, 3D scans, CAD exports, terrain models).

### Key Entities

- **MeshAnalysisReport**: The structured result of analyzing a mesh. Contains a list of defects, overall health classification, per-shell summaries (for multi-body meshes), and aggregate statistics (vertex count, face count, bounding box, detected units).
- **MeshDefect**: A single detected defect. Has a type (from the defect type enum), severity (critical/warning/info), count of affected elements, and affected element indices.
- **RepairResult**: The outcome of a single repair step. Contains the defect type addressed, the strategy applied, elements affected, success status, and before/after mesh state references.
- **RepairSummary**: The aggregate outcome of the full repair pipeline. Contains the list of RepairResults, total defects found, total defects fixed, remaining defects (with reasons), and export file paths.
- **RepairConfig**: User-configurable parameters for the repair pipeline. Includes vertex merge tolerance, decimation target, hole fill strategy preferences, and maximum polygon count threshold.

## Assumptions

- The existing F1 rendering pipeline (`render_preview()`) is sufficient for generating before/after previews during repair steps.
- The existing F1 tool orchestration (trimesh provider) handles mesh loading for all four target formats; this feature extends the loading with unit detection and multi-body handling.
- Vertex merge tolerance default of 1e-8 is suitable for most meshes; users can override via RepairConfig.
- Self-intersection repair is complex and may not be fully automatable — the system will detect and report self-intersections but may not auto-repair all cases. The repair summary will clearly indicate what remains unresolved.
- Mesh decimation preserves topology (no new non-manifold edges introduced) when using quadric-based simplification.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Analysis correctly identifies 100% of planted defects in the test mesh suite (zero false negatives for critical defects).
- **SC-002**: Repair pipeline produces a watertight, print-ready mesh for at least 90% of meshes classified as "repairable".
- **SC-003**: Pipeline is idempotent — running repair on an already-clean mesh produces byte-identical output.
- **SC-004**: Full pipeline (load → analyze → repair → re-analyze → export) completes in under 30 seconds for meshes up to 500K faces.
- **SC-005**: Before/after visual previews are generated for every repair step, enabling the agent to verify fixes without user intervention.
- **SC-006**: Knowledge queries for Fix mode return relevant decision trees and defect pattern data for all documented source types.
- **SC-007**: The repair summary accurately reflects all actions taken — no silent fixes or unreported changes.
