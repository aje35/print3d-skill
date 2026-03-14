# Public API Contract: Core Infrastructure

**Feature**: 001-core-infrastructure
**Date**: 2026-03-14

This document defines the public API surface that consumers
(agent workflows, mode implementations, external callers) depend on.
These signatures are the contract — internal implementation may
change, but these function signatures, parameter names, and return
types are stable.

## Rendering API

```python
def render_preview(
    mesh_path: str,
    output_path: str,
    resolution: tuple[int, int] = (1600, 1200),
    timeout_seconds: float = 30.0,
) -> PreviewResult:
    """Render a multi-angle preview of a mesh file.

    Accepts STL, 3MF, OBJ mesh files. Also accepts .scad files
    if OpenSCAD CLI is available.

    Returns PreviewResult with the path to the output PNG,
    render metadata, and any warnings (unit mismatch, high
    face count).

    Raises:
        FileNotFoundError: mesh_path does not exist
        MeshLoadError: file is corrupt or unreadable
        UnsupportedFormatError: file format not recognized
        RenderTimeoutError: rendering exceeded timeout_seconds
        ScadCompileError: .scad file has syntax errors (includes
            compiler output in the exception message)
        CapabilityUnavailable: .scad file given but OpenSCAD
            not installed
    """
```

## Tool Orchestration API

```python
def get_capability(name: str) -> ToolProvider:
    """Get a tool provider for the named capability.

    Raises:
        CapabilityUnavailable: no provider available for this
            capability. Exception includes: capability name,
            tool that would provide it, install instructions.
    """

def list_capabilities() -> list[ToolCapability]:
    """List all known capabilities and their availability status.

    Returns a list of ToolCapability objects, each with name,
    description, tier, availability, and install instructions
    if unavailable.
    """

def refresh_capabilities() -> list[ToolCapability]:
    """Re-detect all tool availability and return updated list.

    Use after installing a new tool mid-session.
    """
```

## Knowledge System API

```python
def query_knowledge(
    mode: str | None = None,
    material: str | None = None,
    printer: str | None = None,
    problem_type: str | None = None,
) -> list[KnowledgeFile]:
    """Query the knowledge base with context filters.

    Uses AND matching: all specified fields must match.
    Unspecified fields (None) act as wildcards.

    A knowledge file matches a field if:
    - The file's metadata list for that field contains the
      query value, OR
    - The file's metadata list is empty (meaning "applies to all")

    Returns matching KnowledgeFile objects with their data.
    Returns an empty list (not an error) when nothing matches.
    """
```

## Skill Router API

```python
def route(mode: str, **context) -> ModeResponse:
    """Dispatch to the appropriate workflow handler.

    Valid modes: "create", "fix", "modify", "diagnose", "validate"

    Returns ModeResponse with status and result data.
    For unimplemented handlers, status is "not_implemented".

    Raises:
        InvalidModeError: mode string not recognized.
            Exception message lists valid modes.
    """
```

## System Info API

```python
def system_info() -> SystemInfo:
    """Report package version, capabilities, and missing deps.

    Returns SystemInfo with complete capability inventory.
    """
```

## Exception Hierarchy

```text
Print3DSkillError (base)
├── MeshLoadError           # Corrupt/unreadable mesh file
├── UnsupportedFormatError  # Unrecognized file format
├── RenderTimeoutError      # Render exceeded timeout
├── ScadCompileError        # OpenSCAD syntax/compile error
├── CapabilityUnavailable   # Requested capability not installed
├── InvalidModeError        # Unrecognized mode identifier
└── KnowledgeSchemaError    # Knowledge file fails validation
```

## Data Classes (return types)

All return types are Python dataclasses defined in
`print3d_skill.models`. See data-model.md for full field
definitions. Key types:

- `PreviewResult` — rendering output
- `ToolCapability` — capability status
- `ToolProvider` — tool wrapper info
- `KnowledgeFile` — matched knowledge with data
- `ModeResponse` — mode handler result
- `SystemInfo` — package capability summary
