# Print3D Skill — Vision

## One-Liner

An open-source AI agent skill that gives any LLM-powered coding assistant full-stack 3D printing capabilities — from natural language design intent to a finished print.

## The Problem

3D printing has a steep learning curve not because the hardware is hard, but because the software pipeline is fragmented. A user who wants to go from an idea to a finished print must currently:

1. Learn a CAD tool (Fusion 360, OpenSCAD, TinkerCAD) to create a model — or hunt through Thingiverse/Printables hoping someone already made what they need
2. Export to STL/3MF and hope the mesh is clean — if not, learn mesh repair tools (Meshmixer, MeshLab, Netfabb)
3. Import into a slicer (Bambu Studio, PrusaSlicer, Cura), choose from hundreds of settings they may not understand, and generate G-code
4. Transfer to their printer and babysit the print, diagnosing failures through trial and error
5. When something goes wrong at any stage, search Reddit, YouTube, and forums for solutions buried in tribal knowledge

Each step uses a different tool with a different interface. Expertise is siloed. A user who's great at CAD might not know slicer settings. Someone who understands printer tuning might not be able to fix a non-manifold mesh.

AI coding assistants (Claude Code, Codex, Gemini) can already write code, manipulate files, and reason about problems. What they lack is domain-specific knowledge about 3D printing and access to the right tools. That's what this skill provides.

## The Solution

Print3D Skill is a portable, open-source skill definition that any AI agent framework can load. It gives the agent:

**Knowledge** — Design-for-printability rules, tolerance tables, material properties, slicer setting recommendations, printer-specific tribal knowledge, and diagnostic decision trees for common failures.

**Tools** — Orchestrated access to open-source software: OpenSCAD for parametric CAD, trimesh/manifold3d for mesh processing, PrusaSlicer/OrcaSlicer CLI for slicing, and MQTT/REST APIs for printer control.

**Eyes** — The ability to render multi-angle 3D previews and visually inspect its own work at every step, plus the ability to analyze user-submitted photos of real prints to diagnose defects. The agent sees what it's building, catches errors autonomously, iterates without requiring the user to manually preview changes, and can look at a photo of a failed print and tell you what went wrong.

## Five Modes of Operation

### Create
Design new models from scratch via natural language. The agent generates OpenSCAD code (with BOSL2 library support), renders a preview, evaluates the result visually, and iterates until the design matches the user's intent.

*"Make me a wall-mount bracket for a Raspberry Pi 4 with screw holes and ventilation slots."*

### Fix
Diagnose and repair broken models from any source — downloads, AI generation, 3D scans, or CAD exports. The agent identifies the specific defects (non-manifold edges, holes, inverted normals, excessive polygon count), applies the appropriate repair strategy, and verifies the fix.

*"I downloaded this STL from Thingiverse and Bambu Studio says it has non-manifold edges. Fix it."*

### Modify
Iterate on existing models — resize, remix, combine, add features, adapt for different printers or materials. The agent understands the existing geometry and makes targeted changes without breaking what already works.

*"Add an engraved label that says 'MT. FUJI' to the front face of this terrain model, and scale the Z-axis to 68% to match the real height ratio."*

### Diagnose
Analyze user-submitted photos of failed or defective prints alongside their description of the problem. The agent uses its vision capabilities to identify visible defects — stringing, layer shifts, warping, under-extrusion, bed adhesion failure, support scarring — and cross-references against the model geometry, slicer settings, and material properties to determine root cause. It then recommends specific, actionable fixes for everything within the user's control: slicer settings, model orientation, support placement, temperature profiles, retraction tuning, and print speed. For environmental factors (humidity, ambient temperature, enclosure) the agent flags them as contributing causes and suggests mitigations.

*"Here's a photo of my PETG print — the overhangs are really rough and there's stringing everywhere. I'm printing on a P1S with the stock profile."*

### Validate
Review G-code and slicer project settings before a print starts. The agent parses the G-code output from slicing to verify: temperatures match the material, print speeds are within recommended ranges for the material and geometry, retraction settings are appropriate, first layer settings look correct, travel moves aren't excessive, and estimated print time/material usage are reasonable. This catches misconfigured slicer profiles, accidental setting changes, and material/profile mismatches before they waste filament and time.

*"I just sliced this model in Bambu Studio for PETG on my P1S — can you sanity-check the G-code before I send it?"*

## Design Principles

**Open source, open tools.** No proprietary CAD software or cloud APIs required for core functionality. Built on OpenSCAD, trimesh, manifold3d, and other established open-source projects.

**Portable across agent frameworks.** Works with Claude Code, OpenAI Codex, Google Gemini, and any future agent system that supports skill/tool definitions. One source of truth, multiple platform adapters.

**Visual feedback as a first-class concern.** The agent renders and inspects 3D previews at every significant step, and can analyze user-submitted photos of real prints to diagnose defects. Users don't have to be the eyes — the agent can see and reason about both digital geometry and physical print results.

**Validate before you print.** G-code is the final instruction set sent to the printer — a misconfigured profile can waste hours of print time and filament. The skill reviews slicer output before it reaches the printer, catching temperature mismatches, inappropriate speeds, and material/profile conflicts.

**Progressive disclosure.** The skill's full knowledge base spans CAD, mesh processing, slicing, printer control, and material science. But only the relevant subset is loaded into context for any given task. A user asking to fix a mesh doesn't load the printer control documentation.

**Encode tribal knowledge.** The 3D printing community has decades of accumulated wisdom living in Reddit threads, forum posts, and YouTube comments. The skill captures this knowledge in a structured, agent-readable form — tolerance tables, diagnostic decision trees, material profiles, printer-specific tips.

**Tiered dependencies.** Core functionality (CAD + mesh processing + visual preview) should be pip-installable with minimal system dependencies. Extended features (slicing, rendering, printer control) are opt-in and clearly separated.

## Architecture (High Level)

```
User ↔ AI Agent (Claude Code / Codex / Gemini)
              ↕
        Print3D Skill
         ┌─────────────────────────────────────────┐
         │  SKILL.md (routing + instructions)       │
         │  knowledge/ (tolerances, materials, ...)  │
         │  workflows/ (create, fix, modify, ...)    │
         │  references/ (API docs, design rules)     │
         │  scripts/ (lightweight Python helpers)     │
         └──────────────┬──────────────────────────┘
                        │ orchestrates
         ┌──────────────┼──────────────────────────┐
         ▼              ▼              ▼            ▼
    OpenSCAD CLI   trimesh/manifold3d  Slicer CLI  Printer APIs
    (CAD + render)  (mesh processing)  (G-code)   (MQTT/REST)
```

## What Success Looks Like

A user with a 3D printer and an AI coding assistant can:

- Describe a part in plain English and get a printable model in minutes, not hours
- Hand the agent a broken STL and get back a clean, printable file with an explanation of what was wrong
- Say "print this on my Bambu P1S in PETG" and have the agent slice with appropriate settings, transfer the file, and start the print
- Take a photo of a failed print, describe what happened, and get a specific diagnosis with corrected slicer settings — not generic advice, but "change retraction to 0.8mm at 40mm/s and reduce travel speed to 150mm/s for PETG on the P1S"
- Hand the agent a G-code file after slicing and have it sanity-check temperatures, speeds, retraction, and material compatibility before committing to a multi-hour print
- Modify existing models without learning CAD — "make the walls 2mm thicker" or "add a mounting hole here"

## Origin

This project grew out of a mesh repair pipeline (`repair_topo_stl.py`) built to fix topographic terrain STL exports for FDM printing. That pipeline solved three specific problems: boundary edge holes, base-terrain delamination, and text engraving. The experience of debugging those issues — and realizing how much of it could be automated and generalized — inspired the vision for a comprehensive 3D printing skill.

## Status

**F1: Core Infrastructure** — Complete. Rendering pipeline, tool orchestration, knowledge system, and skill router.

**F2: Mesh Analysis & Repair** — Complete. 10 defect detectors, 6 repair strategies, health scoring, multi-format export.

**F3: Parametric CAD** — Complete. Session-based OpenSCAD compilation, 4-check FDM printability validation, BOSL2 detection.

**F4: Model Modification** — Complete. Boolean CSG (manifold3d), uniform/non-uniform/targeted scaling with screw hole feature detection, model combining with alignment, text engraving/embossing (OpenSCAD extended tier), plane-based splitting with alignment pins, before/after visual comparison, 4 knowledge YAML files.

**Next**: F5 (G-code & Slicing) to enable Validate mode, or F6 (Print Diagnosis) to enable Diagnose mode.

Research (completed):
1. Visual feedback architecture — matplotlib mplot3d with Agg backend for headless rendering
2. Skill specification format — portable Python library with agent-framework adapters
3. Open-source toolchain integration — trimesh, manifold3d, OpenSCAD, PrusaSlicer CLI
4. User pain points and workflows — tribal knowledge encoded as structured YAML data
