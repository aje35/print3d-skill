# Implementation Plan: Model Modification

**Branch**: `004-model-modification` | **Date**: 2026-03-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-model-modification/spec.md`

## Summary

Implement Modify mode: standalone mesh modification operations (boolean, scale, combine, text engrave, split) with before/after visual comparison and post-modification validation. Uses manifold3d for boolean CSG, trimesh.creation for primitive generation, trimesh.intersections for splitting, and OpenSCAD for text geometry (extended tier). Each operation is stateless — takes an input mesh, produces a new output mesh. Agent chains operations by feeding outputs as inputs.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: trimesh>=4.0 (mesh ops, primitives, splitting), manifold3d>=3.0 (boolean CSG), numpy>=1.24 (transforms), matplotlib>=3.7 + Pillow>=10.0 (rendering), OpenSCAD CLI (text geometry, extended tier)
**Storage**: File-based (mesh files on local filesystem)
**Testing**: pytest with pytest-cov; unit tests for each operation, integration tests for pipeline
**Target Platform**: Cross-platform (macOS, Linux) — headless (no GPU)
**Project Type**: Library (Python package, src layout)
**Performance Goals**: Full pipeline (load → modify → validate → preview → export) < 30s for meshes < 100K faces
**Constraints**: Headless rendering (matplotlib Agg), pip-installable core tier, no proprietary dependencies
**Scale/Scope**: Single-user local library, processes one mesh at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Open Tools Only | PASS | manifold3d (Apache 2.0), trimesh (MIT), OpenSCAD (GPL), numpy (BSD). All OSI-approved. |
| II | Agent-Portable | PASS | All modify operations are framework-agnostic Python functions. No agent-specific imports in core logic. ModifyHandler follows the same adapter pattern as Fix/Create. |
| III | Visual Verification | PASS | FR-024/FR-025 mandate before/after rendering for every modification. Visual comparison is a first-class output of every operation. |
| IV | Validate Before Print | PASS | FR-027 runs F2 mesh analysis after every modification. Modify mode doesn't print — it produces meshes for downstream slicing. |
| V | Progressive Disclosure | PASS | Knowledge queried on-demand via `query_knowledge(mode="modify", ...)`. Only modify-relevant knowledge loaded. |
| VI | Tiered Dependencies | PASS | Boolean, scale, combine, split = core tier (pip only). Text engrave = extended tier (OpenSCAD). Graceful degradation: text ops return CapabilityUnavailable when OpenSCAD missing. See research.md R7. |
| VII | Encode Tribal Knowledge | PASS | FR-029-032 mandate structured YAML knowledge files for boolean best practices, engraving guidelines, pin tolerances, splitting strategies. |

**Post-Phase 1 re-check**: All 7 principles still pass. Data model uses framework-agnostic dataclasses. Public API is a plain Python function. No constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/004-model-modification/
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
├── modify/                         # NEW — Modify mode subsystem
│   ├── __init__.py                 # Public: modify_mesh()
│   ├── boolean.py                  # Boolean operations (union, diff, intersection)
│   ├── primitives.py               # Primitive shape generation (cylinder, box, sphere, cone)
│   ├── scale.py                    # Scaling operations (uniform, non-uniform, targeted)
│   ├── combine.py                  # Model combining with alignment
│   ├── text.py                     # Text engraving/embossing (requires OpenSCAD)
│   ├── split.py                    # Model splitting with alignment features
│   ├── comparison.py               # Before/after visual comparison
│   └── features.py                 # Feature detection for scaling warnings
├── models/
│   └── modify.py                   # NEW — ModifyRequest, ModifyResult, enums, params
├── modes/
│   └── modify.py                   # UPDATED — ModifyHandler implementation (currently stub)
├── knowledge_base/
│   └── modify/                     # NEW — Modify mode knowledge files
│       ├── boolean_best_practices.yaml
│       ├── text_engraving_guidelines.yaml
│       ├── alignment_pin_tolerances.yaml
│       └── splitting_strategies.yaml
└── __init__.py                     # UPDATED — add modify_mesh to public API

tests/
├── unit/
│   ├── test_boolean.py             # NEW
│   ├── test_primitives.py          # NEW
│   ├── test_scale.py               # NEW
│   ├── test_combine.py             # NEW
│   ├── test_text.py                # NEW
│   ├── test_split.py               # NEW
│   ├── test_comparison.py          # NEW
│   ├── test_features.py            # NEW
│   └── test_modify_models.py       # NEW — dataclass validation
├── integration/
│   └── test_modify_pipeline.py     # NEW — end-to-end modify workflows
└── contract/
    └── test_modify_api.py          # NEW — public API contract tests
```

**Structure Decision**: Follows existing project layout. The `modify/` package mirrors the pattern of `create/`, `analysis/`, and `repair/` — a dedicated subsystem directory with focused modules. Each modification operation type gets its own module for isolation and testability.

## Complexity Tracking

No constitution violations — table not needed.
