# Quickstart: Core Infrastructure

**Feature**: 001-core-infrastructure
**Date**: 2026-03-14

## Install

```bash
pip install print3d-skill
```

Core features work immediately. No system packages needed.

## Render a Mesh Preview

```python
from print3d_skill import render_preview

result = render_preview("model.stl", "preview.png")
print(f"Preview saved to {result.image_path}")
print(f"Resolution: {result.resolution}")
print(f"Render time: {result.render_time_seconds:.1f}s")

if result.warnings:
    for w in result.warnings:
        print(f"Warning: {w}")
```

Output: a 1600x1200 PNG with front, side, top, and isometric views.

## Check Available Tools

```python
from print3d_skill import list_capabilities, system_info

# Quick summary
info = system_info()
print(f"print3d-skill v{info.package_version}")
print(f"Core ready: {info.core_available}")
print(f"Extended available: {info.extended_available}")
print(f"Missing: {info.missing_extended}")

# Detailed capability list
for cap in list_capabilities():
    status = "available" if cap.is_available else "missing"
    print(f"  {cap.name}: {status}")
    if not cap.is_available:
        print(f"    Install: {cap.install_instructions}")
```

## Query Domain Knowledge

```python
from print3d_skill import query_knowledge

# Get tolerance tables for PLA in create mode
results = query_knowledge(mode="create", material="PLA")
for kf in results:
    print(f"Topic: {kf.metadata.topic}")
    print(f"Data: {kf.data}")

# Get all fix-mode knowledge (wildcard other fields)
fix_knowledge = query_knowledge(mode="fix")
```

## Route to a Mode

```python
from print3d_skill import route

response = route("fix", mesh_path="broken.stl")
print(f"Mode: {response.mode}")
print(f"Status: {response.status}")
# Currently returns status="not_implemented" for all modes
```

## Use a Specific Tool

```python
from print3d_skill import get_capability

try:
    mesh_tools = get_capability("mesh_loading")
    print(f"Using: {mesh_tools.name}")
except Exception as e:
    print(f"Not available: {e}")
```

## Optional: OpenSCAD Rendering

Install OpenSCAD via your system package manager:

```bash
# macOS
brew install openscad

# Ubuntu/Debian
sudo apt install openscad

# Windows
choco install openscad
```

Then render .scad files:

```python
from print3d_skill import render_preview

result = render_preview("model.scad", "preview.png")
# Compiles .scad → STL → multi-angle PNG
```

## Verify Installation

```python
from print3d_skill import system_info

info = system_info()
assert info.core_available, "Core features not working!"
print("All core features ready.")
```
