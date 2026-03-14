# Research: Core Infrastructure

**Feature**: 001-core-infrastructure
**Date**: 2026-03-14

## Decision 1: Headless 3D Rendering Engine

**Decision**: matplotlib mplot3d with Agg backend for core tier.

**Rationale**: The only approach that satisfies the zero-system-dependency
constraint. matplotlib's Agg backend is a pure software rasterizer —
it needs no GPU, no OpenGL, no display server, no EGL/osmesa system
libraries. It is fully pip-installable.

The rendering pipeline:
1. Load mesh with trimesh (vertices, faces, face normals)
2. Compute face colors from normals for basic diffuse shading
3. Create matplotlib figure with 2x2 subplot grid (1600x1200)
4. For each view (front, side, top, isometric), create a Poly3DCollection
   with appropriate camera angle (elevation, azimuth)
5. Save via Agg backend to PNG

View angles:
- Front: elevation=0, azimuth=0
- Right side: elevation=0, azimuth=90
- Top: elevation=90, azimuth=0
- Isometric: elevation=35, azimuth=45

**Alternatives considered**:

| Option | Why rejected |
|--------|-------------|
| pyrender | Requires OpenGL. Offscreen mode needs EGL (libegl1-mesa-dev) or osmesa (libosmesa6-dev) — system-level dependencies that violate Tiered Dependencies principle for core tier. |
| trimesh Scene.save_image() | Delegates to pyrender internally. Same OpenGL dependency. |
| pyvista offscreen | Requires VTK + osmesa. Heavy system dependencies (~500MB). |
| Blender headless | Highest quality but requires full Blender installation (~200MB system package). Extended tier only. |
| vedo | Built on VTK. Same osmesa requirement as pyvista. |

**Known limitations**:
- matplotlib mplot3d uses the painter's algorithm for depth sorting,
  which can produce visual artifacts (faces rendered in wrong order)
  on complex meshes with many overlapping faces.
- No true lighting/shadow model — only face-normal-based coloring.
- Rendering meshes with >100K faces is slow (~5-10s). Meshes with
  >1M faces may exceed the 10s target, triggering the timeout.

These limitations are acceptable because:
- The previews are for AI agent inspection, not user-facing display.
- Geometric features (holes, edges, wall thickness) are identifiable
  even with painter's algorithm artifacts.
- The timeout mechanism (FR-007a) handles the large mesh case.

**Future enhancement path**: Two upgrade options for better rendering:
1. pyrender as extended-tier (`pip install print3d-skill[render-hq]`)
   for OpenGL-based rendering on machines with EGL/osmesa.
2. Custom numpy + Pillow z-buffer renderer as a core-tier upgrade
   that replaces matplotlib — proper depth sorting without the
   painter's algorithm artifacts. This would still be pure Python /
   pip-only but with correct occlusion. Worth evaluating if
   matplotlib quality proves insufficient during implementation.

Both are out of scope for this feature. matplotlib is the pragmatic
starting point — if AI agents struggle to interpret the previews,
we upgrade the renderer without changing the public API.

## Decision 2: Knowledge File Format

**Decision**: YAML files with top-level `metadata` and `data` sections.

**Rationale**: YAML is human-readable, supports comments, and is
already a transitive dependency (PyYAML is pulled in by trimesh).
The two-section structure cleanly separates filterable metadata from
knowledge content.

**File format**:

```yaml
metadata:
  type: tolerance_table          # One of: tolerance_table, material_properties,
                                 #         decision_tree, design_rules
  topic: press_fit_clearances    # Free-text topic identifier
  modes: [create, modify]        # Which workflow modes use this knowledge
  materials: [PLA, PETG, ABS]    # Which materials this applies to (empty = all)
  printers: []                   # Which printers this applies to (empty = all)
  version: "1.0"                 # Schema version for future migration

data:
  # Content structure varies by type — schema enforced per type
  description: "Clearance values for press-fit joints by material"
  entries:
    - joint_type: press_fit
      material: PLA
      clearance_mm: 0.1
      notes: "PLA shrinks 0.3-0.5%"
```

**Query matching algorithm**:
- Load `metadata` section from each YAML file in knowledge_base/
- For each query field (mode, material, printer, problem_type):
  - If query field is None/empty → wildcard (matches everything)
  - If query field is set → file's metadata field must contain the
    query value (list membership check) OR be empty (empty = "applies
    to all")
- All specified fields must match (AND logic)
- Return the `data` section of matching files

**Alternatives considered**:

| Option | Why rejected |
|--------|-------------|
| JSON | No comments, less readable for hand-authored knowledge files. JSON would be fine for machine-generated data but knowledge files are authored by humans. |
| TOML | Less common for data files, awkward for nested lists/tables. Better suited for configuration. |
| SQLite | Overkill for ~50-100 files. Adds complexity without benefit at this scale. Would reconsider if knowledge base grows to 1000+ files. |
| Markdown with YAML frontmatter | Frontmatter is a convention (not native YAML). Would require a separate parser. The knowledge content is structured data, not prose. |

## Decision 3: Package Build System

**Decision**: setuptools with pyproject.toml (PEP 621).

**Rationale**: setuptools is included with Python — no additional
build dependency. pyproject.toml is the modern standard (PEP 621)
for declaring metadata. This gives maximum compatibility with pip,
build, and other tools.

**Alternatives considered**:

| Option | Why rejected |
|--------|-------------|
| hatchling | Requires installing hatch as build dependency. Adds friction for contributors. |
| flit | Limited to pure Python. We may need C extension build support for future features. |
| poetry | Opinionated, non-standard lock file format. Adds friction. |
| meson-python | Overkill for a pure Python package. |

**pyproject.toml structure**:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "print3d-skill"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "trimesh>=4.0",
    "manifold3d>=3.0",
    "numpy>=1.24",
    "matplotlib>=3.7",
    "Pillow>=10.0",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
openscad = []    # Marker — system OpenSCAD detected at runtime
slicer = []      # Marker — system PrusaSlicer detected at runtime
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.5",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"print3d_skill.knowledge_base" = ["*.yaml"]
```

## Decision 4: Tool Registry Pattern

**Decision**: Lazy-detection capability registry with provider
interface.

**Rationale**: Tools should be detected on first use (not at import
time) to keep package import fast. Each tool provider implements a
standard interface with `detect()`, `capabilities()`, and
`is_available()` methods.

**Design**:
- `ToolProvider` base class with abstract `detect()` method
- `ToolRegistry` singleton that holds registered providers
- Providers self-register their capabilities at import time
- Availability check (detect) runs lazily on first query
- Detection result cached; can be refreshed via `registry.refresh()`
- `registry.get("boolean_operations")` returns the provider or
  raises `CapabilityUnavailable` with install instructions

**Known capabilities for this feature**:

| Capability | Provider | Tier | Detection |
|------------|----------|------|-----------|
| mesh_loading | TrimeshProvider | Core | `import trimesh` |
| mesh_analysis | TrimeshProvider | Core | `import trimesh` |
| boolean_operations | ManifoldProvider | Core | `import manifold3d` |
| rendering | MatplotlibRenderer | Core | `import matplotlib` |
| cad_compilation | OpenSCADProvider | Extended | `shutil.which("openscad")` |
| cad_rendering | OpenSCADProvider | Extended | `shutil.which("openscad")` |

## Decision 5: Unit Mismatch Detection Heuristic

**Decision**: Bounding-box-based heuristic comparing dimensions
against expected FDM print ranges.

**Algorithm**:
- Compute mesh bounding box dimensions (x, y, z) in file units
- If max dimension < 0.5 → likely meters, suggest ×1000 scale
- If max dimension > 2000 → likely microns or invalid, warn
- If max dimension between 0.5 and 2000 → likely millimeters (OK)
- Special case: if dimensions suggest inches (25.4× factor from
  common sizes like 1", 2", 6"), flag as possible inch model

This is a heuristic with known false positives for legitimately
very small or very large models. The warning is informational only —
the system does not auto-scale.

## Decision 6: OpenSCAD .scad File Handling

**Decision**: Two-step pipeline — compile .scad → STL, then render
STL via matplotlib.

**Rationale**: This keeps the rendering pipeline uniform (all meshes
go through matplotlib). The intermediate STL is also useful as an
artifact for downstream workflows.

**Alternative**: Use `openscad --export=png` for direct image output.
Rejected because: (a) produces only one view angle per invocation,
(b) camera parameters are inconsistent with our multi-angle layout,
(c) we lose the mesh artifact.
