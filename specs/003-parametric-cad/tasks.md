# Tasks: Parametric CAD Generation

**Input**: Design documents from `/specs/003-parametric-cad/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/public-api.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the create/ package structure and add new exception types

- [X] T001 Create src/print3d_skill/create/ package with empty __init__.py, session.py, compiler.py, printability.py, bosl2.py
- [X] T002 [P] Add DesignError and PrintabilityError exception classes to src/print3d_skill/exceptions.py following existing hierarchy (both extend Print3DSkillError)

---

## Phase 2: Foundational (Models & Exports)

**Purpose**: Define all Create mode dataclasses and update package exports. MUST complete before any user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create all Create mode dataclasses in src/print3d_skill/models/create.py: CreateConfig (with defaults from data-model.md), DesignRequest, CreateSession, GeneratedDesign, PrintabilityWarning, PrintabilityReport, DesignExport, CreateResult
- [X] T004 Update src/print3d_skill/models/__init__.py to export all 8 new types from models/create.py
- [X] T005 [P] Update src/print3d_skill/__init__.py to add create_design and validate_printability to top-level exports (can be placeholder imports initially)

**Checkpoint**: All models importable from `print3d_skill.models`, exception classes available

---

## Phase 3: User Story 1 - Generate 3D Model from Description (Priority: P1) 🎯 MVP

**Goal**: Start a design session, submit OpenSCAD code, compile it to STL, and render a multi-angle preview. Single iteration happy path.

**Independent Test**: Call `start_session()` with a DesignRequest, then `submit_iteration()` with valid OpenSCAD code. Verify GeneratedDesign has `compile_success=True`, a valid `mesh_path`, and a `preview_path`.

### Implementation for User Story 1

- [X] T006 [P] [US1] Implement detect_bosl2() with result caching in src/print3d_skill/create/bosl2.py — run `openscad -o /dev/null -e 'include <BOSL2/std.scad>;'` and check exit code, cache result, return bool
- [X] T007 [P] [US1] Implement CreateSession lifecycle in src/print3d_skill/create/session.py — working directory creation (tempfile), iteration counter, file path generation for .scad/.stl/.png per iteration, session state tracking
- [X] T008 [US1] Implement compile_and_render() in src/print3d_skill/create/compiler.py — save .scad code to session working dir, call existing _compile_scad() from rendering/__init__.py to produce STL, call render_preview() for multi-angle PNG, return paths
- [X] T009 [US1] Implement start_session() and submit_iteration() in src/print3d_skill/create/__init__.py — start_session validates OpenSCAD available, creates CreateSession; submit_iteration saves code, compiles, renders, returns GeneratedDesign
- [X] T010 [US1] Update CreateHandler.handle() in src/print3d_skill/modes/create.py — accept description/dimensions/material/config kwargs, call start_session(), return ModeResponse with session info and guidance message
- [X] T011 [US1] Wire route("create", ...) kwargs through to CreateHandler — verify router passes description, dimensions, material, config to mode handler in src/print3d_skill/router.py (if not already forwarded)

**Checkpoint**: `start_session()` + `submit_iteration()` work for a single valid .scad file, producing compiled STL and rendered PNG

---

## Phase 4: User Story 2 - Iterate on Design via Visual Feedback (Priority: P2)

**Goal**: Support multiple iterations with versioned .scad files, compile error capture, max iteration enforcement, and change tracking.

**Independent Test**: Submit code with a syntax error, verify `compile_success=False` and `compile_error` contains the OpenSCAD error. Then submit fixed code, verify iteration increments and versioned files exist. Submit past max_iterations, verify DesignError is raised.

**Depends on**: US1 (session and compilation infrastructure)

### Implementation for User Story 2

- [X] T012 [US2] Add versioned file naming to session in src/print3d_skill/create/session.py — generate paths as design_v1.scad, design_v2.scad, etc. with corresponding design_v1.stl, design_v1_preview.png
- [X] T013 [US2] Add compile error capture to compiler in src/print3d_skill/create/compiler.py — capture OpenSCAD stderr on compile failure, populate GeneratedDesign.compile_error with the error text, set compile_success=False, skip render on failure
- [X] T014 [US2] Add max_iterations enforcement to submit_iteration in src/print3d_skill/create/__init__.py — check session.iteration against config.max_iterations, raise DesignError if exceeded
- [X] T015 [US2] Add changes_from_previous tracking to submit_iteration in src/print3d_skill/create/__init__.py — accept changes parameter, store in GeneratedDesign.changes_from_previous, maintain iteration history list on session

**Checkpoint**: Multiple submit_iteration() calls work with versioned files, compile errors returned cleanly, max iterations enforced

---

## Phase 5: User Story 3 - Validate Design for Printability (Priority: P3)

**Goal**: Check a compiled mesh against 4 FDM printability rules and return a structured report with actionable suggestions.

**Independent Test**: Load a mesh with known thin walls (< 0.8mm), run `validate_printability()`, verify PrintabilityReport has `is_printable=False` with a warning for `min_wall_thickness` rule including specific measured value and suggestion.

**Depends on**: Foundational (models only, no dependency on US1/US2)

### Implementation for User Story 3

- [X] T016 [P] [US3] Implement wall thickness detection via ray casting in src/print3d_skill/create/printability.py — for sampled faces, shoot ray inward along negative normal, measure distance to opposing face via trimesh ray intersection, compare against config.min_wall_thickness
- [X] T017 [P] [US3] Implement overhang angle detection in src/print3d_skill/create/printability.py — compute angle between each face normal and Z-up vector, flag faces where angle from vertical exceeds config.max_overhang_angle (default 45°)
- [X] T018 [P] [US3] Implement bridge distance detection in src/print3d_skill/create/printability.py — identify horizontal downward-facing faces (normal ≈ [0,0,-1]), ray cast downward from centroids, flag unsupported spans exceeding config.max_bridge_distance (default 10mm)
- [X] T019 [P] [US3] Implement bed adhesion area estimation in src/print3d_skill/create/printability.py — find min Z of mesh, select faces within 0.1mm of min Z, sum projected XY area, warn if below config.min_bed_adhesion_area (default 100mm²)
- [X] T020 [US3] Implement validate_printability() composing all 4 checks in src/print3d_skill/create/printability.py — load mesh via trimesh, run all checks, build PrintabilityReport with warnings list, is_printable flag, passed/total counts, and measured extremes

**Checkpoint**: `validate_printability("some.stl")` returns structured report with all 4 checks, actionable suggestions with specific numbers

---

## Phase 6: User Story 4 - Export Final Design (Priority: P4)

**Goal**: Export the approved design as STL, 3MF, and .scad source file with printability report.

**Independent Test**: After a successful session with at least one approved iteration, call `export_design(session, output_dir="/tmp/test")`, verify STL, 3MF, and .scad files exist in output_dir, meshes are watertight, and DesignExport contains correct paths and printability report.

**Depends on**: US1 (session), US3 (printability validation)

### Implementation for User Story 4

- [X] T021 [US4] Implement export_design() in src/print3d_skill/create/__init__.py — copy .scad source to output_dir, export STL and 3MF via existing export/formats.py export_to_formats(), run validate_printability() on final mesh, build and return DesignExport
- [X] T022 [US4] Implement create_design() orchestrator in src/print3d_skill/create/__init__.py — validate OpenSCAD available, detect BOSL2 if config.bosl2_preferred, return CreateResult with status/message/iterations/export/printability_report; handle "error" status for missing OpenSCAD or vague descriptions

**Checkpoint**: Full pipeline works: start_session → submit_iteration(s) → export_design → files on disk with printability report

---

## Phase 7: User Story 5 - Create Mode Knowledge & Design Patterns (Priority: P5)

**Goal**: Populate the knowledge system with CAD-relevant domain knowledge: tolerance tables, feature sizes, design patterns, BOSL2 references.

**Independent Test**: Call `query_knowledge(mode="create", problem_type="lookup_table")` and verify tolerance/feature size knowledge files are returned. Call `query_knowledge(mode="create", problem_type="design_pattern")` and verify design patterns are returned.

**Depends on**: None (uses existing knowledge system from F1)

### Implementation for User Story 5

- [X] T023 [P] [US5] Create tolerance tables in src/print3d_skill/knowledge_base/create/tolerances.yaml — press-fit, snap-fit, screw clearance values organized by material (PLA, PETG, ABS) and nozzle diameter (0.4mm, 0.6mm, 0.8mm)
- [X] T024 [P] [US5] Create minimum feature size tables in src/print3d_skill/knowledge_base/create/feature_sizes.yaml — min wall thickness, min hole diameter, min gap width, min text height by nozzle diameter
- [X] T025 [P] [US5] Create mechanical design patterns in src/print3d_skill/knowledge_base/create/design_patterns.yaml — screw bosses, snap clips, living hinges, vent slots, cable routing channels with recommended dimensions and OpenSCAD code snippets
- [X] T026 [P] [US5] Create BOSL2 module reference summaries in src/print3d_skill/knowledge_base/create/bosl2_reference.yaml — cuboid, threaded_rod, threaded_nut, spur_gear2d, bezier modules with key parameters and usage examples

**Checkpoint**: `query_knowledge(mode="create")` returns relevant knowledge files for all documented material/nozzle combinations

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Contract tests, integration validation, documentation updates

- [X] T027 Update tests/contract/test_public_api.py with F3 contract tests — verify all 6 public functions importable, all 8 model types importable, both new exceptions importable, return type contracts
- [X] T028 [P] Run quickstart.md validation — execute all 7 scenarios from specs/003-parametric-cad/quickstart.md and verify expected outputs
- [X] T029 [P] Update CLAUDE.md public API section to include new create functions (create_design, start_session, submit_iteration, export_design, validate_printability, detect_bosl2)
- [X] T030 Run full test suite (pytest) and verify no regressions against existing F1/F2 tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — core create pipeline
- **US2 (Phase 4)**: Depends on US1 — extends iteration handling
- **US3 (Phase 5)**: Depends on Foundational only — printability is independent of session pipeline
- **US4 (Phase 6)**: Depends on US1 + US3 — export needs session and printability
- **US5 (Phase 7)**: Depends on Foundational only — knowledge files are independent
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```text
Phase 1: Setup
    ↓
Phase 2: Foundational (models, exceptions, exports)
    ↓
    ├── US1 (P1): Session + Compile + Render ────┐
    │       ↓                                     │
    │   US2 (P2): Iteration Loop                  │
    │       ↓                                     │
    ├── US3 (P3): Printability Validation ────────┤
    │                                             │
    ├── US5 (P5): Knowledge Content               │
    │                                             ↓
    └──────────────────────────────────> US4 (P4): Export
                                             ↓
                                      Phase 8: Polish
```

### Within Each User Story

- Models before services (Foundational before all)
- Infrastructure before orchestration (session.py, compiler.py before __init__.py)
- Core implementation before mode integration (create/ before modes/create.py)

### Parallel Opportunities

- **Phase 1**: T001 and T002 are parallel (different files)
- **Phase 2**: T004 and T005 are parallel after T003
- **Phase 3 (US1)**: T006 and T007 are parallel (bosl2.py and session.py are independent)
- **Phase 5 (US3)**: T016, T017, T018, T019 are all parallel (4 independent checks)
- **Phase 7 (US5)**: T023, T024, T025, T026 are all parallel (4 independent YAML files)
- **Cross-story**: US3 and US5 can run in parallel with US1/US2 (independent of session pipeline)

---

## Parallel Example: User Story 3

```bash
# Launch all 4 printability checks in parallel (different functions, same file but independent):
Task: "Implement wall thickness detection in src/print3d_skill/create/printability.py"
Task: "Implement overhang angle detection in src/print3d_skill/create/printability.py"
Task: "Implement bridge distance detection in src/print3d_skill/create/printability.py"
Task: "Implement bed adhesion area estimation in src/print3d_skill/create/printability.py"

# Then compose them sequentially:
Task: "Implement validate_printability() composing all 4 checks"
```

## Parallel Example: User Story 5

```bash
# Launch all 4 knowledge files in parallel (completely independent files):
Task: "Create tolerance tables in knowledge_base/create/tolerances.yaml"
Task: "Create feature size tables in knowledge_base/create/feature_sizes.yaml"
Task: "Create design patterns in knowledge_base/create/design_patterns.yaml"
Task: "Create BOSL2 reference in knowledge_base/create/bosl2_reference.yaml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T005)
3. Complete Phase 3: User Story 1 (T006-T011)
4. **STOP and VALIDATE**: Test single iteration pipeline end-to-end
5. Basic Create mode is functional

### Incremental Delivery

1. Setup + Foundational → Models and package structure ready
2. US1 → Single-shot generate + compile + render (MVP)
3. US2 → Robust iteration loop with error handling
4. US3 + US5 (parallel) → Printability validation + knowledge content
5. US4 → Full export pipeline with printability report
6. Polish → Contract tests, quickstart validation, documentation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US3 and US5 can be worked in parallel since they don't depend on each other
- The create/ package is NEW — does not modify any existing F1/F2 code except modes/create.py and exceptions.py
- Existing _compile_scad() and render_preview() from rendering/ are reused, not reimplemented
- Existing export_to_formats() from export/ is reused for STL/3MF generation
- Knowledge files follow existing YAML schema from F1 knowledge system
