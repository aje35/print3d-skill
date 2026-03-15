# API Contract: Diagnosis Public Interface

## diagnose_print()

**Module**: `print3d_skill.diagnosis`
**Re-exported from**: `print3d_skill.__init__`

### Signature

```python
def diagnose_print(
    defects: list[PrintDefect],
    context: DiagnosticContext | None = None,
) -> DiagnosisResult:
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `defects` | `list[PrintDefect]` | Yes | Pre-identified defects from agent's photo analysis. Must contain at least one defect. |
| `context` | `DiagnosticContext \| None` | No | User's setup information. If None, general diagnosis without context-specific ranking. |

### Returns

`DiagnosisResult` with populated `root_causes`, `recommendations`, `conflicts`, and `context_quality`.

### Raises

| Exception | When |
|-----------|------|
| `ValueError` | Empty defects list |
| `DiagnosisError` | Knowledge base missing or corrupted (new exception in hierarchy) |

### Behavior Contract

1. Each defect's `severity` is populated from `defect_guides.yaml` if not already set
2. For each defect, the relevant decision tree is loaded from knowledge base
3. Decision trees are walked using the provided context to rank root causes
4. Recommendations are generated for each root cause with specific values
5. Recommendations are sorted: severity → impact → ease
6. Conflicting recommendations are detected and flagged
7. If `context` is None or sparse, `context_quality` reflects this and recommendations fall back to general values

### Example

```python
from print3d_skill.diagnosis import diagnose_print
from print3d_skill.diagnosis.models import (
    PrintDefect, PrintDefectCategory, DiagnosticContext
)

result = diagnose_print(
    defects=[
        PrintDefect(
            category=PrintDefectCategory.stringing,
            description="Thin strings between tower features",
            confidence="high",
        ),
    ],
    context=DiagnosticContext(
        printer_model="Bambu Lab P1S",
        material="PETG",
    ),
)

# result.root_causes → ranked causes
# result.recommendations → specific fix values
# result.context_quality → "partial" (no slicer settings provided)
```

---

## DiagnoseHandler.handle()

**Module**: `print3d_skill.modes.diagnose`
**Pattern**: `ModeHandler` ABC

### Signature

```python
def handle(self, **context: object) -> ModeResponse:
```

### Expected Context Keys

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `defects` | `list[dict]` | Yes | Defect dicts with `category`, `description`, `confidence` fields |
| `printer` | `str` | No | Printer model name |
| `material` | `str` | No | Material type |
| `slicer_settings` | `dict` | No | Key slicer settings |

### Returns

`ModeResponse` with:
- `mode`: `"diagnose"`
- `status`: `"success"` or `"error"`
- `message`: Human-readable summary
- `data`: Serialized `DiagnosisResult` dict (or error details)

### Behavior

1. Converts raw dict defects to `PrintDefect` objects
2. Builds `DiagnosticContext` from context kwargs
3. Calls `diagnose_print(defects, context)`
4. Returns `ModeResponse` wrapping the result

---

## Knowledge Query Integration

The diagnosis module queries knowledge via the existing public API:

```python
from print3d_skill.knowledge import query_knowledge

# Load defect guides
guides = query_knowledge(mode="diagnose", problem_type="defect_guide")

# Load decision trees
trees = query_knowledge(mode="diagnose", problem_type="decision_tree")

# Load printer-specific tips
tips = query_knowledge(mode="diagnose", printer="bambu")

# Load material failure modes
failures = query_knowledge(mode="diagnose", material="PETG")
```

No changes to the `query_knowledge` interface are required. Only `VALID_KNOWLEDGE_TYPES` is extended with `"defect_guide"` and `"calibration_procedure"`.
