# Tasks: Model Modification

**Input**: Design documents from `/specs/004-model-modification/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/public-api.md, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create the modify package structure and data models

- [x] T001 Create modify package directory structure: `src/print3d_skill/modify/__init__.py`, `src/print3d_skill/modify/boolean.py`, `src/print3d_skill/modify/primitives.py`, `src/print3d_skill/modify/scale.py`, `src/print3d_skill/modify/combine.py`, `src/print3d_skill/modify/text.py`, `src/print3d_skill/modify/split.py`, `src/print3d_skill/modify/comparison.py`, `src/print3d_skill/modify/features.py`, and `src/print3d_skill/knowledge_base/modify/` directory
- [x] T002 [P] Create all Modify mode enums and dataclasses (ModifyOperation, BooleanType, ScaleMode, TextMode, PrimitiveType, AlignmentType, SurfaceFace, ToolPrimitive, BooleanParams, ScaleParams, CombineParams, TextParams, SplitParams, ModifyRequest, FeatureWarning, AlignmentFeature, ModifyResult) in `src/print3d_skill/models/modify.py` per data-model.md
- [x] T003 [P] Add modify-specific test fixtures (sample meshes with known dimensions, meshes with standard screw holes, multi-shell meshes) to `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement before/after visual comparison module in `src/print3d_skill/modify/comparison.py`: render input mesh with STANDARD_VIEWS before modification, render output mesh with identical ViewAngle objects after, return both preview paths. Use existing `render_preview()` from F1
- [x] T005 Implement ModifyHandler dispatch logic in `src/print3d_skill/modes/modify.py`: replace stub with full handler that validates context kwargs (mesh_path, operation, params), constructs ModifyRequest, dispatches to the appropriate operation module, wraps result in ModeResponse
- [x] T006 Implement `modify_mesh()` public function in `src/print3d_skill/modify/__init__.py`: accept `mesh_path, operation, output_path, **params`, build ModifyRequest from kwargs, dispatch to operation modules, run post-modification analysis (F2 `analyze_mesh()`), trigger before/after comparison, return ModifyResult. Detect input format from file extension and export output in the same format by default (FR-036). Add `modify_mesh` to `src/print3d_skill/__init__.py` public API exports
- [x] T007 [P] Implement output path generation logic in `src/print3d_skill/modify/__init__.py`: given input "model.stl", auto-generate "model_modified.stl" (or "model_modified_001.stl" if exists). For split operations, generate "model_bottom.stl" and "model_top.stl". Ensure output path never equals input path (FR-039)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Boolean Operations on Existing Models (Priority: P1) MVP

**Goal**: Perform boolean union, difference, and intersection operations on meshes using manifold3d, with primitive shape generation and auto-repair

**Independent Test**: Load a known mesh, boolean-subtract a cylinder primitive, verify output mesh has the hole, is watertight, and volume decreased

### Implementation for User Story 1

- [x] T008 [P] [US1] Implement primitive shape generation in `src/print3d_skill/modify/primitives.py`: functions `create_cylinder(diameter, height)`, `create_box(width, depth, height)`, `create_sphere(diameter)`, `create_cone(bottom_diameter, top_diameter, height)` using `trimesh.creation.*`. Accept position and orientation (Euler angles) for placement. Return trimesh.Trimesh
- [x] T009 [P] [US1] Implement manifold3d boolean wrapper in `src/print3d_skill/modify/boolean.py`: functions `boolean_union(mesh_a, mesh_b)`, `boolean_difference(mesh_a, mesh_b)`, `boolean_intersection(mesh_a, mesh_b)`. Convert trimesh.Trimesh to manifold3d.Manifold (via vertices/faces), perform boolean, convert back. Implement trimesh fallback when manifold3d unavailable
- [x] T010 [US1] Add auto-repair integration to `src/print3d_skill/modify/boolean.py`: before boolean operation, run `analyze_mesh()` on both inputs; if either has defects, run `repair_mesh()` from F2 and set `repair_performed=True` on the result. If repair fails to produce manifold mesh, return error
- [x] T011 [US1] Add empty geometry detection to `src/print3d_skill/modify/boolean.py`: after boolean operation, check if result mesh has zero volume or zero faces; if so, return warning explaining why (e.g., "Boolean intersection produced empty result: meshes do not overlap")
- [x] T012 [US1] Wire boolean operations into modify dispatch in `src/print3d_skill/modify/__init__.py`: when `operation="boolean"`, resolve tool mesh (from `tool_mesh_path` or generate from `tool_primitive` via primitives.py), call appropriate boolean function, run comparison, run analysis, build ModifyResult

**Checkpoint**: Boolean operations fully functional — can cut holes, merge meshes, intersect volumes. MVP complete.

---

## Phase 4: User Story 2 - Scaling and Resizing Models (Priority: P2)

**Goal**: Scale meshes uniformly, non-uniformly, or to a target dimension, with feature preservation warnings for standard hardware holes

**Independent Test**: Load a mesh with known bounding box, scale uniformly by 150%, verify output bbox is exactly 150% of original in all axes

### Implementation for User Story 2

- [x] T013 [P] [US2] Implement scaling operations in `src/print3d_skill/modify/scale.py`: functions `scale_uniform(mesh, factor)`, `scale_non_uniform(mesh, factors)`, `scale_to_dimension(mesh, axis, target_mm, proportional)`. All operate on trimesh.Trimesh via `mesh.apply_transform()` with numpy scale matrices. Return scaled mesh plus before/after BoundingBox
- [x] T014 [P] [US2] Implement feature detection for scaling warnings in `src/print3d_skill/modify/features.py`: function `detect_standard_holes(mesh)` that identifies circular boundary loops, fits circles to edge vertices, compares diameters against standard metric screw sizes (M2=2.2mm through M10=10.5mm clearance per ISO 273 with ±0.3mm tolerance). Return list of FeatureWarning with original/new dimensions after scaling
- [x] T015 [US2] Wire scaling into modify dispatch in `src/print3d_skill/modify/__init__.py`: when `operation="scale"`, parse ScaleParams from kwargs, call appropriate scale function, run feature detection and generate warnings, run comparison, run analysis, build ModifyResult with bbox_before/bbox_after and feature_warnings

**Checkpoint**: Scaling fully functional — uniform, non-uniform, dimension-targeted scaling with screw hole warnings

---

## Phase 5: User Story 3 - Combining and Aligning Multiple Models (Priority: P3)

**Goal**: Align and merge multiple meshes into one printable model with scale mismatch detection

**Independent Test**: Load two meshes, center one on top of the other, union them, verify result is a single watertight mesh with correct positioning

**Dependencies**: Requires US1 boolean union (T009)

### Implementation for User Story 3

- [x] T016 [US3] Implement alignment and combining in `src/print3d_skill/modify/combine.py`: function `combine_meshes(target, others, alignment, offset)` that (1) aligns each mesh relative to target using bounding box math — "center" centers on target centroid, "top"/"bottom"/etc. places on target's face, offset adds translation, (2) runs boolean union via `boolean_union()` from boolean.py, (3) runs manifold cleanup on result
- [x] T017 [US3] Add scale mismatch detection to `src/print3d_skill/modify/combine.py`: function `detect_scale_mismatch(meshes)` that compares bounding box volumes/dimensions of input meshes using existing unit detection heuristic from F1 rendering. If ratio exceeds 10:1, warn with suggested conversion factor (25.4 for inches→mm)
- [x] T018 [US3] Wire combining into modify dispatch in `src/print3d_skill/modify/__init__.py`: when `operation="combine"`, load all `other_mesh_paths`, run scale mismatch check, apply alignment and union, run comparison, run analysis, build ModifyResult

**Checkpoint**: Combining fully functional — align and merge models with scale warnings

---

## Phase 6: User Story 4 - Text and Logo Engraving/Embossing (Priority: P4)

**Goal**: Generate 3D text via OpenSCAD, position on model surfaces, boolean subtract (engrave) or add (emboss)

**Independent Test**: Load a flat-top box mesh, engrave "TEST" on the top face, verify text geometry is subtracted at 0.6mm depth

**Dependencies**: Requires US1 boolean operations (T009), requires OpenSCAD (extended tier)

### Implementation for User Story 4

- [x] T019 [US4] Implement text geometry generation in `src/print3d_skill/modify/text.py`: function `generate_text_mesh(text, font, font_size, depth)` that creates an OpenSCAD script with `linear_extrude(height=depth) text(text, size=font_size, font=font)`, compiles via F3 compiler, loads resulting STL as trimesh.Trimesh
- [x] T020 [US4] Implement text surface positioning in `src/print3d_skill/modify/text.py`: function `position_text_on_surface(text_mesh, target_mesh, surface, position)` that translates/rotates text mesh to sit on the specified face (top/bottom/front/back/left/right) of the target's bounding box, with 2D offset on the surface plane
- [x] T021 [US4] Add font size validation and graceful degradation in `src/print3d_skill/modify/text.py`: warn if font_size would produce features below nozzle diameter (default 0.4mm — approximately font_size < 3mm for legibility). Return CapabilityUnavailable error when OpenSCAD is not installed (check via `get_capability("openscad")`)
- [x] T022 [US4] Implement curved surface text projection in `src/print3d_skill/modify/text.py`: function `project_text_to_curved_surface(text_mesh, target_mesh, surface)` that handles simple analytic surfaces (cylinders, spheres) by radially projecting text vertices. For non-analytic surfaces, warn that text placement may be imperfect and fall back to flat plane positioning
- [x] T023 [US4] Wire text operations into modify dispatch in `src/print3d_skill/modify/__init__.py`: when `operation="engrave"`, generate text mesh, position on surface (flat or curved), perform boolean difference (engrave) or union (emboss) via boolean.py, run comparison, run analysis, build ModifyResult

**Checkpoint**: Text engraving/embossing functional on flat and simple curved surfaces with FDM-appropriate defaults

---

## Phase 7: User Story 5 - Splitting Models for Print (Priority: P5)

**Goal**: Split a model along a plane into two watertight parts with automatically generated alignment pins and holes

**Independent Test**: Load a cube mesh, split at Z=10mm, verify two watertight parts produced, alignment pins on bottom part, holes on top part, combined volume equals original

**Dependencies**: Requires US1 boolean operations (T009) for alignment feature attachment

### Implementation for User Story 5

- [x] T024 [US5] Implement plane-based mesh splitting in `src/print3d_skill/modify/split.py`: function `split_mesh(mesh, axis, offset_mm)` using `trimesh.intersections.slice_mesh_plane()` with cap=True to produce two watertight halves. Validate that the cutting plane intersects the mesh; if not, return error with bounding box info
- [x] T025 [US5] Implement alignment feature generation in `src/print3d_skill/modify/split.py`: function `add_alignment_features(part_a, part_b, cut_plane, pin_diameter, pin_height, pin_clearance)` that (1) identifies flat area on the cut face, (2) generates cylindrical pins via primitives.py, (3) boolean-unions pins onto part_a, (4) generates slightly larger cylinders (pin_diameter + 2*clearance), (5) boolean-subtracts holes from part_b. Return list of AlignmentFeature metadata
- [x] T026 [US5] Add split validation and warnings in `src/print3d_skill/modify/split.py`: warn if cut boundary is too thin for alignment features (wall thickness < 2 * pin_diameter at cut edge), warn if model already fits standard print bed (220x220mm), suggest alternative cut plane if current one produces a zero-volume part
- [x] T027 [US5] Wire split operations into modify dispatch in `src/print3d_skill/modify/__init__.py`: when `operation="split"`, parse SplitParams, call split_mesh, add alignment features if requested, export each part as separate file, run comparison (render each part + overview), run analysis on each part, build ModifyResult with multiple output_mesh_paths and alignment_features

**Checkpoint**: Splitting fully functional — plane-based cuts with alignment pins/holes

---

## Phase 8: User Story 6 - Visual Before/After Comparison Enhancements (Priority: P6)

**Goal**: Enhance visual comparison with highlight view angles for subtle changes and per-part rendering for split operations

**Independent Test**: Apply a small engraving to a model, verify at least one preview angle highlights the engraved area. Split a model, verify individual part previews plus overview are rendered.

**Dependencies**: Requires foundational comparison module (T004)

### Implementation for User Story 6

- [x] T028 [US6] Add highlight view angle selection in `src/print3d_skill/modify/comparison.py`: function `select_highlight_views(mesh_before, mesh_after)` that compares vertex positions to find the region of maximum geometric change, then adds a ViewAngle oriented toward that region to the standard views. Use bounding box centroid of the changed region to compute elevation/azimuth
- [x] T029 [US6] Add per-part split rendering in `src/print3d_skill/modify/comparison.py`: function `render_split_comparison(parts, original_preview_path)` that renders each split part individually, plus an overview showing all parts at their original relative positions with slight separation (exploded view offset). Return list of preview paths

**Checkpoint**: Visual comparison enhanced with smart view selection and split part previews

---

## Phase 9: User Story 7 - Modify Mode Knowledge Content (Priority: P7)

**Goal**: Populate knowledge system with Modify-mode-specific YAML content for boolean operations, text engraving, alignment pins, and splitting strategies

**Independent Test**: Query `query_knowledge(mode="modify")` and verify all 4 knowledge files are returned with correct metadata

**Dependencies**: None (can run in parallel with any user story)

### Implementation for User Story 7

- [x] T030 [P] [US7] Create `src/print3d_skill/knowledge_base/modify/boolean_best_practices.yaml` (type: design_rules, modes: [modify]): input preparation rules (repair first, check watertight), operation selection guide (union for combining, difference for holes/channels, intersection for overlap extraction), common failure modes (non-manifold input, degenerate faces, co-planar faces) with solutions
- [x] T031 [P] [US7] Create `src/print3d_skill/knowledge_base/modify/text_engraving_guidelines.yaml` (type: lookup_table, modes: [modify]): minimum font size by nozzle diameter (0.4mm→3mm min, 0.6mm→4mm min, 0.8mm→5mm min), recommended engraving depth by layer height (3x layer height minimum), font recommendations for FDM legibility (sans-serif, bold weight, avoid thin strokes)
- [x] T032 [P] [US7] Create `src/print3d_skill/knowledge_base/modify/alignment_pin_tolerances.yaml` (type: tolerance_table, modes: [modify], materials: [PLA, PETG, ABS]): pin diameter/hole clearance by material and nozzle (PLA 0.4mm: 0.3mm clearance, PETG 0.4mm: 0.35mm, ABS 0.4mm: 0.25mm), press-fit vs slip-fit values, recommended pin height-to-diameter ratios
- [x] T033 [P] [US7] Create `src/print3d_skill/knowledge_base/modify/splitting_strategies.yaml` (type: decision_tree, modes: [modify]): optimal cut plane selection (prefer flat cross-sections, avoid cutting through thin features), minimum wall thickness at boundaries (2x pin diameter), alignment feature type selection (pins for flat cuts, dovetails for shear loads), when to split (model exceeds bed, different materials needed, orientation optimization)

**Checkpoint**: Knowledge system populated — `query_knowledge(mode="modify")` returns all 4 files

---

## Phase 10: Required Tests (Constitution Mandate)

**Purpose**: Integration tests and visual regression tests required by the project constitution (Development Workflow section)

**CRITICAL**: Constitution mandates integration tests for multi-tool workflows and visual regression tests for preview-producing workflows. These are NOT optional.

### Integration Tests

- [x] T034 [P] Integration test: boolean pipeline in `tests/integration/test_modify_pipeline.py` — load STL mesh → auto-repair (F2) → boolean difference with cylinder primitive → analyze result (F2) → render before/after comparison (F1). Verify: output is watertight, volume decreased, preview PNGs produced, analysis report populated
- [x] T035 [P] Integration test: scale + feature detection pipeline in `tests/integration/test_modify_pipeline.py` — load mesh with M3 screw holes → scale uniformly by 150% → verify FeatureWarning generated for screw holes → verify bbox is 150% of original → render comparison. Verify: warnings list non-empty, bbox_after dimensions correct
- [x] T036 [P] Integration test: combine pipeline in `tests/integration/test_modify_pipeline.py` — load two STL meshes → align (center on top) → boolean union → analyze result → render comparison. Verify: single watertight output, no internal faces, correct positioning
- [x] T037 [P] Integration test: split pipeline in `tests/integration/test_modify_pipeline.py` — load mesh → split at Z midpoint → add alignment features → analyze each part → render per-part previews. Verify: two watertight parts, combined volume within 1% of original, alignment features present
- [x] T038 Integration test: operation chaining in `tests/integration/test_modify_pipeline.py` — scale mesh → boolean-subtract hole from scaled output → verify chaining works by feeding output_mesh_paths[0] as next input. Verify: final mesh reflects both operations, original file untouched (FR-039)

### Visual Regression Tests

- [x] T039 [P] Visual regression: comparison output structural validation in `tests/integration/test_modify_comparison.py` — run a boolean operation → verify before_preview_path and after_preview_paths exist, PNGs are non-zero size, both images have matching dimensions (same pixel width/height), at least 3 views rendered per image
- [x] T040 [P] Visual regression: split comparison validation in `tests/integration/test_modify_comparison.py` — run a split operation → verify per-part previews rendered (one per part), overview preview rendered, all PNGs non-zero, view angles deterministic (re-render produces same camera params)

### Contract Tests

- [x] T041 Contract test: `modify_mesh()` public API in `tests/contract/test_modify_api.py` — verify function signature matches contracts/public-api.md: accepts mesh_path/operation/output_path/**params, returns ModifyResult with all documented fields. Verify error contract: FileNotFoundError for missing mesh, ValueError for unknown operation, CapabilityUnavailable for text without OpenSCAD

**Checkpoint**: All constitution-mandated tests pass — integration pipelines verified, visual regression baselines established, API contract validated

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates and validation

- [x] T042 Update `CLAUDE.md`: add `modify/` to project structure, add `modify_mesh()` to public API list (14 functions), update Completed Features section
- [x] T043 [P] Update `README.md`: add Modify mode to status table, add modify examples to quick start section
- [x] T044 [P] Update `docs/vision.md` Status section: mark F4 Model Modification as shipped
- [x] T045 [P] Update `docs/feature-chunking-strategy.md`: update F4 status to complete
- [x] T046 [P] Update `eval/README.md`: add modify-mode evaluation scenarios if eval cases were created during implementation
- [x] T047 Run quickstart.md validation: execute all code examples from `specs/004-model-modification/quickstart.md` against real mesh files to verify API contract

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1 (Boolean) can start immediately after Phase 2
  - US2 (Scale) can start immediately after Phase 2 — independent of US1
  - US3 (Combine) depends on US1 (needs boolean union)
  - US4 (Text) depends on US1 (needs boolean difference/union)
  - US5 (Split) depends on US1 (needs boolean for alignment features)
  - US6 (Visual) depends on Phase 2 foundational comparison module
  - US7 (Knowledge) can start immediately after Phase 1 — no code dependencies
- **Required Tests (Phase 10)**: Each test can run after its corresponding user story completes
- **Polish (Phase 11)**: Depends on all desired user stories and tests being complete

### User Story Dependencies

```text
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ──────────────────────────────────────────┐
    │                                                             │
    ├──► US1 (Boolean) ──┬──► US3 (Combine)                      │
    │         │          ├──► US4 (Text)                          │
    │         │          └──► US5 (Split)                         │
    │         │                                                   │
    │         └──► Integration tests (T034-T038) ◄── after US1+   │
    │                                                             │
    ├──► US2 (Scale) ◄── can run in parallel with US1             │
    │                                                             │
    ├──► US6 (Visual enhancements) ◄── can start after Phase 2   │
    │                                                             │
    └──► US7 (Knowledge) ◄── can start after Phase 1 ────────────┘
```

### Within Each User Story

- Models and shared infrastructure before operation logic
- Operation logic before dispatch wiring
- Dispatch wiring before checkpoint validation
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003 can run in parallel (Phase 1)
- T004, T007 can run in parallel (Phase 2)
- T008, T009 can run in parallel (US1 — different files)
- T013, T014 can run in parallel (US2 — different files)
- US1 and US2 can run in parallel after Phase 2
- US7 (Knowledge) can run in parallel with everything after Phase 1
- T030, T031, T032, T033 can all run in parallel (US7 — independent YAML files)
- T034, T035, T036, T037 can all run in parallel (integration tests — independent test functions)
- T039, T040 can run in parallel (visual regression tests)
- T043, T044, T045, T046 can run in parallel (Polish — different doc files)

---

## Parallel Example: User Story 1

```bash
# Launch parallelizable US1 tasks together:
Task: "Implement primitive shape generation in src/print3d_skill/modify/primitives.py"
Task: "Implement manifold3d boolean wrapper in src/print3d_skill/modify/boolean.py"

# Then sequentially (depend on above):
Task: "Add auto-repair integration to boolean.py"
Task: "Add empty geometry detection to boolean.py"
Task: "Wire boolean operations into modify dispatch"
```

## Parallel Example: Integration Tests

```bash
# After US1 completes, launch all integration tests in parallel:
Task: "Integration test: boolean pipeline in tests/integration/test_modify_pipeline.py"
Task: "Integration test: scale + feature detection pipeline"
Task: "Integration test: combine pipeline"
Task: "Integration test: split pipeline"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: User Story 1 — Boolean Operations (T008-T012)
4. Run integration test T034 (boolean pipeline)
5. **STOP and VALIDATE**: Test boolean union/difference/intersection with primitives
6. The system can now cut holes, merge meshes, and intersect volumes

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Boolean) + boolean integration test → MVP: cut holes, merge meshes
3. Add US2 (Scale) + scale integration test → Can resize models with feature warnings
4. Add US3 (Combine) + combine integration test → Can align and merge multiple files
5. Add US4 (Text) → Can engrave/emboss text (requires OpenSCAD)
6. Add US5 (Split) + split integration test → Can split for multi-part printing
7. Add US6 (Visual) + visual regression tests → Enhanced comparison views
8. Add US7 (Knowledge) → Agent gets domain expertise
9. Run chaining + contract tests → Full pipeline validated
10. Polish → Documentation complete

### Critical Path

Setup → Foundational → US1 (Boolean) → US3/US4/US5 → Integration Tests → Polish

US2 (Scale) and US7 (Knowledge) are off the critical path and can be interleaved.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Text engraving (US4) is the only extended-tier operation — skip if OpenSCAD not available
- US7 (Knowledge) has zero code dependencies — can be done at any time
- Integration tests (Phase 10) are constitution-mandated, not optional
- Run each story's integration test immediately after that story completes
