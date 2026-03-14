# Quickstart: Model Modification (004)

**Branch**: `004-model-modification` | **Date**: 2026-03-14

## Basic Usage

### Cut a hole through a model

```python
from print3d_skill import modify_mesh

result = modify_mesh(
    mesh_path="bracket.stl",
    operation="boolean",
    boolean_type="difference",
    primitive_type="cylinder",
    primitive_dimensions={"diameter": 6.0, "height": 30.0},
    primitive_position=(15.0, 10.0, 0.0),
)

print(result.output_mesh_paths[0])   # "bracket_modified.stl"
print(result.warnings)               # [] if clean, or repair/empty warnings
print(result.analysis_report.health_score)  # 0.0-1.0
```

### Merge two models

```python
result = modify_mesh(
    mesh_path="base.stl",
    operation="boolean",
    boolean_type="union",
    tool_mesh_path="lid.stl",
)
```

### Scale a model to a specific width

```python
result = modify_mesh(
    mesh_path="phone_stand.stl",
    operation="scale",
    scale_mode="dimension_target",
    target_axis="x",
    target_value_mm=80.0,
)

print(f"Before: {result.bbox_before}")
print(f"After:  {result.bbox_after}")

# Check for scaling warnings (e.g., screw holes no longer standard)
for w in result.feature_warnings:
    print(f"Warning: {w.message}")
```

### Uniform scaling

```python
result = modify_mesh("model.stl", operation="scale", scale_mode="uniform", factor=1.5)
```

### Combine and align models

```python
result = modify_mesh(
    mesh_path="box.stl",
    operation="combine",
    other_mesh_paths=["handle.stl"],
    alignment="top",
    offset=(0.0, 0.0, 0.0),
)
```

### Engrave text

```python
result = modify_mesh(
    mesh_path="case.stl",
    operation="engrave",
    text="v2.1",
    text_mode="engrave",
    font_size=8.0,
    depth=0.6,
    surface="bottom",
)
```

### Split a model for printing in parts

```python
result = modify_mesh(
    mesh_path="tall_vase.stl",
    operation="split",
    split_axis="z",
    split_offset_mm=100.0,
    pin_diameter=4.0,
)

print(result.output_mesh_paths)  # ["tall_vase_bottom.stl", "tall_vase_top.stl"]
print(len(result.alignment_features))  # Number of pins/holes added
```

## Chaining Operations

Each operation produces a new file. Chain by passing the output as the next input:

```python
# Step 1: Scale to target size
r1 = modify_mesh("widget.stl", operation="scale", scale_mode="uniform", factor=1.2)

# Step 2: Cut mounting holes
r2 = modify_mesh(
    r1.output_mesh_paths[0],
    operation="boolean",
    boolean_type="difference",
    primitive_type="cylinder",
    primitive_dimensions={"diameter": 3.4, "height": 20.0},
    primitive_position=(5.0, 5.0, 0.0),
)

# Step 3: Engrave version text
r3 = modify_mesh(
    r2.output_mesh_paths[0],
    operation="engrave",
    text="v3",
    surface="top",
)
```

## Via Mode Router

```python
from print3d_skill import route

response = route(
    "modify",
    mesh_path="model.stl",
    operation="scale",
    scale_mode="uniform",
    factor=1.5,
)

if response.status == "success":
    result = response.data  # ModifyResult
    print(result.output_mesh_paths[0])
else:
    print(f"Error: {response.message}")
```

## Visual Comparison

Every operation produces before/after previews automatically:

```python
result = modify_mesh("part.stl", operation="scale", scale_mode="uniform", factor=0.8)

print(result.before_preview_path)   # "part_before.png"
print(result.after_preview_paths)   # ["part_modified_preview.png"]
# Both PNGs use identical camera angles for easy comparison
```
