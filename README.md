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
# Modify an existing mesh: cut a hole, scale, split
from print3d_skill import modify_mesh

# Boolean difference: cut a 6mm hole through a bracket
result = modify_mesh(
    "bracket.stl", operation="boolean",
    boolean_type="difference",
    primitive_type="cylinder",
    primitive_dimensions={"diameter": 6.0, "height": 30.0},
    primitive_position=(15.0, 10.0, 0.0),
)
print(result.output_mesh_paths[0])  # "bracket_modified.stl"

# Scale to a specific width
result = modify_mesh("part.stl", operation="scale",
                     scale_mode="dimension_target",
                     target_axis="x", target_value_mm=80.0)

# Split a tall model for multi-part printing
result = modify_mesh("vase.stl", operation="split",
                     split_axis="z", split_offset_mm=100.0)
print(result.output_mesh_paths)  # ["vase_bottom.stl", "vase_top.stl"]
```

```python
# Parse and validate G-code before printing
from print3d_skill import parse_gcode, validate_gcode

analysis = parse_gcode("model.gcode")
print(f"Slicer: {analysis.slicer}, Layers: {analysis.layer_count}")

result = validate_gcode("model.gcode", material="PLA")
print(f"Validation: {result.status.value}")
for rec in result.recommendations:
    print(f"  - {rec}")
```

```python
# Diagnose a failed print and get specific fix recommendations
from print3d_skill import diagnose_print
from print3d_skill.diagnosis.models import (
    DiagnosticContext, PrintDefect, PrintDefectCategory,
)

defects = [PrintDefect(
    category=PrintDefectCategory.stringing,
    description="Thin strings between travel moves",
    confidence="high",
)]
context = DiagnosticContext(printer_model="Bambu Lab P1S", material="PETG")
result = diagnose_print(defects, context)

for rec in result.recommendations:
    print(f"  {rec.setting}: {rec.suggested_value} ({rec.impact} impact)")
```

```python
# Discover available tools
from print3d_skill import list_capabilities

for cap in list_capabilities():
    status = "available" if cap.is_available else "missing"
    print(f"  {cap.name}: {status}")
```

## Current Status

All six features are complete, covering the full create/fix/modify/diagnose/validate pipeline:

### Roadmap

| Feature | Mode | Status |
|---------|------|--------|
| F1: Core Infrastructure | Foundation | **Complete** |
| F2: Mesh Analysis & Repair | Fix | **Complete** |
| F3: Parametric CAD | Create | **Complete** |
| F4: Model Modification | Modify | **Complete** |
| F5: G-code & Slicing | Validate | **Complete** |
| F6: Print Diagnosis | Diagnose | **Complete** |

See [docs/feature-chunking-strategy.md](docs/feature-chunking-strategy.md) for the full breakdown.

## Architecture

```
src/print3d_skill/
├── create/             # Create mode: parametric CAD via OpenSCAD
├── modify/             # Modify mode: boolean, scale, combine, text, split
├── validate/           # Validate mode: G-code parser, validation engine, profiles
├── slicing/            # Slicer CLI integration (PrusaSlicer, OrcaSlicer)
├── printing/           # Printer control (OctoPrint, Moonraker, Bambu Lab)
├── diagnosis/          # Diagnose mode: decision trees, root causes, recommendations
├── analysis/           # Mesh defect detection (10 detectors)
├── repair/             # Mesh repair pipeline (6 strategies)
├── export/             # Format-specific mesh exporters
├── rendering/          # Headless multi-angle mesh preview (matplotlib Agg)
├── tools/              # Capability registry + providers
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
- PrusaSlicer/OrcaSlicer CLI — G-code slicing
- `requests` — OctoPrint/Moonraker printer control (`pip install requests`)
- `paho-mqtt` — Bambu Lab printer control (`pip install paho-mqtt`)

## Development

```bash
git clone https://github.com/aje35/print3d-skill.git
cd print3d-skill
pip install -e ".[dev]"
pytest                      # Run all tests
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
