# print3d-skill Development Guidelines

## Active Technologies

- Python 3.10+ (src layout, PEP 621)
- trimesh (mesh I/O, analysis, repair), manifold3d (boolean CSG), numpy, matplotlib (Agg), Pillow, PyYAML
- OpenSCAD CLI (extended tier, optional)

## Project Structure

```text
src/print3d_skill/          # Main package (src layout)
  rendering/                # Headless multi-angle mesh preview
  tools/                    # Capability registry + providers
  knowledge/                # YAML knowledge loader
  knowledge_base/           # Bundled YAML knowledge files (package data)
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

## Public API (7 functions)

- `render_preview(mesh_path, output_path)` — multi-angle PNG preview
- `get_capability(name)` — capability-based tool lookup
- `list_capabilities()` — all capabilities with availability
- `refresh_capabilities()` — re-detect tools
- `query_knowledge(mode, material, printer, problem_type)` — AND-filtered knowledge
- `route(mode)` — dispatch to mode handler
- `system_info()` — package capability summary

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

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

## Recent Changes
- 002-mesh-analysis-repair: Planning phase — mesh defect analysis, repair pipeline, knowledge content for Fix mode
