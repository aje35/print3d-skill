# Feature Specification: G-code Validation & Slicing

**Feature Branch**: `005-gcode-validation-slicing`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Implement the Validate mode and the slicing/printing pipeline: parse G-code, validate slicer settings against material and printer profiles, slice models via CLI, and submit print jobs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - G-code Parsing & Analysis (Priority: P1)

A user has a G-code file produced by any major slicer (PrusaSlicer, Bambu Studio, OrcaSlicer, or Cura) and wants to understand what it contains before printing. The agent parses the file and produces a structured analysis report showing all extracted parameters: temperatures (hotend, bed), print speeds, retraction settings, layer heights, travel moves, estimated print time, estimated filament usage, and fan speeds. The user can review these parameters without manually reading raw G-code.

**Why this priority**: G-code parsing is the foundation for everything else in this feature. Validation, slicer integration, and printer control all depend on the ability to extract structured data from G-code files. This story alone delivers immediate value — users can audit any G-code file before printing.

**Independent Test**: Can be fully tested by providing sample G-code files from each supported slicer and verifying the extracted parameters match expected values. Delivers value as a standalone G-code inspection tool.

**Acceptance Scenarios**:

1. **Given** a G-code file from PrusaSlicer, **When** the agent parses it, **Then** it produces a report containing hotend temperature, bed temperature, print speed, retraction distance, retraction speed, layer height, estimated print time, and estimated filament usage.
2. **Given** a G-code file from Bambu Studio, **When** the agent parses it, **Then** it correctly handles Bambu-specific metadata comments and extracts the same parameter set.
3. **Given** a G-code file from OrcaSlicer, **When** the agent parses it, **Then** it correctly parses OrcaSlicer comment formats and extracts all parameters.
4. **Given** a G-code file from Cura, **When** the agent parses it, **Then** it correctly interprets Cura's comment conventions (`;SETTING_3` format) and extracts all parameters.
5. **Given** a G-code file with multiple temperature changes mid-print, **When** the agent parses it, **Then** the report includes all temperature commands with their layer/line references, not just the initial temperatures.
6. **Given** an empty or corrupted file, **When** the agent attempts to parse it, **Then** it reports a clear error indicating the file could not be parsed rather than producing incorrect results.

---

### User Story 2 - Settings Validation Against Profiles (Priority: P2)

A user wants to verify that the slicer settings in a G-code file are appropriate for their material and printer before committing to a print. The agent cross-references extracted G-code parameters against material profiles (temperature ranges, speed limits, retraction settings) and printer capabilities (build volume, max temperatures, extruder type). It produces a pass/warn/fail validation result with specific fix recommendations for any issues found.

**Why this priority**: This is the core value proposition of Validate mode and a constitutional requirement (Principle IV: Validate Before You Print). It prevents wasted filament and failed prints by catching misconfigurations before they reach the printer.

**Independent Test**: Can be tested by providing G-code files with known good and bad settings paired with material/printer profiles. A G-code with PETG temperatures but a PLA material profile should produce specific warnings. Delivers value as a pre-print safety check.

**Acceptance Scenarios**:

1. **Given** a G-code file with hotend temperature of 240C and a PLA material profile (recommended 190-220C), **When** validation runs, **Then** it flags the temperature as a warning with a recommendation to lower it to the PLA range.
2. **Given** a G-code file with retraction distance of 6mm and a direct drive printer profile, **When** validation runs, **Then** it warns that the retraction distance is too high for direct drive (recommended 0.5-2mm) and suggests reducing it.
3. **Given** a G-code file with first layer speed of 80mm/s, **When** validation runs, **Then** it warns that first layer speed should typically be 15-25mm/s for bed adhesion.
4. **Given** a G-code file with print dimensions exceeding the printer's build volume, **When** validation runs, **Then** it produces a fail result indicating the model won't fit.
5. **Given** a G-code file with all settings within recommended ranges for the specified material and printer, **When** validation runs, **Then** it produces a pass result with no warnings.
6. **Given** a G-code file with an estimated print time over 72 hours, **When** validation runs, **Then** it flags this as a warning with a recommendation to consider splitting the model or adjusting quality settings.

---

### User Story 3 - Slicer CLI Integration (Priority: P3)

A user wants to slice a 3D model (STL or 3MF) using a slicer installed on their machine. The agent wraps the slicer's command-line interface to handle profile selection (printer profile, material profile, print quality preset), custom setting overrides, and G-code output generation. If no slicer is installed, the system informs the user and continues operating with externally-produced G-code.

**Why this priority**: Slicing completes the "fix settings and re-slice" workflow. Users who receive validation warnings often want to immediately re-slice with corrected settings rather than manually opening the slicer UI. This is an extended-tier capability — the core system works without it.

**Independent Test**: Can be tested by providing an STL file and a printer/material profile to the slicer wrapper, then verifying the output G-code exists and contains expected settings. Also testable in degraded mode by verifying graceful behavior when no slicer is installed.

**Acceptance Scenarios**:

1. **Given** an STL file and a printer profile, material profile, and quality preset, **When** the agent invokes the slicer, **Then** it produces a G-code file at the specified output location.
2. **Given** an STL file and custom setting overrides (e.g., layer height 0.3mm, infill 30%), **When** the agent invokes the slicer, **Then** the output G-code reflects the overridden settings.
3. **Given** no slicer installed on the system, **When** the agent attempts to slice, **Then** it reports that slicing is unavailable and suggests the user install a supported slicer, without crashing or blocking other functionality.
4. **Given** a 3MF file with embedded print settings, **When** the agent invokes the slicer, **Then** it correctly handles the 3MF format and produces G-code.
5. **Given** an invalid or corrupt model file, **When** the agent attempts to slice, **Then** it reports the slicer error clearly and suggests running mesh repair first.

---

### User Story 4 - Printer Control (Priority: P4)

A user wants to send validated G-code directly to their 3D printer. The agent connects to the printer via its available interface (Bambu Lab, OctoPrint, or Moonraker/Klipper), checks the printer's current status, and submits the print job. The system enforces the Validate Before You Print principle: G-code MUST pass validation before it can be submitted to a printer. If no printer connection is configured, the system operates without printer control capabilities.

**Why this priority**: Printer control is the final step in the prepare-to-print pipeline. It depends on all preceding stories (parsing, validation) and is the thinnest layer — primarily sending already-validated G-code to a printer API. This is an extended-tier capability.

**Independent Test**: Can be tested by connecting to a printer (or mock printer endpoint), verifying the system can enumerate printers, check status, and submit a job. Also testable in degraded mode when no printer is configured.

**Acceptance Scenarios**:

1. **Given** a configured printer connection, **When** the agent queries available printers, **Then** it returns a list of discovered printers with their names, types, and current status (idle, printing, error).
2. **Given** validated G-code and an idle printer, **When** the agent submits a print job, **Then** the job is uploaded to the printer and the agent confirms the job has started.
3. **Given** G-code that has NOT been validated, **When** the agent attempts to submit it to a printer, **Then** the system blocks the submission and requires validation first.
4. **Given** G-code that failed validation, **When** the agent attempts to submit it to a printer, **Then** the system blocks the submission and reports the validation failures that must be resolved.
5. **Given** no printer connection configured, **When** the agent attempts printer operations, **Then** it reports that printer control is unavailable and suggests configuring a printer connection.
6. **Given** a printer in an error state (e.g., filament runout, thermal error), **When** the agent checks status before printing, **Then** it reports the error state and does not attempt to submit the job.

---

### User Story 5 - Knowledge Content for Validation (Priority: P5)

The knowledge system is populated with structured profiles and reference data that support the validation and slicing workflows. This includes material profiles (temperature ranges, speed ranges, retraction settings for PLA, PETG, ABS, ASA, TPU, Nylon, and common composites), printer capability profiles (build volumes, max temperatures, extruder types, enclosure status), and slicer-specific setting mappings. The agent queries this knowledge contextually based on the active material, printer, and problem.

**Why this priority**: Knowledge content is a supporting concern rather than user-facing functionality. The validation story (P2) can operate with a minimal set of built-in profiles; the knowledge system enriches it with broader coverage over time.

**Independent Test**: Can be tested by querying the knowledge system for specific material/printer combinations and verifying the returned profiles contain expected values (e.g., PLA temperature range 190-220C, PETG bed temp 70-85C).

**Acceptance Scenarios**:

1. **Given** a query for PLA material profile, **When** the knowledge system is queried, **Then** it returns temperature ranges, speed recommendations, retraction settings, and any material-specific notes.
2. **Given** a query for a specific printer type (e.g., Bambu Lab X1C), **When** the knowledge system is queried, **Then** it returns build volume, max temperatures, extruder type (direct drive), and enclosure status (enclosed).
3. **Given** a query for TPU material on a bowden extruder, **When** the knowledge system is queried, **Then** it returns specific warnings about flexible filament on bowden setups and recommended slow speeds.
4. **Given** a query for an unknown material or printer, **When** the knowledge system is queried, **Then** it returns a clear "not found" result rather than incorrect defaults.

---

### Edge Cases

- What happens when a G-code file uses non-standard comment formats or custom slicer plugins that add unfamiliar commands?
- How does the system handle G-code files with mixed material settings (e.g., multi-extruder prints with different materials)?
- What happens when a G-code file references a material not in the knowledge base?
- How does the system handle network interruptions during printer communication (upload fails mid-transfer)?
- What happens when the slicer CLI is installed but the specified profile name doesn't exist?
- How does the system handle G-code files that are extremely large (1GB+)?
- What happens when a printer becomes unreachable after a job is submitted but before confirmation?
- How does the system handle G-code files with no slicer metadata comments (hand-written or from obscure generators)?

## Requirements *(mandatory)*

### Functional Requirements

**G-code Parsing**:

- **FR-001**: System MUST parse G-code files and extract hotend temperature commands (M104, M109), bed temperature commands (M140, M190), and chamber temperature commands where present.
- **FR-002**: System MUST extract print speed settings, travel speed settings, and first layer speed from G-code.
- **FR-003**: System MUST extract retraction parameters (distance, speed, z-hop) from G-code.
- **FR-004**: System MUST extract layer height (first layer and subsequent layers) from G-code.
- **FR-005**: System MUST extract estimated print time and estimated filament usage from slicer metadata comments.
- **FR-006**: System MUST extract fan speed commands (M106, M107) and identify fan speed changes across layers.
- **FR-007**: System MUST identify which slicer produced the G-code file by parsing metadata comments.
- **FR-008**: System MUST produce a structured analysis report containing all extracted parameters, organized by category.
- **FR-009**: System MUST handle G-code files from PrusaSlicer, Bambu Studio, OrcaSlicer, and Cura, accounting for each slicer's comment format conventions.
- **FR-010**: System MUST report clear errors for unparseable, empty, or corrupted G-code files.

**Settings Validation**:

- **FR-011**: System MUST validate hotend and bed temperatures against the specified material profile's recommended ranges.
- **FR-012**: System MUST validate print speeds against recommended ranges for the specified material.
- **FR-013**: System MUST validate retraction settings against the printer's extruder type (direct drive vs. bowden).
- **FR-014**: System MUST validate first layer settings (speed, temperature, layer height) against best practices.
- **FR-015**: System MUST validate that the print dimensions fit within the printer's build volume.
- **FR-016**: System MUST flag unreasonable print time estimates (configurable threshold, default 72 hours) and excessive filament usage.
- **FR-017**: System MUST produce a validation result with one of three outcomes: pass, warn, or fail.
- **FR-018**: Each validation warning or failure MUST include a specific fix recommendation describing what to change and to what value.
- **FR-019**: System MUST support validating without a printer profile (material-only validation) or without a material profile (printer-only validation).

**Slicer CLI Integration (Extended Tier)**:

- **FR-020**: System MUST support slicing via PrusaSlicer CLI when installed.
- **FR-021**: System MUST support slicing via OrcaSlicer CLI when installed.
- **FR-022**: System MUST accept a printer profile, material profile, and print quality preset for slicing.
- **FR-023**: System MUST support custom setting overrides that take precedence over profile defaults.
- **FR-024**: System MUST accept STL and 3MF input formats for slicing.
- **FR-025**: System MUST report slicer availability status and degrade gracefully when no slicer is installed.

**Printer Control (Extended Tier)**:

- **FR-026**: System MUST support discovering and listing available printers with their connection type and current status.
- **FR-027**: System MUST support Bambu Lab printers via their network protocol.
- **FR-028**: System MUST support OctoPrint-connected printers via the OctoPrint interface.
- **FR-029**: System MUST support Moonraker/Klipper-connected printers via the Moonraker interface.
- **FR-030**: System MUST enforce validation before submitting any print job — unvalidated or failed G-code MUST be rejected.
- **FR-031**: System MUST check printer status (idle, printing, error) before submitting a job and refuse to submit to a printer in an error state.
- **FR-032**: System MUST degrade gracefully when no printer connection is configured.

**Knowledge Content**:

- **FR-033**: System MUST include material profiles for PLA, PETG, ABS, ASA, TPU, Nylon, and common composites (wood-fill, carbon fiber-reinforced).
- **FR-034**: Each material profile MUST include recommended temperature ranges (hotend, bed), speed ranges, retraction settings for both direct drive and bowden extruders, and any material-specific warnings.
- **FR-035**: System MUST include printer capability profiles covering build volume, maximum temperatures, extruder type, and enclosure status.
- **FR-036**: System MUST load knowledge contextually based on the active validation query (material, printer, problem type) rather than loading all profiles at once.

**Integration**:

- **FR-037**: System MUST integrate with the existing mode routing system as the Validate mode handler.
- **FR-038**: System MUST integrate with the existing tool capability registry to report slicer and printer availability.
- **FR-039**: Slicer and printer capabilities MUST be detected at runtime and reported via the existing capability system.

### Key Entities

- **G-code Analysis Report**: Structured representation of all parameters extracted from a parsed G-code file — temperatures, speeds, retraction, layer settings, time/material estimates, fan speeds, and source slicer identification.
- **Validation Result**: Outcome of cross-referencing G-code settings against profiles — contains overall status (pass/warn/fail), individual check results, and fix recommendations.
- **Validation Check**: A single pass/warn/fail assessment of one setting against its expected range, with a recommendation message when not passing.
- **Material Profile**: Reference data for a filament material — temperature ranges, speed limits, retraction settings per extruder type, and special handling notes.
- **Printer Profile**: Reference data for a specific printer or printer class — build volume dimensions, maximum temperatures, extruder type, enclosure status.
- **Slicer Profile Selection**: The combination of printer profile, material profile, and print quality preset used to configure a slicing operation.
- **Print Job**: A submission of validated G-code to a specific printer, including the validation result that authorized the submission.

## Non-Functional Requirements

- **NFR-001**: G-code parsing MUST complete within 5 seconds for files up to 100MB.
- **NFR-002**: Settings validation MUST complete within 1 second after parsing.
- **NFR-003**: The system MUST operate with core functionality (parsing + validation) without any system-level dependencies beyond the base installation.
- **NFR-004**: Extended-tier features (slicing, printer control) MUST degrade gracefully with clear user messaging when dependencies are unavailable.
- **NFR-005**: Printer credentials and connection details MUST NOT be logged or exposed in error messages.

## Assumptions

- G-code files follow standard RepRap/Marlin G-code conventions (G0/G1 moves, M104/M109 temperatures, etc.). Proprietary binary G-code formats (e.g., Bambu's encrypted .3mf) are out of scope.
- Material profiles cover the most common FDM filaments. Specialty filaments (metal-fill, glow-in-dark) use the closest base material profile with a note.
- Printer profiles cover common FDM printer categories (direct drive enclosed, direct drive open, bowden). Specific printer models can be added as knowledge content over time.
- Slicer CLI integration covers PrusaSlicer and OrcaSlicer. Cura CLI (CuraEngine) is not in initial scope but the architecture should not prevent future addition.
- Printer control uses network APIs only. USB/serial printer connections are out of scope.
- Multi-extruder and multi-material G-code parsing extracts per-extruder parameters but validation focuses on single-material prints initially.

## Out of Scope

- Real-time print monitoring (watching a print in progress, pausing/resuming, handling mid-print errors)
- Slicer profile management (creating, editing, or syncing slicer profiles)
- Proprietary encrypted G-code formats
- USB/serial printer communication
- Print queue management (queuing multiple jobs, scheduling)
- G-code modification or optimization (rewriting G-code to fix issues)

## Dependencies

- F1: Knowledge system for material/printer profile storage and contextual queries
- F1: Tool orchestration for slicer and printer capability detection
- F1: Mode routing for Validate mode dispatch

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can obtain a complete analysis of any G-code file from the four supported slicers within 5 seconds.
- **SC-002**: Validation correctly identifies 95% of common misconfiguration patterns (wrong material temperatures, excessive retraction for extruder type, out-of-bounds speeds).
- **SC-003**: 100% of print job submissions are preceded by a validation check — no pathway exists to bypass validation.
- **SC-004**: Users with a supported slicer installed can slice a model and receive validated G-code in a single workflow without leaving the agent.
- **SC-005**: When extended-tier dependencies are unavailable, the system clearly communicates what is unavailable and continues operating with core capabilities.
- **SC-006**: Validation results include actionable fix recommendations that specify both what to change and the recommended value, for every warning or failure.
- **SC-007**: The knowledge system covers material profiles for at least 8 filament types with per-extruder-type retraction recommendations.
