# Print3D Skill — Feature Chunking Strategy

**Created**: 2026-03-14
**Purpose**: Defines how the Print3D Skill vision decomposes into
a sequence of independently specifiable, plannable, and implementable
features using the spec-kit pipeline.

## Overview

Six features, ordered by dependency. Each passes through the full
spec-kit pipeline: `specify → clarify → plan → tasks → implement`.

```
F1  Core Infrastructure
 ├── F2  Mesh Analysis & Repair  (Fix mode)
 ├── F3  Parametric CAD          (Create mode)
 │    └── F4  Model Modification (Modify mode)
 ├── F5  G-code & Slicing        (Validate mode + slicer/printer)
 └── F6  Print Diagnosis         (Diagnose mode)

Parallel opportunities:
  F4 and F5 can be specified in parallel (independent domains)
```

---

## Feature 1: `core-infrastructure`

**Title**: Core Infrastructure

**Modes**: None directly — enables all five.

**Dependencies**: None (this is the foundation).

**Description for `/speckit.specify`**:

> Build the foundational infrastructure that all five Print3D Skill
> modes depend on. This feature covers four subsystems:
>
> (1) **Rendering pipeline** — A Python module that takes any mesh
> (STL, 3MF, OBJ via trimesh) or OpenSCAD source file and produces
> a multi-angle PNG preview image (front, side, top, and isometric
> views composited into a single image). The agent uses these previews
> to visually inspect its own work. Must work headless with no GPU
> requirement. Primary renderer is trimesh with pyrender/pyglet
> fallback; OpenSCAD CLI `--render --export` for .scad files.
>
> (2) **Tool orchestration layer** — Thin Python wrappers around
> external tools: OpenSCAD CLI (compile .scad → STL/PNG), trimesh
> (load/analyze/repair/export meshes), manifold3d (boolean CSG ops).
> Each wrapper handles dependency detection, reports when a tool is
> unavailable, and degrades gracefully per the Tiered Dependencies
> principle. A registry pattern so workflows can request capabilities
> ("I need boolean operations") without coupling to a specific tool.
>
> (3) **Knowledge system** — Architecture for loading structured
> domain knowledge (JSON/YAML files) on demand based on workflow
> context. Defines the schema for knowledge files (tolerance tables,
> material properties, decision trees, design rules). Implements a
> loader that accepts a query context (mode, material, printer,
> problem type) and returns only the relevant knowledge subset. No
> actual knowledge content yet — just the loading infrastructure and
> a few seed examples to validate the format.
>
> (4) **Skill router** — The top-level entry point that classifies
> user intent into one of the five modes (create, fix, modify,
> diagnose, validate) and dispatches to the appropriate workflow.
> Initially the workflows are stubs that return "not yet implemented"
> — the router just needs to correctly identify and route. Includes
> the package structure (src layout, pyproject.toml, tiered extras).
>
> The package must be pip-installable. Core features (rendering,
> mesh loading, knowledge lookup) must work with zero system-level
> dependencies beyond Python 3.10+. OpenSCAD and slicer CLIs are
> optional extended-tier dependencies.

**Granularity rationale**: These four subsystems are too small to
specify individually (a rendering pipeline alone isn't a shippable
feature), but together they form the platform that every subsequent
feature depends on. Specifying them together ensures their interfaces
are designed holistically — the renderer needs to work with the tool
orchestrator, which needs to feed the knowledge system context.
Splitting these into 3-4 separate features would create
specification churn as interfaces are negotiated across specs.

---

## Feature 2: `mesh-analysis-repair`

**Title**: Mesh Analysis & Repair

**Modes**: Fix

**Dependencies**: F1 (rendering pipeline, tool orchestration, knowledge
system)

**Description for `/speckit.specify`**:

> Implement the Fix mode: the ability to load a mesh from any common
> source, automatically diagnose geometry defects, apply repairs, and
> export a clean printable file — with visual verification at every
> step.
>
> **Mesh loading**: Accept STL, 3MF, OBJ, and PLY files. Detect
> units and scale (mm vs inches vs meters). Handle multi-body meshes
> (multiple shells in one file).
>
> **Automated analysis**: Detect and report these defect categories
> with severity (critical/warning/info): non-manifold edges, non-
> manifold vertices, boundary edges (holes), inverted normals, self-
> intersecting faces, degenerate triangles (zero-area, collinear),
> duplicate vertices/faces, excessive polygon count, and non-watertight
> shells. Produce a structured analysis report (not just text).
>
> **Repair strategies**: For each defect type, implement at least one
> repair approach: hole filling (fan triangulation for simple holes,
> planar fill for complex), normal reconciliation, vertex merging
> with configurable tolerance, degenerate face removal, mesh
> decimation for oversized meshes. Each repair step renders a
> before/after preview so the agent can verify the fix didn't
> introduce new problems.
>
> **Repair pipeline**: A composed pipeline that runs analysis →
> prioritized repairs → re-analysis → visual verification → export.
> The pipeline should be idempotent — running it on an already-clean
> mesh should produce no changes.
>
> **Knowledge content**: Populate the knowledge system with mesh
> repair decision trees (symptom → likely cause → repair strategy),
> slicer error message mappings (what "non-manifold" means in Bambu
> Studio vs PrusaSlicer vs Cura), and common defect patterns by
> source type (Thingiverse downloads, AI-generated meshes, 3D scans,
> CAD exports, terrain models).
>
> **Export**: Output repaired meshes as STL and 3MF. Include a
> repair summary (what was found, what was fixed, what couldn't be
> auto-repaired).

**Granularity rationale**: Fix mode is the most well-understood
pipeline in the project (evolved from the existing repair_topo_stl.py
prototype). It exercises the full infrastructure — tool wrappers,
rendering, knowledge system — without requiring CAD generation.
It's also high standalone value: many users just need mesh repair.
Splitting analysis and repair into separate features would be too
granular (you can't ship analysis without repair). Including CAD
generation here would make it too large and conflate two distinct
user intents.

---

## Feature 3: `parametric-cad`

**Title**: Parametric CAD Generation

**Modes**: Create

**Dependencies**: F1 (rendering pipeline, tool orchestration, knowledge
system)

**Description for `/speckit.specify`**:

> Implement the Create mode: generate printable 3D models from
> natural language descriptions by producing OpenSCAD code, rendering
> previews, and iterating until the design matches the user's intent.
>
> **OpenSCAD code generation**: The agent writes OpenSCAD .scad files
> that produce the requested geometry. Support BOSL2 library modules
> for common operations (rounded boxes, threads, gears, bezier
> curves, attachments). The generated code must be well-structured
> with named modules, parameterized dimensions, and comments
> explaining design choices.
>
> **Render-evaluate-iterate loop**: After generating OpenSCAD code,
> the skill compiles it via the OpenSCAD CLI, renders a multi-angle
> preview, and presents it to the agent for visual inspection. The
> agent evaluates whether the geometry matches the user's intent and
> either approves it or generates a revised .scad file. This loop
> continues until the agent is satisfied or the user approves.
>
> **Design-for-printability enforcement**: Before declaring a design
> complete, the skill checks it against FDM printability rules: minimum
> wall thickness for the nozzle size, overhang angles, bridging
> distances, support requirements, bed adhesion area. Warnings are
> surfaced to the user with specific suggestions (e.g., "this 0.3mm
> wall is below the 0.4mm nozzle minimum — increase to 0.8mm or
> switch to a 0.25mm nozzle").
>
> **Knowledge content**: Populate the knowledge system with tolerance
> tables (press-fit, snap-fit, screw clearance for PLA/PETG/ABS),
> minimum feature size tables by nozzle diameter, standard design
> patterns (screw bosses, snap clips, hinges, vent slots, cable
> routing), and BOSL2 module reference summaries.
>
> **Output**: Export the final model as STL and 3MF, alongside the
> .scad source file so users can further modify it in OpenSCAD.

**Granularity rationale**: Create mode is the flagship capability
and complex enough to warrant its own feature. It introduces a
fundamentally different pipeline from Fix (code generation +
compilation vs. mesh processing). Including Modify here would make
the spec too large — Create is "from scratch" design, Modify is
"alter existing geometry," and they have different user stories and
technical approaches. Splitting Create into "code generation" and
"design validation" sub-features would be too granular since they're
tightly coupled (you validate as you generate).

---

## Feature 4: `model-modification`

**Title**: Model Modification

**Modes**: Modify

**Dependencies**: F1 (rendering, tools, knowledge), F2 (mesh
analysis — needed to verify modifications don't break geometry),
F3 (OpenSCAD generation — some modifications produce .scad code)

**Description for `/speckit.specify`**:

> Implement the Modify mode: make targeted changes to existing 3D
> models without breaking what already works. Users hand the agent an
> existing mesh and describe changes in natural language.
>
> **Boolean operations**: Union (combine multiple STLs into one),
> difference (cut shapes out of a model — for engraving, holes,
> channels), and intersection. Use manifold3d as the primary boolean
> engine with trimesh as fallback. Handle non-manifold input by
> running Fix mode's repair pipeline before attempting booleans.
>
> **Scaling and resizing**: Uniform scaling (make it 20% bigger),
> non-uniform scaling (stretch Z-axis to 68%), and dimension-targeted
> scaling (make the width exactly 50mm). When scaling, detect features
> that should NOT scale (screw holes, mounting holes, thread
> dimensions) and warn the user.
>
> **Combining models**: Align and merge multiple STL files into a
> single printable model. Handle scale mismatches between source
> files. Provide alignment tools (center on axis, place on surface,
> offset by distance).
>
> **Text and logo engraving**: Extrude text from a font, position it
> on a surface of the existing model (flat or curved), and boolean-
> subtract to create engraved text. Support embossing (boolean-add)
> as well.
>
> **Splitting models**: Cut a model along a plane to split into
> multiple printable parts. Automatically add alignment features
> (pins, keys, dovetails) at the cut boundary so parts fit together
> after printing.
>
> **Visual comparison**: Every modification renders before/after
> previews from matching angles so the agent and user can see exactly
> what changed.
>
> **Knowledge content**: Populate the knowledge system with boolean
> operation best practices, text engraving depth/font guidelines for
> FDM, alignment pin tolerances, and splitting strategies.

**Granularity rationale**: Modify mode is distinct from both Create
(starts with existing geometry, not from scratch) and Fix (changes
are intentional, not defect repair). The operations here — booleans,
scaling, text, splitting — form a cohesive set of "alter existing
model" capabilities. Splitting them into individual features
(one for booleans, one for text) would be too granular since they
share the same workflow pattern: load → modify → verify → export.

---

## Feature 5: `gcode-validation-slicing`

**Title**: G-code Validation & Slicing

**Modes**: Validate (primary), plus slicer integration and printer
control that support all modes.

**Dependencies**: F1 (knowledge system, tool orchestration)

**Description for `/speckit.specify`**:

> Implement the Validate mode and the slicing/printing pipeline: the
> ability to parse G-code, validate slicer settings against material
> and printer profiles, slice models via CLI, and submit print jobs.
>
> **G-code parser**: Parse G-code files produced by PrusaSlicer, Bambu
> Studio, OrcaSlicer, and Cura. Extract: temperature commands (hotend,
> bed), speed settings, retraction parameters, layer heights, travel
> moves, estimated print time, estimated filament usage, fan speeds.
> Produce a structured analysis report.
>
> **Settings validation**: Cross-reference extracted G-code parameters
> against material profiles and printer capabilities. Flag: temperature
> mismatches (PETG temps in a PLA profile), speeds outside recommended
> ranges, retraction settings inappropriate for the material (e.g.,
> direct drive vs bowden), missing or incorrect first layer settings,
> unreasonable print time or material estimates. Validation produces
> a pass/warn/fail result with specific fix recommendations.
>
> **Slicer CLI integration**: Wrap PrusaSlicer CLI and OrcaSlicer CLI
> to slice STL/3MF models with specified profiles. Handle profile
> selection (printer + material + print quality), custom setting
> overrides, and output G-code generation. This is an extended-tier
> dependency — if no slicer CLI is installed, the skill can still
> validate externally-produced G-code.
>
> **Printer control** (extended tier): Submit G-code to printers via
> available APIs — Bambu Lab MQTT, OctoPrint REST, Moonraker/Klipper
> REST. Enumerate available printers, check printer status, start
> print jobs. Graceful degradation when no printer API is configured.
> The Validate Before You Print principle is enforced here: the skill
> MUST run validation before submitting any print job.
>
> **Knowledge content**: Populate the knowledge system with material
> profiles (temperature ranges, speed ranges, retraction settings for
> PLA, PETG, ABS, ASA, TPU, Nylon, composites), printer capability
> profiles (build volume, max temps, direct drive vs bowden, enclosed
> vs open), and slicer-specific setting mappings.

**Granularity rationale**: Validation and slicing are part of the
same "prepare for print" pipeline. A user who validates G-code often
wants to re-slice with corrected settings, and a user who slices
wants the output validated before printing. Splitting validation
from slicing would break this natural workflow. Printer control is
included because it's the final step in the same pipeline and is
relatively thin (API calls). Together they form the "right side" of
the pipeline (model → slice → validate → print) while Features 2-4
cover the "left side" (create/fix/modify the model).

---

## Feature 6: `print-diagnosis`

**Title**: Print Failure Diagnosis

**Modes**: Diagnose

**Dependencies**: F1 (knowledge system, rendering), F5 (material and
printer profiles for cross-referencing)

**Description for `/speckit.specify`**:

> Implement the Diagnose mode: analyze user-submitted photos of
> failed or defective 3D prints, identify the visible defects, cross-
> reference against print settings and material properties, and
> recommend specific actionable fixes.
>
> **Photo analysis**: Accept user-submitted photos of prints. The
> agent uses its vision capabilities to identify visible defects from
> these categories: stringing/oozing, layer shifts, warping/curling,
> under-extrusion, over-extrusion, bed adhesion failure, elephant
> foot, poor bridging, support scarring, layer separation/
> delamination, zits/blobs, ghosting/ringing. The agent describes
> what it sees and maps observations to defect categories.
>
> **Diagnostic cross-referencing**: Given the identified defects plus
> the user's context (printer model, material, slicer settings if
> available, model geometry if available), walk diagnostic decision
> trees to determine root cause. A single visible symptom (e.g.,
> stringing) may have multiple causes ranked by likelihood given the
> context (e.g., PETG + high travel speed → retraction settings are
> the most likely cause).
>
> **Actionable recommendations**: For each diagnosed cause, provide
> specific setting changes — not generic advice like "adjust
> retraction" but specific values like "change retraction distance to
> 0.8mm at 40mm/s for PETG on the P1S with its direct drive
> extruder." Recommendations are ordered by impact and ease of
> implementation. Distinguish between settings the user can change
> (slicer settings, print orientation) and environmental factors
> they can only mitigate (humidity, ambient temperature).
>
> **Knowledge content**: This feature is the heaviest consumer of
> the knowledge system. Populate with: defect identification guides
> (visual symptom → defect category mapping with example
> descriptions), diagnostic decision trees per defect type,
> printer-specific troubleshooting tips (community tribal knowledge
> from r/BambuLab, r/prusa3d, r/3Dprinting), material-specific
> failure modes and fixes, and calibration procedures.

**Granularity rationale**: Diagnose mode is last because it's the
most experimental (relies heavily on the agent's vision capabilities
and the quality of the knowledge base built up by Features 2-5) and
the most "nice to have" (users can diagnose manually, unlike mesh
repair or CAD generation which are hard without tools). It's also the
most knowledge-intensive — the diagnostic decision trees and tribal
knowledge compilation are substantial content work. It shouldn't be
split further because diagnosis without recommendations is useless,
and recommendations without diagnosis is guessing.

---

## Specification Order & Parallelism

```
Phase 1:  F1  core-infrastructure         (specify first, alone)
Phase 2:  F2  mesh-analysis-repair        (specify after F1)
Phase 3:  F3  parametric-cad              (specify after F1)
Phase 4:  F4  model-modification    ─┐
                                     ├─── specify in parallel
          F5  gcode-validation      ─┘
Phase 5:  F6  print-diagnosis             (specify last)
```

**Phase 1** must complete first — every other spec references the
infrastructure interfaces.

**Phase 2 before Phase 3**: Fix is simpler and exercises the full
infrastructure pipeline first. Lessons learned from specifying and
implementing Fix will inform how Create is specified (especially
around the rendering and verification patterns). However, they are
technically independent — if you want to move faster, F2 and F3
could be specified in parallel after F1 is implemented.

**Phase 4 parallel**: F4 (Modify) and F5 (Validate/Slice) operate
on completely different parts of the pipeline (mesh manipulation vs.
G-code analysis). Their specs have no overlap. Specify and implement
them in parallel.

**Phase 5** last: F6 (Diagnose) depends on the knowledge base being
substantially populated by all prior features and is the lowest
priority.

## Implementation Order vs. Specification Order

Specification can run ahead of implementation. A reasonable cadence:

| Week | Specify            | Implement          |
|------|--------------------|--------------------|
| 1    | F1                 | —                  |
| 2    | F2                 | F1                 |
| 3    | F3                 | F2                 |
| 4    | F4 + F5 (parallel) | F3                 |
| 5    | F6                 | F4 or F5           |
| 6    | —                  | F5 or F4           |
| 7    | —                  | F6                 |

This keeps specification ~1 step ahead of implementation, so specs
are ready when the prior feature finishes.
