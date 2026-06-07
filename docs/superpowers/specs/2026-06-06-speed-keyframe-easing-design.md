# Speed Keyframe Easing — Design Spec

**Date:** 2026-06-06

## Overview

Add per-keyframe easing to speed keyframes, allowing smooth (non-linear) speed transitions between keyframes. Each keyframe gains independent `easeIn` and `easeOut` curve controls, backed by cubic bezier evaluation. Users can pick from built-in presets or create named custom presets saved per-project.

---

## Data Model

### Extended keyframe shape

```js
{
  t: 1.234,          // seconds relative to segment sourceStart
  speed: 1.5,
  easeOut: { type: 'ease-in-out' },                       // built-in preset
  easeIn:  { type: 'custom', bezier: [0.4, 0, 0.2, 1] }  // custom preset
}
```

- `easeOut` — controls the curve leaving this keyframe toward the next.
- `easeIn` — controls the curve arriving at this keyframe from the previous.
- When interpolating between two adjacent keyframes A and B, **A's `easeOut`** determines the segment's easing (outgoing keyframe wins — matches Premiere/DaVinci convention).
- Missing `easeIn`/`easeOut` defaults to `{ type: 'linear' }`.

### Built-in preset bezier values

| Preset name  | `type` value   | Bezier `[x1, y1, x2, y2]` |
|---|---|---|
| Linear       | `linear`       | `[0, 0, 1, 1]`            |
| Ease In      | `ease-in`      | `[0.42, 0, 1, 1]`         |
| Ease Out     | `ease-out`     | `[0, 0, 0.58, 1]`         |
| Ease In Out  | `ease-in-out`  | `[0.42, 0, 0.58, 1]`      |

### Custom presets (per-project)

Stored on the project object as `project.speedEasingPresets`:

```js
[
  { name: 'My Bounce', bezier: [0.68, -0.55, 0.27, 1.55] }
]
```

- Scoped to the project (travels with save data).
- Referenced in keyframes via `{ type: 'custom', bezier: [...] }` (bezier values are inlined, not referenced by name, so renaming/deleting a preset doesn't break existing keyframes).

---

## Interpolation

### Frontend — `tlInterpolateSpeed`

Upgraded to evaluate a cubic bezier between each keyframe pair instead of raw linear interpolation.

```
segment A → B:
  raw_frac  = (t - A.t) / (B.t - A.t)
  eased_frac = evalUnitBezier(...resolveBezier(A.easeOut), raw_frac)
  speed = A.speed + eased_frac * (B.speed - A.speed)
```

A new standalone helper `evalUnitBezier(x1, y1, x2, y2, t)` is added — a standard CSS timing-function Newton's method solver (~20 lines). A helper `resolveBezier(easing)` maps a `{type}` or `{type, bezier}` object to a `[x1,y1,x2,y2]` array using the built-in lookup table.

### Exporter — `_speed_kfs_to_subsegs` (exporter.py)

The Python `interp()` inner function is upgraded with the same cubic bezier logic. A `eval_unit_bezier(x1, y1, x2, y2, t)` helper is added to `exporter.py`. The existing sub-segment sampling strategy is unchanged — easing is automatically captured because the sampler calls the upgraded `interp()`.

No FFmpeg filter changes required.

---

## UI

### Keyframe list rows

Each row in the speed strip keyframe list gains two inline `<select>` dropdowns below the speed input:

- **Ease In** dropdown (curve arriving at this keyframe)
- **Ease Out** dropdown (curve leaving this keyframe)

Dropdown options:
1. Built-in presets: `Linear`, `Ease In`, `Ease Out`, `Ease In Out`
2. Divider
3. User's `project.speedEasingPresets` entries (by name)
4. `+ Custom…` at the bottom

### Bezier editor

Opens inline (expanding the keyframe row) when the user selects `+ Custom…` or clicks to edit an existing custom entry.

- **SVG canvas** (~160×160px): two draggable control point handles; the bezier curve is drawn live as handles move.
- **Numeric inputs**: four fields `x1`, `y1`, `x2`, `y2`. Clamp ranges: x1/x2 → `[0, 1]`, y1/y2 → `[-2, 2]` (allows overshoot/bounce).
- Handles and inputs are kept in sync bidirectionally.
- **Preset name field** + **Save as preset** button — appends to `project.speedEasingPresets` and selects the new preset in the dropdown.

### Speed lane curve

No rendering changes needed. The speed lane SVG curve is already drawn by sampling `tlInterpolateSpeed` at many points — once the interpolator is upgraded, the drawn curve will automatically reflect easing.

---

## Out of Scope

- Per-keyframe `easeIn` is stored in the data model and shown in the UI but currently has no effect on interpolation (only `easeOut` of the outgoing keyframe is used). It is retained for future symmetric easing support.
- Bezier preset sharing across projects.
- Undo/redo for preset creation (preset saves are not undoable; keyframe easing changes go through the existing `saveHist()` path).
