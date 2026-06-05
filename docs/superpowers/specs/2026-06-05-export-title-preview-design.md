# Export Title Preview & Style Controls

**Date:** 2026-06-05  
**Status:** Approved

## Overview

Add a collapsible "Title Preview & Style" panel to the Export Clip modal. When expanded, it shows a live cropped snapshot of the canvas centered on the title layer, plus the full set of text style controls. Changes made in this panel update the Fabric canvas object directly, so they are picked up by `canvasToTemplate()` at export time without any extra work.

## UI

### Toggle button
A toggle row appears directly below the title input in the export modal:

```
▼  Title Preview & Style          [click to collapse]
```

Clicking toggles the panel open/closed. The panel starts collapsed. State is not persisted between modal opens.

### Preview snippet
- Generated via `cv.toDataURL({ format: 'png', left, top, width, height, multiplier: 0.5 })` cropped to the title layer's bounding box with 20px padding on each side (clamped to canvas bounds).
- Rendered as an `<img>` inside the panel.
- Updates live: debounced 300ms on title input keystrokes, immediate on any style control change.
- A subtle dashed purple outline (`outline: 1.5px dashed rgba(124,92,246,0.5)`) is drawn as a CSS overlay on the `<img>` — it is not baked into the canvas snapshot.
- If the template has no `_isTitle` layer, the toggle button is hidden.

### Text controls
Identical set to the right-panel text section, rendered inside the export panel:

| Control | Type |
|---|---|
| Font | Font picker dropdown |
| Size | Range slider 8–180px + value label |
| Weight | Toggle: Regular / Bold / Black |
| Align | Toggle: L / C / R |
| Overflow | Toggle: Wrap / Truncate / Shrink |
| Color | 8 swatches + custom color input |
| Stroke | Range slider 0–20px + value label |
| Stroke Color | Color input |

## Data Flow

1. **`openExpModal()`** — after opening, call `populateExpTitleControls()`:
   - Find the canvas object where `_isTitle === true`.
   - Read its current property values and set all control states (slider values, active toggle buttons, swatch highlights).
   - If no title object found, hide the toggle button.

2. **Title input (`#exp-title`) `oninput`** — debounce 300ms, then:
   - Set `titleObj.text = value` (or `'{title}'` if empty, restoring placeholder).
   - Call `cv.renderAll()`.
   - Regenerate preview crop.

3. **Style control change** — each control calls a thin wrapper `spTitle(prop, value)`:
   - Finds the `_isTitle` canvas object.
   - Sets the property (same logic as `sp()` but targeted at the title object, not `cv.getActiveObject()`).
   - Calls `cv.renderAll()`.
   - Regenerates preview crop immediately.

4. **`startExport()`** — no changes needed. `canvasToTemplate()` reads the Fabric objects as-is, so updated properties are already present.

## Edge Cases

- **No title layer**: toggle button hidden, panel never shown.
- **Multiple title layers**: use the first one found (`cv.getObjects().find(o => o._isTitle)`).
- **Title input empty**: preview shows the placeholder text `'Your title here 🔥'` (same as canvas display) but export sends `''` (empty string, up to server behavior).
- **Crop out of bounds**: clamp `left`, `top`, `width`, `height` to canvas dimensions before passing to `toDataURL`.

## Files Changed

- `frontend/index.html` — all changes contained here:
  - Export modal HTML: add toggle button + collapsible panel div
  - CSS: panel collapse/expand transition, preview img styling
  - JS: `openExpModal`, `populateExpTitleControls`, `spTitle`, preview regeneration, debounce on title input
