# print3d-skill Development Guidelines

## Active Technologies

- Python 3.10+ (src layout, PEP 621)
- trimesh (mesh I/O, analysis, repair, ray casting for printability, primitives, splitting), manifold3d (boolean CSG), numpy, matplotlib (Agg), Pillow, PyYAML
- OpenSCAD CLI (extended tier, optional), BOSL2 library (optional)
- requests (extended tier, optional — OctoPrint/Moonraker printer control)
- paho-mqtt (extended tier, optional — Bambu Lab printer control)

## Project Structure

```text
src/print3d_skill/          # Main package (src layout)
  create/                   # Create mode: session, compiler, printability, BOSL2
  modify/                   # Modify mode: boolean, scale, combine, text, split
  validate/                 # Validate mode: G-code parser, validator, profiles
  slicing/                  # Slicer CLI integration (PrusaSlicer, OrcaSlicer)
  printing/                 # Printer control backends (OctoPrint, Moonraker, Bambu)
  diagnosis/                # Diagnose mode: decision trees, recommendations
  analysis/                 # Mesh defect detection
  repair/                   # Mesh repair pipeline
  export/                   # Format-specific mesh exporters
  rendering/                # Headless multi-angle mesh preview
  tools/                    # Capability registry + providers
  knowledge/                # YAML knowledge loader
  knowledge_base/           # Bundled YAML knowledge files (package data)
    create/                 # Create mode knowledge (tolerances, patterns, BOSL2)
    modify/                 # Modify mode knowledge (booleans, engraving, pins, splitting)
    validate/               # Validate mode knowledge (materials, printers, slicer mappings)
    diagnose/               # Diagnose mode knowledge (defect guides, decision trees, calibration)
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
pytest                      # Run tests (704 total, 689 passing, 15 skipped)
pytest --cov=print3d_skill  # Run tests with coverage
ruff check src/ tests/      # Lint
ruff format src/ tests/     # Format
```

## Public API (19 functions)

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
- `diagnose_print(defects, context)` — print failure diagnosis with decision trees
- `create_design(request, config)` — Create mode infrastructure setup
- `validate_printability(mesh_path, config)` — FDM printability validation (4 checks)
- `modify_mesh(mesh_path, operation, **params)` — standalone mesh modification (boolean, scale, combine, engrave, split)
- `start_session / submit_iteration / export_design` — session-based create pipeline (via print3d_skill.create)
- `parse_gcode(gcode_path)` — G-code parsing into structured GcodeAnalysis
- `validate_gcode(gcode_path, material, printer)` — G-code validation against profiles (pass/warn/fail)
- `slice_model(model_path, output_path, slicer, ...)` — slicer CLI integration (extended tier)
- `list_printers()` — discover configured printers and query status (extended tier)
- `submit_print(gcode_path, printer_name, material, ...)` — validate-then-print submission (extended tier)

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
- F3: Parametric CAD (OpenSCAD compilation, session-based create pipeline, BOSL2, printability)
- F4: Model Modification (boolean CSG, scaling with feature warnings, combining, text engraving, splitting with alignment pins, before/after comparison)
- F5: G-code Validation & Slicing (G-code parser for 4 slicers, settings validation, slicer CLI wrapping, printer control for OctoPrint/Moonraker/Bambu, 9 knowledge YAML files)
- F6: Print Diagnosis (12 defect categories, decision trees, severity-ranked recommendations, 9 knowledge YAML files)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

## Recent Changes
- 006-print-diagnosis: Implementation complete — Diagnose mode with 12 defect categories, diagnostic decision trees per defect type, severity enrichment, root cause analysis with context-aware tree walking, specific numeric recommendations sorted by severity/impact/ease, conflict detection, 9 knowledge YAML files (defect guides, 5 decision tree files, material failure modes, printer troubleshooting, calibration procedures)
- 005-gcode-validation-slicing: Implementation complete — Validate mode with G-code parser (PrusaSlicer, Bambu Studio, OrcaSlicer, Cura), settings validation against material/printer profiles (pass/warn/fail), slicer CLI wrapping (PrusaSlicer, OrcaSlicer), printer control backends (OctoPrint REST, Moonraker REST, Bambu MQTT), validate-before-print enforcement, 9 knowledge YAML files (7 materials + printer profiles + slicer mappings)
- 004-model-modification: Implementation complete — Modify mode with boolean CSG (manifold3d), uniform/non-uniform/targeted scaling, feature detection for screw holes, model combining with alignment, text engraving/embossing (OpenSCAD), plane-based splitting with alignment pins, before/after visual comparison, 4 knowledge YAML files
