# Print3D Skill

An open-source AI agent skill that gives any LLM-powered coding assistant full-stack 3D printing capabilities — from natural language design intent to a finished print.

## What It Does

Print3D Skill is a portable Python library that any AI agent framework (Claude Code, Codex, Gemini) can use to:

- **Create** — Design parametric 3D models from natural language descriptions
- **Fix** — Diagnose and repair broken meshes from any source
- **Modify** — Resize, remix, and adapt existing models
- **Diagnose** — Analyze photos of failed prints and recommend fixes
- **Validate** — Review G-code and slicer settings before printing

## Install

```bash
pip install print3d-skill
```

Core features work immediately with zero system-level dependencies beyond Python 3.10+.

## Quick Start

```python
from print3d_skill import render_preview, system_info

# Check what's available
info = system_info()
print(f"v{info.package_version} — Core ready: {info.core_available}")

# Render a multi-angle preview of any mesh
result = render_preview("model.stl", "preview.png")
print(f"Preview: {result.image_path} ({result.render_time_seconds:.1f}s)")
```

```python
# Query domain knowledge by context
from print3d_skill import query_knowledge

results = query_knowledge(mode="create", material="PLA")
for kf in results:
    print(f"{kf.metadata.topic}: {kf.data['description']}")
```

```python
# Discover available tools
from print3d_skill import list_capabilities

for cap in list_capabilities():
    status = "available" if cap.is_available else "missing"
    print(f"  {cap.name}: {status}")
```

## Current Status

**Feature 1 (Core Infrastructure)** is complete. This provides:

| Subsystem | What It Does |
|-----------|-------------|
| Rendering pipeline | Headless multi-angle PNG previews (matplotlib, no GPU) for STL, 3MF, OBJ |
| Tool orchestration | Capability-based tool discovery with graceful degradation |
| Knowledge system | YAML domain knowledge with AND-filtered context queries |
| Skill router | Mode dispatch to five workflow handlers (currently stubs) |

### Roadmap

| Feature | Mode | Status |
|---------|------|--------|
| F1: Core Infrastructure | Foundation | **Complete** |
| F2: Mesh Analysis & Repair | Fix | Planned |
| F3: Parametric CAD | Create | Planned |
| F4: Model Modification | Modify | Planned |
| F5: G-code & Slicing | Validate | Planned |
| F6: Print Diagnosis | Diagnose | Planned |

See [docs/feature-chunking-strategy.md](docs/feature-chunking-strategy.md) for the full breakdown.

## Architecture

```
src/print3d_skill/
├── rendering/          # Headless multi-angle mesh preview (matplotlib Agg)
├── tools/              # Capability registry + providers (trimesh, manifold3d, OpenSCAD)
├── knowledge/          # YAML knowledge loader with context-filtered queries
├── knowledge_base/     # Bundled domain knowledge (tolerances, materials, decision trees)
├── modes/              # Workflow handlers (create, fix, modify, diagnose, validate)
├── models/             # Dataclasses (MeshFile, PreviewResult, ToolCapability, etc.)
├── router.py           # Mode dispatch
└── exceptions.py       # Exception hierarchy
```

## Dependencies

**Core** (pip-only, no system packages):
- `trimesh` — mesh loading, analysis, export
- `manifold3d` — boolean CSG operations
- `numpy`, `matplotlib`, `Pillow`, `PyYAML`

**Extended** (optional system packages):
- OpenSCAD — parametric CAD compilation (`brew install openscad`)
- PrusaSlicer/OrcaSlicer CLI — slicing (future)

## Development

```bash
git clone https://github.com/aje35/print3d-skill.git
cd print3d-skill
pip install -e ".[dev]"
pytest                      # 73 tests
ruff check src/ tests/      # Lint
```

### Project Structure

```
docs/                       # Vision, research, feature strategy
specs/                      # Feature specifications (spec-kit pipeline)
eval/                       # Real-world evaluation use cases with mesh assets
src/print3d_skill/          # Main package
tests/                      # pytest suite (unit, integration, contract)
```

### Spec-Kit Workflow

Every feature follows: `specify → clarify → plan → tasks → implement`. The [constitution](.specify/memory/constitution.md) defines seven non-negotiable principles that every feature must satisfy.

## Design Principles

1. **Open Tools Only** — All dependencies are open-source, OSI-licensed
2. **Agent-Portable** — Works across any LLM agent framework
3. **Visual Verification** — Agent renders and inspects its own work at every step
4. **Validate Before Print** — G-code is always reviewed before printing
5. **Progressive Disclosure** — Only relevant knowledge loaded per task
6. **Tiered Dependencies** — Core is pip-only; extended degrades gracefully
7. **Structured Tribal Knowledge** — Community wisdom encoded as queryable data

## License

MIT
