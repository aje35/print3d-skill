# Implementation Plan: Mesh Analysis & Repair

**Branch**: `002-mesh-analysis-repair` | **Date**: 2026-03-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-mesh-analysis-repair/spec.md`

## Summary

Implement Fix mode: a mesh analysis engine that detects 10 defect types with severity classification, a repair pipeline that applies prioritized fixes with visual verification at each step, and domain knowledge content for mesh repair guidance. Built entirely on trimesh (core tier, pip-only) with the existing F1 rendering pipeline for before/after previews.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: trimesh>=4.0 (analysis, repair, loading, export), manifold3d>=3.0 (boolean ops if needed for self-intersection), numpy>=1.24 (array operations), matplotlib>=3.7 + Pillow>=10.0 (rendering via F1), PyYAML>=6.0 (knowledge files)
**Storage**: File-based — mesh files in, repaired mesh files + preview PNGs out
**Testing**: pytest with programmatically generated defective meshes
**Target Platform**: Cross-platform (macOS, Linux, Windows) — headless, no GPU
**Project Type**: Python library (pip-installable)
**Performance Goals**: Full pipeline <30s for meshes up to 500K faces (SC-004)
**Constraints**: All core deps pip-only; open-source OSI-licensed only; no system packages required
**Scale/Scope**: Single mesh files; typical range 1K–500K faces, edge case up to 5M+

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Open Tools Only | PASS | trimesh (MIT), manifold3d (Apache-2.0), numpy (BSD) — all OSI-approved |
| II. Agent-Portable | PASS | Pure Python library with no agent-framework coupling; analysis/repair APIs are framework-agnostic functions |
| III. Visual Verification | PASS | FR-023 requires before/after multi-angle preview for every repair step; uses F1 render_preview() |
| IV. Validate Before Print | N/A | Fix mode repairs meshes but does not send jobs to printers |
| V. Progressive Disclosure | PASS | Knowledge files tagged with `modes: [fix]`; only loaded when Fix mode context is queried |
| VI. Tiered Dependencies | PASS | All analysis/repair deps are pip-installable core tier; no system packages needed |
| VII. Structured Knowledge | PASS | FR-031–033 specify YAML knowledge content: decision trees, slicer error mappings, defect patterns |

No violations. Gate passes.

## Project Structure

### Documentation (this feature)

```text
specs/002-mesh-analysis-repair/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── public-api.md   # analyze_mesh(), repair_mesh(), export_mesh()
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/print3d_skill/
├── __init__.py              # UPDATED: add analyze_mesh, repair_mesh, export_mesh exports
├── exceptions.py            # UPDATED: add MeshAnalysisError, RepairError, ExportError
├── analysis/                # NEW: defect analysis engine
│   ├── __init__.py          # Public API: analyze_mesh()
│   ├── detectors.py         # Individual defect detector functions
│   └── report.py            # AnalysisReport builder + health classification
├── repair/                  # NEW: repair strategies + pipeline
│   ├── __init__.py          # Public API: repair_mesh()
│   ├── strategies.py        # Individual repair strategy functions
│   └── pipeline.py          # Composed repair pipeline with ordering
├── export/                  # NEW: mesh export (STL, 3MF)
│   ├── __init__.py          # Public API: export_mesh()
│   └── formats.py           # Format-specific exporters
├── models/
│   ├── analysis.py          # NEW: DefectType enum, MeshDefect, MeshAnalysisReport
│   ├── repair.py            # NEW: RepairResult, RepairSummary, RepairConfig
│   ├── export.py            # NEW: ExportResult
│   └── mesh.py              # UPDATED: add PLY to supported formats
├── rendering/
│   └── renderer.py          # UPDATED: add PLY to SUPPORTED_FORMATS
├── modes/
│   └── fix.py               # UPDATED: from stub to full Fix mode handler
├── knowledge_base/
│   ├── fix_mesh_repair_decision_tree.yaml    # NEW
│   ├── fix_slicer_error_mappings.yaml        # NEW
│   └── fix_defect_patterns_by_source.yaml    # NEW
└── ... (existing files unchanged)

tests/
├── conftest.py              # UPDATED: add defective mesh fixtures
├── unit/
│   ├── test_detectors.py    # NEW: individual detector tests
│   ├── test_strategies.py   # NEW: individual repair strategy tests
│   └── test_report.py       # NEW: report builder tests
├── integration/
│   ├── test_analysis.py     # NEW: US1 end-to-end analysis tests
│   ├── test_repair.py       # NEW: US2 repair + preview tests
│   ├── test_pipeline.py     # NEW: US3 full pipeline tests
│   └── test_export.py       # NEW: export format tests
├── contract/
│   └── test_public_api.py   # UPDATED: add F2 API contracts
└── ... (existing tests unchanged)
```

**Structure Decision**: Extends the existing `src/print3d_skill/` layout with three new subpackages (`analysis/`, `repair/`, `export/`) following the same pattern as the existing `rendering/`, `tools/`, and `knowledge/` packages. Each subpackage has an `__init__.py` with the public API function and internal modules for implementation details.

## Complexity Tracking

No constitution violations — table not needed.
