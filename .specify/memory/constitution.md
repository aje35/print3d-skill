<!--
  ╔══════════════════════════════════════════════════════════╗
  ║  Sync Impact Report                                      ║
  ╠══════════════════════════════════════════════════════════╣
  ║  Version change: N/A (template) → 1.0.0                 ║
  ║  Bump rationale: Initial ratification — MAJOR 1.0.0     ║
  ║                                                          ║
  ║  Modified principles:                                    ║
  ║    [PRINCIPLE_1] → I. Open Tools Only                    ║
  ║    [PRINCIPLE_2] → II. Agent-Portable Skill Architecture ║
  ║    [PRINCIPLE_3] → III. Visual Verification at Every Step║
  ║    [PRINCIPLE_4] → IV. Validate Before You Print         ║
  ║    [PRINCIPLE_5] → V. Progressive Disclosure of Knowledge║
  ║    (new)         → VI. Tiered Dependencies               ║
  ║    (new)         → VII. Encode Tribal Knowledge          ║
  ║                                                          ║
  ║  Added sections:                                         ║
  ║    - Dependency Constraints                              ║
  ║    - Development Workflow                                ║
  ║    - Governance (populated from template)                ║
  ║                                                          ║
  ║  Removed sections: None                                  ║
  ║                                                          ║
  ║  Templates requiring updates:                            ║
  ║    ✅ .specify/templates/plan-template.md — Constitution ║
  ║       Check section is generic; will be populated per    ║
  ║       feature by /speckit.plan. No template change needed║
  ║    ✅ .specify/templates/spec-template.md — No principle-║
  ║       specific sections; compatible as-is.               ║
  ║    ✅ .specify/templates/tasks-template.md — No principle║
  ║       -specific task types; compatible as-is.            ║
  ║    ✅ No command templates found.                        ║
  ║    ✅ No README.md or CLAUDE.md to update.               ║
  ║                                                          ║
  ║  Follow-up TODOs: None                                   ║
  ╚══════════════════════════════════════════════════════════╝
-->

# Print3D Skill Constitution

## Core Principles

### I. Open Tools Only

All toolchain dependencies MUST be open-source with OSI-approved
licenses. No proprietary CAD engines, no vendor-locked slicer formats,
no cloud-only APIs in the core pipeline. Users MUST be able to install
and run every tool in the pipeline without purchasing a license.

**Rationale**: The vision explicitly states "open source, open tools."
Proprietary dependencies create vendor lock-in and prevent community
contribution. Every tool in the pipeline — OpenSCAD, trimesh,
manifold3d, PrusaSlicer CLI — MUST be freely available.

**Compliance test**: Can a user on a fresh machine install and run the
full core pipeline using only `pip install` and free package managers?

### II. Agent-Portable Skill Architecture

The skill MUST work across Claude Code, OpenAI Codex, Google Gemini,
and any future LLM agent framework. No Anthropic-specific, OpenAI-
specific, or Google-specific APIs in core logic. All agent-framework
coupling MUST be isolated to adapter layers.

- Core logic (mesh processing, CAD generation, validation, knowledge
  lookup) MUST be framework-agnostic Python.
- Agent-specific integration (tool registration, context injection,
  response formatting) MUST live in clearly separated adapter modules.
- The skill definition format MUST be translatable across frameworks
  without rewriting business logic.

**Rationale**: Portability is a core design principle in the vision.
Research doc 02 details the cross-platform architecture with a
universal skill core and per-framework adapters.

**Compliance test**: Can the core logic be imported and executed
without any agent framework installed?

### III. Visual Verification at Every Step

Every workflow that transforms geometry (create, fix, modify) MUST
produce a rendered multi-angle preview before proceeding to the next
step. The agent MUST inspect its own output visually. No "blind"
pipelines where geometry is generated but never rendered or examined.

- Create mode: render after each OpenSCAD generation, before declaring
  the design complete.
- Fix mode: render before and after repair to confirm the fix.
- Modify mode: render the original and modified geometry side by side.
- Diagnose mode: the agent MUST be able to analyze user-submitted
  photos of physical prints.

**Rationale**: The vision calls visual feedback a "first-class concern."
The agent having "eyes" — the ability to see and reason about 3D
geometry — is a core differentiator, not an optional feature.

**Compliance test**: Does every geometry-transforming workflow include
at least one render-and-inspect step in its workflow definition?

### IV. Validate Before You Print

G-code and slicer settings MUST be reviewed and validated before any
print command is issued. The skill MUST never send a job to a printer
without explicit validation of:

- Temperature settings match the declared material.
- Print speeds are within recommended ranges for the material and
  geometry.
- Retraction settings are appropriate for the material.
- First layer settings are correctly configured.
- Estimated print time and material usage are reasonable.

**Rationale**: Prints are expensive in time and material. A
misconfigured slicer profile can waste hours and filament. The vision
and research doc 04 both emphasize this as a critical safety gate.

**Compliance test**: Is it possible to trigger a print command through
the skill without passing through the validation workflow?
(Answer MUST be no.)

### V. Progressive Disclosure of Knowledge

The skill MUST NOT load all knowledge (tolerance tables, material
properties, decision trees, printer-specific settings, design rules)
into context at once. Knowledge MUST be loaded on-demand based on:

- The active workflow mode (create, fix, modify, diagnose, validate).
- The specific problem being solved within that mode.
- The user's printer, material, and geometry context.

**Rationale**: Context window optimization is critical for LLM skills.
Loading the full knowledge base (~100+ pages of tables, trees, and
rules) into every prompt would be wasteful and degrade agent
performance. Research doc 02 details the progressive disclosure
architecture.

**Compliance test**: For a given workflow invocation, is only the
relevant knowledge subset loaded into context?

### VI. Tiered Dependencies

Core functionality MUST be pip-installable with zero system-level
dependencies beyond Python 3.10+.

- **Core tier** (MUST work with `pip install` only): mesh analysis,
  mesh repair, basic rendering, OpenSCAD code generation, knowledge
  lookup, G-code parsing and validation.
- **Extended tier** (MAY require system packages): slicer CLI
  integration (PrusaSlicer/OrcaSlicer), printer APIs (MQTT/REST),
  advanced rendering (Blender headless), photo analysis for diagnose
  mode.

Extended features MUST degrade gracefully when their dependencies are
unavailable. The skill MUST detect missing extended dependencies at
runtime, report what is unavailable, and continue operating with core
capabilities.

**Rationale**: The vision specifies a tiered dependency model. Research
doc 03 maps the core vs. extended boundary. Users should not need to
install system packages just to use mesh repair or CAD generation.

**Compliance test**: Does `pip install print3d-skill` succeed and
provide core functionality without any system-level package
installation?

### VII. Encode Tribal Knowledge as Structured Data

Community-sourced knowledge (Reddit/forum wisdom on print failures,
material quirks, printer-specific settings, calibration tips) MUST be
encoded as structured, queryable data — not embedded in prose prompts
or freeform text.

Target formats:
- **Decision trees**: diagnostic flowcharts for failure analysis.
- **Lookup tables**: tolerance tables, material property tables,
  minimum feature size tables.
- **Structured profiles**: printer-specific settings, material
  profiles, slicer presets.
- **Rule sets**: design-for-printability rules with conditions and
  recommendations.

**Rationale**: The vision calls this out explicitly. Research doc 04
catalogs the tribal knowledge to be encoded. Structured data is
queryable, versionable, testable, and composable — prose is not.

**Compliance test**: Is every piece of domain knowledge stored in a
structured format (JSON, YAML, or typed Python data) rather than
inline in prompt text?

## Dependency Constraints

- **Python**: 3.10+ required.
- **Core dependencies** (pip-installable, no system packages):
  - `trimesh` — mesh loading, analysis, repair, export.
  - `manifold3d` — boolean operations, CSG.
  - `numpy` — numerical computation, array operations.
- **CAD backend**: OpenSCAD (system package, extended tier) as the
  primary parametric CAD engine. Core tier MUST be able to generate
  OpenSCAD code without OpenSCAD being installed; rendering and
  compilation require OpenSCAD.
- **Slicer integration**: PrusaSlicer CLI and/or OrcaSlicer CLI
  (extended tier). Slicer features degrade gracefully when unavailable.
- **License requirement**: All dependencies MUST have OSI-approved
  licenses. No GPL-incompatible or proprietary dependencies.

## Development Workflow

- Feature branches via spec-kit. Every feature goes through the full
  pipeline: `specify → clarify → plan → tasks → implement`.
- **Constitution compliance** is checked at the plan phase gate. The
  Constitution Check section in `plan.md` MUST verify alignment with
  all seven principles before implementation begins.
- **Integration tests** are required for any workflow that spans
  multiple tools (e.g., OpenSCAD → trimesh → slicer). Unit tests
  cover individual tool wrappers; integration tests cover the composed
  pipeline.
- **Visual regression tests**: workflows that produce rendered previews
  MUST include baseline image comparison or structural validation to
  catch rendering regressions.

## Governance

This constitution is the authoritative source of project principles
and constraints. It supersedes informal conventions, ad-hoc decisions,
and conflicting guidance in other documents.

**Amendment procedure**:
1. Propose the change with rationale in a spec-kit feature branch.
2. Document the impact on existing features and workflows.
3. Update the constitution with a version bump following semantic
   versioning:
   - **MAJOR**: Principle removal, redefinition, or backward-
     incompatible governance change.
   - **MINOR**: New principle or section added, or materially expanded
     guidance.
   - **PATCH**: Clarifications, wording fixes, non-semantic
     refinements.
4. Update the Sync Impact Report at the top of this file.

**Compliance review**: Every `plan.md` MUST include a Constitution
Check section that maps the planned implementation against all seven
principles. Violations MUST be documented and justified in the
Complexity Tracking table.

**Version**: 1.0.0 | **Ratified**: 2026-03-14 | **Last Amended**: 2026-03-14
