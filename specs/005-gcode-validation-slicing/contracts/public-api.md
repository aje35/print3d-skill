# Public API Contract: G-code Validation & Slicing

## New Public Functions

### `parse_gcode(gcode_path) -> GcodeAnalysis`

Parse a G-code file and extract structured parameters.

**Parameters**:
- `gcode_path` (str): Path to G-code file. Must exist and be readable.

**Returns**: `GcodeAnalysis` dataclass with all extracted parameters.

**Raises**:
- `FileNotFoundError`: File does not exist
- `UnsupportedFormatError`: File is not a G-code file (wrong extension)
- `GcodeParseError`: File is corrupted or empty

**Behavior**:
- Auto-detects the source slicer from comment metadata
- Extracts all temperature, speed, retraction, layer, time, and fan parameters
- Returns partial results with warnings for unrecognized sections (does not fail on unknown commands)
- Core tier: no external dependencies

---

### `validate_gcode(gcode_path, material=None, printer=None) -> ValidationResult`

Validate G-code settings against material and printer profiles.

**Parameters**:
- `gcode_path` (str): Path to G-code file
- `material` (str | None): Material name (e.g., "PLA", "PETG"). If None, material checks skipped.
- `printer` (str | None): Printer profile name. If None, printer checks skipped.

**Returns**: `ValidationResult` with status (PASS/WARN/FAIL), individual checks, and recommendations.

**Raises**:
- `FileNotFoundError`: G-code file does not exist
- `UnsupportedFormatError`: Not a G-code file
- `GcodeParseError`: File is corrupted or empty

**Behavior**:
- Internally calls `parse_gcode()` first
- Runs all applicable validation checks based on provided profiles
- At least one of `material` or `printer` should be specified; if both are None, only basic structural checks run
- Core tier: no external dependencies

---

### `slice_model(model_path, output_path=None, slicer=None, printer_profile=None, material_profile=None, quality_preset=None, **overrides) -> SliceResult`

Slice a 3D model using an installed slicer CLI.

**Parameters**:
- `model_path` (str): Path to STL or 3MF model file
- `output_path` (str | None): Path for output G-code. Auto-generated if None.
- `slicer` (str | None): "prusaslicer" or "orcaslicer". Auto-detect if None.
- `printer_profile` (str | None): Slicer's printer profile name
- `material_profile` (str | None): Slicer's material profile name
- `quality_preset` (str | None): Slicer's quality preset name
- `**overrides`: Key=value setting overrides (e.g., `layer_height=0.3`, `fill_density=30`)

**Returns**: `SliceResult` with output path, slicer used, profiles applied.

**Raises**:
- `FileNotFoundError`: Model file does not exist
- `UnsupportedFormatError`: Not an STL or 3MF file
- `CapabilityUnavailable`: No slicer CLI installed
- `SlicerError`: Slicer CLI returned an error (includes slicer output)

**Behavior**:
- Extended tier: requires PrusaSlicer or OrcaSlicer installed
- Auto-detects which slicer is available if `slicer` not specified
- Passes overrides as CLI flags to the slicer
- Output path auto-generated as `model_sliced.gcode` if not specified

---

### `list_printers() -> list[PrinterInfo]`

Discover and list configured printers with their current status.

**Parameters**: None

**Returns**: List of `PrinterInfo` with name, type, status, and current temperatures.

**Raises**:
- `CapabilityUnavailable`: No printer connections configured

**Behavior**:
- Extended tier: requires printer configuration file
- Queries each configured printer for current status
- Returns empty list if config exists but all printers unreachable
- Does not raise on individual printer connection failures (reports DISCONNECTED status)

---

### `submit_print(gcode_path, printer_name, material=None, printer_profile=None) -> PrintJob`

Validate and submit G-code to a printer.

**Parameters**:
- `gcode_path` (str): Path to G-code file
- `printer_name` (str): Name of target printer (from configuration)
- `material` (str | None): Material for validation
- `printer_profile` (str | None): Printer profile for validation (auto-detected from printer config if possible)

**Returns**: `PrintJob` with submission status and validation result.

**Raises**:
- `FileNotFoundError`: G-code file does not exist
- `CapabilityUnavailable`: No printer connections configured
- `ValidationError`: G-code failed validation (FAIL status) — print blocked
- `PrinterError`: Printer unreachable or in error state

**Behavior**:
- ALWAYS runs validation before submission (Constitution Principle IV)
- If validation returns FAIL, raises `ValidationError` — does not submit
- If validation returns WARN, submits with warnings included in PrintJob
- If validation returns PASS, submits normally
- Checks printer status before upload — refuses to submit to ERROR state printers
- Extended tier: requires printer configuration and network connectivity

---

## Updated Existing Functions

### `route("validate", **context) -> ModeResponse`

The router dispatches to `ValidateHandler` which wraps the `validate_gcode()` function.

**Expected context kwargs**:
- `gcode_path` (str): Required — path to G-code file
- `material` (str | None): Optional material name
- `printer` (str | None): Optional printer profile name

**Returns**: `ModeResponse` with status="success" and `data={"validation_result": ...}`, or status="error" with error details.

---

## Error Types (New)

- `GcodeParseError(Print3DSkillError)`: G-code file is corrupted, empty, or cannot be parsed.
- `SlicerError(Print3DSkillError)`: Slicer CLI returned a non-zero exit code. Includes the slicer's stderr output.
- `ValidationError(Print3DSkillError)`: G-code failed validation with FAIL status. Includes the validation result.
- `PrinterError(Print3DSkillError)`: Printer communication failed. Includes connection details (without credentials).

---

## Contract Test Requirements

1. **Signature tests**: Verify all return types match documented dataclass fields
2. **Error contracts**: Verify each documented exception is raised for the specified conditions
3. **Capability degradation**: Verify `CapabilityUnavailable` for slicer/printer when not installed
4. **Validation enforcement**: Verify `submit_print()` always validates first and blocks on FAIL
5. **Import test**: Verify all new public functions are importable from `print3d_skill`
