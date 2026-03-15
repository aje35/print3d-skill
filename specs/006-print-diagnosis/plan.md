# Implementation Plan: Print Failure Diagnosis

**Branch**: `006-print-diagnosis` | **Date**: 2026-03-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-print-diagnosis/spec.md`

## Summary

Implement the Diagnose mode: a diagnosis engine that accepts pre-identified defect categories and diagnostic context from the AI agent, walks structured decision trees to determine root causes, and generates specific actionable fix recommendations with numeric slicer values. The skill provides defect guides (for agent-side photo analysis), decision trees, printer/material knowledge, and calibration procedures — all as structured YAML queryable through the existing knowledge system. No new dependencies required; pure Python logic over existing infrastructure.

## Technical Context

**Language/Version**: Python 3.10+ (established; src layout, PEP 621)
**Primary Dependencies**: PyYAML (existing) — no new dependencies
**Storage**: YAML knowledge files in `knowledge_base/diagnose/` (existing pattern)
**Testing**: pytest (existing)
**Target Platform**: Cross-platform Python library (pip-installable)
**Project Type**: Library (extending existing print3d-skill package)
**Performance Goals**: Near-instant — decision tree traversal and knowledge lookup are in-memory operations
**Constraints**: Core tier only (no system-level dependencies); no image processing (agent handles photos)
**Scale/Scope**: 12 defect categories, 5 materials, 3 printer families, ~9 knowledge YAML files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Open Tools Only | PASS | No new dependencies. Pure Python + PyYAML (MIT). |
| II. Agent-Portable | PASS | Diagnosis logic is framework-agnostic Python. Photo analysis boundary is explicitly at the agent level — skill receives structured data. |
| III. Visual Verification | PASS | Constitution specifies diagnose mode: "agent MUST be able to analyze user-submitted photos of physical prints." Agent does this using skill's defect guides; skill processes structured results. |
| IV. Validate Before Print | N/A | Diagnose mode does not send prints. |
| V. Progressive Disclosure | PASS | Knowledge loaded via AND-filtered queries (mode="diagnose" + defect-specific filters). Only relevant decision trees and material data loaded per diagnosis. |
| VI. Tiered Dependencies | PASS | Entire module is core tier. No system packages. |
| VII. Encode Tribal Knowledge | PASS | All diagnostic knowledge encoded as structured YAML: decision trees, defect guides, printer tips, material failure modes, calibration procedures. |

**Gate result**: All principles PASS. No violations to track.

## Project Structure

### Documentation (this feature)

```text
specs/006-print-diagnosis/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── diagnose_api.md  # Public API contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/print3d_skill/
├── diagnosis/                          # NEW: Diagnosis engine package
│   ├── __init__.py                     # Public API: diagnose_print()
│   ├── engine.py                       # DiagnosisEngine: tree walking, recommendations
│   └── models.py                       # PrintDefect, DiagnosticContext, RootCause,
│                                       #   Recommendation, DiagnosisResult
├── modes/
│   └── diagnose.py                     # DiagnoseHandler (existing stub → implement)
├── models/
│   └── knowledge.py                    # Update VALID_KNOWLEDGE_TYPES (+2 types)
├── knowledge_base/
│   └── diagnose/                       # NEW: 9 knowledge YAML files
│       ├── defect_guides.yaml          # 12 defect categories: severity, visual indicators
│       ├── decision_trees_extrusion.yaml   # Stringing, under/over-extrusion
│       ├── decision_trees_adhesion.yaml    # Bed adhesion, warping, elephant foot
│       ├── decision_trees_layers.yaml      # Layer shifts, layer separation
│       ├── decision_trees_surface.yaml     # Zits/blobs, ghosting/ringing, support scarring
│       ├── decision_trees_bridging.yaml    # Poor bridging
│       ├── printer_troubleshooting.yaml    # Bambu, Prusa, Creality tips
│       ├── material_failure_modes.yaml     # PLA, PETG, ABS, TPU, ASA failures
│       └── calibration_procedures.yaml     # Flow rate, e-steps, PID tuning
└── __init__.py                         # Update: add diagnose_print to public API

tests/
├── unit/
│   ├── test_diagnosis_engine.py        # Decision tree walking, recommendation generation
│   └── test_diagnosis_models.py        # Dataclass construction, validation
├── integration/
│   └── test_diagnosis_pipeline.py      # End-to-end: defects + context → recommendations
└── contract/
    └── test_diagnose_api.py            # Public API signature verification
```

**Structure Decision**: Follows established pattern — new `diagnosis/` sub-package (noun form, matching `analysis/`, `repair/`) with models, engine, and public API. Knowledge files in `knowledge_base/diagnose/` subdirectory (matching `knowledge_base/create/`, `knowledge_base/modify/`, `knowledge_base/validate/`). DiagnoseHandler stub in `modes/diagnose.py` gets implemented.

## Complexity Tracking

> No constitution violations. Table not needed.
