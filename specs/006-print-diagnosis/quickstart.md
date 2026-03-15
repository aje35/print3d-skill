# Quickstart: Print Failure Diagnosis

## Scenario 1: Single Defect Diagnosis with Context

```python
from print3d_skill.diagnosis import diagnose_print
from print3d_skill.diagnosis.models import (
    PrintDefect,
    PrintDefectCategory,
    DiagnosticContext,
)

# Agent identified stringing from user's photo
result = diagnose_print(
    defects=[
        PrintDefect(
            category=PrintDefectCategory.stringing,
            description="Thin strings between tower features, especially on travel moves",
            confidence="high",
        ),
    ],
    context=DiagnosticContext(
        printer_model="Bambu Lab P1S",
        material="PETG",
    ),
)

assert result.context_quality == "partial"  # no slicer settings provided
assert len(result.root_causes) >= 1
assert result.root_causes[0].likelihood == "high"

# Recommendations have specific values
for rec in result.recommendations:
    assert rec.suggested_value  # e.g., "0.8mm", "40mm/s"
    assert rec.category in ("controllable", "environmental")
```

## Scenario 2: Multiple Defects with Conflict Detection

```python
from print3d_skill.diagnosis import diagnose_print
from print3d_skill.diagnosis.models import (
    PrintDefect,
    PrintDefectCategory,
    DiagnosticContext,
)

result = diagnose_print(
    defects=[
        PrintDefect(
            category=PrintDefectCategory.warping,
            description="Corners lifting from bed",
            confidence="high",
        ),
        PrintDefect(
            category=PrintDefectCategory.elephant_foot,
            description="First layers wider than design",
            confidence="medium",
        ),
    ],
    context=DiagnosticContext(
        printer_model="Prusa MK4",
        material="ABS",
    ),
)

# print-stopping defects sorted first
assert result.defects[0].severity.value == "print_stopping"  # warping

# Recommendations ordered by severity, then impact
assert len(result.recommendations) >= 2

# Conflicts detected if fixes contradict
# (e.g., "increase first layer squish" for adhesion vs "decrease squish" for elephant foot)
# result.conflicts may contain flagged issues
```

## Scenario 3: Minimal Context (No Printer/Material)

```python
from print3d_skill.diagnosis import diagnose_print
from print3d_skill.diagnosis.models import PrintDefect, PrintDefectCategory

result = diagnose_print(
    defects=[
        PrintDefect(
            category=PrintDefectCategory.under_extrusion,
            description="Gaps between lines, thin walls",
            confidence="high",
        ),
    ],
    # No context provided
)

assert result.context_quality == "minimal"
# General recommendations without printer/material-specific values
assert len(result.root_causes) >= 1
```

## Scenario 4: Knowledge Query for Defect Guides

```python
from print3d_skill.knowledge import query_knowledge

# Agent loads defect guides to identify defects from photos
guides = query_knowledge(mode="diagnose", problem_type="defect_guide")
assert len(guides) >= 1

guide_data = guides[0].data
assert "categories" in guide_data
assert len(guide_data["categories"]) == 12  # all 12 defect types

# Each category has severity and visual indicators
stringing = guide_data["categories"]["stringing"]
assert "severity" in stringing
assert "visual_indicators" in stringing
assert "common_causes" in stringing
```

## Scenario 5: Route via Skill Router

```python
from print3d_skill import route

response = route(
    "diagnose",
    defects=[
        {
            "category": "stringing",
            "description": "Strings between features",
            "confidence": "high",
        }
    ],
    printer="Bambu Lab P1S",
    material="PETG",
)

assert response.mode == "diagnose"
assert response.status == "success"
assert response.data is not None
assert "root_causes" in response.data
assert "recommendations" in response.data
```
