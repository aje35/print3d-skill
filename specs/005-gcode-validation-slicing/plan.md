# Implementation Plan: G-code Validation & Slicing

**Branch**: `005-gcode-validation-slicing` | **Date**: 2026-03-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-gcode-validation-slicing/spec.md`

## Summary

Implement Validate mode and the slicing/printing pipeline: a streaming G-code parser that extracts structured parameters from PrusaSlicer/Bambu Studio/OrcaSlicer/Cura output, a settings validator that cross-references G-code against material and printer profiles, CLI wrappers for PrusaSlicer and OrcaSlicer (extended tier), and printer control backends for OctoPrint, Moonraker, and Bambu Lab (extended tier). G-code parsing and validation are core tier (Python stdlib + PyYAML). Slicer and printer features degrade gracefully when dependencies are unavailable.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: PyYAML (already present, for knowledge/profiles), requests (new, for OctoPrint/Moonraker REST), paho-mqtt (new, for Bambu Lab MQTT). G-code parser uses only Python stdlib (re, io).
**Storage**: File-based — G-code files on local filesystem, printer config YAML at `~/.config/print3d-skill/printers.yaml`
**Testing**: pytest with pytest-cov; unit tests for parser/validator, integration tests for pipeline, contract tests for public API
**Target Platform**: Cross-platform (macOS, Linux) — headless
**Project Type**: Library (Python package, src layout)
**Performance Goals**: G-code parsing < 5s for 100MB files, validation < 1s after parsing
**Constraints**: Core tier pip-installable with zero system dependencies. Extended tier adds `requests` + `paho-mqtt` (pip) plus system binaries (slicers) and network services (printers).
**Scale/Scope**: Single-user local library, processes one G-code file at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Open Tools Only | PASS | PrusaSlicer (AGPL), OrcaSlicer (AGPL), OctoPrint (AGPL), Moonraker (GPL), paho-mqtt (EPL/EDL), requests (Apache 2.0). All OSI-approved. Bambu Lab MQTT protocol is public; no proprietary SDK required. |
| II | Agent-Portable | PASS | All parsing, validation, and slicing logic are framework-agnostic Python functions. ValidateHandler follows the existing adapter pattern. No agent-specific imports in core logic. |
| III | Visual Verification | PASS | This feature does not transform geometry — it inspects/validates existing G-code. Visual verification is not applicable (no geometry to render). Upstream features (Create/Fix/Modify) handle rendering. |
| IV | Validate Before Print | PASS | FR-030 mandates validation before any print submission. `submit_print()` internally calls `validate_gcode()` first and blocks on FAIL. No code path exists to bypass validation. This feature IS the implementation of Principle IV. |
| V | Progressive Disclosure | PASS | Material and printer profiles loaded on-demand via `query_knowledge(mode="validate", material=...)`. Only the relevant profile is loaded for each validation. |
| VI | Tiered Dependencies | PASS | Core tier (parsing + validation) = Python stdlib + PyYAML (existing). Extended tier: slicer CLI (PrusaSlicer/OrcaSlicer binaries), printer control (requests + paho-mqtt + network services). All extended features degrade gracefully via CapabilityUnavailable. See research.md R7. |
| VII | Encode Tribal Knowledge | PASS | Material profiles, printer profiles, and slicer setting mappings stored as structured YAML in knowledge_base/validate/. Queryable via existing knowledge system. |

**Post-Phase 1 re-check**: All 7 principles still pass. Data model uses framework-agnostic dataclasses. Public API is plain Python functions. Validation enforcement is structural (code path, not policy).

## Project Structure

### Documentation (this feature)

```text
specs/005-gcode-validation-slicing/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Dataclass definitions
├── quickstart.md        # Usage examples
├── contracts/
│   └── public-api.md    # Public API contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/print3d_skill/
├── validate/                           # NEW — Validate mode subsystem
│   ├── __init__.py                     # Public: parse_gcode(), validate_gcode()
│   ├── parser.py                       # Streaming G-code parser
│   ├── slicer_detect.py                # Slicer auto-detection from comments
│   ├── extractors.py                   # Parameter extraction (temps, speeds, retraction, etc.)
│   ├── validator.py                    # Settings validation engine
│   ├── checks.py                       # Individual validation check implementations
│   └── profiles.py                     # Material/printer profile loading from knowledge
├── slicing/                            # NEW — Slicer CLI integration (extended tier)
│   ├── __init__.py                     # Public: slice_model()
│   ├── base.py                         # SlicerBackend ABC
│   ├── prusaslicer.py                  # PrusaSlicer CLI wrapper
│   └── orcaslicer.py                   # OrcaSlicer CLI wrapper
├── printing/                           # NEW — Printer control (extended tier)
│   ├── __init__.py                     # Public: list_printers(), submit_print()
│   ├── base.py                         # PrinterBackend ABC
│   ├── config.py                       # Printer configuration loading
│   ├── octoprint.py                    # OctoPrint REST backend
│   ├── moonraker.py                    # Moonraker/Klipper REST backend
│   └── bambu.py                        # Bambu Lab MQTT backend
├── models/
│   └── validate.py                     # NEW — GcodeAnalysis, ValidationResult, enums, profiles
├── modes/
│   └── validate.py                     # UPDATED — ValidateHandler implementation (currently stub)
├── tools/
│   ├── slicer_tools.py                 # NEW — SlicerProvider (PrusaSlicer/OrcaSlicer detection)
│   └── printer_tools.py                # NEW — PrinterProvider (printer config detection)
├── knowledge_base/
│   └── validate/                       # NEW — Validate mode knowledge files
│       ├── material_pla.yaml
│       ├── material_petg.yaml
│       ├── material_abs.yaml
│       ├── material_asa.yaml
│       ├── material_tpu.yaml
│       ├── material_nylon.yaml
│       ├── material_composites.yaml
│       ├── printer_profiles.yaml
│       └── slicer_settings_map.yaml
├── exceptions.py                       # UPDATED — add GcodeParseError, SlicerError, ValidationError, PrinterError
└── __init__.py                         # UPDATED — add parse_gcode, validate_gcode, slice_model, list_printers, submit_print

tests/
├── unit/
│   ├── test_gcode_parser.py            # NEW — parser with sample G-code snippets
│   ├── test_slicer_detect.py           # NEW — slicer identification
│   ├── test_extractors.py              # NEW — parameter extraction
│   ├── test_validator.py               # NEW — validation logic
│   ├── test_checks.py                  # NEW — individual check implementations
│   ├── test_profiles.py                # NEW — profile loading
│   ├── test_validate_models.py         # NEW — dataclass validation
│   ├── test_slicer_cli.py              # NEW — slicer CLI wrapper (mocked subprocess)
│   └── test_printer_backends.py        # NEW — printer backends (mocked HTTP/MQTT)
├── integration/
│   ├── test_validate_pipeline.py       # NEW — end-to-end parse → validate
│   └── test_slicing_pipeline.py        # NEW — slice → parse → validate chain
├── contract/
│   └── test_validate_api.py            # NEW — public API contract tests
└── fixtures/
    └── gcode/                          # NEW — sample G-code files for testing
        ├── prusaslicer_benchy.gcode
        ├── bambustudio_benchy.gcode
        ├── orcaslicer_benchy.gcode
        ├── cura_benchy.gcode
        ├── minimal.gcode
        ├── empty.gcode
        └── no_comments.gcode
```

**Structure Decision**: Three new packages: `validate/` (core tier parser + validator), `slicing/` (extended tier slicer CLI wrappers), `printing/` (extended tier printer control). This separates the three dependency tiers cleanly. The `validate/` package follows the existing pattern of `analysis/`, `repair/`, `modify/` — a focused subsystem directory. Slicer and printer packages are separate because they have different external dependencies and different availability patterns.

## Complexity Tracking

No constitution violations — table not needed.
