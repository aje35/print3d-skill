# Tasks: G-code Validation & Slicing

**Input**: Design documents from `/specs/005-gcode-validation-slicing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/public-api.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package directories, new error types, and test fixture files

- [X] T001 Create validate/, slicing/, and printing/ package directories with __init__.py stubs under src/print3d_skill/
- [X] T002 Add GcodeParseError, SlicerError, ValidationError, and PrinterError to src/print3d_skill/exceptions.py (all inherit from Print3DSkillError)
- [X] T003 [P] Create sample G-code test fixture files in tests/fixtures/gcode/ — minimal files for PrusaSlicer, Bambu Studio, OrcaSlicer, Cura (each with slicer-identifying header comments, temperature commands, speed settings, retraction, fan control, layer changes, and metadata comments for print time and filament usage), plus empty.gcode and no_comments.gcode

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models and test infrastructure that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create src/print3d_skill/models/validate.py with all enums (ValidationStatus, CheckSeverity, CheckCategory, ExtruderType, PrinterConnectionType, PrinterStatus, SlicerType) and all dataclasses (TemperatureCommand, FanCommand, PrintDimensions, GcodeAnalysis, ValidationCheck, ValidationResult, MaterialProfile, PrinterProfile, SliceRequest, SliceResult, PrinterConnection, PrinterInfo, PrintJob) per data-model.md — use dataclasses with field() defaults, from __future__ import annotations
- [X] T005 Add validate-specific pytest fixtures to tests/conftest.py — minimal_gcode_path (writes a small valid G-code string to tmp_path), prusaslicer_gcode_path, bambustudio_gcode_path, orcaslicer_gcode_path, cura_gcode_path, pla_material_profile (MaterialProfile dataclass instance), ender3_printer_profile (PrinterProfile dataclass instance with bowden extruder, 220x220x250mm build volume)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — G-code Parsing & Analysis (Priority: P1) MVP

**Goal**: Parse G-code files from PrusaSlicer, Bambu Studio, OrcaSlicer, and Cura into a structured GcodeAnalysis report

**Independent Test**: Provide sample G-code files and verify extracted parameters (temperatures, speeds, retraction, layer height, time, filament) match expected values

### Implementation for User Story 1

- [X] T006 [P] [US1] Implement slicer auto-detection in src/print3d_skill/validate/slicer_detect.py — detect_slicer(lines) function that identifies PrusaSlicer, Bambu Studio, OrcaSlicer, Cura, or Unknown from header comment patterns (first 100 lines). Pre-compiled regex patterns for each slicer's signature comment.
- [X] T007 [P] [US1] Implement parameter extractors in src/print3d_skill/validate/extractors.py — pre-compiled regex patterns and extraction functions: extract_temperatures(line) for M104/M109/M140/M190, extract_speed(line) for G0/G1 F parameters, extract_retraction(line) for G10/G11 and G1 E moves, extract_fan(line) for M106/M107, extract_metadata(line) for slicer-specific comment patterns (print time, filament usage, layer height). Each function returns typed result or None.
- [X] T008 [US1] Implement streaming G-code parser in src/print3d_skill/validate/parser.py — parse_gcode_file(path) function that opens the file, iterates line-by-line, calls extractors, tracks state (current layer number, current Z height), and builds a GcodeAnalysis dataclass. Handle encoding errors with errors='replace'. Raise GcodeParseError for empty/unreadable files.
- [X] T009 [US1] Create public API in src/print3d_skill/validate/__init__.py — parse_gcode(gcode_path) function that validates the file exists and has .gcode extension, delegates to parser.parse_gcode_file(), returns GcodeAnalysis. Raise FileNotFoundError, UnsupportedFormatError, GcodeParseError as documented in contracts/public-api.md.
- [X] T010 [US1] Write integration tests in tests/integration/test_validate_pipeline.py — test parse_gcode() with each slicer fixture (PrusaSlicer, Bambu Studio, OrcaSlicer, Cura): verify slicer detected, temperatures extracted, speeds extracted, retraction extracted, layer height extracted, time/filament estimates present. Test empty file raises GcodeParseError. Test non-.gcode extension raises UnsupportedFormatError.
- [X] T011 [US1] Add parse_gcode to public API in src/print3d_skill/__init__.py — import from print3d_skill.validate, add to __all__

**Checkpoint**: parse_gcode() works end-to-end with all 4 slicer formats

---

## Phase 4: User Story 5 — Knowledge Content for Validation (Priority: P5)

**Goal**: Populate the knowledge system with material profiles, printer profiles, and slicer setting mappings

**Independent Test**: Query the knowledge system for specific materials/printers and verify returned profiles contain correct values

**Note**: Positioned before US2 because validation depends on knowledge profiles for meaningful testing. YAML files have no code dependencies and can be created in parallel with US1 (Phase 3).

### Implementation for User Story 5

- [X] T033 [P] [US5] Create material profile YAML files in src/print3d_skill/knowledge_base/validate/ — material_pla.yaml, material_petg.yaml, material_abs.yaml, material_asa.yaml (metadata: type=material_properties, modes=[validate], materials=[<material>]). Each with data section containing: hotend_temp_min/max/recommended_c, bed_temp_min/max/recommended_c, print_speed_min/max_mm_s, retraction_direct_drive_mm, retraction_bowden_mm, retraction_speed_mm_s, requires_enclosure, requires_heated_bed, fan_speed_percent, notes list.
- [X] T034 [P] [US5] Create material profile YAML files for flexible and specialty materials in src/print3d_skill/knowledge_base/validate/ — material_tpu.yaml, material_nylon.yaml, material_composites.yaml. TPU: slow speeds (20-40mm/s), minimal retraction, notes about bowden difficulties. Nylon: enclosure recommended, high temps, moisture warnings. Composites: hardened nozzle notes, abrasion warnings.
- [X] T035 [P] [US5] Create printer capability profile YAML in src/print3d_skill/knowledge_base/validate/printer_profiles.yaml — metadata: type=printer_capabilities, modes=[validate]. Data section with profiles for common printer categories: generic_direct_drive_enclosed (Bambu X1C class: 256x256x256, 300C hotend, direct drive, enclosed), generic_direct_drive_open (Prusa MK3S class: 250x210x210, 280C, direct drive, open), generic_bowden (Ender 3 class: 220x220x250, 260C, bowden, open). Each with build_volume, max_hotend_temp_c, max_bed_temp_c, extruder_type, has_heated_bed, has_enclosure, notes.
- [X] T036 [US5] Create slicer settings mapping YAML in src/print3d_skill/knowledge_base/validate/slicer_settings_map.yaml — metadata: type=lookup_table, modes=[validate]. Data section mapping slicer comment key names to canonical parameter names across PrusaSlicer, Bambu Studio, OrcaSlicer, and Cura (e.g., PrusaSlicer's "nozzle_temperature" = Cura's ";SETTING_3" = canonical "hotend_temp_c").

**Checkpoint**: query_knowledge(mode="validate", material="PLA") returns complete PLA profile

---

## Phase 5: User Story 2 — Settings Validation Against Profiles (Priority: P2)

**Goal**: Cross-reference parsed G-code parameters against material and printer profiles, producing pass/warn/fail results with fix recommendations

**Independent Test**: Validate G-code with known mismatched settings (e.g., PETG temps with PLA profile) and verify correct warnings with specific recommendations

### Implementation for User Story 2

- [X] T012 [P] [US2] Implement profile loading in src/print3d_skill/validate/profiles.py — load_material_profile(name) and load_printer_profile(name) functions that query the knowledge system via query_knowledge(mode="validate", material=name) and parse the YAML data into MaterialProfile/PrinterProfile dataclasses. Return None if profile not found.
- [X] T013 [P] [US2] Implement validation checks in src/print3d_skill/validate/checks.py — individual check functions: check_hotend_temperature(analysis, material) -> ValidationCheck, check_bed_temperature(analysis, material) -> ValidationCheck, check_print_speed(analysis, material) -> ValidationCheck, check_retraction(analysis, printer) -> ValidationCheck, check_first_layer(analysis, material) -> ValidationCheck, check_build_volume(analysis, printer) -> ValidationCheck, check_print_time(analysis, max_hours=72) -> ValidationCheck, check_enclosure(analysis, material, printer) -> ValidationCheck. Each returns a ValidationCheck with severity, actual/expected values, message, and recommendation.
- [X] T014 [US2] Implement validation engine in src/print3d_skill/validate/validator.py — validate_gcode_settings(analysis, material_profile, printer_profile) function that runs all applicable checks (skip material checks if no material, skip printer checks if no printer), aggregates results into a ValidationResult with overall status (FAIL if any check fails, WARN if any warns, PASS otherwise), summary, warnings list, failures list, and recommendations list.
- [X] T015 [US2] Add validate_gcode() to src/print3d_skill/validate/__init__.py — validate_gcode(gcode_path, material=None, printer=None) function that calls parse_gcode() first, loads profiles via profiles.py, runs validator.validate_gcode_settings(), returns ValidationResult. At least one of material/printer should be specified. If a material or printer name is provided but no matching profile is found, skip those checks and include a warning in the result.
- [X] T016 [US2] Implement ValidateHandler in src/print3d_skill/modes/validate.py — override handle(**context) to extract gcode_path, material, printer from context kwargs, call validate_gcode(), return ModeResponse with status="success" and data={"validation_result": result} or status="error" on failure.
- [X] T017 [US2] Write integration tests in tests/integration/test_validate_pipeline.py (append to existing) — test validate_gcode() with PLA profile on a G-code with correct PLA temps (expect PASS), test with mismatched PETG temps on PLA profile (expect WARN), test with build volume exceeded (expect FAIL), test material-only validation (no printer), test printer-only validation (no material), test with unknown material name (expect graceful skip of material checks with warning in result). Test route("validate", gcode_path=..., material="PLA") returns ModeResponse.
- [X] T018 [US2] Add validate_gcode to public API in src/print3d_skill/__init__.py — import from print3d_skill.validate, add to __all__. Update router test in tests/unit/test_router.py to remove "validate" from stub parametrize and add test_validate_mode_returns_response.

**Checkpoint**: validate_gcode() produces accurate pass/warn/fail results with fix recommendations

---

## Phase 6: User Story 3 — Slicer CLI Integration (Priority: P3)

**Goal**: Wrap PrusaSlicer and OrcaSlicer CLIs to slice STL/3MF models with profile selection and custom overrides

**Independent Test**: Slice a model with a specified profile and verify output G-code exists. Verify graceful degradation when no slicer installed.

### Implementation for User Story 3

- [X] T019 [P] [US3] Implement SlicerBackend ABC in src/print3d_skill/slicing/base.py — abstract base class with methods: slice(model_path, output_path, printer_profile, material_profile, quality_preset, overrides) -> SliceResult, detect() -> bool, get_version() -> str | None, slicer_type property.
- [X] T020 [P] [US3] Implement PrusaSlicer CLI wrapper in src/print3d_skill/slicing/prusaslicer.py — PrusaSlicerBackend(SlicerBackend) that detects prusa-slicer via shutil.which(), invokes --export-gcode with --load for profiles and key=value overrides via temp INI file, parses stderr for errors, returns SliceResult. Handle subprocess timeout (120s default).
- [X] T021 [P] [US3] Implement OrcaSlicer CLI wrapper in src/print3d_skill/slicing/orcaslicer.py — OrcaSlicerBackend(SlicerBackend) that detects orca-slicer via shutil.which(), invokes --export-gcode with --load-settings for JSON profiles and overrides via temp JSON file, parses stderr for errors, returns SliceResult.
- [X] T022 [US3] Create public API in src/print3d_skill/slicing/__init__.py — slice_model(model_path, output_path, slicer, printer_profile, material_profile, quality_preset, **overrides) that auto-detects available slicer, validates model file exists and has .stl/.3mf extension, delegates to appropriate backend, returns SliceResult. Raise CapabilityUnavailable if no slicer installed, FileNotFoundError if model missing, SlicerError on CLI failure.
- [X] T023 [US3] Implement SlicerProvider in src/print3d_skill/tools/slicer_tools.py — ToolProvider subclass that detects PrusaSlicer/OrcaSlicer via shutil.which(), reports capabilities ["gcode_slicing"], tier="extended", provides install instructions. Register in src/print3d_skill/tools/__init__.py.
- [X] T024 [US3] Add slice_model to public API in src/print3d_skill/__init__.py — import from print3d_skill.slicing, add to __all__. Write unit test in tests/unit/test_slicer_cli.py with mocked subprocess: test PrusaSlicer invocation builds correct command, test OrcaSlicer invocation builds correct command, test CapabilityUnavailable when no slicer found, test SlicerError on non-zero exit code.

**Checkpoint**: slice_model() wraps slicer CLIs with profile selection and graceful degradation

---

## Phase 7: User Story 4 — Printer Control (Priority: P4)

**Goal**: Discover printers, check status, and submit validated G-code to OctoPrint, Moonraker, or Bambu Lab printers

**Independent Test**: Connect to a printer (or mock endpoint), enumerate printers, check status, and submit a job. Verify validation enforcement blocks unvalidated G-code.

### Implementation for User Story 4

- [X] T025 [P] [US4] Implement PrinterBackend ABC in src/print3d_skill/printing/base.py — abstract base class with methods: connect() -> bool, status() -> PrinterInfo, upload(gcode_path) -> bool, start_print(filename) -> bool, disconnect() -> None. Property: connection_type.
- [X] T026 [P] [US4] Implement printer config loading in src/print3d_skill/printing/config.py — load_printer_config() that reads YAML from ~/.config/print3d-skill/printers.yaml (XDG) or ~/Library/Application Support/print3d-skill/printers.yaml (macOS), parses into list[PrinterConnection]. Return empty list if config file doesn't exist. Never log credentials.
- [X] T027 [P] [US4] Implement OctoPrint backend in src/print3d_skill/printing/octoprint.py — OctoPrintBackend(PrinterBackend) using requests library: connect with X-Api-Key header, status via GET /api/printer, upload via POST /api/files/local (multipart), start_print via POST /api/files/local/<filename> with {"command":"select","print":true}. Handle connection timeouts (10s), HTTP errors.
- [X] T028 [P] [US4] Implement Moonraker backend in src/print3d_skill/printing/moonraker.py — MoonrakerBackend(PrinterBackend) using requests library: status via GET /printer/objects/query, upload via POST /server/files/upload (multipart), start_print via POST /printer/print/start?filename=<name>. Handle connection timeouts (10s), HTTP errors.
- [X] T029 [P] [US4] Implement Bambu Lab backend in src/print3d_skill/printing/bambu.py — BambuBackend(PrinterBackend) using paho-mqtt: connect to device IP on port 8883 with serial/access_code auth, status via subscribe to device/<serial>/report, start_print via publish to device/<serial>/request. Handle MQTT connection timeouts, TLS setup. Degrade gracefully if paho-mqtt not installed.
- [X] T030 [US4] Create public API in src/print3d_skill/printing/__init__.py — list_printers() that loads config, connects to each printer, returns list[PrinterInfo] with status (DISCONNECTED if unreachable). submit_print(gcode_path, printer_name, material, printer_profile) that loads config, finds printer by name, runs validate_gcode() first (ALWAYS), blocks on FAIL (raises ValidationError), uploads and starts on PASS/WARN, returns PrintJob. Raise CapabilityUnavailable if no config, PrinterError if printer unreachable or in error state.
- [X] T031 [US4] Implement PrinterProvider in src/print3d_skill/tools/printer_tools.py — ToolProvider subclass that checks for printer config file existence, reports capabilities ["printer_control"], tier="extended". Register in src/print3d_skill/tools/__init__.py.
- [X] T032 [US4] Add list_printers and submit_print to public API in src/print3d_skill/__init__.py — import from print3d_skill.printing, add to __all__. Write unit tests in tests/unit/test_printer_backends.py with mocked HTTP/MQTT: test OctoPrint status/upload/start with mocked requests.get/post, test Moonraker status/upload/start, test Bambu connect/status with mocked paho-mqtt, test config loading with temp YAML file, test validation enforcement (submit_print blocks on FAIL).

**Checkpoint**: list_printers() and submit_print() work with all three backends, validation enforcement is structural

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Contract tests, integration tests, documentation updates, quickstart validation

- [X] T037 [P] Write contract tests in tests/contract/test_validate_api.py — test parse_gcode return type has all GcodeAnalysis fields, test validate_gcode return type has all ValidationResult fields, test FileNotFoundError/UnsupportedFormatError/GcodeParseError raised for documented conditions, test CapabilityUnavailable for slice_model when no slicer, test submit_print validates first (mock printer to verify validation called), test all 5 new functions importable from print3d_skill
- [X] T038 [P] Write integration test for slice-validate chain in tests/integration/test_slicing_pipeline.py — if slicer available: slice model → parse output → validate output (full pipeline). If no slicer: test CapabilityUnavailable raised. Test with invalid model file raises SlicerError.
- [X] T039 Run ruff check and ruff format on all new source files in src/print3d_skill/validate/, src/print3d_skill/slicing/, src/print3d_skill/printing/, src/print3d_skill/models/validate.py, and all new test files — fix any lint errors
- [X] T040 Run full pytest suite and ensure all existing tests still pass plus all new tests pass
- [X] T041 Run quickstart.md validation — test scenarios 1-3 (parse, validate with PLA, validate with material+printer) programmatically. Scenarios 4-9 tested via existing integration/contract tests.
- [X] T042 Update tests/unit/test_router.py — remove "validate" from stub parametrize list if still present, verify ValidateHandler returns ModeResponse
- [X] T043 Update CLAUDE.md — add validate/, slicing/, printing/ to project structure, update public API count (13→18 functions), add requests and paho-mqtt to active technologies, add F5 to completed features, update test count, update recent changes
- [X] T044 Update README.md — add F5 to roadmap as complete, add validate/slice/print examples to Quick Start, update architecture section with validate/slicing/printing packages
- [X] T045 Update docs/vision.md — mark F5 complete in Status section
- [X] T046 Update docs/feature-chunking-strategy.md — mark F5 as complete in tree diagram
- [X] T047 Update eval/README.md — update use case status if applicable

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 G-code Parsing (Phase 3)**: Depends on Foundational — MVP, no other story dependencies
- **US5 Knowledge Content (Phase 4)**: Depends on Foundational only — YAML files, no code dependencies. Can run in parallel with Phase 3.
- **US2 Settings Validation (Phase 5)**: Depends on US1 (needs parse_gcode output) and US5 (needs knowledge profiles for meaningful validation)
- **US3 Slicer CLI (Phase 6)**: Depends on Foundational only — independent of other stories
- **US4 Printer Control (Phase 7)**: Depends on US2 (submit_print calls validate_gcode)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundational → US1 (no story dependencies)
- **US5 (P5)**: Foundational → US5 (independent, YAML only)
- **US2 (P2)**: Foundational → US5 (profiles) + US1 (parser) → US2
- **US3 (P3)**: Foundational → US3 (independent)
- **US4 (P4)**: Foundational → US2 (validation) → US4

### Within Each User Story

- Models before services (models in Foundational phase)
- Extractors/backends before orchestrators
- Public API wrapper last
- Integration tests after implementation

### Parallel Opportunities

- T001, T002, T003 can run in parallel (Setup phase, different files)
- T006 and T007 can run in parallel (slicer_detect.py and extractors.py)
- T033, T034, T035, T036 can run in parallel (all knowledge YAML files)
- T012 and T013 can run in parallel (profiles.py and checks.py)
- T019, T020, T021 can run in parallel (slicer base and backends)
- T025-T029 can run in parallel (printer base, config, and all 3 backends)
- US5 (Phase 4) can run in parallel with US1 (Phase 3)
- US3 (Phase 6) can run in parallel with US2 (Phase 5)
- T037 and T038 can run in parallel (different test files)

---

## Parallel Example: User Story 1

```bash
# Launch extractors and slicer detection in parallel:
Task: "Implement slicer auto-detection in src/print3d_skill/validate/slicer_detect.py"
Task: "Implement parameter extractors in src/print3d_skill/validate/extractors.py"

# Then sequentially: parser → public API → tests
```

## Parallel Example: User Story 4

```bash
# Launch all printer backends in parallel:
Task: "Implement PrinterBackend ABC in src/print3d_skill/printing/base.py"
Task: "Implement printer config loading in src/print3d_skill/printing/config.py"
Task: "Implement OctoPrint backend in src/print3d_skill/printing/octoprint.py"
Task: "Implement Moonraker backend in src/print3d_skill/printing/moonraker.py"
Task: "Implement Bambu Lab backend in src/print3d_skill/printing/bambu.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (G-code Parsing)
4. **STOP and VALIDATE**: parse_gcode() works with all 4 slicer formats
5. Users can already audit G-code files

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (G-code Parsing) + US5 (Knowledge Content) → in parallel, MVP + profiles
3. US2 (Settings Validation) → Core value delivered
4. US3 (Slicer CLI) → Re-slice workflow enabled (independent, can overlap with US2)
5. US4 (Printer Control) → Full pipeline complete
6. Polish → Contract tests, docs, quickstart validation

### Recommended Execution Order

Phases are ordered to match execution dependencies:

1. Setup → Foundational (Phases 1-2)
2. US1 + US5 (Phases 3-4, in parallel — parser code + knowledge YAML files)
3. US2 (Phase 5, depends on both US1 and US5)
4. US3 (Phase 6, independent, can overlap with Phase 5)
5. US4 (Phase 7, depends on US2)
6. Polish (Phase 8)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Core tier (US1, US2, US5) = no system dependencies beyond pip
- Extended tier (US3, US4) = requires slicer binaries / printer network / requests / paho-mqtt
- Test fixtures use minimal G-code snippets, not full print files
- Printer backends use mocked HTTP/MQTT in unit tests
- Validation enforcement (submit_print always validates first) is structural, not policy
