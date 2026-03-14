# Deep Research Task 2: Skill Architecture & Cross-Platform Specification Format

## Background

I'm building an open-source AI agent skill called "Print3D Skill" — a universal capability layer that gives LLM-powered coding assistants (Claude Code, OpenAI Codex, Gemini, etc.) full-stack 3D printing abilities: parametric CAD generation (via OpenSCAD), mesh repair, visual validation (the agent renders and inspects its own 3D output), slicing, and printer control.

The key design constraint is that this skill must work across multiple AI agent frameworks — not just Claude Code, but also OpenAI's Codex, Google's Gemini agent tooling, and other emerging agentic systems. The 3D printing domain is complex, spanning 20+ distinct capabilities across CAD design, mesh processing, slicing, and hardware control. The skill needs a structure that keeps it portable, discoverable, and efficient with LLM context windows.

The skill will also heavily use visual feedback — rendering multi-angle 3D previews that the agent inspects to validate its work. This visual loop needs to be architecturally supported, not bolted on.

## Research Question

**What is the optimal skill/agent-tool architecture that works across Claude Code, Codex, and other agent frameworks while supporting a domain as complex as full-stack 3D printing — and how should it be structured for progressive disclosure, composability, and visual feedback?**

## Specific Areas to Investigate

### 1. Existing Skill/Agent-Tool Specification Formats

Research and compare these specific specification formats and approaches:

- **Anthropic Agent Skills Specification** (agentskills.io) — The formal open specification for portable AI agent skills. Analyze the SKILL.md format (YAML frontmatter + markdown body), the progressive disclosure model (metadata ~100 tokens → instructions <5000 tokens → resources on-demand), naming constraints, and the plugin marketplace system. Study the reference implementation at `github.com/anthropics/skills`.
- **Dicer LLM Kits** (github.com/Dicer-ai/dicer-llm-kits) — A more opinionated multi-file approach with separate `SKILL.md`, `LLM.md` (agent-specific instructions), `README.md` (human docs), `workflows/` (per-command files), `knowledge/` (embedded domain expertise), and `templates/` (output scaffolding). Analyze how they handle lazy loading via situation-to-file mapping tables.
- **OpenAI function calling / tool use** — How does OpenAI's tool definition schema (JSON function definitions with parameters) relate to skill definitions? Can a SKILL.md-style definition be automatically converted to OpenAI tool schemas?
- **Google Gemini agent tools** — What is Google's approach to defining agent capabilities? How do Gemini extensions and function declarations compare?
- **Model Context Protocol (MCP)** — The open protocol for connecting AI models to external tools via JSON-RPC. How does MCP relate to skills? Should the skill's heavy operations (rendering, mesh analysis, printer control) be exposed as MCP tools that the skill orchestrates?

### 2. Progressive Disclosure for a Large Domain

The Print3D Skill will have capabilities spanning:
- CAD generation (OpenSCAD code gen, BOSL2 library usage, parametric editing)
- Mesh processing (repair, boolean operations, analysis, format conversion)
- Visual validation (multi-angle rendering, visual diff, printability inspection)
- Terrain processing (topographic model repair, elevation data handling)
- Slicing (PrusaSlicer/OrcaSlicer/Cura CLI integration, print time estimation)
- Printer control (Bambu MQTT, OctoPrint API, Klipper/Moonraker API)
- Multi-color (AMS filament mapping, vertex coloring, texture-to-color conversion)

How should this be structured so that:
- The initial metadata loaded for ALL installed skills is tiny (~100 tokens) but has enough keywords to trigger correctly
- The main instructions loaded on activation are lean (<5000 tokens) and route to the right sub-capability
- Detailed reference docs, code examples, and domain knowledge are loaded only when needed
- The agent can handle "design a bracket" and "send this to my printer" in the same conversation without loading everything upfront

Study how these existing projects handle multi-capability skills:
- **bambu-studio-ai** (github.com/heyixuan2/bambu-studio-ai) — Uses 6 distinct named workflows (A-F) for different model source types in a single SKILL.md
- **3d-print-skill** (github.com/EdwinjJ1/3d-print-skill) — Uses a 4-phase workflow (Specify → Generate → Validate → Export) with strict gates
- **Dicer's site-audit skill** — Uses a 4-layer methodology with prerequisite enforcement between layers
- **Anthropic's mcp-builder skill** — Uses phased workflows with "Load During Phase X" directives for reference files

### 3. MCP Server vs. Embedded Scripts vs. Hybrid

Three architectural patterns exist for where the skill's computational work happens:

**Pattern A: Embedded Scripts** — Python/bash scripts in a `scripts/` directory, invoked by the agent via shell commands. Used by Anthropic's skill examples (pdf skill has 8 scripts). Simple, self-contained, but requires all dependencies installed locally.

**Pattern B: MCP Server** — Heavy operations exposed as MCP tools via a long-running server process. Multiple OpenSCAD MCP servers already exist (quellant/openscad-mcp, jabberjabberjabber/openscad-mcp). The `mcp-3D-printer-server` by DMontgomery40 wraps 7 printer APIs. Rich tool ecosystem, but adds deployment complexity.

**Pattern C: Hybrid** — The skill orchestrates via SKILL.md instructions, delegates rendering/analysis to an MCP server, and uses embedded scripts for lightweight operations (file conversion, config management).

Research the tradeoffs. Consider:
- How do current agent frameworks discover and invoke MCP tools vs. shell scripts?
- Can a skill definition reference MCP servers as dependencies?
- What's the user setup experience for each pattern? (pip install vs. Docker vs. npm)
- How does the `mcp-3D-printer-server` Docker deployment model work, and is it a good pattern to follow?

### 4. Cross-Platform Portability

The skill should work with Claude Code, Codex, and Gemini. Research:
- What is the common subset of capabilities across these platforms? (All support: text instructions, tool/function calling, image input. Differences?)
- Can a single SKILL.md be the source of truth, with generated adapters for each platform's native format?
- Are there any existing tools or projects that solve cross-platform skill portability?
- How does the `agentskills.io` specification position itself relative to platform-specific formats?

### 5. Visual Feedback as Architectural Concern

The agent needs to render 3D previews and inspect them as part of its workflow. How should this be architecturally supported?
- Should rendering be a dedicated MCP tool, a script, or built into the skill's workflow instructions?
- How do you instruct the agent (in SKILL.md) to render and inspect at specific pipeline stages without making every operation slow?
- Are there patterns for "conditional rendering" — only render when a significant change is made, not after every micro-edit?

## Desired Output

A comprehensive report covering:

1. **Specification format recommendation** — Which format to adopt as primary, with mapping strategy for other platforms
2. **Skill directory structure** — Proposed file/folder layout for a skill this complex, with rationale
3. **Progressive disclosure design** — How to layer metadata → instructions → workflows → references → knowledge for 20+ capabilities
4. **Architecture recommendation** — MCP server, embedded scripts, or hybrid, with deployment strategy
5. **Cross-platform portability plan** — How to support Claude Code, Codex, and Gemini from a single source
6. **Comparison table** — Side-by-side analysis of the specification formats studied
7. **Example SKILL.md skeleton** — A draft frontmatter + top-level routing structure for Print3D Skill

---

# **Architecture and Specification Design for Cross-Platform AI Agent 3D Printing Skills**

## **The Convergence of Agentic Reasoning and Physical Manufacturing**

The intersection of generative artificial intelligence and physical manufacturing represents a paradigm shift in computer-aided design (CAD) and hardware operation. Modern large language models (LLMs) are evolving from text-based conversational interfaces into autonomous, agentic systems capable of executing complex, multi-step operations within local and remote environments. However, the domain of 3D printing and parametric modeling is notoriously hostile to pure linguistic reasoning. Generating a physical artifact requires navigating a highly complex, interconnected pipeline: conceptual ideation, precise parametric code generation (utilizing frameworks like OpenSCAD), geometric compilation, mesh manifold validation, slicing algorithm orchestration, and direct hardware communication protocols. An autonomous AI agent attempting to traverse this physical-digital pipeline faces severe hurdles regarding spatial reasoning, context window management, deterministic code generation, and hardware safety.

To bridge this divide, complex capabilities must be encapsulated into specialized "skills" that equip the agent with procedural knowledge and executable tooling on demand. Constructing a universal "Print3D Skill"—a comprehensive capability layer spanning CAD generation, mesh processing, visual validation, slicing, and printer control—requires a rigorous architectural strategy. The primary design constraint for this endeavor is strict cross-platform portability. The skill must function seamlessly across distinct, competitive agentic ecosystems, including Anthropic's Claude Code, OpenAI's Codex, and Google's Gemini command-line interfaces, while actively mitigating the catastrophic context bloat that typically accompanies large, monolithic toolsets.

This comprehensive research report provides an exhaustive analysis of the optimal architectural patterns, specification formats, and execution models required to deploy a highly complex, hardware-interfacing AI agent skill. It evaluates the structural mechanics of progressive disclosure architectures, the critical integration of visual feedback loops for autonomous spatial validation, the bridging of distinct platform ecosystems, and the architectural dichotomy between local script execution and the Model Context Protocol (MCP).

## **Comparative Analysis of Agent-Tool Specification Formats**

The ecosystem of agentic capabilities is currently partitioned into two distinct philosophical and technical approaches: the packaging of procedural knowledge (typically defined as "Skills") and the exposure of executable actions (defined as "Tools" or "Functions"). A foundational understanding of how different platforms implement, parse, and execute these concepts is required to design a cross-compatible architecture that operates efficiently regardless of the underlying LLM engine.

### **The Anthropic Agent Skills Specification**

The open standard introduced by Anthropic, hosted at agentskills.io, conceptualizes a skill as a modular, filesystem-based directory that packages domain expertise, instructions, and resources into a portable format.1 The standard mandates a primary SKILL.md file containing YAML frontmatter for metadata and a Markdown body for behavioral instructions.2 This architecture was built explicitly to solve the problem of context window degradation, treating the skill not merely as an API endpoint, but as a cognitive playbook for the model.

The specification enforces a strict parameter set for the frontmatter. The name field is restricted to lowercase letters, numbers, and hyphens, with a maximum length of 64 characters, while the description field is capped at 1024 characters.4 This metadata serves as the foundational discovery mechanism. The format introduces "progressive disclosure," a three-level loading system designed to optimize token economics. Level 1 consists of the YAML metadata, which is permanently injected into the agent's system prompt at startup, consuming approximately 100 tokens per installed skill.4 Level 2 is the core Markdown instruction set within SKILL.md, which is loaded into the active context window via a bash read command only when the agent semantically matches the user's intent to the skill's description.2 Level 3 comprises peripheral resources, templates, and executable scripts referenced within the main body, accessed dynamically by the agent only when an edge case or specific workflow demands them.4 This progressive architecture allows users to install hundreds of capabilities without overwhelming the initial prompt capacity.

### **Dicer LLM Kits and Multi-File Topologies**

The Dicer LLM Kits project represents a highly opinionated, multi-file approach to capability packaging. Rather than consolidating routing logic into a single entry-point document, Dicer distributes capabilities across a rigidly structured directory topology. This includes separate files for agent-specific instructions (LLM.md), human-readable documentation (README.md), and dedicated subdirectories containing specialized logic, such as workflows/ for per-command files, knowledge/ for embedded domain expertise, and templates/ for output scaffolding.7

Dicer implements lazy loading through complex situation-to-file mapping tables. This architecture effectively treats the skill directory as a localized Retrieval-Augmented Generation (RAG) database, forcing the agent to dynamically map user requests to specific isolated files. While this high fragmentation allows for extreme modularity and excellent version control granularity, it introduces significant operational overhead for the orchestrating agent. The agent must continuously invoke filesystem tools to navigate the directory tree and reconstruct the procedural workflow piece by piece. For a continuous 3D printing pipeline requiring tight procedural coupling between CAD generation and mesh repair, the Dicer approach risks fragmenting the workflow state across too many disconnected context windows, potentially leading to hallucinated transitions and increased latency.9

### **OpenAI Function Calling and Schema Conversion**

OpenAI's historical approach to agent capabilities relies heavily on rigid JSON schemas to define "tools." A function definition requires a precise mapping of parameters, types, and descriptions using OpenAPI 3.0 specifications, allowing the model to return a structured JSON object intended for application-side execution.10 Under the function calling paradigm, the burden of execution falls entirely on the client application, which must parse the JSON, execute the local code, and return the result as a subsequent message in the conversation history.

However, OpenAI has recently converged toward the filesystem-based skill approach for its Codex CLI and hosted execution environments, recognizing the limitations of purely stateless JSON functions for complex procedural workflows.12 In this updated architecture, OpenAI automatically parses a folder containing a SKILL.md file. The service extracts the YAML frontmatter and injects the tool's name, description, and file path into the hidden system prompt context.14 Upon invocation, OpenAI dynamically mounts the entire skill bundle into a containerized execution environment (container\_auto). This allows the model to utilize native shell tools to explore the bundled resources, read the Markdown instructions, and execute auxiliary scripts directly within the sandbox.15 This architectural shift indicates that SKILL.md is becoming the universal authoring format, with platform-specific engines handling the automatic conversion into function schemas and execution environments.

### **Google Gemini Extensions and Function Declarations**

Google's Gemini ecosystem utilizes a dual-track paradigm: Function Declarations and Extensions. Function Declarations operate similarly to OpenAI's traditional model, requiring OpenAPI 3.0 compatible JSON schemas that dictate how the model should format its output to trigger external, developer-managed code.17 Extensions, conversely, act as standardized connectors executing directly on the agent side, enabling seamless API interactions using few-shot learning examples embedded within the configuration without requiring custom routing code for every endpoint.19

Recent updates to the Gemini CLI have fundamentally altered its approach, embracing the open Agent Skills standard. Gemini now actively scans local .gemini/skills/ and universal .agents/skills/ directories for SKILL.md files, establishing a clear hierarchy of discovery across workspace, user, and extension scopes.20 Gemini injects the name and description into the system prompt and utilizes a proprietary activate\_skill tool to load the full context upon identifying a semantic match. Crucially, Gemini enforces a strict user-consent security model; whenever an agent attempts to activate a skill or execute a bundled script, the interface pauses execution and displays a confirmation gate, ensuring the agent cannot autonomously execute destructive filesystem operations without explicit human oversight.20

### **The Model Context Protocol (MCP)**

While Agent Skills define *how* an agent should think and behave procedurally, the Model Context Protocol (MCP) defines *what* an agent can connect to technically. MCP is an open standard based on a JSON-RPC 2.0 client-server architecture designed to standardize communication between AI applications and external capability providers.22 It operates as a universal interface layer, allowing agents to query databases, read local files, or trigger proprietary APIs without requiring bespoke, hardcoded integrations for each individual tool.24

MCP servers expose three fundamental primitives: Tools (executable functions with defined schemas), Resources (structured data like files, application state, or database schemas), and Prompts (reusable instruction templates).23 While an agent skill is fundamentally stateless and loaded entirely via a filesystem read, an MCP server operates as a stateful, persistent connection leveraging Server-Sent Events (SSE) for continuous, low-latency communication.22 Therefore, skills and MCP are highly complementary architectures rather than competitive ones. A complex capability, such as 3D printing orchestration, should theoretically encode the procedural workflow, error recovery logic, and formatting rules within its SKILL.md, while delegating heavy computational tasks—such as slicing algorithms or interfacing with a printer's MQTT network—to the persistent tools exposed by an MCP server.

### **Format Comparison Summary**

To effectively design a cross-platform skill, the structural variances between these formats must be synthesized. The table below outlines the core dimensions of each specification approach.

| Specification Format | Primary Paradigm | Core Configuration Format | State Management | Loading Mechanism | Execution Engine | Optimal Use Case |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Agent Skills (agentskills.io)** | Procedural Knowledge | SKILL.md (YAML \+ Markdown) | Stateless (Filesystem) | Progressive Disclosure | Native shell / Client sandbox | Workflows, styling, heuristics, code generation |
| **Dicer LLM Kits** | Fragmented Knowledge Base | Multiple Markdown / Config files | Stateless (RAG indexing) | Lazy Loading via Routing Tables | Host application | Complex audits, massive legacy codebases |
| **OpenAI Function Calling** | Structured Tool Execution | JSON Schema (OpenAPI 3.0) | Stateless (Request/Response) | Upfront Schema Injection | Client-side application | Strict data parsing, database queries, webhooks |
| **Gemini CLI Skills** | Procedural Knowledge / API Hooks | SKILL.md / gemini-extension.json | Stateless | Progressive via activate\_skill | Local Host / CLI | User-gated local automation, data retrieval |
| **Model Context Protocol (MCP)** | Secure System Connectivity | JSON-RPC 2.0 Client-Server | Stateful (Persistent connection) | Upfront Tool Registry | Remote or Local Server | Hardware APIs, heavy computation, live monitoring |

## **Architecting Progressive Disclosure for a Multi-Faceted Domain**

The 3D printing domain is exceptionally vast and technically dense. A single agent managing the full pipeline must comprehend OpenSCAD syntax, the advanced BOSL2 parametric library, mesh manifold rules, boolean intersection logic, G-code slicing parameters, multi-color filament mapping, and network protocols for Bambu, OctoPrint, or Klipper hardware. If the entirety of this technical context were loaded into an LLM's working memory simultaneously, the token cost would be exorbitant, inference latency would spike to unusable levels, and the model's reasoning capabilities would degrade significantly due to context saturation and the "needle in a haystack" phenomenon.27

The architectural solution to this complexity is a hyper-optimized implementation of progressive disclosure. The agent must incrementally discover relevant context through exploration, navigating the workflow layer by layer, guided by strict heuristic boundaries.

### **The Three-Tier Loading Optimization**

To support over twenty distinct capabilities without degrading the agent's idle performance, the skill directory must rigorously adhere to the tier-loading principles identified in the agentskills.io specification. This requires segmenting the capability into three discrete phases of contextual awareness.

The first phase is the Trigger Layer. The YAML frontmatter embedded at the top of the SKILL.md file must be ruthlessly concise. Because this metadata resides permanently in the agent's system prompt, the description field acts as the primary routing heuristic. It must contain the maximum density of domain-specific trigger words (e.g., "OpenSCAD", "BOSL2", "mesh repair", "slice", "OctoPrint", "G-code", "Bambu") within its strict 1024-character limit.4 A dense description allows the agent to recognize the skill's precise utility and implicitly activate it without loading its deep contents unnecessarily.

The second phase is the Routing Layer, represented by the main body of the SKILL.md file. Upon activation, the agent reads this document into the active context window. Crucially, this document must not contain deep technical tutorials or raw API schemas. Instead, it must function as a high-level orchestrator or "table of contents." It outlines the available capabilities, establishes the boundaries of the workflow, and provides exact relative file paths to the specialized instructions needed for specific sub-tasks.5 The routing layer must remain under 5000 tokens to preserve the model's analytical focus.

The third phase is the Deep Context Layer. The heavy intellectual lifting of the skill is deferred to the references/ and scripts/ subdirectories. If a user asks the agent to "design a parametric mounting bracket," the agent reads the routing layer, identifies that a CAD workflow is required, and dynamically loads references/openscad\_bosl2\_patterns.md. The documentation regarding mesh repair, slicing profiles, and printer control network requests remains completely unloaded, preserving thousands of tokens.

### **Phased Workflows and Load Directives**

Analyzing existing multi-capability skills reveals specific architectural patterns required for successful domain orchestration. The official Anthropic mcp-builder skill demonstrates the high efficacy of "Load During Phase X" directives.28 By dividing the workflow into rigid chronological phases (e.g., Phase 1: Planning, Phase 2: Implementation, Phase 3: Review), the SKILL.md explicitly instructs the agent exactly *when* to load external reference documents, preventing premature context bloat.

For the Print3D Skill, this methodology translates to a strictly linear, phase-gated progression. During Phase 1 (Geometry Generation), the skill issues a directive to load references/bosl2\_syntax.md only if parametric CAD generation is required. During Phase 2 (Visual Validation), the directive shifts to executing scripts/render\_multiview.sh and analyzing the output, explicitly omitting code generation documentation. Phase 3 (Mesh Processing) triggers the loading of references/manifold\_repair.md strictly if the validation phase detects intersecting geometry or non-manifold edges. Finally, Phase 4 (Slicer Orchestration) prompts the loading of references/slicer\_profiles.md only when preparing for hardware export.

Furthermore, the structure of the bambu-studio-ai project illustrates the necessity of defining distinct, named workflows within a single skill. It segments its capabilities into explicitly labeled pipelines (e.g., Workflow A: Text-to-3D, Workflow B: Mesh Repair, Workflow C: Hardware Print).30 A robust SKILL.md for Print3D must utilize top-level Markdown headers to define these discrete workflows. This structural clarity allows the LLM's attention mechanism to lock onto the relevant procedural block while safely ignoring the instructions meant for alternate workflows.

### **Execution Gates and User Consent Models**

Hardware manipulation inherently carries physical and financial risk. Sending an untested, unvalidated, or hallucinatory G-code file to a 3D printer can result in hardware damage, thermal runaway, or wasted materials. Therefore, the progressive disclosure architecture must implement unyielding "Gates."

Modeled after the ntm-orchestrator and a11y-agent-team behavioral patterns, an Execution Gate is a rigid instruction block that intentionally halts autonomous execution. The routing layer within the SKILL.md must explicitly state directives such as: STOP GATE: Do not proceed to slicing or printing operations until the user has explicitly confirmed the visual rendering of the generated mesh.32 This pattern forces the agent to yield control back to the human operator at critical junctures, transforming the workflow from fully autonomous (which is dangerous in physical manufacturing contexts) to a highly supervised co-pilot model.

## **Computational Architecture: Embedded Scripts vs. MCP Servers vs. Hybrid Orchestration**

Once the procedural logic is established via progressive disclosure, the locus of computational execution must be determined. 3D printing tasks are profoundly computationally intensive. The processes of compiling OpenSCAD syntax to a manifold STL, calculating boolean geometric intersections, analyzing mesh structures, and parsing massive G-code files cannot be performed natively by an LLM relying solely on text generation. The skill must interact with a robust execution environment. Three distinct architectural patterns exist for managing this computational load.

### **Pattern A: Embedded Script Execution**

In the Embedded Script architecture, the skill directory contains a scripts/ folder populated with executable files written in Python, Bash, or Node.js.4 The agent invokes these scripts directly using its native host environment (such as the local terminal in Claude Code or the sandboxed execution container in OpenAI Codex).15

The primary advantage of this approach is absolute portability. The entire capability—instructions, logic, and tools—is bundled into a single compressed repository. The setup experience is frictionless, as the user simply clones the skill folder into the appropriate .agents/skills/ directory without configuring external services.

However, the drawbacks are significant. This pattern relies entirely on the host machine possessing the correct local dependencies. If a Python script requires trimesh or numpy for mesh analysis, or relies on the local system path to locate the openscad binary, and the user's local environment lacks these dependencies, the execution fails immediately.35 Furthermore, embedded scripts are inherently stateless; they spin up, execute a single command, and terminate. This makes them poorly suited for continuous operations, such as monitoring the temperature fluctuations and telemetry of a three-hour print job via a WebSocket connection.

### **Pattern B: Dedicated MCP Server Backend**

The second architecture offloads all computational execution to a persistent, locally hosted or remote Model Context Protocol server. Existing projects vividly demonstrate the raw power of this approach. The openscad-mcp server, developed by developers quellant and jabberjabberjabber, directly wraps the OpenSCAD binary. It provides the agent with tools for real-time rendering, Base64 image generation optimized for vision models, and persistent scratchpads that maintain geometric work across conversational sessions.36

Similarly, the highly complex mcp-3D-printer-server developed by DMontgomery40 acts as a comprehensive middleware hub. It connects the agent to OctoPrint, Klipper, and Bambu APIs via HTTP and MQTT protocols.38 This server provides enterprise-grade isolation and includes advanced STL manipulation tools (such as programmatic scaling, sectional translation, and base extension) alongside direct external slicer integration.39 Because the server handles the intense execution logic, the LLM simply calls semantic tools (e.g., slice\_stl, get\_printer\_status), drastically reducing token consumption and preventing the agent from becoming entangled in low-level programming syntax.40

The primary drawback of the pure MCP approach is deployment complexity. To utilize the mcp-3D-printer-server, users must deploy a Docker container or manage complex Node.js environments locally, handling .env files for printer IP addresses and API keys.41 This introduces severe friction compared to dropping a folder into a directory. Furthermore, an MCP server merely exposes tools; it lacks the deep, conversational procedural guidance that a SKILL.md provides regarding *when* and *why* to use those tools.

### **Pattern C: The Hybrid Orchestration Model**

The optimal architecture for the Print3D Skill is a Hybrid Orchestration Model. This approach synergizes the strengths of both paradigms: the filesystem-based SKILL.md acts as the cognitive orchestrator and procedural guide, while one or more MCP servers operate as the muscular execution engines.

In this topology, the agent initially loads the Print3D SKILL.md. The procedural instructions within the skill actively mandate the presence of specific MCP tools, directing the agent to run an environment check (e.g., verifying if the generate\_stl\_visualization or get\_printer\_status tools are present in its registry).

Lightweight operations, such as reading basic user configuration files, calculating initial parametric variables, or drafting OpenSCAD syntax, are handled natively by the LLM using the procedural knowledge embedded in the skill's references/ directory. However, when the code must be rendered into an image, the mesh repaired, or the hardware queried, the SKILL.md explicitly directs the agent to delegate the task to the connected MCP server.43 This hybrid design entirely resolves the token bloat issue. The agent does not attempt to parse raw 3D mesh data or write complex API request loops to Klipper; it simply invokes the appropriate MCP tool as directed by its skill instructions.

To mitigate the user setup friction associated with MCP deployment, the skill directory should bundle an embedded bootstrap script (e.g., scripts/install\_mcp.sh). If the agent detects the required MCP tools are missing during its initial environment check, the SKILL.md instructs the agent to automatically execute the bootstrap script, which silently handles the Docker deployment or NPM installation of the required MCP backend, creating a seamless, self-healing installation experience.

## **The Visual Feedback Loop as a Core Architectural Concern**

A critical vulnerability in applying language models to parametric physical design is their complete lack of intrinsic spatial awareness. While an LLM can easily generate syntactically flawless OpenSCAD or BOSL2 code, it routinely fails to comprehend intersecting volumes, proper absolute scaling, or the physical viability of a geometry under gravity.44 Without sight, an agent generating CAD code operates entirely blind, inevitably producing non-manifold meshes, inverted normals, and structurally impossible artifacts.

Architecturally, the Print3D Skill must elevate visual validation from a peripheral, bolted-on feature to a core systemic loop. This requires integrating multimodal vision-language models (VLMs)—such as GPT-4o, Claude 3.5 Sonnet, or Gemini 2.5 Pro—directly into the iterative design process, utilizing the agent's ability to "see" its own output.

### **Multi-Angle Rendering Integration**

To properly validate a 3D construct, a single isometric render is vastly insufficient, as it hides the reverse side and obscures internal geometries. The architecture must enforce a multi-view projection methodology. When the agent generates a CAD file, the SKILL.md must instruct it to invoke a rendering script or dedicated MCP tool (such as the rendering engine found in quellant/openscad-mcp 45). The tool must be programmed to automatically generate orthographic projections—front, top, side, and isometric views—and dynamically combine these into a single, consolidated image grid encoded in Base64.

These multi-view images are then fed directly back into the agent's active context window. Crucially, the skill instructions must contain specific "inspective prompts." The prompt engineering here must guide the agent beyond generic observation, instructing it to evaluate specific physical and spatial constraints 46:

* Are there floating, unattached manifolds or disconnected artifacts?  
* Do the boolean subtractions (holes, cutouts) cleanly intersect the intended planes without leaving micro-artifacts?  
* Are the wall thicknesses sufficient for Fused Deposition Modeling (FDM) printing tolerances?  
* Is the base geometry flat enough to guarantee bed adhesion without excessive raft generation?

Empirical research across AI-driven CAD frameworks demonstrates that this iterative visual feedback loop—where the multimodal agent perceives the render, identifies lacking constraints, and autonomously revises the spatial code—dramatically increases the success rate of complex geometric generation compared to blind, text-only iteration.47

### **Conditional Rendering and Token Economics**

While visual feedback is vital for structural success, rendering and analyzing high-resolution images after every minor code alteration is computationally prohibitive. It will rapidly exhaust the model's vision token limits, trigger API rate limits, and introduce unacceptable latency into the workflow. Consequently, the skill architecture must implement rigid "Conditional Rendering" logic.50

The SKILL.md should establish strict heuristic boundaries for when an image render is permitted. For example, the routing instructions should dictate that the agent only triggers the rendering tool when a primary structural component is fully drafted, or when a major boolean operation (like an intersection or union) is completed. Micro-edits—such as changing a chamfer radius from 2.0mm to 2.5mm, renaming a variable, or formatting code structure—should bypass the visual validation loop entirely unless specifically requested by the user. By embedding this conditional logic, the agent conserves context bandwidth and computational budget while maintaining absolute structural safety.

## **Strategies for Cross-Platform Portability**

The ultimate design goal of the Print3D Skill is true universality across the highly competitive ecosystems of Claude Code, OpenAI Codex, and Google Gemini CLI. While these platforms possess divergent underlying architectures, the recent stabilization and widespread adoption of the agentskills.io standard provides a highly viable path for establishing a single source of truth.

### **The Unified Directory Structure**

All three major AI agent platforms have converged on a shared directory discovery mechanism. By housing the capability in a project-root .agents/skills/print3d-skill/ directory, or a globally accessible \~/.agents/skills/print3d-skill/ directory, the skill becomes automatically discoverable and parsable by Claude, Codex, and Gemini simultaneously, without requiring platform-specific installation commands.13

To maintain this portability, the directory structure must encapsulate the domain complexity cleanly, following a standardized layout:

| Directory/File | Purpose and Content | Platform Handling |
| :---- | :---- | :---- |
| SKILL.md | The core entry point. Contains YAML metadata for trigger routing and the primary workflow instructions. | Read by all platforms. OpenAI translates to JSON schema; Gemini maps to Extension config; Claude injects directly. |
| references/ | Deep domain knowledge (BOSL2 syntax manuals, Klipper API specs, Slicer profiles). | Loaded on demand via agent file-read tools. Universally supported. |
| scripts/ | Lightweight, platform-agnostic configuration scripts (e.g., install\_mcp.sh). | Executed via Claude's bash, Codex's container\_auto shell, or Gemini's local terminal. |
| assets/ | Base templates, default configuration files, and starter .scad documents. | Accessed via standard file-read operations. |

### **Platform-Agnostic Instruction Design**

To ensure the SKILL.md functions correctly across distinct AI inference engines, the instruction set must completely avoid platform-specific invocation syntax or proprietary tool assumptions.

Developers must not rely on proprietary tool names. For instance, Anthropic relies heavily on its native bash tool, while OpenAI relies on its containerized shell tool. The instructions should use generic, descriptive language: "Execute the script located at scripts/validate.py using your available command-line execution tool." The underlying LLM is capable enough to map the generic instruction to its specific available toolset.

Furthermore, schema abstraction is paramount. The skill author must not embed raw JSON function calling schemas directly into the markdown body. OpenAI will automatically translate the SKILL.md YAML frontmatter into its required OpenAPI 3.0 schema during initialization 16, while Gemini will handle the filesystem access and tool routing via its native extension protocols.20 By keeping the SKILL.md written in clear, declarative Markdown prose, the cognitive load is reduced for the agent, and the platforms are free to handle the technical execution mapping internally.

### **Fallback Mechanisms and Graceful Degradation**

Because the availability of local binaries (like OpenSCAD), persistent MCP servers, or specific network configurations will vary wildly depending on the user's host environment, the skill must implement graceful degradation.

The SKILL.md should define a mandatory bootstrap verification phase. When activated, the agent should first check the environment (e.g., "Verify if the OpenSCAD binary is available in the system PATH" or "Query the tool registry to check if the mcp-3D-printer-server tools are connected"). If a required component or server is missing, the skill instructions must explicitly guide the agent to halt the process, notify the user, and offer the automated bootstrap script (scripts/install\_mcp.sh), rather than attempting to hallucinate a failed execution path or write raw API requests from scratch.

## **Proposed SKILL.md Skeleton for Print3D Capability**

Based on the extensive synthesis of progressive disclosure patterns, phased workflows, and hybrid execution architectures, the following represents the optimal skeleton for the primary SKILL.md file. It leverages concise metadata for efficient routing, distinct workflow branching to prevent context bleed, and explicit instructions for conditional visual validation and MCP tool integration.

## ---

**name: print3d-skill description: Full-stack 3D printing capabilities. Parametric OpenSCAD/BOSL2 generation, multi-angle visual validation, mesh repair, slicer orchestration, and Bambu/OctoPrint hardware control. Use when designing physical objects or managing 3D printers. version: 1.0.0**

# **Print3D Orchestration Skill**

You are an expert mechanical engineer and additive manufacturing specialist. You coordinate a full-stack workflow from parametric CAD generation to physical hardware printing.

## **Core Behavioral Principles**

1. **Never guess spatial geometry:** Rely strictly on visual validation and multi-angle renders.  
2. **Hardware Safety:** Never execute hardware commands blindly. Always require a user STOP GATE before sending G-code to a physical printer.  
3. **Execution Delegation:** For heavy STL manipulation or continuous printer communication, rely exclusively on your connected 3D-printer MCP tools.

## **Environment Verification**

Before beginning any workflow, verify that the required MCP tools (e.g., slice\_stl, get\_printer\_status, generate\_stl\_visualization) are available in your tool registry. If they are missing, alert the user and offer to run scripts/install\_mcp.sh.

## **Workflow Routing**

Identify the user's core request and execute ONLY the relevant procedural phase below. Do not load reference documents for phases you are not currently executing.

### **Phase 1: Parametric CAD Generation**

*Triggered when designing, generating, or modifying a 3D object.*

1. If the user requests advanced shapes, load references/bosl2\_best\_practices.md to understand syntax constraints.  
2. Generate the OpenSCAD code cleanly.  
3. Once the base structural geometry is drafted, proceed immediately to Phase 2\. Do NOT proceed to slicing or hardware control.

### **Phase 2: Visual Validation & Iteration (Conditional)**

*Triggered ONLY after major geometric generation or structural boolean changes. Do not execute for minor variable edits.*

1. Execute the rendering tool/script to generate a consolidated image grid (isometric, top, and front views) of the .scad file.  
2. Inspective Analysis: Carefully inspect the generated multi-view images. Look for floating artifacts, failed boolean intersections, and proper FDM wall thickness.  
3. If errors are found, revise the code and loop Phase 2\. If visually perfect, await user confirmation.  
   **STOP GATE:** Present the visual render to the user. Do not proceed to Phase 3 or 4 without explicit user approval of the physical geometry.

### **Phase 3: Mesh Processing and Repair**

*Triggered when handling imported STLs, repairing meshes, or finalizing a design.*

1. If mesh repair is needed, load references/mesh\_manifold\_rules.md.  
2. Use your available MCP tools (e.g., modify\_stl\_section, extend\_stl\_base) to manipulate the physical mesh rather than rewriting code.

### **Phase 4: Slicer and Hardware Orchestration**

*Triggered when the user requests to print a visually validated artifact.*

1. Load references/slicer\_profiles.md to identify correct G-code parameters based on the requested material.  
2. Utilize the MCP server's slice\_stl tool to generate the final G-code.  
3. Query the hardware state using get\_printer\_status. Ensure the bed is clear and temperatures are within safe thresholds.  
4. **STOP GATE:** Prompt the user for final physical confirmation before invoking start\_print.

## **Error Handling**

If an OpenSCAD compilation fails, or an MCP tool returns an error, do not hallucinate a code fix. Read the error trace, hypothesize the mechanical, geometric, or network failure, and present the structured diagnosis to the user.

## **Synthesized Conclusions**

The construction of a universal, hardware-interfacing AI capability requires moving significantly beyond naive prompt engineering and into the realm of robust, fault-tolerant systems architecture.

By adopting the open agentskills.io standard as the foundational source of truth, developers can guarantee capability portability across the Claude Code, OpenAI Codex, and Google Gemini CLI ecosystems, allowing the respective platforms to handle the complex translation into proprietary schemas or extensions. To manage the immense technical complexity of the 3D printing domain—which spans code generation, geometric mathematics, and network hardware control—the architecture must implement a strict progressive disclosure model. This ensures the LLM only consumes context pertinent to the immediate phase of the manufacturing pipeline, preserving token limits and analytical focus.

Furthermore, because large language models inherently lack intrinsic spatial awareness, a mandatory, multi-angle visual feedback loop is not merely a supplementary feature—it is an absolute architectural necessity for reliable geometric validation. Finally, while local embedded scripts offer frictionless deployment, offloading computationally heavy tasks and stateful hardware communication to a containerized Model Context Protocol (MCP) server creates a hybrid orchestration framework. This hybrid model leverages the cognitive routing power of the skill alongside the secure, token-efficient execution of the protocol, establishing a highly scalable blueprint for the next generation of physical-world AI agents.

#### **Works cited**

1. Specification and documentation for Agent Skills \- GitHub, accessed March 14, 2026, [https://github.com/agentskills/agentskills](https://github.com/agentskills/agentskills)  
2. WHAT ARE AGENT SKILLS?, accessed March 14, 2026, [https://medium.com/@tahirbalarabe2/what-are-agent-skills-c7793b206daf](https://medium.com/@tahirbalarabe2/what-are-agent-skills-c7793b206daf)  
3. Use Agent Skills in VS Code, accessed March 14, 2026, [https://code.visualstudio.com/docs/copilot/customization/agent-skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)  
4. The SKILL.md Pattern: How to Write AI Agent Skills That Actually Work | by Bibek Poudel, accessed March 14, 2026, [https://bibek-poudel.medium.com/the-skill-md-pattern-how-to-write-ai-agent-skills-that-actually-work-72a3169dd7ee](https://bibek-poudel.medium.com/the-skill-md-pattern-how-to-write-ai-agent-skills-that-actually-work-72a3169dd7ee)  
5. Fatih Kadir Akın (@f) | prompts.chat, accessed March 14, 2026, [https://prompts.chat/@f](https://prompts.chat/@f)  
6. Agent Skills \- Claude API Docs, accessed March 14, 2026, [https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)  
7. artkulak/repo2file: Dump selected files from your repo into single file to easily use in LLMs (Claude, Openai, etc..) \- GitHub, accessed March 14, 2026, [https://github.com/artkulak/repo2file](https://github.com/artkulak/repo2file)  
8. GitHub \- cased/kit: The toolkit for AI devtools context engineering. Build with codebase mapping, symbol extraction, and many kinds of code search., accessed March 14, 2026, [https://github.com/cased/kit](https://github.com/cased/kit)  
9. How do you handle LLM scans when files reference each other? : r/LLMDevs \- Reddit, accessed March 14, 2026, [https://www.reddit.com/r/LLMDevs/comments/1ofd9ln/how\_do\_you\_handle\_llm\_scans\_when\_files\_reference/](https://www.reddit.com/r/LLMDevs/comments/1ofd9ln/how_do_you_handle_llm_scans_when_files_reference/)  
10. Demystifying OpenAI Function Calling vs Anthropic's Model Context Protocol (MCP), accessed March 14, 2026, [https://evgeniisaurov.medium.com/demystifying-openai-function-calling-vs-anthropics-model-context-protocol-mcp-b5e4c7b59ac2](https://evgeniisaurov.medium.com/demystifying-openai-function-calling-vs-anthropics-model-context-protocol-mcp-b5e4c7b59ac2)  
11. Function calling | OpenAI API, accessed March 14, 2026, [https://developers.openai.com/api/docs/guides/function-calling/](https://developers.openai.com/api/docs/guides/function-calling/)  
12. OpenAI Launches Anthropic‑Style 'Skills' System for ChatGPT \- UBOS.tech, accessed March 14, 2026, [https://ubos.tech/news/openai-launches-anthropic%E2%80%91style-skills-system-for-chatgpt/](https://ubos.tech/news/openai-launches-anthropic%E2%80%91style-skills-system-for-chatgpt/)  
13. Using skills to accelerate OSS maintenance \- OpenAI for developers, accessed March 14, 2026, [https://developers.openai.com/blog/skills-agents-sdk/](https://developers.openai.com/blog/skills-agents-sdk/)  
14. Building Agent Skills from Scratch \- DEV Community, accessed March 14, 2026, [https://dev.to/onlyoneaman/building-agent-skills-from-scratch-lbl](https://dev.to/onlyoneaman/building-agent-skills-from-scratch-lbl)  
15. From model to agent: Equipping the Responses API with a computer environment | OpenAI, accessed March 14, 2026, [https://openai.com/index/equip-responses-api-computer-environment](https://openai.com/index/equip-responses-api-computer-environment)  
16. Skills in OpenAI API, accessed March 14, 2026, [https://developers.openai.com/cookbook/examples/skills\_in\_api/](https://developers.openai.com/cookbook/examples/skills_in_api/)  
17. Function calling using the Gemini API | Firebase AI Logic \- Google, accessed March 14, 2026, [https://firebase.google.com/docs/ai-logic/function-calling](https://firebase.google.com/docs/ai-logic/function-calling)  
18. Function calling reference | Generative AI on Vertex AI \- Google Cloud Documentation, accessed March 14, 2026, [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/function-calling](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/function-calling)  
19. Functions vs Extensions in AI Agents: A Practical Guide to Powering Generative AI \- Medium, accessed March 14, 2026, [https://medium.com/@ronivaldo/functions-vs-extensions-in-ai-agents-a-practical-guide-to-powering-generative-ai-0b133a578b51](https://medium.com/@ronivaldo/functions-vs-extensions-in-ai-agents-a-practical-guide-to-powering-generative-ai-0b133a578b51)  
20. Agent Skills | Gemini CLI, accessed March 14, 2026, [https://geminicli.com/docs/cli/skills/](https://geminicli.com/docs/cli/skills/)  
21. Gemini CLI Skills: Google Just Made AI Workflows Actually Usable : r/AISEOInsider \- Reddit, accessed March 14, 2026, [https://www.reddit.com/r/AISEOInsider/comments/1r62k2d/gemini\_cli\_skills\_google\_just\_made\_ai\_workflows/](https://www.reddit.com/r/AISEOInsider/comments/1r62k2d/gemini_cli_skills_google_just_made_ai_workflows/)  
22. Agent Skills vs MCP: Technical Comparison \- K-Dense AI, accessed March 14, 2026, [https://www.k-dense.ai/examples/session\_20251231\_185247\_6dce8fea6faa/writing\_outputs/final/agent\_skills\_vs\_mcp\_report.pdf](https://www.k-dense.ai/examples/session_20251231_185247_6dce8fea6faa/writing_outputs/final/agent_skills_vs_mcp_report.pdf)  
23. Model Context Protocol architecture patterns for multi-agent AI systems \- IBM Developer, accessed March 14, 2026, [https://developer.ibm.com/articles/mcp-architecture-patterns-ai-systems/](https://developer.ibm.com/articles/mcp-architecture-patterns-ai-systems/)  
24. Model Context Protocol (MCP) vs Agent Skills: Empowering AI Agents with Tools and Expertise | by ByteBridge | Jan, 2026, accessed March 14, 2026, [https://bytebridge.medium.com/model-context-protocol-mcp-vs-agent-skills-empowering-ai-agents-with-tools-and-expertise-3062acafd4f7](https://bytebridge.medium.com/model-context-protocol-mcp-vs-agent-skills-empowering-ai-agents-with-tools-and-expertise-3062acafd4f7)  
25. Code execution with MCP: building more efficient AI agents \- Anthropic, accessed March 14, 2026, [https://www.anthropic.com/engineering/code-execution-with-mcp](https://www.anthropic.com/engineering/code-execution-with-mcp)  
26. AI Agent Architecture via A2A/MCP | by Jeffrey Richter \- Medium, accessed March 14, 2026, [https://medium.com/@jeffreymrichter/ai-agent-architecture-via-a2a-mcp-b864080c4bbc](https://medium.com/@jeffreymrichter/ai-agent-architecture-via-a2a-mcp-b864080c4bbc)  
27. Effective context engineering for AI agents \- Anthropic, accessed March 14, 2026, [https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)  
28. code-execution-with-MCP/skills/mcp-builder/SKILL.md at main \- GitHub, accessed March 14, 2026, [https://github.com/ArtemisAI/code-execution-with-MCP/blob/main/skills/mcp-builder/SKILL.md?plain=1](https://github.com/ArtemisAI/code-execution-with-MCP/blob/main/skills/mcp-builder/SKILL.md?plain=1)  
29. Analyzing mcp-builder: A Complete Guide to MCP Server Development \- Skills, accessed March 14, 2026, [https://skills.deeptoai.com/en/docs/development/analyzing-mcp-builder](https://skills.deeptoai.com/en/docs/development/analyzing-mcp-builder)  
30. Working on a skill that links web search, podcast search, rss feed understanding, and my web/android \- Friends of the Crustacean \- Answer Overflow, accessed March 14, 2026, [https://www.answeroverflow.com/m/1477922876597469295?focus=1477922876597469295](https://www.answeroverflow.com/m/1477922876597469295?focus=1477922876597469295)  
31. bambu-studio-ai \- SkillWink, accessed March 14, 2026, [https://www.skillwink.com/skill/1638?lang=en](https://www.skillwink.com/skill/1638?lang=en)  
32. Single-responsibility agents and multi-agent workflows in AI-powered development tools, accessed March 14, 2026, [https://www.epam.com/insights/ai/blogs/single-responsibility-agents-and-multi-agent-workflows](https://www.epam.com/insights/ai/blogs/single-responsibility-agents-and-multi-agent-workflows)  
33. Breyta | Build workflows with your coding agents, accessed March 14, 2026, [https://breyta.ai/](https://breyta.ai/)  
34. Agent Skills | Microsoft Learn, accessed March 14, 2026, [https://learn.microsoft.com/en-us/agent-framework/agents/skills](https://learn.microsoft.com/en-us/agent-framework/agents/skills)  
35. Skill authoring best practices \- Claude API Docs, accessed March 14, 2026, [https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)  
36. Unlocking AI-Powered 3D Modeling: A Deep Dive into trikos529's OpenSCAD MCP Server, accessed March 14, 2026, [https://skywork.ai/skypage/en/ai-3d-modeling-openscad/1980065548520247296](https://skywork.ai/skypage/en/ai-3d-modeling-openscad/1980065548520247296)  
37. jabberjabberjabber/openscad-mcp: Let an LLM create openscad models \- GitHub, accessed March 14, 2026, [https://github.com/jabberjabberjabber/openscad-mcp](https://github.com/jabberjabberjabber/openscad-mcp)  
38. Dmontgomery40 MCP 3D Printer Server \- AIBase, accessed March 14, 2026, [https://mcp.aibase.com/server/1916354823803871234](https://mcp.aibase.com/server/1916354823803871234)  
39. The New Frontier of 3D Printing: A Deep Dive into DMontgomery40's MCP Server, accessed March 14, 2026, [https://skywork.ai/skypage/en/3d-printing-dmontgomery40-mcp-server/1977622237076197376](https://skywork.ai/skypage/en/3d-printing-dmontgomery40-mcp-server/1977622237076197376)  
40. How Context-First MCP Design Reduces Agent Failures on Backend Tasks, accessed March 14, 2026, [https://astrodevil.medium.com/how-context-first-mcp-design-reduces-agent-failures-on-backend-tasks-3b3b5bae796a](https://astrodevil.medium.com/how-context-first-mcp-design-reduces-agent-failures-on-backend-tasks-3b3b5bae796a)  
41. The Ultimate Guide to esa MCP Server: Your AI's Bridge to Smarter Document Management, accessed March 14, 2026, [https://skywork.ai/skypage/en/esa-mcp-server-ai-document-management/1981614608929058816](https://skywork.ai/skypage/en/esa-mcp-server-ai-document-management/1981614608929058816)  
42. MCP 3D Printer Server, accessed March 14, 2026, [https://mcpservers.org/servers/DMontgomery40/mcp-3D-printer-server](https://mcpservers.org/servers/DMontgomery40/mcp-3D-printer-server)  
43. MCP or Skills for delivering extra context to AI agents? : r/AI\_Agents \- Reddit, accessed March 14, 2026, [https://www.reddit.com/r/AI\_Agents/comments/1r0ynp1/mcp\_or\_skills\_for\_delivering\_extra\_context\_to\_ai/](https://www.reddit.com/r/AI_Agents/comments/1r0ynp1/mcp_or_skills_for_delivering_extra_context_to_ai/)  
44. All LLMs have struggled helping me generate OpenSCAD models for 3D prin... | Hacker News, accessed March 14, 2026, [https://news.ycombinator.com/item?id=45327538](https://news.ycombinator.com/item?id=45327538)  
45. OpenSCAD MCP Server \- LobeHub, accessed March 14, 2026, [https://lobehub.com/pl/mcp/quellant-openscad-mcp](https://lobehub.com/pl/mcp/quellant-openscad-mcp)  
46. (PDF) 3D-printed Architectural Structures Created Using Artificial Intelligences: A Review of Techniques and Applications \- ResearchGate, accessed March 14, 2026, [https://www.researchgate.net/publication/372690971\_3D-printed\_Architectural\_Structures\_Created\_Using\_Artificial\_Intelligences\_A\_Review\_of\_Techniques\_and\_Applications](https://www.researchgate.net/publication/372690971_3D-printed_Architectural_Structures_Created_Using_Artificial_Intelligences_A_Review_of_Techniques_and_Applications)  
47. From text to design: a framework to leverage LLM agents for automated CAD generation, accessed March 14, 2026, [https://www.cambridge.org/core/journals/proceedings-of-the-design-society/article/from-text-to-design-a-framework-to-leverage-llm-agents-for-automated-cad-generation/5BD8D63CFCED28BDD7A01313162FFBE7](https://www.cambridge.org/core/journals/proceedings-of-the-design-society/article/from-text-to-design-a-framework-to-leverage-llm-agents-for-automated-cad-generation/5BD8D63CFCED28BDD7A01313162FFBE7)  
48. SCENECRAFT: AN LLM AGENT FOR SYNTHESIZING 3D SCENE AS BLENDER CODE \- OpenReview, accessed March 14, 2026, [https://openreview.net/pdf/459bf90d894ce1362ced0dd2fe0df351405931ad.pdf](https://openreview.net/pdf/459bf90d894ce1362ced0dd2fe0df351405931ad.pdf)  
49. Follow-Your-Instruction: A Comprehensive MLLM Agent for World Data Synthesis \- arXiv.org, accessed March 14, 2026, [https://arxiv.org/pdf/2508.05580](https://arxiv.org/pdf/2508.05580)  
50. How to Design High-Performance Salesforce UX with Lightning Design? | Medium, accessed March 14, 2026, [https://medium.com/@alliancetek/design-high-performance-salesforce-ux-with-lightning-design-0abee19b3f62](https://medium.com/@alliancetek/design-high-performance-salesforce-ux-with-lightning-design-0abee19b3f62)  
51. Agent orchestration for design systems | by Cristian Morales Achiardi | Jan, 2026, accessed March 14, 2026, [https://www.designsystemscollective.com/agent-orchestration-for-design-systems-da0f6a5f24fb](https://www.designsystemscollective.com/agent-orchestration-for-design-systems-da0f6a5f24fb)  
52. huggingface/skills \- GitHub, accessed March 14, 2026, [https://github.com/huggingface/skills](https://github.com/huggingface/skills)