# Quickstart: Mesh Analysis & Repair

**Feature**: 002-mesh-analysis-repair
**Date**: 2026-03-14

## Scenario 1: Analyze a Mesh for Defects

```python
from print3d_skill import analyze_mesh

report = analyze_mesh("model.stl")

print(f"Health: {report.classification.value} (score: {report.health_score:.2f})")
print(f"Shells: {report.shell_count}")
print(f"Defects: {len(report.defects)}")

for defect in report.defects:
    print(f"  [{defect.severity.value}] {defect.defect_type.value}: {defect.count} affected")
```

Expected output for a mesh with holes and inverted normals:
```
Health: repairable (score: 0.62)
Shells: 1
Defects: 2
  [critical] boundary_edges: 24 affected
  [warning] inconsistent_normals: 156 affected
```

## Scenario 2: Repair a Broken Mesh

```python
from print3d_skill import repair_mesh

summary = repair_mesh("broken_model.stl", output_path="fixed_model.stl")

print(f"Found {summary.total_defects_found} defects, fixed {summary.total_defects_fixed}")
print(f"Classification: {summary.initial_analysis.classification.value} → {summary.final_analysis.classification.value}")

for repair in summary.repairs:
    status = "OK" if repair.success else "FAILED"
    print(f"  [{status}] {repair.strategy.value}: {repair.description}")

print(f"Exported to: {summary.export_paths}")
```

Expected output:
```
Found 3 defects, fixed 3
Classification: repairable → print_ready
  [OK] merge_vertices: Merged 42 duplicate vertices (tolerance: 1e-08)
  [OK] fill_holes: Filled 2 boundary holes (24 edges)
  [OK] fix_normals: Reconciled 156 inconsistent normals
Exported to: {'stl': '/path/to/fixed_model.stl', '3mf': '/path/to/fixed_model.3mf'}
```

## Scenario 3: Analyze a Clean Mesh (Idempotent)

```python
from print3d_skill import analyze_mesh, repair_mesh

report = analyze_mesh("clean_model.stl")
assert report.classification.value == "print_ready"
assert len(report.defects) == 0

# Repair on a clean mesh is a no-op
summary = repair_mesh("clean_model.stl")
assert summary.total_defects_found == 0
assert summary.total_defects_fixed == 0
```

## Scenario 4: Custom Repair Configuration

```python
from print3d_skill import repair_mesh
from print3d_skill.models import RepairConfig

config = RepairConfig(
    vertex_merge_tolerance=1e-6,  # More aggressive vertex merging
    max_poly_count=500_000,       # Lower threshold for "excessive"
    decimation_target=100_000,    # Decimate to 100K faces
    export_formats=["stl"],       # Only export STL
    render_previews=False,        # Skip preview rendering
)

summary = repair_mesh("high_poly_model.obj", config=config)
print(f"Faces: {summary.initial_analysis.face_count} → {summary.final_analysis.face_count}")
```

## Scenario 5: Export a Mesh to Multiple Formats

```python
from print3d_skill import export_mesh

result = export_mesh("model.stl", output_dir="/output", formats=["stl", "3mf"])

for fmt, path in result.paths.items():
    print(f"  {fmt}: {path}")
```

## Scenario 6: Query Fix Mode Knowledge

```python
from print3d_skill import query_knowledge

# Get repair decision trees
results = query_knowledge(mode="fix", problem_type="decision_tree")
for kf in results:
    print(f"{kf.metadata.topic}: {kf.data['description']}")

# Get slicer error mappings
results = query_knowledge(mode="fix", problem_type="lookup_table")
for kf in results:
    print(f"{kf.metadata.topic}")
```

## Scenario 7: Fix Mode via Router

```python
from print3d_skill import route

response = route("fix", mesh_path="broken.stl", output_path="fixed.stl")

print(f"Status: {response.status}")
print(f"Message: {response.message}")

if response.data:
    summary = response.data  # RepairSummary
    print(f"Fixed {summary.total_defects_fixed}/{summary.total_defects_found} defects")
```
