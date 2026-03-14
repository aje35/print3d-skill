# Tasks: Core Infrastructure

**Input**: Design documents from `/specs/001-core-infrastructure/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md, research.md, quickstart.md

**Tests**: Integration tests included per constitution requirement (workflows spanning multiple tools). No TDD approach — tests follow implementation.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/print3d_skill/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, package structure, build config

- [x] T001 Create full directory structure per plan.md — all directories and empty `__init__.py` files under `src/print3d_skill/` (rendering/, tools/, knowledge/, knowledge_base/, modes/, models/) and `tests/` (unit/, integration/, contract/, fixtures/)
- [x] T002 [P] Create `pyproject.toml` with PEP 621 metadata, setuptools build backend, all 6 core dependencies (trimesh>=4.0, manifold3d>=3.0, numpy>=1.24, matplotlib>=3.7, Pillow>=10.0, PyYAML>=6.0), optional extras (openscad, slicer, dev), package-data for knowledge_base/*.yaml, ruff config, and pytest config per research.md Decision 3
- [x] T003 [P] Create `tests/conftest.py` with shared pytest fixtures — programmatically generate test meshes via trimesh (cube STL, simple OBJ, colored 3MF, corrupt/truncated STL, high-poly sphere >1M faces for timeout tests). Create `tests/fixtures/sample.scad` with a simple OpenSCAD cube module

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared types that all user stories import

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement exception hierarchy in `src/print3d_skill/exceptions.py` — Print3DSkillError base, MeshLoadError, UnsupportedFormatError, RenderTimeoutError, ScadCompileError, CapabilityUnavailable, InvalidModeError, KnowledgeSchemaError per contracts/api.md
- [x] T005 [P] Create `src/print3d_skill/__init__.py` with `__version__ = "0.1.0"` and docstring. Public API re-exports will be added incrementally as each user story completes

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Render Mesh Preview (Priority: P1) MVP

**Goal**: Pass any STL/3MF/OBJ mesh file and get back a 1600x1200 multi-angle PNG preview, headless, no GPU

**Independent Test**: `render_preview("cube.stl", "out.png")` produces a valid PNG with 4 views, file size <1MB, completes in <10s

### Implementation for User Story 1

- [x] T006 [P] [US1] Create MeshFile and BoundingBox dataclasses in `src/print3d_skill/models/mesh.py` — fields per data-model.md (path, format, vertices, faces, face_count, vertex_count, bounding_box, detected_units, unit_warning, file_size_bytes)
- [x] T007 [P] [US1] Create PreviewResult and ViewAngle dataclasses in `src/print3d_skill/models/preview.py` — fields per data-model.md (image_path, resolution, file_size_bytes, views, warnings, render_time_seconds, timed_out). Define 4 standard ViewAngle constants (front=0/0, side=0/90, top=90/0, iso=35/45)
- [x] T008 [US1] Implement mesh loading with format detection and unit heuristic in `src/print3d_skill/rendering/renderer.py` — load STL/3MF/OBJ via trimesh, extract vertices/faces/normals, compute bounding box, detect units per research.md Decision 5 (max_dim <0.5 → meters, >2000 → warn, check for inch scaling). Return MeshFile. Raise MeshLoadError for corrupt files, UnsupportedFormatError for unknown formats
- [x] T009 [US1] Implement single-view rendering function in `src/print3d_skill/rendering/renderer.py` — accept MeshFile + ViewAngle, create matplotlib figure, build Poly3DCollection from faces with face-normal-based diffuse coloring, set camera elevation/azimuth, return matplotlib Axes. Use Agg backend for headless rendering per research.md Decision 1
- [x] T010 [US1] Implement 2x2 grid compositor in `src/print3d_skill/rendering/compositor.py` — accept MeshFile, render all 4 standard views into a 2x2 subplot grid at 1600x1200, save as PNG, verify file size <1MB (adjust compression if needed). Return PreviewResult with render timing and warnings
- [x] T011 [US1] Implement `render_preview()` public API in `src/print3d_skill/rendering/__init__.py` — orchestrate load → render → composite. Handle .scad files: check for OpenSCAD via `shutil.which("openscad")`, compile .scad→STL via subprocess, raise CapabilityUnavailable if missing or ScadCompileError on syntax errors. Implement configurable timeout (default 30s) for large meshes per FR-007a. Collect warnings (unit mismatch, high face count >1M). Match signature from contracts/api.md
- [x] T012 [US1] Export `render_preview` in `src/print3d_skill/__init__.py`
- [x] T013 [US1] Integration test in `tests/integration/test_render_pipeline.py` — test STL→PNG end-to-end (verify valid PNG, 1600x1200, <1MB), test 3MF rendering, test OBJ rendering, test corrupt file raises MeshLoadError, test unit warning for tiny mesh, test .scad renders if OpenSCAD available (skip if not), test .scad without OpenSCAD raises CapabilityUnavailable

**Checkpoint**: User Story 1 fully functional — `pip install -e .` then `render_preview()` works

---

## Phase 4: User Story 2 — Discover and Use Tools (Priority: P2)

**Goal**: Request capabilities by name, get tool wrappers. Missing tools report clear install instructions. Core capabilities always available.

**Independent Test**: `list_capabilities()` returns all 6 capabilities with correct availability status. `get_capability("mesh_loading")` returns a provider. `get_capability("cad_compilation")` raises CapabilityUnavailable when OpenSCAD is not installed.

### Implementation for User Story 2

- [x] T014 [P] [US2] Create ToolCapability and ToolProvider status dataclasses in `src/print3d_skill/models/capability.py` — fields per data-model.md (name, description, tier, provider_name, is_available, install_instructions for capability; name, capabilities, tier, is_available, version, detection_method, install_instructions for provider)
- [x] T015 [US2] Implement ToolProvider abstract base class in `src/print3d_skill/tools/base.py` — abstract `detect() -> bool`, `get_capabilities() -> list[str]`, `get_version() -> str|None`. Concrete `is_available` property with lazy detection (detect on first access, cache result). Include tier and install_instructions attributes
- [x] T016 [US2] Implement ToolRegistry in `src/print3d_skill/tools/registry.py` — singleton holding registered providers. Methods: `register(provider)`, `get(capability_name) -> ToolProvider` (raises CapabilityUnavailable), `list_all() -> list[ToolCapability]`, `refresh()` (re-detect all). Lazy detection on first query per research.md Decision 4. Build capability→provider mapping from registered providers
- [x] T017 [P] [US2] Implement TrimeshProvider in `src/print3d_skill/tools/trimesh_tools.py` — provides ["mesh_loading", "mesh_analysis"]. Detection: `import trimesh`. Core tier. Install: `pip install trimesh`
- [x] T018 [P] [US2] Implement ManifoldProvider in `src/print3d_skill/tools/manifold_tools.py` — provides ["boolean_operations"]. Detection: `import manifold3d`. Core tier. Install: `pip install manifold3d`
- [x] T019 [P] [US2] Implement OpenSCADProvider in `src/print3d_skill/tools/openscad.py` — provides ["cad_compilation", "cad_rendering"]. Detection: `shutil.which("openscad")`. Extended tier. Install instructions per platform (brew/apt/choco)
- [x] T020 [US2] Wire up providers, implement `get_capability()`, `list_capabilities()`, `refresh_capabilities()` in `src/print3d_skill/tools/__init__.py` — instantiate default registry, register all 3 providers, expose public functions per contracts/api.md
- [x] T021 [US2] Export `get_capability`, `list_capabilities`, `refresh_capabilities` in `src/print3d_skill/__init__.py`
- [x] T022 [US2] Integration test in `tests/integration/test_tool_discovery.py` — test list returns all 6 capabilities, test core capabilities always available, test get_capability("mesh_loading") succeeds, test get_capability for unavailable tool raises CapabilityUnavailable with install instructions, test refresh re-detects

**Checkpoint**: User Stories 1 AND 2 both work independently

---

## Phase 5: User Story 3 — Query Domain Knowledge (Priority: P3)

**Goal**: Query knowledge base with context filters (mode, material, printer, problem_type). AND matching with wildcards. Returns only relevant subset.

**Independent Test**: `query_knowledge(mode="create", material="PLA")` returns only files tagged for both create mode AND PLA material. `query_knowledge(mode="fix")` returns all fix-mode files regardless of material (wildcard).

### Implementation for User Story 3

- [x] T023 [P] [US3] Create KnowledgeFile, KnowledgeMetadata, KnowledgeQuery dataclasses in `src/print3d_skill/models/knowledge.py` — fields per data-model.md. KnowledgeMetadata includes type enum validation (tolerance_table, material_properties, decision_tree, design_rules)
- [x] T024 [US3] Implement schema validation in `src/print3d_skill/knowledge/schemas.py` — validate YAML structure (must have metadata and data top-level keys), validate metadata fields (type in allowed enum, modes/materials/printers are lists, version is string). Raise KnowledgeSchemaError on invalid files
- [x] T025 [US3] Implement knowledge loader with AND query matching in `src/print3d_skill/knowledge/loader.py` — discover YAML files in knowledge_base/ via importlib.resources, parse metadata section, filter by KnowledgeQuery using AND logic (all specified fields must match, unspecified=wildcard, empty metadata list=matches all), return list of KnowledgeFile with data loaded on-demand per FR-015
- [x] T026 [P] [US3] Create 4 seed knowledge YAML files in `src/print3d_skill/knowledge_base/` — (1) `seed_tolerance_table.yaml`: type=tolerance_table, modes=[create,modify], materials=[PLA,PETG,ABS], sample press-fit clearances. (2) `seed_material_properties.yaml`: type=material_properties, modes=[], materials=[PLA], sample temp/speed ranges. (3) `seed_decision_tree.yaml`: type=decision_tree, modes=[fix], materials=[], sample non-manifold diagnosis flow. (4) `seed_design_rules.yaml`: type=design_rules, modes=[create], materials=[], sample min wall thickness rules
- [x] T027 [US3] Implement `query_knowledge()` public API in `src/print3d_skill/knowledge/__init__.py` — instantiate loader, delegate query, match signature from contracts/api.md
- [x] T028 [US3] Export `query_knowledge` in `src/print3d_skill/__init__.py`
- [x] T029 [US3] Integration test in `tests/integration/test_knowledge_query.py` — test mode-only query returns matching files, test material-only query, test multi-field AND query (mode+material), test wildcard behavior (unspecified fields), test empty result returns empty list not error, test schema validation rejects malformed YAML

**Checkpoint**: All three subsystems (rendering, tools, knowledge) work independently

---

## Phase 6: User Story 4 — Route User Intent to Mode (Priority: P4)

**Goal**: Accept mode identifier, dispatch to correct handler stub. 5 valid modes, stubs return "not_implemented". system_info() reports full capability summary.

**Independent Test**: `route("fix")` returns ModeResponse with status="not_implemented" and mode="fix". `route("invalid")` raises InvalidModeError listing valid modes. `system_info()` returns complete capability inventory.

### Implementation for User Story 4

- [x] T030 [P] [US4] Create WorkflowMode enum, ModeResponse dataclass, and SystemInfo dataclass in `src/print3d_skill/models/mode.py` — WorkflowMode with 5 values (create, fix, modify, diagnose, validate), ModeResponse with mode/status/message/data fields, SystemInfo with package_version/python_version/capabilities/core_available/extended fields per data-model.md
- [x] T031 [US4] Implement ModeHandler base class with stub response in `src/print3d_skill/modes/base.py` — abstract `handle(**context) -> ModeResponse`, default stub implementation returning status="not_implemented"
- [x] T032 [P] [US4] Implement 5 stub mode handlers in `src/print3d_skill/modes/create.py`, `fix.py`, `modify.py`, `diagnose.py`, `validate.py` — each extends ModeHandler, returns stub response with mode name
- [x] T033 [US4] Implement skill router in `src/print3d_skill/router.py` — validate mode string against WorkflowMode enum, look up handler, dispatch, raise InvalidModeError for unknown modes with list of valid options per contracts/api.md
- [x] T034 [US4] Implement `system_info()` in `src/print3d_skill/tools/__init__.py` — aggregate package version, Python version, all capabilities from registry, compute core_available/extended_available/missing_extended
- [x] T035 [US4] Export `route` and `system_info` in `src/print3d_skill/__init__.py`. Verify all 7 public functions are exported: render_preview, get_capability, list_capabilities, refresh_capabilities, query_knowledge, route, system_info
- [x] T036 [US4] Unit test in `tests/unit/test_router.py` — test all 5 valid modes dispatch correctly, test stub responses include mode name and not_implemented status, test invalid mode raises InvalidModeError, test system_info returns valid SystemInfo with core_available=True

**Checkpoint**: All four user stories independently functional. Full public API available.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: API stability verification, end-to-end validation

- [x] T037 [P] Contract test in `tests/contract/test_public_api.py` — verify all 7 public functions exist with correct signatures (parameter names, types, defaults) per contracts/api.md. Verify all 7 exception classes exist. Verify all dataclass return types are importable.
- [x] T038 Validate quickstart.md examples — run each code snippet from quickstart.md in sequence, verify no errors for core features (skip OpenSCAD example if not installed)
- [x] T039 Verify clean install — create temporary virtual environment, `pip install .`, import print3d_skill, call `system_info()`, call `render_preview()` with generated cube mesh, confirm all core capabilities available

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001 for directory structure)
- **User Story 1 (Phase 3)**: Depends on Phase 2 — **MVP target**
- **User Story 2 (Phase 4)**: Depends on Phase 2 — independent of US1
- **User Story 3 (Phase 5)**: Depends on Phase 2 — independent of US1, US2
- **User Story 4 (Phase 6)**: Depends on Phase 2 — independent of US1-US3 (uses tools/__init__.py from US2 for system_info, but only the registry which is self-contained)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories. Self-contained rendering pipeline.
- **US2 (P2)**: No dependencies on other stories. Self-contained tool registry.
- **US3 (P3)**: No dependencies on other stories. Self-contained knowledge system.
- **US4 (P4)**: T034 (system_info) depends on US2's registry being available. All other US4 tasks are independent. If implementing in parallel, T034 can be deferred until US2 completes.

### Within Each User Story

- Models before services (dataclasses → business logic)
- Business logic before public API (renderer → render_preview)
- Public API before exports (render_preview → __init__.py)
- Exports before tests (working API → integration test)
- Tasks marked [P] within a story can run in parallel

### Parallel Opportunities

- Phase 1: T002, T003 can run in parallel (after T001)
- Phase 2: T004, T005 can run in parallel
- US1: T006, T007 in parallel → then T008 → T009 → T010 → T011 → T012 → T013
- US2: T014 parallel with T015 → T016 → T017-T019 in parallel → T020 → T021 → T022
- US3: T023, T026 in parallel → T024 → T025 → T027 → T028 → T029
- US4: T030, T032 in parallel → T031 → T033 → T034 → T035 → T036
- **Cross-story**: US1, US2, US3 can run fully in parallel after Phase 2
- Phase 7: T037 in parallel with T038

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `pip install -e .` → `render_preview("cube.stl", "out.png")` → valid PNG

### Incremental Delivery

1. Setup + Foundational → package installable
2. User Story 1 → rendering works (MVP)
3. User Story 2 → tool discovery works
4. User Story 3 → knowledge queries work
5. User Story 4 → router + system_info complete the infrastructure
6. Polish → API contract stable, quickstart validated

### Sequential Implementation (single developer)

1. Phase 1 + 2 → foundation
2. Phase 3 (US1) → rendering MVP
3. Phase 4 (US2) → tools
4. Phase 5 (US3) → knowledge
5. Phase 6 (US4) → router
6. Phase 7 → polish

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- The rendering pipeline (US1) loads meshes directly via trimesh — it does NOT go through the tool registry (US2). This keeps US1 independent.
- system_info() (US4/T034) uses the tool registry from US2. If building US4 before US2, stub the capability list.
- Seed knowledge files (US3/T026) are deliberately varied in metadata so integration tests can verify AND filtering.
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
