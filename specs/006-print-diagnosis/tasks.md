# Tasks: Print Failure Diagnosis

**Input**: Design documents from `/specs/006-print-diagnosis/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested — test tasks omitted. Tests should be written during implementation as needed.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create diagnosis package structure and extend knowledge schema

- [X] T001 Create src/print3d_skill/diagnosis/ package directory with empty __init__.py, engine.py, models.py files
- [X] T002 [P] Add DiagnosisError exception class to src/print3d_skill/exceptions.py (subclass of Print3DSkillError)
- [X] T003 [P] Add "defect_guide" and "calibration_procedure" to VALID_KNOWLEDGE_TYPES tuple in src/print3d_skill/models/knowledge.py

**Checkpoint**: Package structure exists, knowledge schema extended

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create all diagnosis dataclasses and enums in src/print3d_skill/diagnosis/models.py: PrintDefectCategory enum (12 values), PrintDefectSeverity enum (cosmetic/functional/print_stopping), PrintDefect, DiagnosticContext, RootCause, Recommendation, DiagnosisResult dataclasses per data-model.md
- [X] T005 Create src/print3d_skill/knowledge_base/diagnose/ directory for diagnosis knowledge YAML files

**Checkpoint**: Foundation ready — all models defined, knowledge directory exists

---

## Phase 3: User Story 1 — Photo-Based Defect Identification (Priority: P1) MVP

**Goal**: Agent can use defect guides to identify defects from photos, and the skill enriches defects with severity from the knowledge base

**Independent Test**: Call diagnose_print() with a list of PrintDefect objects (no context), verify severity is populated from knowledge base and DiagnosisResult returned with correct defects and context_quality="minimal"

- [X] T006 [US1] Create defect_guides.yaml in src/print3d_skill/knowledge_base/diagnose/defect_guides.yaml with all 12 defect categories: each category has severity (cosmetic/functional/print_stopping), visual_indicators (list of observable symptoms the agent should look for in photos), common_causes (summary list), and spatial_patterns (localized vs. global descriptions). Use metadata type="defect_guide", modes=["diagnose"]
- [X] T007 [US1] Implement DiagnosisEngine class in src/print3d_skill/diagnosis/engine.py with load_defect_guides() method (queries knowledge system for defect_guide type) and enrich_defects() method (populates PrintDefect.severity from knowledge base by category lookup, sets context_quality based on DiagnosticContext completeness)
- [X] T008 [US1] Create diagnose_print() public API function in src/print3d_skill/diagnosis/__init__.py: accepts list[PrintDefect] and optional DiagnosticContext, creates DiagnosisEngine, calls enrich_defects(), returns DiagnosisResult with populated defects and context_quality (root_causes and recommendations empty at this stage)
- [X] T009 [US1] Implement DiagnoseHandler.handle() in src/print3d_skill/modes/diagnose.py: parse defects from context kwargs (list of dicts → PrintDefect objects), build DiagnosticContext from printer/material/slicer_settings kwargs, call diagnose_print(), serialize DiagnosisResult to ModeResponse data dict

**Checkpoint**: US1 complete — defect guides exist, severity enrichment works, ModeHandler routes correctly

---

## Phase 4: User Story 2 — Contextual Root Cause Analysis (Priority: P2)

**Goal**: For each identified defect, walk decision trees using diagnostic context to determine ranked root causes

**Independent Test**: Call diagnose_print() with defects + DiagnosticContext (printer, material), verify root_causes are populated with ranked causes reflecting the context (e.g., PETG + direct drive → retraction-related causes ranked highest for stringing)

### Knowledge Files (parallelizable — independent files)

- [X] T010 [P] [US2] Create decision_trees_extrusion.yaml in src/print3d_skill/knowledge_base/diagnose/ covering stringing/oozing, under-extrusion, and over-extrusion decision trees. Each tree has nested condition/branches/causes structure branching on material_type, extruder_type, printer_characteristics. Use metadata type="decision_tree", modes=["diagnose"]
- [X] T011 [P] [US2] Create decision_trees_adhesion.yaml in src/print3d_skill/knowledge_base/diagnose/ covering bed adhesion failure, warping/curling, and elephant foot decision trees with condition branches for material, bed_surface, enclosure, first_layer_settings
- [X] T012 [P] [US2] Create decision_trees_layers.yaml in src/print3d_skill/knowledge_base/diagnose/ covering layer shifts and layer separation/delamination decision trees with condition branches for mechanical (belt tension, frame rigidity) and thermal (temperature, cooling) factors
- [X] T013 [P] [US2] Create decision_trees_surface.yaml in src/print3d_skill/knowledge_base/diagnose/ covering zits/blobs, ghosting/ringing, and support scarring decision trees with condition branches for speed, acceleration, seam settings, support interface
- [X] T014 [P] [US2] Create decision_trees_bridging.yaml in src/print3d_skill/knowledge_base/diagnose/ covering poor bridging decision tree with condition branches for speed, cooling, temperature, span distance

### Engine Implementation

- [X] T015 [US2] Implement walk_decision_tree() method in src/print3d_skill/diagnosis/engine.py: loads decision trees from knowledge system (type="decision_tree", mode="diagnose"), selects tree matching defect category, walks tree by matching DiagnosticContext fields to branch conditions, collects RootCause objects with likelihood rankings. Handle missing context gracefully (return general causes when context fields are None)
- [X] T016 [US2] Integrate tree walking into diagnose_print() in src/print3d_skill/diagnosis/__init__.py: after enriching defects, call walk_decision_tree() for each defect, populate DiagnosisResult.root_causes sorted by defect severity then cause likelihood

**Checkpoint**: US2 complete — decision trees exist for all 12 defect categories, tree walking produces ranked root causes

---

## Phase 5: User Story 3 — Actionable Fix Recommendations (Priority: P3)

**Goal**: Generate specific numeric fix recommendations ordered by severity/impact/ease, with conflict detection

**Independent Test**: Call diagnose_print() with defects + context, verify recommendations contain specific numeric values (not generic advice), are sorted by severity→impact→ease, distinguish controllable vs. environmental, and conflicts are flagged when present

### Knowledge Files (parallelizable)

- [X] T017 [P] [US3] Create material_failure_modes.yaml in src/print3d_skill/knowledge_base/diagnose/ covering PLA, PETG, ABS, TPU, ASA: each material has common_failures (defect categories ranked by frequency), temperature_sensitivity, humidity_sensitivity, recommended_settings per defect type with specific numeric values (retraction, speed, temperature). Use metadata type="material_properties", modes=["diagnose"]
- [X] T018 [P] [US3] Create printer_troubleshooting.yaml in src/print3d_skill/knowledge_base/diagnose/ covering Bambu Lab (P1S/X1C/A1), Prusa (MK3S/MK4/Mini), Creality (Ender 3/K1) printer families: each has extruder_type, known_quirks, recommended_settings_overrides per defect type, community_tips. Use metadata type="printer_capabilities", modes=["diagnose"]

### Engine Implementation

- [X] T019 [US3] Implement generate_recommendations() method in src/print3d_skill/diagnosis/engine.py: for each RootCause, load material failure modes and printer troubleshooting knowledge, generate Recommendation objects with specific suggested_value, impact, difficulty, and category (controllable/environmental). Fall back to extruder-type/material defaults when printer model not in knowledge base (FR-016)
- [X] T020 [US3] Implement sort_recommendations() and detect_conflicts() methods in src/print3d_skill/diagnosis/engine.py: sort by defect severity (print_stopping first) → impact (high first) → difficulty (easy first) per FR-008. Detect conflicting recommendations (e.g., "increase squish" + "decrease squish") and populate DiagnosisResult.conflicts list per FR-015
- [X] T021 [US3] Complete diagnose_print() full pipeline in src/print3d_skill/diagnosis/__init__.py: enrich defects → walk decision trees → generate recommendations → sort and detect conflicts → return complete DiagnosisResult
- [X] T022 [US3] Update DiagnoseHandler.handle() in src/print3d_skill/modes/diagnose.py to pass full context (slicer_settings, geometry_info) through to diagnose_print() and serialize complete DiagnosisResult including recommendations and conflicts in ModeResponse data

**Checkpoint**: US3 complete — full diagnosis pipeline works end-to-end with specific numeric recommendations

---

## Phase 6: User Story 4 — Diagnostic Knowledge Base (Priority: P4)

**Goal**: Comprehensive knowledge coverage across printers, materials, and defect types

**Independent Test**: Query knowledge system with mode="diagnose" and various filters (problem_type, material, printer), verify structured data returned for each defect category, all 3 printer families, all 5 materials, and calibration procedures

- [X] T023 [US4] Create calibration_procedures.yaml in src/print3d_skill/knowledge_base/diagnose/ covering flow rate calibration, e-steps calibration, PID tuning (hotend and bed), bed leveling/tramming, retraction tower test, temperature tower test: each procedure has steps (ordered list), printer_type_variants, verification_criteria, when_to_run (which defects suggest this calibration). Use metadata type="calibration_procedure", modes=["diagnose"]
- [X] T024 [P] [US4] Expand defect_guides.yaml in src/print3d_skill/knowledge_base/diagnose/defect_guides.yaml: add detailed spatial_pattern descriptions (e.g., "warping at corners only" vs. "entire first layer"), photo_cues for agent photo analysis (what to look for in specific regions of the print), severity_modifiers (when context changes the default severity), and related_defects (defects that commonly co-occur)
- [X] T025 [P] [US4] Expand printer_troubleshooting.yaml in src/print3d_skill/knowledge_base/diagnose/printer_troubleshooting.yaml: add community tribal knowledge per printer family — Bambu (firmware update impacts, AMS quirks, fan control notes), Prusa (Live-Z tuning, SuperPINDA behavior, input shaper), Creality (common mods that affect diagnosis, Klipper vs. Marlin differences, dual-Z alignment)
- [X] T026 [P] [US4] Expand material_failure_modes.yaml in src/print3d_skill/knowledge_base/diagnose/material_failure_modes.yaml: add environmental_factors per material (humidity thresholds, ambient temperature ranges, storage requirements), drying_procedures, and cross-material_interactions (e.g., printing PETG after PLA without purging)

**Checkpoint**: US4 complete — comprehensive knowledge base covers all 12 defects, 3 printer families, 5 materials, and calibration procedures

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Public API surface, documentation updates, validation

- [X] T027 Add diagnose_print import and export in src/print3d_skill/__init__.py: import from print3d_skill.diagnosis, add to __all__ list
- [X] T028 [P] Update CLAUDE.md: add diagnosis/ to project structure, update public API count to 19, add F6 to completed features, update test count after running suite
- [X] T029 [P] Update README.md: mark F6 complete in roadmap, add diagnosis example to Quick Start, update architecture with diagnosis package
- [X] T030 [P] Update docs/vision.md: add F6 completion status paragraph in Status section
- [X] T031 [P] Update docs/feature-chunking-strategy.md: change F6 from planned to complete
- [X] T032 Run quickstart.md validation scenarios programmatically: execute all 5 quickstart scenarios, verify assertions pass, fix any issues

**Checkpoint**: Feature complete — public API updated, docs current, quickstart validated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational
- **US2 (Phase 4)**: Depends on US1 (needs defect enrichment before tree walking)
- **US3 (Phase 5)**: Depends on US2 (needs root causes before recommendations)
- **US4 (Phase 6)**: Depends on US1 (needs base knowledge files to expand). Can run in parallel with US2/US3 for knowledge file creation.
- **Polish (Phase 7)**: Depends on US3 completion (needs full pipeline for public API)

### User Story Dependencies

- **User Story 1 (P1)**: Foundational → US1 (MVP — defect identification and severity enrichment)
- **User Story 2 (P2)**: US1 → US2 (decision tree walking requires enriched defects as input)
- **User Story 3 (P3)**: US2 → US3 (recommendations require root causes as input)
- **User Story 4 (P4)**: US1 → US4 (knowledge expansion requires base files; parallelizable with US2/US3 for YAML-only tasks)

### Within Each User Story

- Knowledge YAML files before engine implementation
- Engine methods before public API integration
- Public API before ModeHandler updates

### Parallel Opportunities

- T002/T003 in Setup: different files, independent
- T010–T014 in US2: five decision tree YAML files, all independent
- T017/T018 in US3: two knowledge YAML files, independent
- T024–T026 in US4: three knowledge expansions, independent files
- T028–T031 in Polish: four doc updates, different files

---

## Parallel Example: User Story 2

```bash
# Launch all 5 decision tree YAML files together:
Task: "Create decision_trees_extrusion.yaml in src/print3d_skill/knowledge_base/diagnose/"
Task: "Create decision_trees_adhesion.yaml in src/print3d_skill/knowledge_base/diagnose/"
Task: "Create decision_trees_layers.yaml in src/print3d_skill/knowledge_base/diagnose/"
Task: "Create decision_trees_surface.yaml in src/print3d_skill/knowledge_base/diagnose/"
Task: "Create decision_trees_bridging.yaml in src/print3d_skill/knowledge_base/diagnose/"

# Then sequentially:
Task: "Implement walk_decision_tree() in engine.py"
Task: "Integrate tree walking into diagnose_print()"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (3 tasks)
2. Complete Phase 2: Foundational (2 tasks)
3. Complete Phase 3: User Story 1 (4 tasks)
4. **STOP and VALIDATE**: diagnose_print() accepts defects, enriches with severity, returns result
5. The agent can now use defect guides for photo analysis and get structured defect data back

### Incremental Delivery

1. Setup + Foundational → Package structure ready
2. Add US1 → Defect identification MVP (9 total tasks)
3. Add US2 → Root cause analysis (16 total tasks)
4. Add US3 → Full recommendations (22 total tasks)
5. Add US4 → Comprehensive knowledge (26 total tasks)
6. Polish → Documentation and validation (32 total tasks)

Each story adds capability without breaking previous stories.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1→US2→US3 is a pipeline: each story adds a stage
- US4 knowledge expansion can partially parallelize with US2/US3 (YAML files only)
- Knowledge YAML files are the most parallelizable work in this feature
- No new pip dependencies — all core tier
