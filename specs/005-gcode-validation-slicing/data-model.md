# Data Model: G-code Validation & Slicing

## Enums

### ValidationStatus
Overall outcome of a validation run.
- `PASS` — All checks passed
- `WARN` — Some checks produced warnings but no failures
- `FAIL` — At least one check is a failure (blocks printing)

### CheckSeverity
Severity level for an individual validation check.
- `PASS` — Within expected range
- `WARN` — Outside recommended range but not dangerous
- `FAIL` — Will cause print failure or equipment damage

### CheckCategory
Category of a validation check for grouping results.
- `TEMPERATURE` — Hotend, bed, chamber temperatures
- `SPEED` — Print speed, travel speed, first layer speed
- `RETRACTION` — Distance, speed, z-hop settings
- `DIMENSIONS` — Build volume fit
- `FIRST_LAYER` — First layer-specific settings
- `TIME_ESTIMATE` — Print time reasonableness
- `MATERIAL_ESTIMATE` — Filament usage reasonableness
- `COMPATIBILITY` — Printer/material compatibility

### ExtruderType
Type of extruder for retraction validation.
- `DIRECT_DRIVE`
- `BOWDEN`

### PrinterConnectionType
Type of printer API connection.
- `OCTOPRINT`
- `MOONRAKER`
- `BAMBU`

### PrinterStatus
Current state of a connected printer.
- `IDLE` — Ready to accept jobs
- `PRINTING` — Currently printing
- `PAUSED` — Print paused
- `ERROR` — Printer in error state
- `DISCONNECTED` — Cannot reach printer
- `UNKNOWN` — Status could not be determined

### SlicerType
Supported slicer CLI backends.
- `PRUSASLICER`
- `ORCASLICER`

## Entities

### GcodeAnalysis
Structured report from parsing a G-code file.

| Field | Type | Description |
|-------|------|-------------|
| file_path | str | Path to the parsed G-code file |
| file_size_bytes | int | Size of the G-code file |
| slicer | str or None | Detected slicer name (e.g., "PrusaSlicer 2.7") |
| hotend_temps | list[TemperatureCommand] | All hotend temperature commands |
| bed_temps | list[TemperatureCommand] | All bed temperature commands |
| chamber_temps | list[TemperatureCommand] | Chamber temperature commands (if any) |
| print_speed_mm_s | float or None | Primary print speed extracted |
| travel_speed_mm_s | float or None | Travel speed extracted |
| first_layer_speed_mm_s | float or None | First layer speed |
| retraction_distance_mm | float or None | Retraction distance |
| retraction_speed_mm_s | float or None | Retraction speed |
| z_hop_mm | float or None | Z-hop distance |
| layer_height_mm | float or None | Layer height |
| first_layer_height_mm | float or None | First layer height |
| layer_count | int or None | Total number of layers |
| estimated_time_s | float or None | Estimated print time in seconds |
| estimated_filament_mm | float or None | Estimated filament usage in mm |
| estimated_filament_g | float or None | Estimated filament usage in grams |
| fan_speeds | list[FanCommand] | Fan speed changes |
| print_dimensions | PrintDimensions or None | Estimated print dimensions from moves |
| line_count | int | Total number of lines in the file |
| warnings | list[str] | Any parsing warnings (unrecognized commands, etc.) |

### TemperatureCommand
A single temperature command extracted from G-code.

| Field | Type | Description |
|-------|------|-------------|
| command | str | G-code command (e.g., "M104", "M109") |
| target_temp_c | float | Target temperature in Celsius |
| line_number | int | Line number in the G-code file |
| layer | int or None | Layer number if determinable |
| wait | bool | Whether command waits for temp (M109/M190 vs M104/M140) |

### FanCommand
A fan speed change extracted from G-code.

| Field | Type | Description |
|-------|------|-------------|
| command | str | G-code command ("M106" or "M107") |
| speed_percent | float | Fan speed as percentage (0-100) |
| line_number | int | Line number in the G-code file |
| layer | int or None | Layer number if determinable |

### PrintDimensions
Estimated bounding box of print moves (stdlib-only, no numpy dependency).

| Field | Type | Description |
|-------|------|-------------|
| min_x | float | Minimum X coordinate from moves |
| max_x | float | Maximum X coordinate from moves |
| min_y | float | Minimum Y coordinate from moves |
| max_y | float | Maximum Y coordinate from moves |
| min_z | float | Minimum Z coordinate from moves |
| max_z | float | Maximum Z coordinate from moves |

### ValidationResult
Complete output of validating G-code against profiles.

| Field | Type | Description |
|-------|------|-------------|
| status | ValidationStatus | Overall result: PASS, WARN, or FAIL |
| gcode_analysis | GcodeAnalysis | The parsed G-code data |
| material_profile | str or None | Material profile name used for validation |
| printer_profile | str or None | Printer profile name used for validation |
| checks | list[ValidationCheck] | All individual check results |
| summary | str | Human-readable summary of findings |
| warnings | list[str] | Aggregated warning messages |
| failures | list[str] | Aggregated failure messages |
| recommendations | list[str] | Aggregated fix recommendations |

### ValidationCheck
A single validation check result.

| Field | Type | Description |
|-------|------|-------------|
| category | CheckCategory | Category of this check |
| name | str | Short check name (e.g., "hotend_temperature") |
| severity | CheckSeverity | Result: PASS, WARN, or FAIL |
| actual_value | str | What was found in the G-code |
| expected_range | str | What the profile recommends |
| message | str | Human-readable description of the finding |
| recommendation | str | Specific fix recommendation (empty if PASS) |

### MaterialProfile
Reference data for a filament material used in validation.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Material name (e.g., "PLA", "PETG") |
| hotend_temp_min_c | float | Minimum recommended hotend temperature |
| hotend_temp_max_c | float | Maximum recommended hotend temperature |
| bed_temp_min_c | float | Minimum recommended bed temperature |
| bed_temp_max_c | float | Maximum recommended bed temperature |
| speed_min_mm_s | float | Minimum recommended print speed |
| speed_max_mm_s | float | Maximum recommended print speed |
| retraction_direct_drive_mm | float | Recommended retraction for direct drive |
| retraction_bowden_mm | float | Recommended retraction for bowden |
| retraction_speed_mm_s | float | Recommended retraction speed |
| requires_enclosure | bool | Whether material needs an enclosure |
| requires_heated_bed | bool | Whether material needs a heated bed |
| fan_speed_percent | float | Recommended part cooling fan speed |
| notes | list[str] | Material-specific warnings/tips |

### PrinterProfile
Reference data for a printer's capabilities.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Printer name/model |
| build_volume_x_mm | float | Build volume X dimension |
| build_volume_y_mm | float | Build volume Y dimension |
| build_volume_z_mm | float | Build volume Z dimension |
| max_hotend_temp_c | float | Maximum hotend temperature |
| max_bed_temp_c | float | Maximum bed temperature |
| extruder_type | ExtruderType | Direct drive or bowden |
| has_heated_bed | bool | Whether printer has a heated bed |
| has_enclosure | bool | Whether printer is enclosed |
| notes | list[str] | Printer-specific notes |

### SliceRequest
Request to slice a model via CLI.

| Field | Type | Description |
|-------|------|-------------|
| model_path | str | Path to input model (STL or 3MF) |
| output_path | str or None | Path for output G-code (auto-generated if None) |
| slicer | SlicerType or None | Which slicer to use (auto-detect if None) |
| printer_profile | str or None | Slicer printer profile name |
| material_profile | str or None | Slicer material profile name |
| quality_preset | str or None | Slicer quality preset name |
| overrides | dict[str, str] | Custom setting overrides (key=value) |

### SliceResult
Result of a slicing operation.

| Field | Type | Description |
|-------|------|-------------|
| gcode_path | str | Path to the generated G-code file |
| slicer_used | SlicerType | Which slicer was used |
| slicer_version | str | Version of the slicer |
| model_path | str | Input model path |
| profiles_used | dict[str, str] | Profiles that were applied |
| overrides_applied | dict[str, str] | Setting overrides that were applied |
| warnings | list[str] | Any slicer warnings |

### PrinterConnection
Configuration for connecting to a printer.

| Field | Type | Description |
|-------|------|-------------|
| name | str | User-friendly printer name |
| connection_type | PrinterConnectionType | OCTOPRINT, MOONRAKER, or BAMBU |
| host | str | Hostname or IP address |
| port | int or None | Port number (defaults per type) |
| api_key | str or None | API key (OctoPrint, Moonraker) |
| serial | str or None | Device serial (Bambu Lab) |
| access_code | str or None | Access code (Bambu Lab) |

### PrinterInfo
Status information about a connected printer.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Printer name from configuration |
| connection_type | PrinterConnectionType | Connection type |
| status | PrinterStatus | Current printer state |
| hotend_temp_c | float or None | Current hotend temperature |
| bed_temp_c | float or None | Current bed temperature |
| progress_percent | float or None | Print progress (if printing) |
| current_file | str or None | Currently printing file (if any) |

### PrintJob
A submission of validated G-code to a printer.

| Field | Type | Description |
|-------|------|-------------|
| printer_name | str | Target printer name |
| gcode_path | str | Path to the G-code file |
| validation_result | ValidationResult | Validation that authorized this job |
| submitted | bool | Whether the job was successfully submitted |
| message | str | Status message |

## Relationships

- `GcodeAnalysis` is produced by the G-code parser and consumed by `ValidationResult`
- `ValidationResult` references the `GcodeAnalysis` and the material/printer profile names used
- `ValidationCheck` items compose a `ValidationResult`
- `MaterialProfile` and `PrinterProfile` are loaded from knowledge YAML files
- `SliceResult` produces a G-code file that can be parsed into a `GcodeAnalysis`
- `PrintJob` requires a `ValidationResult` with status != FAIL before submission is allowed
- `PrinterConnection` is loaded from user configuration; `PrinterInfo` is queried at runtime
