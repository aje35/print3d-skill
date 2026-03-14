# print3d-skill Development Guidelines

## Active Technologies

- Python 3.10+ (src layout, PEP 621)
- trimesh (mesh I/O, analysis, repair, ray casting for printability), manifold3d (boolean CSG), numpy, matplotlib (Agg), Pillow, PyYAML
- OpenSCAD CLI (extended tier, optional), BOSL2 library (optional)

## Project Structure

```text
src/print3d_skill/          # Main package (src layout)
  create/                   # Create mode: session, compiler, printability, BOSL2
  analysis/                 # Mesh defect detection
  repair/                   # Mesh repair pipeline
  export/                   # Format-specific mesh exporters
  rendering/                # Headless multi-angle mesh preview
  tools/                    # Capability registry + providers
  knowledge/                # YAML knowledge loader
  knowledge_base/           # Bundled YAML knowledge files (package data)
    create/                 # Create mode knowledge (tolerances, patterns, BOSL2)
  modes/                    # Workflow handlers (5 modes)
  models/                   # Dataclasses
  router.py                 # Mode dispatch
  exceptions.py             # Exception hierarchy
tests/                      # pytest suite (unit/, integration/, contract/)
eval/                       # Real-world evaluation use cases with mesh assets
docs/                       # Vision, research, feature chunking strategy
specs/                      # Feature specs (spec-kit pipeline)
.specify/                   # Spec-kit templates, scripts, constitution
```

## Commands

```bash
pip install -e ".[dev]"     # Install in dev mode
pytest                      # Run tests (73 passing)
pytest --cov=print3d_skill  # Run tests with coverage
ruff check src/ tests/      # Lint
ruff format src/ tests/     # Format
```

## Public API (13 functions)

- `render_preview(mesh_path, output_path)` — multi-angle PNG preview
- `get_capability(name)` — capability-based tool lookup
- `list_capabilities()` — all capabilities with availability
- `refresh_capabilities()` — re-detect tools
- `query_knowledge(mode, material, printer, problem_type)` — AND-filtered knowledge
- `route(mode)` — dispatch to mode handler
- `system_info()` — package capability summary
- `analyze_mesh(mesh_path)` — mesh defect detection and health scoring
- `repair_mesh(mesh_path, output_path)` — automated mesh repair pipeline
- `export_mesh(mesh_path, output_dir, formats)` — multi-format mesh export
- `create_design(request, config)` — Create mode infrastructure setup
- `validate_printability(mesh_path, config)` — FDM printability validation (4 checks)
- `start_session / submit_iteration / export_design` — session-based create pipeline (via print3d_skill.create)

## Code Style

- Python 3.10+: type hints, dataclasses for models, src layout
- `from __future__ import annotations` in all modules
- ruff for linting and formatting (line-length 99)

## Documentation Maintenance

When making changes, update the relevant docs:
- `README.md` — status, architecture, quick start
- `CLAUDE.md` — this file (technologies, structure, commands)
- `docs/vision.md` — Status section when features ship
- `docs/feature-chunking-strategy.md` — feature status
- `eval/README.md` — use case index

## Key Design Decisions

- Headless rendering via matplotlib mplot3d (Agg backend) — no GPU, no OpenGL
- YAML knowledge files with metadata/data sections, AND-filtered queries
- Lazy-detection tool registry with provider pattern
- Tiered dependencies: core (pip-only) vs extended (system packages)

## Completed Features

- F1: Core Infrastructure (rendering, tool orchestration, knowledge system, skill router)
- F2: Mesh Analysis & Repair (10 detectors, 6 repair strategies, health scoring, export)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

## Recent Changes
- 003-parametric-cad: Implementation complete — Create mode with session-based OpenSCAD compilation, 4-check FDM printability validation, BOSL2 detection, knowledge content
- 002-mesh-analysis-repair: Complete — mesh defect analysis, repair pipeline, knowledge content for Fix mode
