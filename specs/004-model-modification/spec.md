# Feature Specification: Model Modification

**Feature Branch**: `004-model-modification`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Implement the Modify mode: make targeted changes to existing 3D models — boolean operations, scaling/resizing, combining models, text/logo engraving, splitting for print, and visual before/after comparison."

## Clarifications

### Session 2026-03-14

- Q: Should the system generate primitive tool shapes (cylinder, box, sphere, cone) for boolean operations, or must the user always provide a second mesh file? → A: System generates primitive tool shapes from user-specified parameters (dimensions, position, orientation). No second mesh file required for common operations like cutting holes.
- Q: Should Modify mode support chaining multiple operations in a session, or is each operation standalone? → A: Standalone operations — each call takes an input mesh and produces an output mesh. The agent chains operations by passing the output path of one operation as the input to the next. No session model needed.
- Q: Should modifications always write a new output file (preserving the original), or support overwriting? → A: Always write a new output file; the original is never modified.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Boolean Operations on Existing Models (Priority: P1)

A user has an existing STL model and wants to cut, combine, or intersect it with another shape. For example, "cut a 6mm hole through this bracket for a bolt" or "merge these two halves into one model." The skill loads the mesh, performs the requested boolean operation (union, difference, or intersection) using the primary boolean engine, and produces a new mesh. If the input mesh is non-manifold, the system automatically repairs it before attempting the boolean operation. After the operation completes, the user receives before/after preview images from matching angles.

**Why this priority**: Boolean operations are the most fundamental modification capability. Difference (cutting holes, channels, engraving) and union (combining parts) cover the majority of real-world mesh modification requests. Every other modification type builds on or benefits from this foundation.

**Independent Test**: Can be fully tested by loading a known mesh, performing union/difference/intersection with a primitive shape, and verifying the output mesh has the expected geometry (vertex count changed, volume changed in the right direction, mesh remains watertight).

**Acceptance Scenarios**:

1. **Given** a valid STL model and a request to cut a cylindrical hole through it, **When** the user invokes Modify mode with a difference operation, **Then** the system produces a new mesh with the hole removed and both the original and modified meshes remain watertight.
2. **Given** two separate STL files, **When** the user requests a union operation, **Then** the system merges them into a single watertight mesh with no internal faces.
3. **Given** two overlapping meshes, **When** the user requests an intersection operation, **Then** the system produces a mesh containing only the shared volume.
4. **Given** a non-manifold input mesh, **When** a boolean operation is requested, **Then** the system automatically runs the repair pipeline before attempting the boolean and reports that repair was performed.
5. **Given** a boolean operation that would produce empty geometry (e.g., difference of non-overlapping objects), **When** the operation completes, **Then** the system warns the user that the result is empty rather than producing a zero-volume mesh.

---

### User Story 2 - Scaling and Resizing Models (Priority: P2)

A user wants to resize an existing model — uniformly ("make it 20% bigger"), non-uniformly ("stretch the Z-axis to 150%"), or to a specific dimension ("make the width exactly 50mm"). The skill loads the mesh, calculates current dimensions, applies the requested transformation, and renders before/after previews showing the size change. When scaling, the system detects features that should typically preserve their dimensions (holes matching standard screw sizes, thread patterns) and warns the user if these features will be distorted.

**Why this priority**: Scaling is the second most common modification request after booleans. It's conceptually simple but has important subtleties (feature preservation warnings, dimension-targeted scaling requiring bounding box math). It delivers immediate value with lower implementation complexity than text engraving or splitting.

**Independent Test**: Can be fully tested by loading a mesh with known dimensions, applying uniform/non-uniform/dimension-targeted scaling, and measuring the output mesh bounding box to verify the correct transformation was applied.

**Acceptance Scenarios**:

1. **Given** a model and a request to scale uniformly by 120%, **When** the scaling operation runs, **Then** the output mesh bounding box is exactly 120% of the original in all axes.
2. **Given** a model and a request to set the width (X-axis) to exactly 50mm, **When** dimension-targeted scaling runs, **Then** the X dimension of the output mesh is 50mm and all other axes are scaled proportionally.
3. **Given** a model containing holes that match standard M3 screw dimensions (3.2mm diameter), **When** the model is scaled up by 150%, **Then** the system warns the user that the screw holes will no longer fit M3 screws and reports their new diameter.
4. **Given** a model and a non-uniform scaling request (e.g., stretch Z to 200%), **When** the operation runs, **Then** only the specified axis is scaled and the mesh remains valid.

---

### User Story 3 - Combining and Aligning Multiple Models (Priority: P3)

A user has multiple STL files and wants to merge them into a single printable model. For example, "place this handle on top of this lid" or "center this logo on the front face of the box." The skill provides alignment tools — center on axis, place on a surface, offset by a specific distance — so the user can position parts relative to each other before merging via boolean union. The system handles scale mismatches between source files by detecting unit differences.

**Why this priority**: Combining models extends the boolean union capability (P1) with spatial positioning. It's a frequent workflow for remixing and customizing downloaded models from repositories. Depends on boolean union being functional.

**Independent Test**: Can be fully tested by loading two meshes, applying alignment operations (center, offset, place-on-surface), performing a union, and verifying the output geometry has the correct relative positioning and is a single watertight mesh.

**Acceptance Scenarios**:

1. **Given** two STL files and a request to center one on top of the other, **When** the alignment and union operations run, **Then** the result is a single mesh with the second model centered on the top face of the first.
2. **Given** a model and a request to place another model offset by 10mm in the X direction, **When** the alignment runs, **Then** the second model is translated exactly 10mm along X before the union.
3. **Given** two models with significantly different bounding box scales (suggesting different units), **When** combining is requested, **Then** the system warns about the scale mismatch and suggests a rescaling factor.
4. **Given** multiple models to combine, **When** the union produces internal faces or non-manifold geometry, **Then** the system runs a cleanup pass to produce a valid printable mesh.
5. **Given** two meshes in different unit systems (one in mm, one in inches), **When** the user asks to combine them, **Then** the system detects the scale mismatch and offers to rescale to a common unit before combining.

---

### User Story 4 - Text and Logo Engraving/Embossing (Priority: P4)

A user wants to engrave text into a model surface (e.g., "engrave 'v2.1' on the bottom face") or emboss text that protrudes from the surface. The skill generates 3D text geometry from a specified string and font, positions it on the target surface of the model, and performs a boolean difference (engrave) or union (emboss). The system uses appropriate depth/height defaults based on FDM printing capabilities so the text is actually visible and printable.

**Why this priority**: Text engraving is a common personalization task but depends on boolean operations (P1) and surface positioning. It adds significant user value for labeling, versioning, and branding printed parts.

**Independent Test**: Can be fully tested by loading a flat-top model, specifying text to engrave, and verifying the output mesh has the text geometry subtracted from the surface at the correct depth and position.

**Acceptance Scenarios**:

1. **Given** a model with a flat surface and a request to engrave text, **When** the engraving operation runs, **Then** the text is subtracted from the surface at a depth suitable for FDM visibility (default 0.6mm for a 0.4mm nozzle).
2. **Given** a model and a request to emboss text, **When** the embossing operation runs, **Then** the text geometry protrudes from the surface and is merged via boolean union.
3. **Given** a text engraving request with a font size that is too small to print (below minimum feature size for the nozzle), **When** the operation is requested, **Then** the system warns that the text may not be legible and suggests a minimum font size.
4. **Given** a model with a smoothly curved surface (cylinder or sphere) and a request to engrave text, **When** the engraving runs, **Then** the text geometry is projected radially to conform to the curvature. For highly organic or irregular surfaces, the system warns that text placement may be imperfect and suggests using a flat surface instead.
5. **Given** an engraving request, **When** the operation completes, **Then** before/after previews are rendered showing the text on the model from an angle where it is clearly visible.

---

### User Story 5 - Splitting Models for Print (Priority: P5)

A user has a model too large for their print bed or with geometry that would benefit from printing in sections. They specify a cutting plane (or let the system suggest one), and the skill splits the model into two or more parts. At each cut boundary, alignment features (pins and corresponding holes) are automatically added so the printed parts fit together during assembly. The user receives each part as a separate file plus a preview showing the cut location and alignment features.

**Why this priority**: Splitting is a specialized workflow that fewer users need compared to booleans, scaling, and text. It requires the most complex geometry generation (alignment features) and depends on boolean difference (P1) for the actual cutting. High value when needed, but lower frequency.

**Independent Test**: Can be fully tested by loading a model larger than a typical print bed, splitting it along a plane, and verifying: (a) two separate watertight meshes are produced, (b) alignment pin geometry exists on one part and matching holes on the other, (c) the combined volume of the parts equals the original.

**Acceptance Scenarios**:

1. **Given** a model and a horizontal cutting plane at Z=50mm, **When** the split operation runs, **Then** two separate watertight meshes are produced — one containing geometry below Z=50mm and one above.
2. **Given** a split operation, **When** alignment features are generated, **Then** cylindrical pins (default 4mm diameter, 6mm height) are added to one part and matching holes with clearance (default 0.3mm) are added to the other.
3. **Given** a model that fits within a standard print bed, **When** the user requests a split, **Then** the system executes the split but informs the user the model doesn't require splitting for their bed size.
4. **Given** a split that would cut through thin geometry (walls thinner than 2x the alignment pin diameter), **When** the system plans the split, **Then** it warns that alignment features cannot be placed in that region and suggests an alternative cut plane.

---

### User Story 6 - Visual Before/After Comparison (Priority: P6)

Every modification operation — boolean, scale, combine, engrave, split — produces a visual comparison showing the model before and after the change. The before and after previews use identical camera angles and lighting so differences are immediately apparent. This comparison is the primary way the agent and user verify that the modification achieved the intended result.

**Why this priority**: Visual comparison is a cross-cutting capability used by all other stories. It has its own priority because it can be tested independently and provides value even if only one modification type is implemented.

**Independent Test**: Can be fully tested by rendering a mesh, applying any trivial transformation (e.g., scaling by 110%), rendering again from the same angles, and verifying the two preview images use matching camera positions and the difference is visually apparent.

**Acceptance Scenarios**:

1. **Given** a modification operation that changes geometry, **When** the operation completes, **Then** both before and after preview images are rendered from at least 3 matching angles.
2. **Given** before and after previews, **When** the images are compared, **Then** the camera position, angle, and lighting are identical between corresponding views.
3. **Given** a modification that produces a subtle change (e.g., small text engraving), **When** previews are rendered, **Then** at least one view angle is chosen to highlight the area where the change occurred.
4. **Given** a split operation producing multiple parts, **When** previews are rendered, **Then** each resulting part gets its own preview in addition to an overview showing all parts in their relative positions.

---

### User Story 7 - Modify Mode Knowledge Content (Priority: P7)

The knowledge system is populated with Modify-mode-specific content: boolean operation best practices (when to use union vs. difference vs. intersection, handling non-manifold inputs), text engraving depth and font size guidelines by nozzle diameter, alignment pin tolerances for common materials, and model splitting strategies (optimal cut plane selection, when to split, alignment feature types).

**Why this priority**: Knowledge content makes the agent's modifications smarter and more reliable but the core modification pipeline works without it. Can be populated incrementally.

**Independent Test**: Can be fully tested by querying the knowledge system with Modify mode context and verifying relevant guidelines are returned for boolean operations, engraving, and splitting.

**Acceptance Scenarios**:

1. **Given** a query for text engraving guidelines with a 0.4mm nozzle, **When** the knowledge system is queried, **Then** it returns minimum font size, recommended engraving depth, and font recommendations for FDM legibility.
2. **Given** a query for alignment pin tolerances for PLA, **When** the knowledge system is queried, **Then** it returns pin diameter, hole clearance, and interference fit values by nozzle size.
3. **Given** a query for boolean operation best practices, **When** the knowledge system is queried, **Then** it returns guidance on input preparation (repair first), operation selection, and common failure modes.
4. **Given** a query for splitting strategies, **When** the knowledge system is queried, **Then** it returns recommended cut plane orientations, minimum wall thickness at cut boundaries, and alignment feature selection criteria.

---

### Edge Cases

- What happens when a boolean operation fails because the boolean engine cannot process the input geometry (degenerate triangles, self-intersections)?
- What happens when the user requests a boolean difference that would remove all geometry from the model?
- What happens when scaling a model by a very large factor (e.g., 10000%) produces geometry exceeding reasonable print dimensions?
- What happens when text engraving is requested on a model with no flat or smoothly curved surfaces (e.g., a highly organic mesh)?
- What happens when the cutting plane for a split doesn't intersect the model at all?
- What happens when a split produces a part with zero volume (cutting plane tangent to a surface)?
- What happens when combining two models that have no overlap and the user hasn't specified alignment?
- What happens when the input mesh file format is not supported (e.g., STEP, IGES)?
- What happens when the boolean engine (manifold3d) is not installed?
- What happens when a modification produces a mesh that is no longer printable (new overhangs, thin walls created by boolean subtraction)?

## Requirements *(mandatory)*

### Functional Requirements

**Boolean Operations**:

- **FR-001**: System MUST support boolean union (combine two meshes into one), difference (subtract one mesh from another), and intersection (keep only shared volume).
- **FR-002**: System MUST use manifold3d as the primary boolean engine, with trimesh boolean as fallback when manifold3d is unavailable.
- **FR-003**: When input meshes are non-manifold or have defects, the system MUST automatically run the existing repair pipeline (F2) before attempting the boolean operation.
- **FR-004**: System MUST report when automatic repair was required and whether it succeeded before proceeding with the boolean.
- **FR-005**: When a boolean operation produces empty geometry (zero volume), the system MUST warn the user and explain why (e.g., non-overlapping inputs for intersection).
- **FR-005a**: System MUST generate primitive tool shapes (cylinder, box, sphere, cone) from user-specified parameters (dimensions, position, orientation) for use as boolean operands, so users can perform operations like "cut a 6mm hole" without providing a separate mesh file.
- **FR-005b**: Primitive generation MUST support at minimum: cylinder (diameter, height), box (width, depth, height), sphere (diameter), and cone (top diameter, bottom diameter, height).

**Scaling and Resizing**:

- **FR-006**: System MUST support uniform scaling (percentage-based, e.g., 120%).
- **FR-007**: System MUST support non-uniform scaling (per-axis percentage, e.g., X: 100%, Y: 100%, Z: 150%).
- **FR-008**: System MUST support dimension-targeted scaling (set a specific axis to a target measurement, e.g., "width = 50mm", with proportional scaling of other axes).
- **FR-009**: When scaling, the system MUST detect features matching standard hardware dimensions (holes matching M2-M10 screw sizes, common thread pitches) and warn the user that these features will no longer match standard sizes after scaling.
- **FR-010**: System MUST report the before and after bounding box dimensions for every scaling operation.

**Combining and Alignment**:

- **FR-011**: System MUST provide alignment operations: center on axis, place on surface (top, bottom, front, back, left, right), and offset by distance along any axis.
- **FR-012**: System MUST detect scale mismatches between models being combined (e.g., one in mm and one in inches) and warn the user with a suggested conversion factor.
- **FR-013**: After combining, the system MUST run a manifold check and clean up any internal faces or non-manifold artifacts from the union.

**Text and Logo Engraving**:

- **FR-014**: System MUST generate 3D text geometry from a specified string using available system fonts.
- **FR-015**: System MUST support both engraving (boolean difference — text cut into surface) and embossing (boolean union — text raised from surface).
- **FR-016**: System MUST use FDM-appropriate default depths: engraving depth of at least 0.6mm (minimum 3 layer heights at 0.2mm layer height), embossing height of at least 0.8mm.
- **FR-017**: When requested font size would produce features smaller than the nozzle diameter, the system MUST warn that the text may not be legible and suggest a minimum size.
- **FR-018**: System MUST support positioning text on flat surfaces of the target model (top, bottom, front, back, left, right faces).

**Splitting**:

- **FR-019**: System MUST split a model along a user-specified plane (defined by axis and offset, e.g., "Z = 50mm") into two separate watertight meshes.
- **FR-020**: System MUST automatically generate alignment features (cylindrical pins on one part, matching holes with clearance on the other) at the cut boundary.
- **FR-021**: Alignment pin dimensions MUST default to 4mm diameter, 6mm height, with 0.3mm clearance on the receiving hole — configurable by the user.
- **FR-022**: When alignment features cannot be placed (cut boundary too thin, insufficient flat area), the system MUST warn the user and suggest alternatives.
- **FR-023**: Each resulting part MUST be exported as a separate mesh file.

**Visual Comparison**:

- **FR-024**: Every modification operation MUST produce before and after preview images rendered from identical camera angles.
- **FR-025**: Before/after previews MUST use the existing multi-angle rendering system (F1) with at least 3 matching views.
- **FR-026**: For split operations, the system MUST render each resulting part individually plus an overview showing all parts in relative position.

**Post-Modification Validation**:

- **FR-027**: After every modification, the system MUST run the mesh analysis pipeline (F2) on the output to verify the result is still a valid, printable mesh.
- **FR-028**: When a modification introduces new defects (non-manifold edges, thin walls from boolean subtraction), the system MUST report them with the same detail as the analysis pipeline.

**Knowledge Content**:

- **FR-029**: Knowledge system MUST contain boolean operation best practices: input preparation, operation selection guidelines, and common failure modes with solutions.
- **FR-030**: Knowledge system MUST contain text engraving guidelines: minimum font size by nozzle diameter, recommended engraving depth by layer height, font recommendations for FDM legibility.
- **FR-031**: Knowledge system MUST contain alignment pin tolerance tables: pin diameter, hole clearance, and press-fit values by material (PLA, PETG, ABS) and nozzle diameter.
- **FR-032**: Knowledge system MUST contain splitting strategy guidance: optimal cut plane selection, minimum wall thickness at boundaries, alignment feature type selection.

**Mode Integration**:

- **FR-033**: Modify mode MUST be accessible via the existing mode router (`route("modify", **context)`).
- **FR-034**: Modify mode MUST return results using the existing `ModeResponse` envelope (status, message, data).
- **FR-035**: Modify mode MUST accept input mesh paths in STL, OBJ, PLY, and 3MF formats.
- **FR-036**: System MUST export modified meshes in the same format as the input by default, with optional format override.
- **FR-037**: Each Modify mode invocation MUST be a standalone operation — accepting one input mesh (or set of meshes for combine), performing one operation type, and producing one output mesh. No session state is maintained between calls.
- **FR-038**: The output mesh path from one operation MUST be usable as the input mesh path for the next operation, enabling the agent to chain modifications sequentially.
- **FR-039**: Modifications MUST always write to a new output file. The original input mesh MUST never be modified or overwritten.

### Key Entities

- **ModifyRequest**: The user's input to Modify mode. Contains the source mesh path(s), the requested operation type (boolean, scale, combine, engrave, split), operation-specific parameters, and output preferences.
- **ModifyResult**: The output of a modification operation. Contains the output mesh path(s), before/after preview paths, the mesh analysis report of the modified mesh, any warnings generated during the operation, and metadata about what changed (bounding box before/after, vertex/face count changes).
- **BooleanParams**: Parameters for a boolean operation. Contains the boolean type (union, difference, intersection), the tool mesh path or primitive specification (the shape being applied), and the tool's position/orientation relative to the target.
- **ToolPrimitive**: A parametrically defined shape for use as a boolean operand. Contains the primitive type (cylinder, box, sphere, cone), dimensions, position, and orientation. Generated on-the-fly without requiring an external mesh file.
- **ScaleParams**: Parameters for a scaling operation. Contains the scale mode (uniform, non-uniform, dimension-targeted), scale factors or target dimension, and proportional scaling flag.
- **TextParams**: Parameters for a text engraving or embossing operation. Contains the text string, font, font size, depth/height, target surface, position on surface, and mode (engrave or emboss).
- **SplitParams**: Parameters for a split operation. Contains the cutting plane definition (axis and offset), alignment feature parameters (pin diameter, height, clearance), and whether to add alignment features.
- **FeatureWarning**: A warning about a feature affected by scaling. Contains the feature type, original dimension, new dimension, standard hardware match (if any), and human-readable message.
- **AlignmentFeature**: Represents a pin or hole added at a split boundary. Contains position, dimensions, type (pin or hole), and the part it belongs to.

## Assumptions

- The manifold3d package is the preferred boolean engine due to its robustness with imperfect inputs. When unavailable, trimesh's boolean operations (based on the `manifold3d` or `blender` backends via `trimesh.boolean`) serve as a fallback with reduced reliability.
- Text geometry generation uses OpenSCAD's `text()` and `linear_extrude()` primitives via the existing F3 compilation pipeline. No additional font rendering library is needed — system fonts available to OpenSCAD are sufficient.
- Curved surface engraving is limited to smoothly curved surfaces (cylinders, spheres). Highly organic or irregular surfaces may produce imperfect results, which the system will flag.
- Feature detection for scaling warnings uses heuristic size matching (comparing hole diameters against standard screw size tables), not machine-learning-based feature recognition. This covers the most common case (round holes matching metric screw sizes) but won't detect every preservable feature.
- The default alignment pin dimensions (4mm diameter, 6mm height, 0.3mm clearance) are based on common FDM printing tolerances for PLA. Users printing in other materials or with different nozzle sizes may need to adjust these values.
- The repair pipeline (F2) is called as-is before boolean operations. If repair cannot produce a manifold mesh, the boolean operation will fail gracefully with an error rather than producing corrupt geometry.
- The existing rendering system (F1) supports rendering the same mesh from deterministic camera angles, enabling before/after comparison with matched viewpoints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Boolean operations (union, difference, intersection) produce watertight, manifold output meshes in 100% of cases where input meshes are valid or repairable.
- **SC-002**: Scaling operations produce output meshes with bounding box dimensions within 0.1% of the requested scale factor in 100% of cases.
- **SC-003**: Feature preservation warnings correctly identify standard metric screw holes (M2-M10) in test models with 90% accuracy.
- **SC-004**: Text engraving produces legible results (visually distinguishable characters) for font sizes at or above the system-recommended minimum in 100% of test cases on flat surfaces.
- **SC-005**: Split operations produce parts whose combined volume equals the original model's volume (within 1% tolerance) in 100% of cases.
- **SC-006**: Alignment features (pins and holes) fit together with the specified clearance — verified by checking that the pin mesh and hole mesh do not intersect when positioned at the same coordinates.
- **SC-007**: Before/after preview images use identical camera angles (same azimuth, elevation, and distance) for all modification types in 100% of cases.
- **SC-008**: Post-modification mesh analysis runs automatically and detects 100% of defects introduced by modification operations in the test suite.
- **SC-009**: Full modification pipeline (load → modify → validate → preview → export) completes in under 30 seconds for models with fewer than 100,000 faces.
- **SC-010**: Knowledge queries for Modify mode return relevant content for boolean operations, engraving guidelines, pin tolerances, and splitting strategies.
