# Implementation Plan: Parametric CAD Generation

**Branch**: `003-parametric-cad` | **Date**: 2026-03-14 | **Spec**: `specs/003-parametric-cad/spec.md`
**Input**: Feature specification from `/specs/003-parametric-cad/spec.md`

## Summary

Implement the Create mode pipeline: session-based OpenSCAD code
generation infrastructure with compile-render-iterate loop, FDM
printability validation (wall thickness, overhangs, bridges, bed
adhesion via trimesh ray casting), BOSL2 runtime detection, and
STL/3MF/.scad export. The agent writes OpenSCAD code; the skill
provides compilation, rendering, validation, and export infrastructure.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: trimesh (mesh analysis, ray casting for
printability), numpy (numerical computation), OpenSCAD CLI (extended
tier — .scad compilation and rendering), manifold3d (CSG, existing),
matplotlib (headless rendering, existing)
**Storage**: Filesystem — temporary directories for session working
files (versioned .scad, .stl, .png per iteration)
**Testing**: pytest with existing conftest.py fixtures; contract,
integration, and unit test tiers
**Target Platform**: macOS, Linux (headless CI compatible via
matplotlib Agg backend)
**Project Type**: Python library (pip-installable skill package)
**Performance Goals**: Full create pipeline (describe → generate →
iterate → validate → export) completes in under 2 minutes for simple
parts (SC-007)
**Constraints**: Core tier (models, knowledge, printability analysis)
MUST work without OpenSCAD installed; compilation/rendering require
OpenSCAD (extended tier). BOSL2 optional.
**Scale/Scope**: Single-body part generation, up to 5 iterations per
session, 4 printability checks, 2 export formats + .scad source

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Open Tools Only | PASS | OpenSCAD (GPLv2), trimesh (MIT), numpy (BSD), BOSL2 (BSD). All OSI-approved. No proprietary dependencies. |
| II | Agent-Portable Architecture | PASS | Core logic is pure Python: session management, printability validation, export. No agent-framework APIs in create module. The agent calls `start_session()` / `submit_iteration()` — framework-agnostic function calls. |
| III | Visual Verification | PASS | Every iteration renders a multi-angle preview via existing `render_preview()`. The agent inspects previews before approving. No blind pipeline. |
| IV | Validate Before Print | PASS | Printability validation runs before export. 4 FDM checks (wall thickness, overhangs, bridges, bed adhesion) with actionable warnings. Export includes the PrintabilityReport. |
| V | Progressive Disclosure | PASS | Knowledge loaded on-demand via `query_knowledge(mode="create", problem_type=...)`. Tolerance tables, design patterns, and BOSL2 references are separate knowledge files loaded only when queried. |
| VI | Tiered Dependencies | PASS | Models, printability analysis, knowledge — all pip-installable (trimesh + numpy). OpenSCAD compilation is extended tier with `CapabilityUnavailable` error when missing. BOSL2 detected at runtime, graceful fallback to native primitives. |
| VII | Structured Knowledge | PASS | Tolerance tables, feature size tables, design patterns, BOSL2 references stored as structured YAML knowledge files — not embedded in prompts. Queryable via existing knowledge system. |

**Gate result**: ALL PASS — no violations, no complexity tracking needed.

### Post-Design Re-evaluation

After Phase 1 design (data-model.md, contracts, quickstart.md):

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Open Tools Only | PASS | No new dependencies added beyond existing stack. |
| II | Agent-Portable | PASS | Session API (`start_session`, `submit_iteration`, `export_design`) is pure Python, no framework coupling. |
| III | Visual Verification | PASS | `GeneratedDesign.preview_path` produced every iteration; quickstart scenarios confirm render-before-approve flow. |
| IV | Validate Before Print | PASS | `validate_printability()` is a separate public function and runs before `export_design()`. |
| V | Progressive Disclosure | PASS | Knowledge queries scoped to `mode="create"` and `problem_type`. |
| VI | Tiered Dependencies | PASS | `detect_bosl2()` and `start_session()` raise `CapabilityUnavailable` when OpenSCAD missing. Core models work without it. |
| VII | Structured Knowledge | PASS | 4 new knowledge files (tolerances, feature sizes, design patterns, BOSL2 reference) as structured YAML. |

## Project Structure

### Documentation (this feature)

```text
specs/003-parametric-cad/
├── plan.md              # This file
├── spec.md              # Feature specification (5 user stories)
├── research.md          # Phase 0 output (6 decisions: R1-R6)
├── data-model.md        # Phase 1 output (7 entities, state machine)
├── quickstart.md        # Phase 1 output (7 scenarios)
├── contracts/
│   └── public-api.md    # Phase 1 output (6 functions, 2 exceptions)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/print3d_skill/
├── __init__.py                  # Add create_design, validate_printability exports
├── models/
│   └── create.py                # NEW: CreateConfig, DesignRequest, GeneratedDesign,
│                                #   PrintabilityWarning, PrintabilityReport,
│                                #   DesignExport, CreateResult, CreateSession
├── create/
│   ├── __init__.py              # NEW: start_session, submit_iteration, create_design,
│   │                            #   export_design public functions
│   ├── session.py               # NEW: CreateSession management, iteration tracking,
│   │                            #   working directory setup
│   ├── compiler.py              # NEW: OpenSCAD compilation wrapper (uses existing
│   │                            #   _compile_scad), versioned file management
│   ├── printability.py          # NEW: validate_printability() — 4 FDM checks via
│   │                            #   trimesh ray casting + numpy
│   └── bosl2.py                 # NEW: detect_bosl2() with caching
├── modes/
│   └── create.py                # UPDATE: CreateHandler to use create/ pipeline
├── exceptions.py                # UPDATE: Add DesignError, PrintabilityError
├── router.py                    # No changes (existing create route works)
├── rendering/
│   └── __init__.py              # No changes (existing _compile_scad, render_preview)
├── knowledge/                   # No changes to loader/schemas
├── knowledge_base/
│   └── create/                  # NEW: Knowledge content files
│       ├── tolerances.yaml      # Tolerance tables (press-fit, snap-fit, screw clearance)
│       ├── feature_sizes.yaml   # Min feature sizes by nozzle diameter
│       ├── design_patterns.yaml # Mechanical patterns (bosses, clips, hinges, vents)
│       └── bosl2_reference.yaml # BOSL2 module summaries and usage examples

tests/
├── contract/
│   └── test_public_api.py       # UPDATE: Add F3 contract tests
├── integration/
│   ├── test_create_pipeline.py  # NEW: End-to-end create session tests
│   └── test_printability.py     # NEW: Printability validation with known meshes
└── unit/
    ├── test_create_models.py    # NEW: CreateConfig, DesignRequest, etc.
    ├── test_session.py          # NEW: Session lifecycle, iteration tracking
    ├── test_printability.py     # NEW: Individual printability checks
    └── test_bosl2.py            # NEW: BOSL2 detection logic
```

**Structure Decision**: Follows the existing single-project layout
established by F1 and F2. New `create/` subpackage mirrors the
`analysis/`, `repair/`, and `export/` pattern. Models in
`models/create.py` follows the existing `models/analysis.py`,
`models/repair.py` convention. Knowledge content in
`knowledge_base/create/` follows the existing knowledge base
directory structure.

## Complexity Tracking

> No constitution violations — this section is intentionally empty.

No violations to justify. All seven principles pass both pre-research
and post-design gates.
