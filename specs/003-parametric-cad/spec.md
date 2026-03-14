# Feature Specification: Parametric CAD Generation

**Feature Branch**: `003-parametric-cad`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Implement the Create mode: generate printable 3D models from natural language descriptions by producing OpenSCAD code, rendering previews, and iterating until the design matches the user's intent."

## Clarifications

### Session 2026-03-14

- Q: Should Create mode handle multi-part assemblies or only single-body parts? → A: Single-body parts only — multi-part assemblies are explicitly out of scope for this feature; documented as future capability.
- Q: When the description is too vague to produce meaningful geometry, what should the system do? → A: Prompt the user with clarifying questions (shape type, approximate size, intended use) before attempting generation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a 3D Model from a Description (Priority: P1)

A user describes a part they want in plain English — for example, "Make me a wall-mount bracket for a Raspberry Pi 4 with screw holes and ventilation slots." The skill generates parametric CAD code that produces the described geometry, compiles it into a mesh, and renders a multi-angle preview. The generated code is well-structured with named modules, parameterized dimensions, and comments explaining design choices so the user can further modify it.

**Why this priority**: This is the core Create mode capability — everything else builds on the ability to go from words to geometry. Without this, there is no Create mode.

**Independent Test**: Can be fully tested by providing natural language descriptions of varying complexity, generating CAD code, compiling it, and verifying the output mesh is valid geometry that visually matches the description.

**Acceptance Scenarios**:

1. **Given** a natural language description of a simple geometric part (e.g., "a box with rounded corners, 50mm x 30mm x 20mm"), **When** the user invokes Create mode, **Then** the skill produces CAD code that compiles without errors and renders a mesh matching the description.
2. **Given** a description referencing common mechanical features (screw holes, mounting tabs, snap clips), **When** the user invokes Create mode, **Then** the generated code uses appropriate parameterized modules for those features with standard dimensions.
3. **Given** a description with explicit dimensions (e.g., "80mm wide, 40mm deep"), **When** the user invokes Create mode, **Then** the generated code uses those exact dimensions as named parameters.
4. **Given** a description with no explicit dimensions (e.g., "a phone stand"), **When** the user invokes Create mode, **Then** the skill chooses reasonable default dimensions based on domain knowledge and documents them as parameters the user can adjust.
5. **Given** a description that references BOSL2 library capabilities (threads, gears, bezier curves), **When** the user invokes Create mode, **Then** the generated code uses BOSL2 modules rather than reimplementing the geometry from scratch.

---

### User Story 2 - Iterate on a Design via Visual Feedback (Priority: P2)

After the initial model is generated, the agent inspects the multi-angle preview and evaluates whether the geometry matches the user's intent. If the design needs changes — missing features, wrong proportions, structural issues — the agent generates a revised version of the CAD code and re-renders. This render-evaluate-iterate loop continues until the design is satisfactory.

**Why this priority**: One-shot generation rarely produces a perfect result. The iteration loop is what makes Create mode practical — it's the difference between "here's my first attempt" and "here's a design that actually works."

**Independent Test**: Can be fully tested by providing a description, generating an intentionally imperfect first version, and verifying the system can identify issues in the preview and produce an improved revision.

**Acceptance Scenarios**:

1. **Given** a generated model with a visible issue (e.g., missing feature from the description), **When** the agent evaluates the preview, **Then** it identifies the gap and generates a revised CAD file that includes the missing feature.
2. **Given** a generated model that compiles with errors, **When** the compile step fails, **Then** the skill captures the error output and generates a corrected CAD file that addresses the specific compile error.
3. **Given** an iteration loop, **When** the agent determines the design matches the user's intent, **Then** the loop terminates and the design proceeds to validation.
4. **Given** an iteration loop that has not converged, **When** a maximum iteration count is reached, **Then** the skill presents the best version so far and asks the user for direction rather than looping indefinitely.
5. **Given** user feedback on a rendered preview (e.g., "make the walls thicker"), **When** the agent receives the feedback, **Then** it generates a targeted revision modifying only the relevant parameters without rewriting the entire design.

---

### User Story 3 - Validate Design for Printability (Priority: P3)

Before declaring a design complete, the skill checks it against FDM printability rules: minimum wall thickness for the nozzle size, overhang angles, bridging distances, support requirements, and bed adhesion area. Warnings are surfaced to the user with specific, actionable suggestions — not generic advice, but precise recommendations like "this 0.3mm wall is below the 0.4mm nozzle minimum — increase to 0.8mm or switch to a 0.25mm nozzle."

**Why this priority**: A model that looks correct but can't be printed is a wasted effort. Printability validation is the gate between "nice design" and "printable part." It depends on US1 (having a model to validate) and benefits from US2 (ability to iterate on issues found).

**Independent Test**: Can be fully tested by generating models with known printability issues (thin walls, steep overhangs, unsupported features) and verifying the system flags each issue with the correct rule violation and actionable suggestion.

**Acceptance Scenarios**:

1. **Given** a model with walls thinner than the minimum for a 0.4mm nozzle, **When** printability validation runs, **Then** the system warns about the specific thin walls and suggests a minimum thickness.
2. **Given** a model with overhangs exceeding 45 degrees without support, **When** printability validation runs, **Then** the system identifies the overhang regions and recommends adding supports or redesigning the angle.
3. **Given** a model with bridging distances beyond typical FDM capability, **When** printability validation runs, **Then** the system flags the bridges and suggests reducing span or adding intermediate supports.
4. **Given** a model that passes all printability checks, **When** validation runs, **Then** the system confirms the design is print-ready for the specified material and nozzle size.
5. **Given** a model with printability warnings, **When** the user chooses to proceed anyway, **Then** the system allows export with the warnings documented in the output.

---

### User Story 4 - Export Final Design (Priority: P4)

Once the design is approved (by the agent and/or user), the skill exports the final model as STL and 3MF mesh files alongside the original CAD source file. The user receives all three artifacts: the mesh files for slicing/printing and the source file for future modifications in a CAD tool.

**Why this priority**: Export is the delivery mechanism — without it the user can't print. It's straightforward but depends on US1-US3 being complete.

**Independent Test**: Can be fully tested by generating a complete design and verifying all three output files (STL, 3MF, source CAD) are produced, valid, and represent the same geometry.

**Acceptance Scenarios**:

1. **Given** an approved design, **When** the user requests export, **Then** the system produces STL (binary), 3MF, and the source CAD file.
2. **Given** an exported STL, **When** loaded by an external tool, **Then** the mesh is watertight and manifold with no defects.
3. **Given** the exported CAD source file, **When** opened in the CAD tool, **Then** it compiles to the same geometry as the exported meshes.
4. **Given** an export request with a custom output directory, **When** the export runs, **Then** all files are written to the specified directory with clear filenames.

---

### User Story 5 - Create Mode Knowledge & Design Patterns (Priority: P5)

The knowledge system is populated with CAD-relevant domain knowledge: tolerance tables (press-fit, snap-fit, screw clearance for PLA/PETG/ABS by nozzle size), minimum feature size tables by nozzle diameter, standard mechanical design patterns (screw bosses, snap clips, living hinges, vent slots, cable routing channels), and reference summaries for common BOSL2 library modules.

**Why this priority**: Knowledge content makes the agent smarter about what it generates, but the core generation pipeline works without it. Knowledge can be populated incrementally.

**Independent Test**: Can be fully tested by querying the knowledge system with Create mode context and verifying relevant tolerance tables, design patterns, and module references are returned.

**Acceptance Scenarios**:

1. **Given** a query for tolerance data for PLA press-fit joints, **When** the knowledge system is queried, **Then** it returns specific clearance values by nozzle diameter.
2. **Given** a query for minimum feature sizes with a 0.4mm nozzle, **When** the knowledge system is queried, **Then** it returns minimum wall thickness, minimum hole diameter, and minimum gap width.
3. **Given** a query for standard design patterns for screw bosses, **When** the knowledge system is queried, **Then** it returns recommended dimensions, draft angles, and boss-to-wall ratios.
4. **Given** a query about BOSL2 modules for threads, **When** the knowledge system is queried, **Then** it returns module names, key parameters, and usage examples.

---

### Edge Cases

- What happens when the natural language description is too vague to produce geometry (e.g., "make something cool")?
- What happens when the description requests geometry that is physically impossible to print (e.g., "a fully enclosed hollow sphere with no openings")?
- What happens when the CAD code compiles but produces empty geometry (zero volume)?
- What happens when the BOSL2 library is not installed and the description requires BOSL2 features?
- What happens when the user specifies conflicting dimensions (e.g., "10mm hole in a 5mm wall")?
- What happens when the iteration loop cannot resolve a compile error after multiple attempts?
- What happens when the description references a specific real-world object the skill has no dimensional data for?
- What happens when printability validation conflicts with the user's explicit design intent (e.g., intentionally thin decorative features)?

## Requirements *(mandatory)*

### Functional Requirements

**CAD Code Generation**:

- **FR-001**: System MUST generate CAD source code that produces the geometry described in a natural language prompt.
- **FR-002**: Generated code MUST be well-structured with named modules, parameterized dimensions (no magic numbers), and comments explaining design choices.
- **FR-003**: System MUST support BOSL2 library modules for common operations: rounded boxes, threads, gears, bezier curves, and attachments.
- **FR-004**: When the user provides explicit dimensions, the generated code MUST use those exact values as named parameters.
- **FR-005**: When the user omits dimensions, the system MUST choose reasonable defaults based on domain knowledge and document them as adjustable parameters.
- **FR-006**: System MUST detect when BOSL2 is not available and either fall back to native primitives or report the limitation with install instructions.
- **FR-006a**: Create mode is scoped to single-body parts only. Multi-part assemblies are out of scope. If the description implies multiple separate parts (e.g., "a box with a separate lid"), the system MUST generate a single unified body or inform the user that the request requires multiple Create invocations.
- **FR-006b**: When the description is too vague to produce meaningful geometry (lacks shape, size, or purpose), the system MUST prompt the user with clarifying questions (e.g., shape type, approximate dimensions, intended use) before attempting code generation.

**Render-Evaluate-Iterate Loop**:

- **FR-007**: After generating CAD code, the system MUST compile it to produce a mesh and render a multi-angle preview for visual inspection.
- **FR-008**: If compilation fails, the system MUST capture error output and generate a corrected revision that addresses the specific error.
- **FR-009**: The agent MUST evaluate each rendered preview against the user's original description to identify missing features, wrong proportions, or structural issues.
- **FR-010**: When issues are identified, the system MUST generate a targeted revision modifying only the relevant code sections rather than rewriting from scratch.
- **FR-011**: The iteration loop MUST terminate after a configurable maximum number of iterations (default: 5) and present the best version achieved.
- **FR-012**: The system MUST accept user feedback on a rendered preview and incorporate it into the next revision.

**Design-for-Printability Validation**:

- **FR-013**: System MUST check minimum wall thickness against the configured nozzle diameter and warn when walls are too thin.
- **FR-014**: System MUST identify overhang regions exceeding 45 degrees and recommend supports or redesign.
- **FR-015**: System MUST detect bridging spans beyond typical FDM capability (default threshold: 10mm) and suggest alternatives.
- **FR-016**: System MUST estimate bed adhesion area and warn if it is insufficient for stable printing.
- **FR-017**: Printability warnings MUST include specific, actionable suggestions referencing actual dimensions and thresholds — not generic advice.
- **FR-018**: Users MUST be able to acknowledge warnings and proceed with export despite printability issues.

**Export**:

- **FR-019**: System MUST export the final model as binary STL.
- **FR-020**: System MUST export the final model as 3MF.
- **FR-021**: System MUST include the original CAD source file alongside mesh exports.
- **FR-022**: Exported meshes MUST be watertight and manifold (valid for slicing).

**Knowledge Content**:

- **FR-023**: Knowledge system MUST contain tolerance tables for press-fit, snap-fit, and screw clearance organized by material (PLA, PETG, ABS) and nozzle diameter.
- **FR-024**: Knowledge system MUST contain minimum feature size tables (wall thickness, hole diameter, gap width) by nozzle diameter.
- **FR-025**: Knowledge system MUST contain standard mechanical design patterns: screw bosses, snap clips, living hinges, vent slots, and cable routing channels with recommended dimensions.
- **FR-026**: Knowledge system MUST contain BOSL2 module reference summaries with key parameters and usage examples.

### Key Entities

- **DesignRequest**: The user's input to Create mode. Contains the natural language description, optional explicit dimensions, target material, nozzle diameter, and any constraints (max build volume, orientation preferences).
- **GeneratedDesign**: A single iteration of the CAD code. Contains the source code text, compile status (success/error), error messages (if any), iteration number, and the changes made from the previous iteration.
- **PrintabilityReport**: The result of validating a compiled design against FDM printability rules. Contains a list of warnings (each with rule violated, measured value, threshold, and actionable suggestion) and an overall pass/warn status.
- **DesignExport**: The final output bundle. Contains paths to the STL file, 3MF file, and source CAD file, plus the final PrintabilityReport and total iteration count.

## Assumptions

- The existing F1 rendering pipeline handles .scad compilation and multi-angle preview rendering (F1 already includes `_compile_scad()` and the preview compositor).
- The existing F1 tool orchestration provides OpenSCAD availability detection; this feature uses it to check for BOSL2 availability as well.
- The agent (LLM) is responsible for interpreting the natural language description and writing the CAD code. The skill provides the compilation, rendering, validation, and export infrastructure — not the code-generation intelligence itself.
- BOSL2 is the preferred library for complex geometry but is optional. The system degrades gracefully to native OpenSCAD primitives when BOSL2 is unavailable.
- The default iteration limit of 5 is sufficient for most designs. Complex designs may need more iterations, but the user can always provide feedback and trigger additional rounds.
- Printability validation operates on the compiled mesh geometry, not the source code. Checks like wall thickness and overhang analysis require mesh-level inspection.
- The maximum bridge distance threshold (10mm) and overhang angle (45 degrees) are reasonable FDM defaults that can be overridden via configuration for specific printers/materials.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The system generates compilable CAD code (zero compile errors) on the first attempt for at least 80% of simple geometry descriptions (single-feature parts with explicit dimensions).
- **SC-002**: The render-evaluate-iterate loop converges to an agent-approved design within the default iteration limit (5) for at least 70% of descriptions.
- **SC-003**: Generated CAD code is parameterized — all dimensions are named variables, not inline constants — in 100% of outputs.
- **SC-004**: Printability validation detects 100% of planted violations in the test suite (thin walls, steep overhangs, long bridges).
- **SC-005**: Printability warnings include actionable suggestions with specific numeric thresholds in 100% of flagged issues.
- **SC-006**: Exported meshes pass watertightness and manifold checks in 100% of successful exports.
- **SC-007**: Full Create pipeline (describe → generate → iterate → validate → export) completes in under 2 minutes for simple parts.
- **SC-008**: Knowledge queries for Create mode return relevant tolerance tables and design patterns for all documented material/nozzle combinations.
