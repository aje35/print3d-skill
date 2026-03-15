# Feature Specification: Print Failure Diagnosis

**Feature Branch**: `006-print-diagnosis`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Implement the Diagnose mode: analyze user-submitted photos of failed or defective 3D prints, identify visible defects, cross-reference against print settings and material properties, and recommend specific actionable fixes."

## Clarifications

### Session 2026-03-14

- Q: What is the input to the skill's diagnosis logic — raw photo paths or pre-identified defect categories? → A: Agent identifies defects using skill's defect guides, then calls skill with identified defect categories + context. The skill does not receive or process photos directly.
- Q: Should each identified defect carry a severity rating? → A: Yes, three-level severity (cosmetic / functional / print-stopping) assigned per defect category in the knowledge base, not per-instance by the agent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Photo-Based Defect Identification (Priority: P1)

A user has a failed or defective 3D print and wants to understand what went wrong. They submit one or more photos of the print to the AI agent. The system analyzes the photos, identifies visible defects from a known set of 12 defect categories, describes the visual observations in plain language, and maps each observation to its defect category with a confidence assessment.

The 12 defect categories are: stringing/oozing, layer shifts, warping/curling, under-extrusion, over-extrusion, bed adhesion failure, elephant foot, poor bridging, support scarring, layer separation/delamination, zits/blobs, and ghosting/ringing.

**Why this priority**: Defect identification is the foundation of the entire diagnosis workflow. Without correctly identifying what is wrong, root cause analysis and recommendations are meaningless. This is also the minimum viable product — even without recommendations, knowing what defect category a problem falls into helps users search for solutions.

**Independent Test**: Can be fully tested by providing photos exhibiting known defects and verifying the system correctly identifies and describes them. Delivers value by giving users a structured understanding of their print problems.

**Acceptance Scenarios**:

1. **Given** a photo of a print with visible stringing between features, **When** the user submits it for diagnosis, **Then** the system identifies "stringing/oozing" as a defect, describes the visible strings/wisps between travel moves, and provides a confidence level for the identification.
2. **Given** a photo showing multiple defects (e.g., warping at corners and elephant foot on first layers), **When** the user submits it for diagnosis, **Then** the system identifies all visible defect categories separately with individual descriptions and confidence levels.
3. **Given** a photo that is too blurry or poorly lit to reliably identify defects, **When** the user submits it for diagnosis, **Then** the system reports that the image quality is insufficient for reliable diagnosis and suggests retaking the photo with better lighting/focus.
4. **Given** a photo of a successful print with no visible defects, **When** the user submits it for diagnosis, **Then** the system reports no defects detected.

---

### User Story 2 - Contextual Root Cause Analysis (Priority: P2)

After defects are identified, the user provides context about their setup — printer model, material, slicer settings (if available), and model geometry (if available). The system walks diagnostic decision trees to determine the most likely root cause for each identified defect, given the user's specific context. A single symptom (e.g., stringing) may have multiple possible causes; the system ranks them by likelihood based on the context provided.

For example: stringing on a Bambu P1S with PETG at high travel speed points to retraction settings as the most likely cause, while stringing on a Bowden-tube printer with PLA points to temperature being too high.

**Why this priority**: Identifying defects (P1) tells the user WHAT is wrong; root cause analysis tells them WHY. This is the diagnostic intelligence that separates useful diagnosis from simple pattern matching. Depends on P1 for defect input.

**Independent Test**: Can be tested by providing known defect-context combinations and verifying the system returns correctly ranked root causes. Delivers value by explaining the cause chain behind each defect.

**Acceptance Scenarios**:

1. **Given** an identified stringing defect and the context "PETG on Bambu P1S with default profile," **When** the system performs root cause analysis, **Then** it returns ranked causes with retraction settings as the highest-likelihood cause for a direct-drive extruder printing PETG.
2. **Given** an identified warping defect and the context "ABS on an open-frame printer," **When** the system performs root cause analysis, **Then** it identifies insufficient enclosure/ambient temperature as a primary environmental factor and bed adhesion settings as the primary controllable factor.
3. **Given** an identified defect but no user context provided (printer and material unknown), **When** the system performs root cause analysis, **Then** it returns the general decision tree with all possible causes listed in order of statistical likelihood, noting that results would improve with more context.
4. **Given** multiple identified defects with a shared root cause (e.g., under-extrusion causing both poor layer adhesion and gaps in top surfaces), **When** the system performs root cause analysis, **Then** it identifies the shared root cause and explains how it manifests as multiple symptoms.

---

### User Story 3 - Actionable Fix Recommendations (Priority: P3)

For each diagnosed root cause, the system provides specific, actionable setting changes — not generic advice. Recommendations include exact values (e.g., "change retraction distance to 0.8mm at 40mm/s") tailored to the user's printer and material. Recommendations are ordered by impact (how much improvement expected) and ease of implementation (simple slicer setting change vs. hardware modification). The system distinguishes between factors the user can directly change (slicer settings, print orientation, support placement) and environmental factors they can only mitigate (humidity, ambient temperature, enclosure quality).

**Why this priority**: This is the ultimate value delivery — users don't just want to know what's wrong and why, they want to know exactly what to change. Depends on P2 for root cause input to generate appropriate fixes.

**Independent Test**: Can be tested by providing known root causes with printer/material context and verifying recommendations contain specific numeric values, are correctly ordered, and distinguish controllable from environmental factors. Delivers value by giving users a concrete action plan.

**Acceptance Scenarios**:

1. **Given** a root cause of "retraction settings too low for PETG on direct drive," **When** the system generates recommendations, **Then** it provides specific values (e.g., retraction distance: 0.8mm, retraction speed: 40mm/s) appropriate for the user's extruder type and material.
2. **Given** multiple root causes for a print failure, **When** the system generates recommendations, **Then** recommendations are ordered with highest-impact, easiest-to-implement changes first (e.g., slicer setting change before hardware modification).
3. **Given** a root cause that involves both controllable and environmental factors (e.g., ABS warping from insufficient enclosure + bed temp too low), **When** the system generates recommendations, **Then** it clearly separates "Change bed temperature to 110C" (controllable) from "Consider adding an enclosure or printing in a warmer room" (environmental mitigation).
4. **Given** a root cause for a printer model not in the knowledge base, **When** the system generates recommendations, **Then** it provides general recommendations for the extruder type (direct drive vs. Bowden) and material, noting that printer-specific values are unavailable.

---

### User Story 4 - Diagnostic Knowledge Base (Priority: P4)

The diagnosis system is backed by a comprehensive, structured knowledge base covering: defect identification guides (visual symptoms mapped to defect categories with descriptive examples), diagnostic decision trees per defect type, printer-specific troubleshooting tips (community tribal knowledge from r/BambuLab, r/prusa3d, r/3Dprinting, and similar sources), material-specific failure modes and fixes, and calibration procedures for common issues. This knowledge is queryable through the existing knowledge system using the Diagnose mode filter.

**Why this priority**: The knowledge base is the content that powers all three previous stories. While basic diagnosis can work with minimal built-in knowledge, comprehensive coverage across printers, materials, and defect types requires substantial structured data. This story covers populating the knowledge base beyond the minimum needed for P1-P3.

**Independent Test**: Can be tested by querying the knowledge system with diagnose-mode filters for each defect category, printer family, and material, and verifying that structured data is returned with the expected fields. Delivers value by ensuring diagnosis quality scales across the full range of user setups.

**Acceptance Scenarios**:

1. **Given** the knowledge system is queried with mode="diagnose" and problem_type="stringing," **When** the query executes, **Then** it returns structured data including: visual symptom descriptions, a diagnostic decision tree with branching conditions, and recommended fixes with specific values.
2. **Given** the knowledge system is queried for a specific printer family (e.g., Bambu Lab P1 series), **When** the query executes, **Then** it returns printer-specific troubleshooting tips, known quirks, and community-sourced recommendations.
3. **Given** the knowledge system is queried for material-specific failure modes (e.g., PETG), **When** the query executes, **Then** it returns common failure modes for that material, temperature ranges, and material-specific setting recommendations.
4. **Given** a calibration-related root cause is identified (e.g., flow rate calibration needed), **When** the system looks up the calibration procedure, **Then** it returns step-by-step calibration instructions appropriate for the user's printer type.

---

### Edge Cases

- What happens when the user submits a non-photo file (e.g., an STL or G-code file) to the diagnosis workflow? The system should reject non-image inputs with a clear message directing the user to the appropriate workflow (Fix mode for STL issues, Validate mode for G-code).
- What happens when a defect doesn't match any of the 12 known categories? The system should report it as "unclassified defect" with a description of the visual anomaly and suggest the user provide additional context or consult community resources.
- What happens when the user provides contradictory context (e.g., claims PETG material but settings show PLA temperatures)? The system should flag the inconsistency and ask for clarification before proceeding with diagnosis.
- How does the system handle defects that only appear at specific layers or regions of a print? The system should note the spatial distribution of the defect as diagnostic context (e.g., "warping at corners only" vs. "warping across entire first layer" have different root causes).
- What happens when a recommended fix for one defect would worsen another identified defect? The system should flag the conflict and suggest a balanced compromise or prioritized fix order.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The skill's diagnosis function MUST accept pre-identified defect categories and diagnostic context as input. Photo analysis is performed by the AI agent using the skill's defect guides; the skill receives structured defect data, not raw images.
- **FR-002**: System MUST identify visible defects from 12 categories: stringing/oozing, layer shifts, warping/curling, under-extrusion, over-extrusion, bed adhesion failure, elephant foot, poor bridging, support scarring, layer separation/delamination, zits/blobs, and ghosting/ringing.
- **FR-003**: System MUST describe visual observations in plain language and map each observation to its defect category with a confidence assessment (high/medium/low).
- **FR-004**: System MUST support identifying multiple simultaneous defects in a single photo.
- **FR-005**: System MUST accept optional diagnostic context: printer model, material type, slicer settings, and model geometry information.
- **FR-006**: System MUST walk diagnostic decision trees to determine root causes for each identified defect, using the provided context to rank causes by likelihood.
- **FR-007**: System MUST provide specific, actionable fix recommendations with numeric values (e.g., "retraction distance: 0.8mm") rather than generic advice (e.g., "adjust retraction").
- **FR-008**: System MUST order recommendations by defect severity (print-stopping before functional before cosmetic), then by impact (expected improvement), then by ease of implementation (slicer change vs. hardware change).
- **FR-009**: System MUST distinguish between controllable factors (slicer settings, orientation, support placement) and environmental factors (humidity, ambient temperature, enclosure) in recommendations.
- **FR-010**: System MUST integrate with the existing knowledge system, using mode="diagnose" for AND-filtered queries.
- **FR-011**: System MUST route through the skill router as the "diagnose" mode, following the existing ModeHandler pattern.
- **FR-012**: System MUST populate structured knowledge YAML files covering: defect identification guides, diagnostic decision trees, printer-specific tips, material-specific failure modes, and calibration procedures.
- **FR-013**: System MUST report when image quality is insufficient for reliable diagnosis.
- **FR-014**: System MUST handle the case where no defects are detected (successful print) gracefully.
- **FR-015**: System MUST flag conflicting recommendations when fixes for one defect would worsen another.
- **FR-016**: System MUST provide general recommendations when the user's specific printer model is not in the knowledge base, falling back to extruder type and material defaults.
- **FR-017**: Each defect category MUST have a default severity level (cosmetic, functional, or print-stopping) defined in the knowledge base, used to prioritize diagnosis and recommendation ordering when multiple defects are present.

### Key Entities

- **Defect**: A print quality problem identified from a photo. Has a category (one of 12 types), severity (cosmetic / functional / print-stopping, assigned per category from knowledge base), visual description, confidence level, and spatial distribution (localized vs. global).
- **DiagnosticContext**: The user's setup information used for cross-referencing. Includes printer model, material type, slicer settings (optional), and model geometry characteristics (optional).
- **RootCause**: A determined reason for a defect, derived from walking a decision tree with the diagnostic context. Has a description, likelihood ranking, and the contributing factors.
- **Recommendation**: A specific fix for a root cause. Has the setting or action to change, the specific value, the expected impact level, implementation difficulty, and whether it's a controllable or environmental factor.
- **DiagnosticDecisionTree**: A structured flowchart for a defect category that branches based on context (material type, extruder type, printer characteristics) to arrive at ranked root causes.
- **DefectGuide**: A knowledge entry mapping visual symptoms to defect categories, with descriptive examples to aid identification.

## Non-Functional Requirements

- **NFR-001**: Diagnosis knowledge MUST be stored as structured YAML data queryable through the existing knowledge system, not embedded in code or prompt text.
- **NFR-002**: The diagnosis module MUST operate in core tier (no system-level dependencies beyond Python 3.10+ and pip-installable packages) for defect identification, decision tree walking, and recommendation generation. Photo analysis itself relies on the AI agent's vision capabilities, not on a local image processing dependency.
- **NFR-003**: Knowledge content MUST be extensible — adding a new printer model, material, or defect subcategory should require only adding or updating YAML files, not code changes.
- **NFR-004**: The diagnosis workflow MUST follow progressive disclosure — only load knowledge relevant to the identified defects and user context, not the entire diagnostic knowledge base.

## Assumptions

- Photo analysis (visual defect identification) is performed by the AI agent's built-in vision capabilities, not by the skill. The responsibility boundary is: the skill provides defect guides (visual symptom descriptions for each category) that the agent uses to identify defects from photos; the agent then passes identified defect categories + diagnostic context to the skill's diagnosis function for decision tree walking and recommendation generation. The skill never receives or processes image files.
- The existing knowledge system (AND-filtered YAML queries) is sufficient for diagnostic knowledge retrieval without architectural changes.
- The existing ModeHandler pattern and skill router can accommodate the Diagnose mode without structural changes.
- Printer-specific knowledge will initially cover the most popular consumer FDM printers (Bambu Lab P1/X1/A1 series, Prusa MK3/MK4/Mini, Creality Ender 3/K1 series) with the knowledge base designed to be extended over time.
- Material coverage will initially focus on the 5 most common FDM materials: PLA, PETG, ABS, TPU, and ASA.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 12 defect categories have corresponding defect identification guides with visual symptom descriptions, enabling the agent to match photo observations to categories.
- **SC-002**: Each of the 12 defect categories has a diagnostic decision tree with at least 3 branching conditions (e.g., material type, extruder type, printer characteristics) leading to ranked root causes.
- **SC-003**: Recommendations for the top 5 materials (PLA, PETG, ABS, TPU, ASA) include specific numeric values for slicer settings, not generic advice, for at least the 3 most common defects per material.
- **SC-004**: The diagnosis workflow correctly routes through the skill router and integrates with the existing knowledge system without requiring changes to the knowledge query interface.
- **SC-005**: Printer-specific knowledge covers at least 3 printer families (Bambu Lab, Prusa, Creality) with community-sourced troubleshooting tips and known quirks.
- **SC-006**: Users can complete a full diagnosis cycle (submit photo description, provide context, receive recommendations) in a single interaction session.
- **SC-007**: When conflicting recommendations arise from multiple defects, the system identifies the conflict and suggests a resolution approach in 100% of tested conflict scenarios.
