# Data Model: Print Failure Diagnosis

## Entities

### PrintDefectCategory (Enum)

Enumerates the 12 recognized print defect categories.

| Value | Description |
|-------|-------------|
| `stringing` | Thin strings/wisps of filament between features during travel moves |
| `layer_shift` | Layers misaligned horizontally, creating a stepped/offset appearance |
| `warping` | Corners or edges lifting/curling away from the build plate |
| `under_extrusion` | Insufficient filament deposited — gaps, thin walls, weak layers |
| `over_extrusion` | Excess filament deposited — blobby surfaces, dimensional inaccuracy |
| `bed_adhesion_failure` | Print detaches from build plate during printing |
| `elephant_foot` | First few layers wider than intended due to compression/squish |
| `poor_bridging` | Sagging or drooping filament over unsupported spans |
| `support_scarring` | Rough surface finish where supports contacted the print |
| `layer_separation` | Layers delaminating — visible splits between layer boundaries |
| `zits_blobs` | Small bumps/pimples on surface at seam points or travel starts |
| `ghosting` | Ripple/echo artifacts on surfaces after sharp direction changes |

### PrintDefectSeverity (Enum)

Three-level severity assigned per defect category in the knowledge base.

| Value | Description |
|-------|-------------|
| `cosmetic` | Affects appearance only; print is functionally sound (e.g., zits/blobs, minor ghosting, support scarring) |
| `functional` | Affects dimensional accuracy or surface quality enough to impact the part's intended use (e.g., stringing, elephant foot, over-extrusion) |
| `print_stopping` | Can cause print failure, structural weakness, or part unusability (e.g., layer separation, warping, bed adhesion failure, layer shift, under-extrusion) |

### PrintDefect

A print quality problem identified by the agent from photo analysis.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `category` | `PrintDefectCategory` | Yes | One of the 12 defect types |
| `severity` | `PrintDefectSeverity` | Yes | Looked up from knowledge base by category |
| `description` | `str` | Yes | Plain language description of the visual observation |
| `confidence` | `str` | Yes | Agent's confidence in the identification: "high", "medium", or "low" |
| `spatial_distribution` | `str` | No | Where on the print: "localized", "regional", "global". Defaults to "global" |

### DiagnosticContext

The user's setup information for cross-referencing during root cause analysis.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `printer_model` | `str` | No | User's printer model (e.g., "Bambu Lab P1S", "Prusa MK4") |
| `printer_family` | `str` | No | Derived or specified printer family (e.g., "bambu", "prusa", "creality") |
| `extruder_type` | `str` | No | "direct_drive" or "bowden". Derived from printer if known |
| `material` | `str` | No | Filament material (e.g., "PLA", "PETG", "ABS") |
| `slicer_settings` | `dict[str, Any]` | No | Key slicer settings if available (temps, speeds, retraction, etc.) |
| `geometry_info` | `dict[str, Any]` | No | Model characteristics if available (overhangs, bridges, thin walls) |

### RootCause

A determined reason for a defect, derived from walking a decision tree.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | `str` | Yes | What is causing the defect |
| `likelihood` | `str` | Yes | "high", "medium", or "low" given the diagnostic context |
| `contributing_factors` | `list[str]` | Yes | Context elements that support this diagnosis |
| `defect_category` | `PrintDefectCategory` | Yes | Which defect this cause explains |

### Recommendation

A specific fix for a root cause.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `setting` | `str` | Yes | The setting or action to change (e.g., "retraction_distance", "bed_temperature") |
| `current_issue` | `str` | Yes | What's wrong with the current value/state |
| `suggested_value` | `str` | Yes | Specific value to use (e.g., "0.8mm", "110C", "40mm/s") |
| `impact` | `str` | Yes | "high", "medium", or "low" expected improvement |
| `difficulty` | `str` | Yes | "easy" (slicer setting), "moderate" (hardware adjustment), "hard" (hardware modification) |
| `category` | `str` | Yes | "controllable" (user can directly change) or "environmental" (can only mitigate) |
| `explanation` | `str` | Yes | Why this fix addresses the root cause |

### DiagnosisResult

The complete output of the diagnosis pipeline.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `defects` | `list[PrintDefect]` | Yes | Input defects with severity populated |
| `context` | `DiagnosticContext` | Yes | The diagnostic context used (may have derived fields filled in) |
| `root_causes` | `list[RootCause]` | Yes | Identified root causes, ranked by severity then likelihood |
| `recommendations` | `list[Recommendation]` | Yes | Ordered fixes: severity → impact → ease |
| `conflicts` | `list[str]` | Yes | Any flagged conflicts between recommendations (empty if none) |
| `context_quality` | `str` | Yes | "full", "partial", or "minimal" — how much context was available |

## Relationships

```text
PrintDefect ──────── 1:N ──── RootCause
     │                            │
     │ severity from              │ generates
     │ knowledge base             │
     ▼                            ▼
DefectGuide YAML          Recommendation
                               │
                               │ may conflict with
                               ▼
                          Other Recommendation
```

- Each `PrintDefect` may have multiple `RootCause`s (ranked by likelihood)
- Each `RootCause` generates one or more `Recommendation`s
- `Recommendation`s may conflict with each other (flagged in `DiagnosisResult.conflicts`)
- `PrintDefectSeverity` is looked up from `defect_guides.yaml` by category

## Validation Rules

- `PrintDefect.category` must be a valid `PrintDefectCategory` enum value
- `PrintDefect.confidence` must be one of: "high", "medium", "low"
- `DiagnosticContext` may be entirely empty (all fields None) — diagnosis proceeds with general decision trees
- `RootCause.likelihood` must be one of: "high", "medium", "low"
- `Recommendation.impact` must be one of: "high", "medium", "low"
- `Recommendation.difficulty` must be one of: "easy", "moderate", "hard"
- `Recommendation.category` must be one of: "controllable", "environmental"
- `DiagnosisResult.recommendations` must be sorted: print-stopping defects first, then by impact descending, then by difficulty ascending
