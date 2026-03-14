# Tasks: Mesh Analysis & Repair

**Input**: Design documents from `/specs/002-mesh-analysis-repair/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/public-api.md, quickstart.md

**Tests**: Included — the spec requires pytest with programmatically generated defective meshes (SC-001 through SC-007), and the plan explicitly lists test files.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new package directories and extend existing files with shared types needed across all user stories

- [X] T001 Create analysis/, repair/, export/ package directories with __init__.py stubs in src/print3d_skill/
- [X] T002 [P] Add MeshAnalysisError, RepairError, ExportError exception classes to src/print3d_skill/exceptions.py
- [X] T003 [P] Add PLY to SUPPORTED_FORMATS set in src/print3d_skill/rendering/renderer.py and add "ply" to format detection logic in src/print3d_skill/models/mesh.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define all data model types used across user stories and create defective mesh test fixtures

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Implement analysis enums (DefectType with 10 values, DefectSeverity, MeshHealthClassification) and dataclasses (MeshDefect, ShellAnalysis, MeshAnalysisReport) per data-model.md in src/print3d_skill/models/analysis.py
- [X] T005 [P] Implement repair enum (RepairStrategy with 6 values) and dataclasses (RepairResult, RepairSummary, RepairConfig with defaults) per data-model.md in src/print3d_skill/models/repair.py
- [X] T006 [P] Implement ExportResult dataclass per data-model.md in src/print3d_skill/models/export.py
- [X] T007 Update src/print3d_skill/models/__init__.py to re-export all new model classes from analysis, repair, and export modules
- [X] T008 Add defective mesh fixture generators to tests/conftest.py: mesh_with_holes (removed faces to create boundary edges), mesh_with_bad_normals (flipped face winding), mesh_with_duplicate_vertices (vertices within 1e-8), mesh_with_degenerate_faces (zero-area triangles), mesh_with_duplicate_faces (repeated face indices), mesh_non_manifold (edges shared by >2 faces), mesh_multi_body (two separate shells), mesh_self_intersecting (overlapping geometry), mesh_high_poly (>1M faces), clean_mesh (watertight cube with no defects)

**Checkpoint**: All models defined, fixtures ready — user story implementation can begin

---

## Phase 3: User Story 1 — Analyze Mesh Defects (Priority: P1) MVP

**Goal**: Load a mesh file (STL, 3MF, OBJ, PLY), detect all 10 defect types with severity classification, produce a structured MeshAnalysisReport with health score and classification

**Independent Test**: Load known-defective mesh fixtures, verify analysis report correctly identifies all planted defects with accurate severity classifications and health scores

### Implementation for User Story 1

- [X] T009 [US1] Implement 9 core defect detector functions in src/print3d_skill/analysis/detectors.py: detect_non_manifold_edges, detect_non_manifold_vertices, detect_boundary_edges, detect_non_watertight, detect_inconsistent_normals, detect_degenerate_faces, detect_duplicate_vertices, detect_duplicate_faces, detect_excessive_poly_count — each returns a MeshDefect or None using trimesh APIs per research.md R1
- [X] T010 [US1] Implement self-intersection detector with R-tree spatial index pre-filtering and Moller-Trumbore triangle-triangle intersection tests in src/print3d_skill/analysis/detectors.py — sample subset for meshes >100K faces per research.md R3
- [X] T011 [US1] Implement report builder with health score calculation (weighted penalties: critical -0.1, warning -0.05, info -0.01 per element with caps) and classification logic (>=0.8 print_ready, 0.3-0.8 repairable, <0.3 severely_damaged) in src/print3d_skill/analysis/report.py
- [X] T012 [US1] Implement analyze_mesh() public API in src/print3d_skill/analysis/__init__.py: load mesh via trimesh, auto-triangulate, detect units via bounding box heuristics, split into shells via mesh.split(), run all detectors on each shell, aggregate into MeshAnalysisReport — raise MeshAnalysisError/UnsupportedFormatError/MeshLoadError per contracts/public-api.md
- [X] T013 [P] [US1] Write unit tests for all 10 defect detectors in tests/unit/test_detectors.py using defective mesh fixtures — verify each detector returns correct DefectType, severity, count, and affected_indices
- [X] T014 [P] [US1] Write unit tests for report builder in tests/unit/test_report.py — verify health score calculation, classification thresholds, multi-shell aggregation, and edge cases (empty mesh, all-defective mesh)
- [X] T015 [US1] Write integration tests for analyze_mesh() in tests/integration/test_analysis.py — test all 5 acceptance scenarios: non-manifold detection, inconsistent normals, clean mesh (print-ready), unsupported format error, multi-body per-shell analysis

**Checkpoint**: analyze_mesh() works end-to-end — load any supported mesh, get a complete defect report with health classification

---

## Phase 4: User Story 2 — Repair Mesh Defects (Priority: P2)

**Goal**: Apply targeted repair strategies for each defect type using trimesh repair APIs, with before/after visual preview at each step

**Independent Test**: Provide meshes with specific known defects, run individual repair strategies, verify output mesh passes re-analysis with those defects resolved

**Depends on**: US1 (needs analyze_mesh for pre/post-repair verification)

### Implementation for User Story 2

- [X] T016 [US2] Implement all 6 repair strategy functions in src/print3d_skill/repair/strategies.py: strategy_merge_vertices (trimesh merge_vertices with configurable tolerance), strategy_remove_degenerates (remove_degenerate_faces), strategy_remove_duplicates (remove_duplicate_faces), strategy_fill_holes (trimesh.repair.fill_holes), strategy_fix_normals (trimesh.repair.fix_normals + fix_winding), strategy_decimate (simplify_quadric_decimation) — each returns a RepairResult per research.md R2
- [X] T017 [US2] Write unit tests for individual repair strategies in tests/unit/test_strategies.py — verify each strategy: merge_vertices reduces vertex count, remove_degenerates removes zero-area faces, fill_holes makes mesh watertight, fix_normals reconciles winding, decimate reduces face count to target
- [X] T018 [US2] Write integration tests for repair operations with before/after analysis verification in tests/integration/test_repair.py — test all 6 acceptance scenarios: hole filling, normal reconciliation, vertex merging, degenerate removal, idempotent on clean mesh, multi-defect prioritized repair with previews

**Checkpoint**: Individual repair strategies work correctly — each fixes its targeted defect type and produces RepairResult

---

## Phase 5: User Story 3 — End-to-End Repair Pipeline (Priority: P3)

**Goal**: Compose analysis + repair + export into a seamless pipeline: load → analyze → repair in priority order → re-analyze → render previews → export to STL/3MF

**Independent Test**: Provide a mesh with multiple defects, run the full pipeline, verify exported mesh is clean, repair summary is accurate, and previews were generated

**Depends on**: US1 (analysis), US2 (repair strategies)

### Implementation for User Story 3

- [X] T019 [US3] Implement ordered repair pipeline in src/print3d_skill/repair/pipeline.py: execute strategies in order (merge_vertices → remove_degenerates → remove_duplicates → fill_holes → fix_normals), render before/after preview at each step via render_preview(), collect RepairResults, handle severely-damaged meshes with best-effort + warning per FR-025a
- [X] T020 [US3] Implement repair_mesh() public API in src/print3d_skill/repair/__init__.py: load mesh, run initial analyze_mesh(), skip if print-ready, execute pipeline, re-analyze, export to configured formats, return RepairSummary — raise RepairError on unrecoverable failures per contracts/public-api.md
- [X] T021 [P] [US3] Implement format-specific exporters (STL binary via mesh.export file_type="stl", 3MF via mesh.export file_type="3mf") in src/print3d_skill/export/formats.py per research.md R5
- [X] T022 [US3] Implement export_mesh() public API in src/print3d_skill/export/__init__.py: load mesh, export to requested formats in output directory, return ExportResult with paths and analysis — raise ExportError on failure per contracts/public-api.md
- [X] T023 [US3] Update Fix mode handler from stub to full pipeline routing in src/print3d_skill/modes/fix.py: accept mesh_path and output_path kwargs, call repair_mesh(), return ModeResponse with RepairSummary as data per contracts/public-api.md
- [X] T024 [US3] Add analyze_mesh, repair_mesh, export_mesh to public API exports in src/print3d_skill/__init__.py and __all__ list
- [X] T025 [US3] Write integration tests for full pipeline in tests/integration/test_pipeline.py — test all 4 acceptance scenarios: defective mesh produces repaired file + summary, unfixable defects listed in remaining, 3MF export format, before/after previews generated
- [X] T026 [P] [US3] Write integration tests for export formats in tests/integration/test_export.py — verify STL binary export, 3MF export, multi-format export, output directory creation, ExportResult paths
- [X] T027 [US3] Add F2 contract tests to tests/contract/test_public_api.py: verify analyze_mesh/repair_mesh/export_mesh signatures, return types, documented exceptions (FileNotFoundError, UnsupportedFormatError, MeshLoadError, MeshAnalysisError, RepairError, ExportError), and idempotency per contracts/public-api.md

**Checkpoint**: Full pipeline works end-to-end — hand it a broken mesh, get back a clean exported file with complete repair summary

---

## Phase 6: User Story 4 — Mesh Repair Knowledge & Guidance (Priority: P4)

**Goal**: Populate the knowledge system with Fix mode domain knowledge: decision trees, slicer error mappings, and defect patterns by source type

**Independent Test**: Query knowledge system with mode="fix" and verify relevant YAML content is returned for each knowledge type

**Depends on**: None (independent of US1-US3, uses existing knowledge loader)

### Implementation for User Story 4

- [X] T028 [P] [US4] Create mesh repair decision tree YAML in src/print3d_skill/knowledge_base/fix_mesh_repair_decision_tree.yaml — map symptoms (non-manifold, holes, bad normals, self-intersection, degenerate faces) to causes and repair strategies with priority ordering, tagged with modes: [fix] and type: decision_tree
- [X] T029 [P] [US4] Create slicer error mappings YAML in src/print3d_skill/knowledge_base/fix_slicer_error_mappings.yaml — map error messages from Bambu Studio, PrusaSlicer, and Cura to underlying DefectType values with recommended fixes, tagged with modes: [fix] and type: lookup_table
- [X] T030 [P] [US4] Create defect patterns by source type YAML in src/print3d_skill/knowledge_base/fix_defect_patterns_by_source.yaml — document common defects for Thingiverse downloads, AI-generated meshes, 3D scans, CAD exports, and terrain models with recommended repair approaches, tagged with modes: [fix] and type: lookup_table

**Checkpoint**: Knowledge queries for Fix mode return relevant decision trees, slicer mappings, and defect patterns

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, cleanup, and final integration verification

- [X] T031 Run all 7 quickstart.md scenarios as end-to-end validation (analyze mesh, repair mesh, clean mesh idempotency, custom config, export, query knowledge, fix via router)
- [X] T032 Verify all tests pass and review test coverage across analysis/, repair/, export/ modules

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001) — BLOCKS all user stories
- **US1 Analyze (Phase 3)**: Depends on Foundational completion
- **US2 Repair (Phase 4)**: Depends on US1 (needs analyze_mesh for verification)
- **US3 Pipeline (Phase 5)**: Depends on US1 + US2 (composes both)
- **US4 Knowledge (Phase 6)**: Depends on Foundational only — can run in parallel with US1/US2/US3
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — no dependencies on other stories
- **US2 (P2)**: Depends on US1 — needs analyze_mesh() to verify repairs worked
- **US3 (P3)**: Depends on US1 + US2 — composes analysis + repair strategies + export
- **US4 (P4)**: Independent — can start after Foundational, parallel with US1/US2/US3

### Within Each User Story

- Models before service logic
- Service logic before public API wrapper
- Public API before integration tests
- Unit tests can run in parallel with each other after implementation

### Parallel Opportunities

- T002, T003 can run in parallel (different files, Phase 1)
- T004, T005, T006 can run in parallel (different model files, Phase 2)
- T013, T014 can run in parallel (different test files, US1)
- T021 can run in parallel with T019-T020 (export/formats.py independent of pipeline.py)
- T025, T026 can run in parallel (different test files, US3)
- T028, T029, T030 can ALL run in parallel (independent YAML files, US4)
- US4 (Phase 6) can run entirely in parallel with US1-US3

---

## Parallel Example: User Story 1

```text
# After T012 (analyze_mesh API) completes, launch tests in parallel:
Task: T013 "Unit tests for detectors in tests/unit/test_detectors.py"
Task: T014 "Unit tests for report builder in tests/unit/test_report.py"
# Then sequential:
Task: T015 "Integration tests for analyze_mesh() in tests/integration/test_analysis.py"
```

## Parallel Example: User Story 4

```text
# All three knowledge files can be created simultaneously:
Task: T028 "Decision tree YAML"
Task: T029 "Slicer error mappings YAML"
Task: T030 "Defect patterns YAML"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T008)
3. Complete Phase 3: US1 Analyze (T009-T015)
4. **STOP and VALIDATE**: Test analyze_mesh() independently with all defective mesh fixtures
5. Users can now diagnose mesh problems — immediate value

### Incremental Delivery

1. Setup + Foundational → models and fixtures ready
2. US1 Analyze → users can diagnose meshes (MVP)
3. US2 Repair → individual repair strategies work
4. US3 Pipeline → full end-to-end repair + export
5. US4 Knowledge → domain expertise for agent guidance
6. Each story adds value without breaking previous stories

### Parallel Execution Strategy

With context for parallel work:

1. Complete Setup + Foundational sequentially
2. Once Foundational is done:
   - **Track A**: US1 → US2 → US3 (sequential dependency chain)
   - **Track B**: US4 (independent, can run alongside Track A)
3. Polish after both tracks complete

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- All repair strategies use trimesh APIs per research.md decisions R1-R2
- Self-intersection detection (T010) is the most complex single task — uses spatial indexing per research.md R3
- Test fixtures in conftest.py (T008) generate meshes programmatically — no binary fixtures in repo
- Before/after previews use existing F1 render_preview() — no new rendering code needed
