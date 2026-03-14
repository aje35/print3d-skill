# Research: Model Modification (004)

**Branch**: `004-model-modification` | **Date**: 2026-03-14

## R1: manifold3d Boolean API Integration

**Decision**: Use manifold3d as primary boolean engine with trimesh conversion wrappers.

**Rationale**: manifold3d>=3.0 is already a core dependency in pyproject.toml. The `ManifoldProvider` in `tools/manifold_tools.py` detects availability but provides no actual operation wrappers. The conversion path is: trimesh.Trimesh → manifold3d.Manifold (via vertices/faces arrays) → perform boolean → convert result back to trimesh.Trimesh. manifold3d handles non-manifold repair internally for many cases, but the spec requires pre-repair via F2 for transparency.

**Alternatives considered**:
- trimesh.boolean: Relies on external backends (manifold3d or blender). Less control over error handling. Used as fallback when manifold3d import fails.
- PyMeshLab: GPL license, heavier dependency. Rejected per Constitution I (prefer pip-installable core).

## R2: Primitive Tool Shape Generation

**Decision**: Generate primitives via `trimesh.creation` module (core tier, no OpenSCAD needed).

**Rationale**: trimesh provides `trimesh.creation.box()`, `trimesh.creation.cylinder()`, `trimesh.creation.icosphere()`, and `trimesh.creation.cone()`. These produce trimesh.Trimesh objects directly — no compilation step, no external tool. `box()` and `icosphere()` are already used extensively in test fixtures (conftest.py). This keeps primitive generation in the core tier (pip-only).

**Alternatives considered**:
- OpenSCAD primitives: Would make primitive generation extended tier. Rejected — cutting a hole shouldn't require OpenSCAD installed.
- numpy-based manual mesh construction: Too low-level; trimesh already provides this.

## R3: Text Geometry Generation

**Decision**: Use OpenSCAD `text()` + `linear_extrude()` for text geometry (extended tier). Gracefully degrade when OpenSCAD unavailable.

**Rationale**: No pure-Python library generates 3D text meshes from font files without significant complexity. OpenSCAD's `text()` module handles font rendering, kerning, and extrusion in a single call. The existing F3 compiler infrastructure already wraps the OpenSCAD CLI. Text engraving is the only Modify operation that requires OpenSCAD — all others (boolean, scale, combine, split) work at core tier.

**Alternatives considered**:
- Pillow text rasterization → heightmap → mesh: Complex pipeline, poor quality for small text, no vector precision.
- fonttools + shapely + triangle: Possible but requires 3 additional dependencies and significant geometry code.
- cadquery/build123d: Heavy dependencies, GPL-adjacent licensing concerns.

**Graceful degradation**: When OpenSCAD is not installed, text operations return an error with status="error" and a message explaining that text engraving requires OpenSCAD. All other Modify operations continue to work.

## R4: Mesh Splitting

**Decision**: Use `trimesh.intersections.slice_mesh_plane()` for plane-based splitting.

**Rationale**: trimesh provides `slice_mesh_plane(mesh, plane_normal, plane_origin)` which returns a trimesh.Trimesh containing only the geometry on one side of the plane. Call twice (or use the cap parameter) to get both halves. The function handles face splitting at the plane boundary and produces watertight results when the `cap` parameter is True. Not currently used in the codebase but is a stable trimesh API.

**Alternatives considered**:
- Manual vertex classification + face splitting: Reimplements what trimesh already does. Rejected.
- Boolean difference with a large box: Works but wasteful (creates and booleans a huge primitive). Less precise plane placement.

## R5: Feature Detection for Scaling Warnings

**Decision**: Heuristic circle-fitting on mesh boundary loops to detect standard screw holes.

**Rationale**: Standard metric screw holes (M2=2.2mm, M3=3.4mm, M4=4.5mm, M5=5.5mm, M6=6.6mm, M8=8.4mm, M10=10.5mm clearance holes per ISO 273) have well-known diameters. The detection approach: (1) identify boundary edge loops or through-holes in the mesh, (2) fit circles to the edge vertices, (3) compare fitted diameter against the standard screw size table with a tolerance band (±0.3mm). This is a heuristic that catches the most common case without ML.

**Alternatives considered**:
- ML-based feature recognition: Over-engineered for this use case. Would require training data, model dependency.
- No detection (just scale and let user figure it out): Spec requires warnings (FR-009). Rejected.

## R6: Curved Surface Text Engraving

**Decision**: Support flat surfaces for MVP. Curved surface engraving limited to simple analytic surfaces (cylinders, spheres) via projection.

**Rationale**: Flat surface text engraving is a boolean subtraction of extruded text from the model — straightforward. Curved surface engraving requires projecting text geometry onto the surface, which is complex for arbitrary meshes. For smooth analytic surfaces (cylinders, spheres), the text can be radially projected. Highly organic surfaces are documented as "may produce imperfect results" per spec Assumptions.

**Alternatives considered**:
- Full UV-unwrap based text placement: Requires UV parameterization of the mesh, which arbitrary STL files don't have.
- Skip curved surfaces entirely: Too limiting — cylindrical objects (cups, tubes) are common targets.

## R7: Tiered Dependency Mapping

**Decision**: All operations core tier except text engraving (extended tier, requires OpenSCAD).

| Operation | Tier | Dependencies |
|-----------|------|-------------|
| Boolean (union, diff, intersection) | Core | manifold3d, trimesh |
| Primitive generation | Core | trimesh.creation |
| Scaling (uniform, non-uniform, targeted) | Core | trimesh, numpy |
| Combining/alignment | Core | trimesh, numpy, manifold3d |
| Text engraving/embossing | Extended | OpenSCAD CLI, F3 compiler |
| Splitting | Core | trimesh.intersections |
| Visual comparison | Core | matplotlib, Pillow (F1 renderer) |
| Post-modification validation | Core | F2 analysis pipeline |

**Constitution VI compliance**: Core operations work with `pip install` only. Text engraving degrades gracefully when OpenSCAD is unavailable.

## R8: Before/After Rendering Architecture

**Decision**: Reuse F1 `render_preview()` with explicit `ViewAngle` objects for deterministic camera matching.

**Rationale**: The existing renderer uses `ViewAngle(name, elevation, azimuth)` dataclass with `ax.view_init(elev, azim)` in matplotlib. Rendering is fully deterministic — same mesh + same ViewAngle = same image. For before/after: render the original mesh with `STANDARD_VIEWS`, perform the modification, render the result with the same `STANDARD_VIEWS`. The camera angles are identical because they're defined as constants.

**No changes needed to the rendering system** — just call `render_preview()` twice with the same output parameters.
