# Research: Print Failure Diagnosis

## R1: Package Naming

- **Decision**: Name the new package `diagnosis/` (noun form)
- **Rationale**: Consistent with existing package names: `analysis/`, `repair/`, `create/`, `export/`, `rendering/`. Noun form describes _what the package is_, not a verb.
- **Alternatives considered**: `diagnose/` (verb form, matches mode name) — rejected for inconsistency with established naming convention.

## R2: Dependencies

- **Decision**: No new dependencies required. Pure Python + existing PyYAML.
- **Rationale**: The diagnosis module performs in-memory operations: YAML knowledge loading (PyYAML already present), decision tree traversal (dict/list operations), and recommendation assembly (dataclass construction). Photo analysis is handled by the AI agent, not the skill. This keeps the module firmly in core tier.
- **Alternatives considered**: Adding a rule engine library (e.g., `business-rules`, `durable-rules`) for decision tree evaluation — rejected because the trees are simple branching structures that don't need a dedicated engine. Python dicts and conditional logic suffice.

## R3: Knowledge File Structure

- **Decision**: 9 YAML files in `knowledge_base/diagnose/` subdirectory, grouped by content type.
- **Rationale**: Matches the scale of the validate module (9 files). Grouping decision trees by related defect types (extrusion, adhesion, layers, surface, bridging) keeps individual files manageable while allowing AND-filtered queries via `mode="diagnose"` + `problem_type="decision_tree"`. Defect guides, printer tips, material failures, and calibration procedures each get their own file.
- **Alternatives considered**:
  - One file per defect category (12+ files) — rejected as too granular; increases maintenance burden.
  - Single monolithic file — rejected; too large, violates progressive disclosure.

## R4: Knowledge Type Extensions

- **Decision**: Add 2 new valid knowledge types: `"defect_guide"` and `"calibration_procedure"`.
- **Rationale**: Defect guides (visual symptom → category mappings) and calibration procedures don't map cleanly to existing types. `defect_guide` is distinct from `lookup_table` (it has structured fields: severity, visual_indicators, common_causes, spatial_patterns). `calibration_procedure` is distinct from `design_rules` (it has ordered steps, printer-type variants, and verification criteria). Adding dedicated types enables precise `problem_type` queries.
- **Alternatives considered**: Reusing `lookup_table` for defect guides and `design_rules` for calibration — rejected because it muddies the semantics and makes queries return mixed content.

## R5: Entity Naming

- **Decision**: Name the defect entity `PrintDefect` (not `Defect`).
- **Rationale**: The existing codebase already has `DefectType` and `DefectSeverity` enums in `models/analysis.py` for mesh defects (non-manifold edges, boundary edges, etc.). Print defects (stringing, warping, layer shifts) are a completely different domain. `PrintDefect` disambiguates clearly.
- **Alternatives considered**: `DiagnosisDefect`, `PrintQualityDefect` — rejected as unnecessarily verbose. `PrintDefect` is concise and unambiguous.

## R6: Reusing Existing Material/Printer Knowledge

- **Decision**: Diagnose-mode knowledge files are separate from validate-mode files. The diagnosis engine does NOT cross-query validate-mode knowledge.
- **Rationale**: While validate-mode material profiles (`material_pla.yaml`, etc.) contain temperature/speed ranges, the diagnose-mode needs _failure modes_ and _fix recommendations_ — different content. Coupling diagnosis to validate knowledge would create cross-mode dependencies and violate progressive disclosure (loading validate knowledge during diagnose). Instead, diagnose-mode YAML files embed the relevant fix values directly (e.g., "recommended retraction: 0.8mm for PETG on direct drive").
- **Alternatives considered**: Querying validate-mode profiles for baseline values — rejected because it creates tight coupling and the diagnosis engine would need to understand validate-mode data schemas.

## R7: Decision Tree Representation

- **Decision**: Decision trees are represented as nested YAML dictionaries with `condition`, `branches`, and `causes` keys. The engine walks the tree by evaluating conditions against the DiagnosticContext.
- **Rationale**: YAML natively supports nested structures. Each node has a `condition` (what to check: material_type, extruder_type, etc.), `branches` (keyed by condition values), and leaf nodes have `causes` (ranked list of root causes with recommendations). This is the simplest representation that supports the branching described in the spec.
- **Alternatives considered**:
  - Flat lookup tables with composite keys — rejected; loses the branching logic and makes complex multi-factor trees hard to express.
  - External DSL for rules — rejected; over-engineering for structured YAML data.
