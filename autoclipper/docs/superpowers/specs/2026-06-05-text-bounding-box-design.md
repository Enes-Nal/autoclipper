# Text Element Resizable Bounding Box

**Date:** 2026-06-05  
**Status:** Approved

## Overview

Text elements on the canvas get a proper resizable bounding box. Dragging the width handle controls where text wraps; an optional fixed-height mode locks both dimensions. Export renders match the editor 1:1.

## Approach

Use Fabric.js `Textbox` native resize — intercept the `scaling` event and convert scale deltas into direct `width`/`height` mutations, then reset `scaleX`/`scaleY` to `1`. This keeps the existing word-wrap, inline editing, and export pipeline intact.

## Canvas Behavior

### Resize Handles

- **AutoHeight mode (default):** Show only left/right edge handles (`ml`/`mr`). Top/bottom and corner handles are hidden. Width drag updates `textbox.width`; height auto-expands with content.
- **Fixed frame mode:** Show all 8 handles. Width and height are both user-controlled.

A utility function `syncTextHandles(obj)` sets `setControlsVisibility` based on `obj._autoHeight`. Called on `object:added` and whenever the mode toggles.

### Scale Interception

In the `object:scaling` event, when `e.target._type === 'text'`:

1. Compute `newWidth = obj.width * obj.scaleX`
2. If fixed mode: compute `newHeight = obj.height * obj.scaleY`
3. Set `obj.width = newWidth` (and `obj.height = newHeight` if fixed)
4. Reset `obj.scaleX = obj.scaleY = 1`
5. Call `obj.setCoords()`

Remove the existing uniform-scale lock (`const sc = Math.max(scaleX, scaleY)`) for text objects in `onSnapScale`.

### Dimension Label

A `<div id="resize-label">` sits inside `#canvas-area` with `position:absolute`. During `object:scaling` for text objects it shows `{width} × {height}` in canvas-space pixels (a small dark pill, similar to Figma). Hidden on `mouse:up`.

### Visual Style

Set on all text objects at creation:

```js
borderColor: '#2563eb',
cornerColor: '#2563eb',
cornerSize: 9,
transparentCorners: false,
```

## Data Model

One new property on Fabric `Textbox` objects:

| Property | Type | Default | Meaning |
|---|---|---|---|
| `_autoHeight` | boolean | `true` | When true, height grows with content |

`verticalAlign` (`'top'` / `'middle'` / `'bottom'`) is also added, defaulting to `'top'`. Existing `width`, `height`, `textAlign` are unchanged.

`scaleX` and `scaleY` are always `1` for text objects after this change, so `width` and `height` are always the true pixel dimensions in the serialized snapshot.

## Properties Panel

Two new controls added to the existing text properties panel:

1. **Fixed height checkbox** — label "Fixed height". Checking it:
   - Sets `_autoHeight = false`
   - Captures the current auto-computed `height` as the initial fixed height
   - Calls `syncTextHandles(obj)` to show all 8 handles

   Unchecking reverses this.

2. **Vertical align buttons** — row of 3 icon buttons (top / middle / bottom). Only meaningful and visible in fixed frame mode. Updates `obj.verticalAlign`.

## Export

### Serialization

No changes. `width` and `height` are already included in the layer snapshot. With `scaleX/scaleY` always `1`, they are always the true frame dimensions.

### `text_renderer.py`

`_wrap_lines` already uses `frame_w = layer.get("width")` — no change needed.

**Vertical alignment** — add handling in `render_text_layer`:

- Compute `total_text_h = len(lines) * line_h`
- `top`: `y_start = 0` (current behavior)
- `middle`: `y_start = max(0, (frame_h - total_text_h) // 2)`
- `bottom`: `y_start = max(0, frame_h - total_text_h)`

Only applied when `autoHeight` is `false` (i.e., `layer.get("auto_height", True)` is `False`).

**AutoHeight in export:** When `auto_height` is `True`, `frame_h` is ignored (current behavior). When `False`, text clips at `frame_h` via the existing `overflow_mode: 'wrap'` logic.

## Files Changed

| File | Change |
|---|---|
| `frontend/index.html` | Resize interception, `syncTextHandles`, dimension label, panel controls, blue handle style |
| `text_renderer.py` | Vertical alignment offset in `render_text_layer` |
| `exporter.py` | Pass `auto_height` and `vertical_align` from layer snapshot to `render_text_layer` |

## Out of Scope

- Minimum width/height constraints (not specified)
- Text overflow clipping visual indicator in editor (only in export)
- Undo/redo for resize (covered by existing history system)
