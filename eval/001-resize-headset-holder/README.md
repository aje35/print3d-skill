# Use Case 001: Resize Headset Holder

**Mode**: Modify
**Requires**: F4 (model-modification)
**Status**: Waiting for implementation

## Problem

Printed a headset holder designed to mount underneath a desk. The clamp portion is too narrow for the desks in my office — the part doesn't fit around the desk edge.

## Assets

- `obj_1_Headset Holder Underneath Screw.stl` — Screw/fastener component
- `obj_2_Headset Holder Underneath Main Part.stl` — Main clamp body (this is the part that needs resizing)

## What the Skill Should Do

1. Load the main part STL
2. Identify the clamp opening dimension (the gap that wraps around the desk edge)
3. Accept a target desk thickness or range (e.g., "my desks are 25-32mm thick")
4. Modify the clamp geometry to accommodate the specified desk thickness range, adding clearance
5. Preserve the screw mounting interface so the two parts still fit together
6. Render before/after preview for visual verification
7. Export the modified STL

## Constraints

- The screw component should not need modification — only the main clamp body
- The modified clamp must still align with the screw holes
- Need enough clearance for the clamp to slide onto the desk edge without forcing
