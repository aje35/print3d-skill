# Implementation Plan: Core Infrastructure

**Branch**: `001-core-infrastructure` | **Date**: 2026-03-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-core-infrastructure/spec.md`

## Summary

Build the foundational Python package for the Print3D Skill: a
rendering pipeline that produces multi-angle mesh previews headlessly
via matplotlib, a tool orchestration layer with capability-based
discovery and graceful degradation, a knowledge system that loads
structured YAML domain knowledge on demand with AND-filtered context
queries, and a skill router that dispatches to five mode handler
stubs. The package is pip-installable with core features requiring
zero system-level dependencies.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: trimesh (mesh I/O), manifold3d (boolean CSG),
numpy (numerics), matplotlib (headless rendering via Agg backend),
Pillow (image composition), PyYAML (knowledge files)
**Storage**: Filesystem — knowledge YAML files bundled as package data,
preview PNGs written to caller-specified output path
**Testing**: pytest, pytest-cov
**Target Platform**: Cross-platform (Linux, macOS, Windows),
headless-capable (no GPU or display server for core features)
**Project Type**: Library (pip-installable Python package)
**Performance Goals**: <10s render for typical meshes (<100K faces),
<1s tool discovery and knowledge queries
**Constraints**: No GPU required for core rendering, preview images
at 1600x1200 and <1MB, no system-level dependencies for core tier
**Scale/Scope**: Single-user library, ~15 source modules, 4 seed
knowledge files in this feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Open Tools Only | PASS | All deps OSI-licensed: trimesh (MIT), manifold3d (Apache-2.0), numpy (BSD), matplotlib (PSF), Pillow (HPND), PyYAML (MIT). OpenSCAD (GPL-2) optional. |
| II. Agent-Portable | PASS | Core is pure Python, no agent framework imports. Router accepts mode identifiers. No Claude/OpenAI/Gemini APIs. |
| III. Visual Verification | PASS | This feature builds the rendering pipeline all modes depend on. |
| IV. Validate Before Print | N/A | No print capabilities in this feature. Validate mode is a stub. |
| V. Progressive Disclosure | PASS | Knowledge system uses AND-filtered context queries, loads only matching files (FR-014, FR-015). |
| VI. Tiered Dependencies | PASS | Core tier fully pip-installable. OpenSCAD detected at runtime with graceful degradation (FR-011, FR-021). |
| VII. Tribal Knowledge | PASS | Knowledge system defines structured YAML schemas for all four knowledge types (FR-013). Seed files validate the format. |

No violations. Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-infrastructure/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
└── tasks.md
```

### Source Code (repository root)

```text
src/print3d_skill/
├── __init__.py                  # Package version, public API re-exports
├── router.py                    # Skill router: mode dispatch
├── rendering/
│   ├── __init__.py
│   ├── renderer.py              # Multi-angle mesh rendering (matplotlib)
│   └── compositor.py            # 2x2 grid composition, PNG output
├── tools/
│   ├── __init__.py
│   ├── registry.py              # Capability registry, discovery
│   ├── base.py                  # ToolProvider base class
│   ├── openscad.py              # OpenSCAD CLI wrapper
│   ├── trimesh_tools.py         # trimesh wrapper (mesh I/O, analysis)
│   └── manifold_tools.py        # manifold3d wrapper (boolean CSG)
├── knowledge/
│   ├── __init__.py
│   ├── loader.py                # Query engine: context → matching files
│   └── schemas.py               # Knowledge file schema validation
├── knowledge_base/              # Bundled YAML knowledge files
│   ├── seed_tolerance_table.yaml
│   ├── seed_material_properties.yaml
│   ├── seed_decision_tree.yaml
│   └── seed_design_rules.yaml
├── modes/
│   ├── __init__.py
│   ├── base.py                  # ModeHandler base, stub response
│   ├── create.py                # Stub
│   ├── fix.py                   # Stub
│   ├── modify.py                # Stub
│   ├── diagnose.py              # Stub
│   └── validate.py              # Stub
└── models/
    ├── __init__.py
    ├── mesh.py                  # MeshFile dataclass
    ├── preview.py               # PreviewResult dataclass
    ├── capability.py            # ToolCapability, ToolProvider status
    ├── knowledge.py             # KnowledgeFile, KnowledgeQuery
    └── mode.py                  # WorkflowMode enum, ModeResponse

tests/
├── conftest.py                  # Shared fixtures, test mesh paths
├── fixtures/
│   ├── cube.stl                 # Minimal valid STL
│   ├── colored.3mf              # 3MF with vertex colors
│   ├── simple.obj               # Simple OBJ mesh
│   ├── corrupt.stl              # Truncated/invalid STL
│   ├── large_mesh.stl           # >1M faces for timeout tests
│   └── sample.scad              # Simple OpenSCAD source
├── unit/
│   ├── test_renderer.py
│   ├── test_compositor.py
│   ├── test_registry.py
│   ├── test_knowledge_loader.py
│   ├── test_knowledge_schemas.py
│   └── test_router.py
├── integration/
│   ├── test_render_pipeline.py  # Mesh file → PNG end-to-end
│   ├── test_tool_discovery.py   # Registry + real tool detection
│   └── test_knowledge_query.py  # Query → filtered results
└── contract/
    └── test_public_api.py       # Public function signatures stable

pyproject.toml                   # PEP 621 metadata, build config
```

**Structure Decision**: Single-project src layout. Python library with
no frontend/backend split. The `src/` prefix prevents import shadowing
during development. Knowledge files bundled as package data via
`pyproject.toml [tool.setuptools.package-data]`.
