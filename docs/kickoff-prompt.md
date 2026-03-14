# Print3D Skill — Kickoff Prompt

Use this document in two phases. Run **Phase 1** first (constitution), then **Phase 2** (chunking strategy). These are designed as prompts you paste into a Claude Code session with this repo open.

---

## Phase 1: Establish the Constitution

Run `/speckit.constitution` with the following input:

```
Project name: Print3D Skill

Read these files before drafting principles:
- docs/vision.md (project vision, five modes of operation, design principles, architecture)
- docs/research/02-skill-architecture-specification.md (cross-platform portability, progressive disclosure, context window optimization)
- docs/research/03-open-source-toolchain-integration.md (dependency strategy: core vs extended, tool composition)
- docs/research/04-common-problems-workflows-pain-points.md (user workflows, tribal knowledge encoding)

Based on the vision and research, establish these constitutional principles (7 total):

1. **Open Tools Only** — All toolchain dependencies MUST be open-source. No proprietary CAD engines, no vendor-locked slicer formats. Users must be able to install and run every tool in the pipeline without a license. Rationale: the vision explicitly states "open source, open tools."

2. **Agent-Portable Skill Architecture** — The skill MUST work across Claude Code, OpenAI Codex, Google Gemini, and any future LLM agent framework. No Anthropic-specific APIs in core logic. All agent-framework coupling MUST be isolated to adapter layers. Rationale: portability is a core design principle in the vision; research doc 02 details the cross-platform architecture.

3. **Visual Verification at Every Step** — Every workflow that transforms geometry (create, fix, modify) MUST produce a rendered multi-angle preview before proceeding to the next step. The agent MUST inspect its own output visually. No "blind" pipelines. Rationale: vision calls visual feedback a "first-class concern."

4. **Validate Before You Print** — G-code and slicer settings MUST be reviewed and validated before any print command is issued. The skill MUST never send a job to a printer without explicit validation. Rationale: prints are expensive in time and material; the vision and research doc 04 both emphasize this.

5. **Progressive Disclosure of Knowledge** — The skill MUST NOT load all knowledge (tolerance tables, material properties, decision trees) into context at once. Knowledge MUST be loaded on-demand based on the active workflow mode and the specific problem being solved. Rationale: context window optimization is critical for LLM skills; research doc 02 details this architecture.

6. **Tiered Dependencies** — Core functionality (mesh analysis, basic rendering, OpenSCAD generation) MUST be pip-installable with zero system-level dependencies beyond Python. Extended features (slicer CLI, printer APIs, advanced rendering) MAY require additional system packages but MUST degrade gracefully when unavailable. Rationale: vision specifies tiered dependency model; research doc 03 maps the core vs extended boundary.

7. **Encode Tribal Knowledge as Structured Data** — Community-sourced knowledge (Reddit/forum wisdom on print failures, material quirks, printer-specific settings) MUST be encoded as structured, queryable data — not embedded in prose prompts. Decision trees, lookup tables, and diagnostic flowcharts are the target formats. Rationale: vision calls this out explicitly; research doc 04 catalogs the knowledge to be encoded.

Additional sections:

- **Dependency Constraints**: Python 3.10+ required. Core dependencies limited to: trimesh, manifold3d, numpy. OpenSCAD as the primary CAD backend. PrusaSlicer/OrcaSlicer CLI for slicing. All dependencies must have OSI-approved licenses.

- **Development Workflow**: Feature branches via spec-kit. Every feature goes through specify → clarify → plan → tasks → implement. Constitution compliance checked at the plan phase gate. Integration tests required for any workflow that spans multiple tools (e.g., OpenSCAD → trimesh → slicer).

Ratification date: 2026-03-14
```

---

## Phase 2: Plan the Specify Sequence

After the constitution is committed, use this prompt in a new conversation (or continue if context allows):

```
I need your help planning how to break the Print3D Skill vision into a sequence of /speckit.specify commands. Do NOT run any commands yet — just help me design the chunking strategy.

Read these files for context:
- docs/vision.md
- docs/research/01-visual-feedback-architecture.md
- docs/research/02-skill-architecture-specification.md
- docs/research/03-open-source-toolchain-integration.md
- docs/research/04-common-problems-workflows-pain-points.md
- .specify/memory/constitution.md (the constitution you just created)

The vision describes five modes (Create, Fix, Modify, Diagnose, Validate) plus cross-cutting infrastructure (rendering, knowledge system, tool orchestration, skill routing).

Here are my constraints for the chunking:
- Each /speckit.specify command should describe ONE coherent feature that can be independently specified, planned, tasked, and implemented.
- Features should build on each other — later features can depend on earlier ones, but each should be a shippable increment.
- I want to avoid both extremes: don't try to specify the entire vision in one shot, but also don't over-fragment into 20 tiny specs.
- Target 5-8 features total.
- The first feature MUST be the foundational infrastructure that all five modes depend on (rendering pipeline, tool orchestration, knowledge loading system).
- The last feature should be the most "nice to have" mode.

For each proposed feature, give me:
1. A working title (2-4 words, suitable as a branch name)
2. A one-paragraph description of what this feature covers (this is what I'll paste into /speckit.specify)
3. Which modes from the vision it maps to
4. Key dependencies on earlier features
5. Why this is the right granularity (not too big, not too small)

Also recommend the order they should be specified in, noting which ones could potentially be specified in parallel (independent features where one doesn't inform the other's spec).
```

---

## Usage Notes

- **Run Phase 1 first.** The constitution gates the plan phase of every feature, so it needs to exist before you start specifying.
- **Phase 2 is a planning conversation, not execution.** It produces the chunking strategy. Once you're happy with the sequence, you run each `/speckit.specify` individually with the description from step 2.
- **After each specify**, you'll run the normal flow: `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`. Don't skip clarify on the first couple of features — the clarification questions will surface assumptions that should feed back into the constitution.
- **Constitution is living.** If clarify or plan surfaces a principle that should be constitutional, run `/speckit.constitution` again to amend. The versioning will track changes.
