# Feature Specification: Core Infrastructure

**Feature Branch**: `001-core-infrastructure`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Build the foundational infrastructure that all five Print3D Skill modes depend on — rendering pipeline, tool orchestration layer, knowledge system, and skill router."

## Clarifications

### Session 2026-03-14

- Q: When a knowledge query specifies multiple context fields (mode + material + printer), should matching use AND, OR, or scoring? → A: AND with wildcards — all specified fields must match; unspecified fields match anything.
- Q: What is the minimum resolution for preview images to ensure AI agents can identify geometric features? → A: 1600x1200 pixels (2x2 grid, ~400x600 per view), targeting under 1MB file size.
- Q: When a mesh has millions of faces, should the system auto-decimate, refuse, or warn and attempt? → A: Warn and render — log a warning above a threshold, attempt rendering with a timeout, fail gracefully if too slow. No silent modification of the user's mesh.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Render Mesh Preview (Priority: P1)

An agent developer passes any supported mesh file (STL, 3MF, OBJ) to the rendering subsystem and receives back a multi-angle preview image showing the model from four viewpoints: front, side, top, and isometric. The preview is composited into a single image so the agent can visually inspect the model in one glance. This works on a headless server with no GPU or display server — the rendering pipeline produces the image entirely in software.

When an OpenSCAD source file is provided instead of a mesh, the system compiles it to a mesh first (if OpenSCAD CLI is installed) and then renders the preview. If OpenSCAD is not installed, the system reports that .scad rendering is unavailable and suggests installing OpenSCAD.

**Why this priority**: Visual verification is the foundation that all five modes depend on (Constitution Principle III). Without rendering, the agent cannot inspect its own work. Every geometry-transforming workflow in the project requires this capability before it can be specified or implemented.

**Independent Test**: Hand the rendering subsystem a known-good STL file and verify it produces a valid PNG image containing four distinct viewpoints. Confirm the same works on a headless machine with no display server.

**Acceptance Scenarios**:

1. **Given** a valid STL file, **When** the rendering subsystem is invoked, **Then** it produces a PNG image showing front, side, top, and isometric views of the model composited into a single image.
2. **Given** a valid 3MF file containing a colored mesh, **When** the rendering subsystem is invoked, **Then** it produces a preview that preserves the model's visual appearance.
3. **Given** a valid OpenSCAD .scad file and OpenSCAD CLI is installed, **When** the rendering subsystem is invoked, **Then** it compiles the .scad to a mesh and produces a multi-angle preview.
4. **Given** an OpenSCAD .scad file but OpenSCAD CLI is NOT installed, **When** the rendering subsystem is invoked, **Then** it returns a clear message stating that OpenSCAD is required for .scad files, without crashing.
5. **Given** a headless environment with no GPU or display server, **When** the rendering subsystem is invoked with a valid mesh, **Then** it produces the same preview image as on a machine with a display.
6. **Given** a mesh file with more than 1 million faces, **When** the rendering subsystem is invoked, **Then** it logs a warning about the high face count, attempts rendering with a timeout, and either produces the preview or returns a graceful timeout error recommending decimation — without silently modifying the mesh.

---

### User Story 2 - Discover and Use Tools (Priority: P2)

An agent developer requests a capability by name (e.g., "boolean operations," "mesh loading," "CAD compilation") and the tool orchestration layer returns the appropriate tool wrapper, ready to use. The developer does not need to know which specific external tool provides the capability — they just ask for what they need.

When an optional external tool is not installed, the orchestration layer reports exactly which capability is unavailable, what tool would provide it, and how to install it. The system continues functioning with whatever tools ARE available. Core capabilities (mesh loading, mesh analysis, basic rendering) always work because they depend only on pip-installable packages.

**Why this priority**: Tool orchestration is the interface between workflows and external tools. Without it, every workflow would need to handle dependency detection, error reporting, and fallbacks individually — duplicating logic across all five modes.

**Independent Test**: On a machine with only pip-installed packages (no OpenSCAD, no slicer), invoke the orchestration layer to list available capabilities. Verify that core capabilities are listed as available and extended capabilities are listed as unavailable with installation instructions.

**Acceptance Scenarios**:

1. **Given** a fresh installation with only pip dependencies, **When** the orchestration layer is queried for available capabilities, **Then** it lists core capabilities (mesh loading, mesh analysis, basic rendering) as available and extended capabilities (CAD compilation, slicing) as unavailable.
2. **Given** OpenSCAD is installed on the system, **When** the orchestration layer is queried for "CAD compilation," **Then** it returns a ready-to-use wrapper for the OpenSCAD CLI.
3. **Given** an agent developer requests "boolean operations," **When** the capability is available, **Then** the orchestration layer returns a tool wrapper without the developer needing to specify which boolean engine to use.
4. **Given** a requested capability is unavailable, **When** the orchestration layer is queried, **Then** it returns a structured response naming the missing tool, what it provides, and the installation command.

---

### User Story 3 - Query Domain Knowledge (Priority: P3)

An agent developer describes the current workflow context (which mode is active, what material is being used, what printer is targeted, what type of problem is being solved) and the knowledge system returns only the relevant domain knowledge — not the entire knowledge base. For example, when working on mesh repair for a model downloaded from Thingiverse, the system returns mesh defect patterns common in community downloads and repair strategies, but does not load material temperature tables or printer calibration tips.

The knowledge system ships with a small set of seed knowledge files that validate the format and demonstrate each knowledge type (tolerance table, material properties, decision tree, design rules). Subsequent features populate the knowledge base with real content.

**Why this priority**: Progressive disclosure of knowledge (Constitution Principle V) is critical for context window efficiency. This subsystem must exist before any mode can be implemented, because modes load their domain knowledge through it.

**Independent Test**: Create a set of test knowledge files spanning multiple topics and modes. Query for a specific context and verify the returned subset is relevant (contains matching files) and minimal (excludes unrelated files).

**Acceptance Scenarios**:

1. **Given** knowledge files tagged for "fix" mode and "create" mode, **When** the knowledge system is queried with mode="fix", **Then** only fix-mode knowledge files are returned.
2. **Given** knowledge files for PLA and PETG materials, **When** the knowledge system is queried with material="PETG", **Then** only PETG-relevant knowledge is returned.
3. **Given** knowledge files tagged for mode="fix" and material="PETG", plus files tagged for mode="fix" and material="PLA", **When** the knowledge system is queried with mode="fix" AND material="PETG", **Then** only files matching BOTH fields are returned (AND logic). Files tagged fix+PLA are excluded.
4. **Given** a query specifying only mode="fix" with no material or printer, **When** the knowledge system is queried, **Then** all fix-mode files are returned regardless of their material or printer tags (unspecified fields act as wildcards).
5. **Given** a query context that matches no knowledge files, **When** the knowledge system is queried, **Then** it returns an empty result set with a message indicating no matching knowledge was found.
6. **Given** the full knowledge base contains 50+ files, **When** a specific multi-field context query is made, **Then** the returned subset contains fewer than 20% of the total files.

---

### User Story 4 - Route User Intent to Mode (Priority: P4)

An end user describes their 3D printing need to an AI agent that has loaded the Print3D Skill. The skill definition provides clear routing instructions so the agent can determine which of the five modes (create, fix, modify, diagnose, validate) is appropriate. The skill's entry point accepts the selected mode and dispatches to the corresponding workflow handler.

For this foundational feature, the workflow handlers are stubs that acknowledge the mode selection and report "not yet implemented." The value is in correct routing — ensuring the infrastructure correctly dispatches to the right handler — not in the handlers themselves.

**Why this priority**: The skill router ties all subsystems together and defines the package's public interface. It is lower priority than the subsystems it coordinates because it is thin glue — the real work is in rendering, tools, and knowledge. However, it must exist so that subsequent mode features have a clear integration point.

**Independent Test**: Pass each of the five mode identifiers (create, fix, modify, diagnose, validate) to the skill entry point and verify each dispatches to the correct handler stub. Pass an unrecognized mode and verify it returns an appropriate error.

**Acceptance Scenarios**:

1. **Given** a mode of "fix," **When** the skill entry point is invoked, **Then** it dispatches to the fix workflow handler and returns its response.
2. **Given** a mode of "create," **When** the skill entry point is invoked, **Then** it dispatches to the create workflow handler and returns its response.
3. **Given** an unrecognized mode string, **When** the skill entry point is invoked, **Then** it returns an error listing the five valid modes.
4. **Given** a valid mode whose handler is a stub, **When** the skill entry point is invoked, **Then** the stub response includes the mode name and a "not yet implemented" indicator.

---

### Edge Cases

- What happens when a mesh file is corrupt, truncated, or contains no faces? The system MUST return a descriptive error rather than an unhandled exception.
- What happens when an STL file uses inches instead of millimeters? The system MUST detect and report the likely unit mismatch (based on bounding box heuristics) rather than silently producing a microscopic or enormous preview.
- What happens when an OpenSCAD source file has syntax errors? The system MUST capture and return the compiler's error output, not just a generic "compilation failed."
- What happens when NO external tools are installed (only pip packages)? The system MUST still provide all core capabilities and cleanly report which extended features are unavailable.
- What happens when the knowledge base directory is empty? The system MUST return an empty result set rather than failing.
- What happens when a mesh file is extremely large (millions of faces)? The rendering pipeline MUST warn about the high face count, attempt rendering with a timeout, and fail gracefully if the timeout is exceeded — recommending decimation. The system MUST NOT silently decimate the mesh.

## Requirements *(mandatory)*

### Functional Requirements

**Rendering Pipeline**

- **FR-001**: System MUST accept mesh files in STL, 3MF, and OBJ formats and produce a PNG preview image.
- **FR-002**: System MUST render four views (front, side, top, isometric) composited into a single output image.
- **FR-003**: System MUST produce renders in a headless environment with no GPU or display server.
- **FR-004**: System MUST accept OpenSCAD .scad source files and render them when the OpenSCAD CLI is available.
- **FR-005**: When OpenSCAD CLI is unavailable and a .scad file is provided, system MUST return a clear error indicating the missing dependency and installation instructions.
- **FR-006**: System MUST detect likely unit mismatches in mesh files (based on bounding box heuristics) and include a warning in the render output.
- **FR-007**: Preview images MUST be at least 1600x1200 pixels (2x2 grid of views, ~400x600 per view) and under 1MB file size, sufficient for an AI agent to distinguish geometric features, holes, surface details, and defects.
- **FR-007a**: For meshes exceeding 1 million faces, the rendering pipeline MUST log a warning, attempt rendering with a configurable timeout, and return a graceful error if the timeout is exceeded — recommending decimation. The system MUST NOT silently decimate or modify the input mesh.

**Tool Orchestration**

- **FR-008**: System MUST detect which external tools are available at startup and maintain a capability registry.
- **FR-009**: System MUST allow consumers to request capabilities by name (e.g., "boolean_operations") without specifying the underlying tool.
- **FR-010**: When a requested capability is unavailable, the system MUST return a structured error naming the missing tool, the capability it provides, and installation instructions.
- **FR-011**: System MUST continue operating with available capabilities when optional tools are missing — missing extended tools MUST NOT prevent core features from working.
- **FR-012**: System MUST provide a way to enumerate all known capabilities and their availability status.

**Knowledge System**

- **FR-013**: System MUST support structured knowledge files with defined schemas for: tolerance tables, material properties, decision trees, and design rules.
- **FR-014**: System MUST accept a query context (mode, material, printer, problem type) and return only matching knowledge files using AND logic — all specified fields must match. Unspecified fields act as wildcards (match anything).
- **FR-015**: System MUST load knowledge on-demand per query, not pre-load the entire knowledge base into memory.
- **FR-016**: System MUST ship with seed knowledge files (at least one per knowledge type) that validate the schema and demonstrate the format.
- **FR-017**: System MUST return an empty result set (not an error) when no knowledge matches a query.

**Skill Router & Package**

- **FR-018**: System MUST provide a single entry point that accepts a mode identifier and dispatches to the corresponding workflow handler.
- **FR-019**: System MUST support five mode identifiers: create, fix, modify, diagnose, validate.
- **FR-020**: Unimplemented workflow handlers MUST return a structured "not yet implemented" response that includes the mode name.
- **FR-021**: The package MUST be installable via pip with core features functional immediately, no system-level dependencies required.
- **FR-022**: Extended features MUST be installable via optional dependency groups (e.g., `pip install print3d-skill[openscad]`, `pip install print3d-skill[slicer]`).
- **FR-023**: System MUST provide a capability summary command that reports installed version, available capabilities, and missing optional dependencies.

### Key Entities

- **Mesh File**: A 3D model file with associated metadata — format (STL/3MF/OBJ), detected units, vertex count, face count, bounding box dimensions. The fundamental input to the rendering pipeline and most workflows.
- **Preview Image**: A composited PNG rendering of a mesh from multiple angles (1600x1200 minimum, under 1MB). Output of the rendering pipeline, consumed by the AI agent for visual inspection.
- **Tool Capability**: A named function the system can perform (e.g., "boolean_operations," "mesh_loading," "cad_compilation"). Capabilities map to one or more tool providers.
- **Tool Provider**: A wrapper around an external tool that implements one or more capabilities. Has an availability status (available, missing, error) and provides installation guidance when missing.
- **Knowledge File**: A structured data file containing domain knowledge, tagged with metadata (topic, applicable modes, applicable materials, applicable printers) for contextual filtering.
- **Knowledge Query**: A context descriptor specifying the active mode, material, printer, and problem type. Uses AND matching with wildcards — all specified fields must match, unspecified fields match anything. Used to filter the knowledge base and return only the relevant subset.
- **Workflow Mode**: One of five operating modes (create, fix, modify, diagnose, validate). Each mode has a handler that receives dispatches from the skill router.

### Assumptions

- Python 3.10+ is available on the target system.
- Users have internet access for initial pip installation.
- For .scad file rendering, OpenSCAD is installed separately via system package manager — this is an expected extended-tier dependency.
- The AI agent framework handles natural language understanding and intent classification; the skill router receives a mode identifier, not raw natural language text.
- Knowledge files are bundled with the package (not fetched from external sources at runtime).
- Preview images are written to the local filesystem (the agent framework handles presenting them to the user or agent).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can install the package and render a multi-angle preview of any valid STL/3MF/OBJ mesh file within 10 seconds of invocation, with no setup beyond `pip install`.
- **SC-002**: When an optional tool is missing, the system reports the missing capability, the tool name, and installation instructions within 1 second — without crashing or degrading core features.
- **SC-003**: Knowledge queries return fewer than 20% of the total knowledge base for any single-context query, demonstrating effective filtering rather than bulk loading.
- **SC-004**: All five mode identifiers correctly dispatch to their respective handlers, with zero routing errors for valid mode strings.
- **SC-005**: The package installs successfully and all core features are functional on a clean machine with only Python 3.10+ — no system-level packages required.
- **SC-006**: Preview images at 1600x1200 resolution are of sufficient quality that a human reviewer can identify the model's key geometric features (holes, edges, surface details) from the rendered image alone, with file size under 1MB.
