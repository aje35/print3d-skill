# Quickstart: G-code Validation & Slicing

## Scenario 1: Parse a G-code file

```python
from print3d_skill import parse_gcode

analysis = parse_gcode("benchy.gcode")
print(f"Slicer: {analysis.slicer}")
print(f"Layer height: {analysis.layer_height_mm}mm")
print(f"Hotend temp: {analysis.hotend_temps[0].target_temp_c}C")
print(f"Bed temp: {analysis.bed_temps[0].target_temp_c}C")
print(f"Print time: {analysis.estimated_time_s / 3600:.1f} hours")
print(f"Filament: {analysis.estimated_filament_mm / 1000:.1f}m")
print(f"Print speed: {analysis.print_speed_mm_s}mm/s")
print(f"Retraction: {analysis.retraction_distance_mm}mm")
```

**Expected**: Structured analysis report with all parameters extracted. Works with G-code from PrusaSlicer, Bambu Studio, OrcaSlicer, and Cura.

## Scenario 2: Validate G-code against PLA profile

```python
from print3d_skill import validate_gcode

result = validate_gcode("benchy.gcode", material="PLA")
print(f"Status: {result.status}")  # PASS, WARN, or FAIL
for check in result.checks:
    if check.severity != "pass":
        print(f"  [{check.severity}] {check.name}: {check.message}")
        print(f"    Fix: {check.recommendation}")
```

**Expected**: Validation result showing any temperature, speed, or retraction issues relative to PLA material profile.

## Scenario 3: Validate with both material and printer

```python
from print3d_skill import validate_gcode

result = validate_gcode(
    "benchy.gcode",
    material="PETG",
    printer="ender3_v2"
)
# Check for build volume fit, temperature compatibility, retraction for bowden
print(f"Status: {result.status}")
print(f"Warnings: {len(result.warnings)}")
print(f"Failures: {len(result.failures)}")
for rec in result.recommendations:
    print(f"  - {rec}")
```

**Expected**: Validation against both material (PETG temps, speeds) and printer (build volume, bowden retraction, max temps).

## Scenario 4: Slice a model (extended tier)

```python
from print3d_skill import slice_model

result = slice_model(
    "benchy.stl",
    printer_profile="Original Prusa i3 MK3S+",
    material_profile="Prusament PLA",
    quality_preset="0.20mm QUALITY",
)
print(f"G-code: {result.gcode_path}")
print(f"Slicer: {result.slicer_used} {result.slicer_version}")
```

**Expected**: G-code file generated via PrusaSlicer CLI with specified profiles. Raises `CapabilityUnavailable` if no slicer installed.

## Scenario 5: Slice with custom overrides

```python
from print3d_skill import slice_model

result = slice_model(
    "bracket.3mf",
    printer_profile="Bambu Lab X1 Carbon",
    layer_height=0.3,
    fill_density=30,
    support_material=True,
)
print(f"G-code: {result.gcode_path}")
print(f"Overrides applied: {result.overrides_applied}")
```

**Expected**: G-code with overridden settings. Profile defaults used for unspecified settings.

## Scenario 6: Check printer status (extended tier)

```python
from print3d_skill import list_printers

printers = list_printers()
for p in printers:
    print(f"{p.name} ({p.connection_type}): {p.status}")
    if p.hotend_temp_c is not None:
        print(f"  Hotend: {p.hotend_temp_c}C, Bed: {p.bed_temp_c}C")
```

**Expected**: List of configured printers with current status. Raises `CapabilityUnavailable` if no printers configured.

## Scenario 7: Submit print job (extended tier)

```python
from print3d_skill import submit_print

job = submit_print(
    "benchy.gcode",
    printer_name="My Bambu X1C",
    material="PLA"
)
print(f"Submitted: {job.submitted}")
print(f"Validation: {job.validation_result.status}")
```

**Expected**: G-code is validated first (always), then submitted to the printer. Raises `ValidationError` if validation fails. Raises `PrinterError` if printer unreachable or in error state.

## Scenario 8: Validate mode via router

```python
from print3d_skill import route

response = route(
    "validate",
    gcode_path="benchy.gcode",
    material="PLA",
    printer="prusa_mk3s"
)
print(f"Status: {response.status}")
print(f"Data: {response.data}")
```

**Expected**: ModeResponse with status="success" and data containing the validation result.

## Scenario 9: Graceful degradation (no slicer installed)

```python
from print3d_skill import slice_model
from print3d_skill.exceptions import CapabilityUnavailable

try:
    result = slice_model("benchy.stl")
except CapabilityUnavailable as e:
    print(f"Slicing unavailable: {e}")
    print(f"Install: {e.install_instructions}")
    # Fall back to parsing externally-produced G-code
    from print3d_skill import validate_gcode
    result = validate_gcode("externally_sliced.gcode", material="PLA")
```

**Expected**: Clear error with install instructions. Core features (parse, validate) still work.

## Scenario 10: Knowledge query for material profiles

```python
from print3d_skill import query_knowledge

profiles = query_knowledge(mode="validate", material="PETG")
for profile in profiles:
    print(f"Type: {profile.metadata.type}")
    print(f"Topic: {profile.metadata.topic}")
    data = profile.data
    print(f"Hotend: {data['properties']['hotend_temp_min_c']}-{data['properties']['hotend_temp_max_c']}C")
```

**Expected**: Returns PETG material profile with temperature ranges, speed limits, retraction settings.
