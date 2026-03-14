# Research: Parametric CAD Generation

**Feature**: 003-parametric-cad
**Date**: 2026-03-14

## R1: OpenSCAD Code Generation Strategy

**Decision**: The skill generates OpenSCAD `.scad` source code as text. The
LLM agent writes the code; the skill provides compilation, rendering, and
validation infrastructure.

**Rationale**: OpenSCAD's declarative, text-based language is ideal for LLM
code generation. It's pure text, deterministic, and compiles to guaranteed
manifold meshes. The existing F1 infrastructure already has `_compile_scad()`
and `render_preview()` for `.scad` files.

**Alternatives considered**:
- CadQuery/Build123d (Python CAD): More powerful (fillets, NURBS) but
  heavier dependency (OCCT kernel ~300MB). Not pip-installable without
  system packages. Violates Principle VI (Tiered Dependencies) for core.
- SDF library: Interesting but niche, poor ecosystem, no BOSL2-equivalent.
- Direct mesh construction: No parametric source file for the user to modify.

## R2: BOSL2 Library Integration

**Decision**: Support BOSL2 as an optional enhancement. Detect availability
at runtime by attempting a test compile. Fall back to native OpenSCAD
primitives when unavailable.

**Rationale**: BOSL2 adds rounded boxes (`cuboid` with `rounding`), threads
(`threaded_rod`, `threaded_nut`), gears (`spur_gear2d`), bezier paths, and
the attachments system. These are essential for mechanical parts.

**Detection method**: Run `openscad -o /dev/null -e 'include <BOSL2/std.scad>;'`
and check exit code. Cache the result in the tool registry.

**BOSL2 include pattern**: `include <BOSL2/std.scad>` for the standard set,
plus specific includes for specialized modules (`BOSL2/threading.scad`,
`BOSL2/gears.scad`, etc.).

**Installation paths**:
- macOS: `~/.local/share/OpenSCAD/libraries/BOSL2/`
- Linux: `~/.local/share/OpenSCAD/libraries/BOSL2/`
- Windows: `Documents\OpenSCAD\libraries\BOSL2\`

**Alternatives considered**:
- Require BOSL2: Would violate graceful degradation principle.
- Bundle BOSL2: Licensing allows it (BSD), but adds ~10MB and versioning
  complexity. Better to use the user's installed version.

## R3: Render-Evaluate-Iterate Loop Design

**Decision**: The skill provides a `create_design()` function that:
1. Takes a `DesignRequest` (description + constraints)
2. Generates a `.scad` file (agent writes the code via the LLM)
3. Compiles via `_compile_scad()` → STL
4. Renders via `render_preview()` → multi-angle PNG
5. Returns a `GeneratedDesign` with compile status, mesh path, preview path
6. The agent inspects the preview and decides: approve or iterate
7. Loop until approved or max iterations reached

**Rationale**: The skill is infrastructure, not the intelligence. The agent
(LLM) interprets the description, writes code, and evaluates previews. The
skill handles the compile-render-export mechanical steps.

**Iteration protocol**:
- Each iteration produces a new `.scad` file (versioned: `design_v1.scad`,
  `design_v2.scad`, etc.)
- Compile errors are captured and returned to the agent for correction
- The agent can reference the previous version's code + error output
- Max iterations default: 5 (configurable via `CreateConfig`)

**Alternatives considered**:
- Single-shot (no iteration): Too fragile — first attempts rarely perfect.
- Autonomous iteration without agent: The skill can't evaluate visual
  correctness — that requires the LLM's vision capabilities.

## R4: Printability Validation Approach

**Decision**: Implement mesh-level printability checks using trimesh + numpy.
Four checks: wall thickness, overhang angle, bridge distance, bed adhesion.

**Wall thickness detection**:
- Use ray casting: for a sample of faces, shoot a ray inward (opposite the
  face normal) and measure distance to the nearest opposing face.
- trimesh's `ray.intersects_location()` provides this capability.
- Compare measured thickness against `min_wall_thickness` (default:
  `nozzle_diameter * 2 = 0.8mm` for 0.4mm nozzle).

**Overhang detection**:
- Compute angle between each face normal and the Z-up vector (build direction).
- Faces with angle > threshold (default: 45°) from vertical are overhangs.
- `angle = arccos(dot(face_normal, [0,0,1]))` — faces where this > 135°
  (pointing downward more than 45° from vertical) need support.

**Bridge detection**:
- Identify horizontal downward-facing faces (normal ≈ [0,0,-1]) that are
  not directly above other geometry within a threshold distance.
- Use ray casting downward from face centroids to detect unsupported spans.
- Default bridge threshold: 10mm.

**Bed adhesion estimation**:
- Find the minimum Z coordinate of the mesh.
- Select faces whose lowest vertex is within 0.1mm (one layer) of min Z.
- Sum the projected area of those faces onto the XY plane.
- Warn if total contact area < threshold (default: 100mm²).

**Alternatives considered**:
- Voxelization: More accurate for wall thickness but much slower.
  Ray casting is a good tradeoff for real-time validation.
- Slicer-based validation: Would require PrusaSlicer, violating core tier.
  Mesh-level checks work with trimesh only.

## R5: Code Structure Conventions for Generated OpenSCAD

**Decision**: Enforce a standard structure for all generated `.scad` files:

```openscad
// [Description of what this creates]
// Generated by Print3D Skill

// --- Parameters ---
wall_thickness = 2;    // mm - minimum printable wall
overall_width = 50;    // mm
overall_depth = 30;    // mm
overall_height = 20;   // mm

// --- BOSL2 (if available) ---
include <BOSL2/std.scad>

// --- Modules ---
module main_body() { ... }
module feature_name() { ... }

// --- Assembly ---
main_body();
```

**Rationale**: Named parameters (no magic numbers), modular structure, and
comments make the code useful to users who want to modify it. This satisfies
FR-002 and SC-003.

## R6: Export Pipeline

**Decision**: Reuse the existing `export_to_formats()` from F2. The Create
mode additionally exports the `.scad` source file alongside mesh files.

**Rationale**: F2's export infrastructure handles STL/3MF via trimesh.
Create mode just adds the `.scad` file copy. No new export code needed.

**Alternatives considered**:
- OpenSCAD direct 3MF export: OpenSCAD can export 3MF directly, but
  going through trimesh ensures the mesh passes our analysis pipeline
  (watertight check, defect detection) before export.
