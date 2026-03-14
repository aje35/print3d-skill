# Quickstart: Parametric CAD Generation

**Feature**: 003-parametric-cad
**Date**: 2026-03-14

## Scenario 1: Start a Design Session and Submit Code

```python
from print3d_skill.create import start_session, submit_iteration
from print3d_skill.models import DesignRequest, CreateConfig

request = DesignRequest(
    description="A wall-mount bracket for a Raspberry Pi 4 with screw holes",
    dimensions={"width": 65, "depth": 35, "height": 25},
    material="PLA",
)
config = CreateConfig(render_previews=True, max_iterations=5)

session = start_session(request, config)

# Agent generates OpenSCAD code and submits it
scad_code = """
// Wall-mount bracket for Raspberry Pi 4
wall_thickness = 2;
width = 65;
depth = 35;
height = 25;

module bracket() {
    difference() {
        cube([width, depth, height]);
        translate([wall_thickness, wall_thickness, wall_thickness])
            cube([width - 2*wall_thickness, depth - 2*wall_thickness, height]);
    }
}

bracket();
"""

result = submit_iteration(session, scad_code)
print(f"Compile: {'OK' if result.compile_success else 'FAILED'}")
print(f"Preview: {result.preview_path}")
```

Expected output:
```
Compile: OK
Preview: /tmp/.../design_v1_preview.png
```

## Scenario 2: Handle Compile Error and Iterate

```python
# Submit code with a syntax error
bad_code = "cube([10, 20, 30);"  # missing bracket

result = submit_iteration(session, bad_code)
print(f"Compile: {'OK' if result.compile_success else 'FAILED'}")
print(f"Error: {result.compile_error[:80]}")

# Agent fixes the error and resubmits
fixed_code = "cube([10, 20, 30]);"
result = submit_iteration(session, fixed_code, changes="Fixed syntax error")
print(f"Compile: {'OK' if result.compile_success else 'FAILED'}")
print(f"Iteration: {result.iteration}")
```

Expected output:
```
Compile: FAILED
Error: ERROR: Parser error in line 1 ...
Compile: OK
Iteration: 3
```

## Scenario 3: Validate Printability

```python
from print3d_skill.create.printability import validate_printability
from print3d_skill.models import CreateConfig

config = CreateConfig(
    nozzle_diameter=0.4,
    min_wall_thickness=0.8,
    max_overhang_angle=45.0,
)

report = validate_printability("bracket.stl", config=config)

print(f"Printable: {report.is_printable}")
print(f"Checks: {report.passed_checks}/{report.total_checks}")
for w in report.warnings:
    print(f"  [{w.severity}] {w.rule}: {w.suggestion}")
```

Expected output for a model with thin walls:
```
Printable: False
Checks: 3/4
  [error] min_wall_thickness: Wall at front face is 0.3mm — increase to 0.8mm for 0.4mm nozzle
```

## Scenario 4: Export Final Design

```python
from print3d_skill.create import export_design

export = export_design(session, output_dir="/output")

print(f"Source: {export.scad_path}")
for fmt, path in export.mesh_paths.items():
    print(f"  {fmt}: {path}")
print(f"Iterations: {export.total_iterations}")
print(f"Printable: {export.printability_report.is_printable}")
```

Expected output:
```
Source: /output/bracket.scad
  stl: /output/bracket.stl
  3mf: /output/bracket.3mf
Iterations: 2
Printable: True
```

## Scenario 5: Detect BOSL2 Availability

```python
from print3d_skill.create.bosl2 import detect_bosl2

if detect_bosl2():
    print("BOSL2 available — using rounded boxes, threads, etc.")
else:
    print("BOSL2 not installed — using native OpenSCAD primitives only")
```

## Scenario 6: Query Create Mode Knowledge

```python
from print3d_skill import query_knowledge

# Get tolerance tables
results = query_knowledge(mode="create", problem_type="lookup_table")
for kf in results:
    print(f"  {kf.metadata.topic}")

# Get design patterns
results = query_knowledge(mode="create", problem_type="design_pattern")
for kf in results:
    print(f"  {kf.metadata.topic}")
```

## Scenario 7: Create Mode via Router

```python
from print3d_skill import route

response = route(
    "create",
    description="A simple phone stand, 80mm wide",
    material="PLA",
)
print(f"Status: {response.status}")
print(f"Message: {response.message}")
```
