# Video Masking — Design Spec
**Date:** 2026-05-30
**Scope:** Template mode. Applies to video layers only.

---

## Overview

Video layers can be clipped to a mask shape. Four shapes are supported: rectangle (sharp), rounded rectangle (adjustable radius), circle/ellipse, and polygon (drawn by clicking points directly on the canvas). Masking works in both the canvas preview (Fabric.js `clipPath`) and the FFmpeg export (Pillow-rendered mask PNG + `alphamerge`).

---

## Data Model

A `mask` object is added to video layers in the template JSON:

```json
{
  "type": "video",
  "mask": {
    "shape": "none",
    "radius": 20,
    "points": [[0.1, 0.0], [0.9, 0.0], [1.0, 1.0], [0.0, 1.0]]
  }
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `shape` | `"none" \| "rect" \| "rounded_rect" \| "circle" \| "polygon"` | Active mask shape. `"none"` is the default — no masking applied. |
| `radius` | number | Corner radius in canvas pixels at 1080px width. Only used when `shape == "rounded_rect"`. Default `20`. |
| `points` | `[[x,y], ...]` | Polygon vertices, normalised 0–1 relative to layer width/height. Only used when `shape == "polygon"`. |

`mask` defaults to `{shape: "none"}` when absent from the layer. The existing export pipeline is unchanged when `shape == "none"`.

---

## Feature 1 — Canvas Preview (Fabric.js)

### Clip Path Assignment

When a video layer's mask is set or changed, a Fabric.js `clipPath` object is assigned to the video canvas object (`obj.clipPath`). All coordinates are in the object's local coordinate space (centred at 0,0):

| Shape | Fabric object |
|-------|--------------|
| `none` | `obj.clipPath = null` |
| `rect` | `new fabric.Rect({width: w, height: h, left: -w/2, top: -h/2, rx: 0, ry: 0})` |
| `rounded_rect` | `new fabric.Rect({width: w, height: h, left: -w/2, top: -h/2, rx: radius, ry: radius})` |
| `circle` | `new fabric.Ellipse({rx: w/2, ry: h/2, left: -w/2, top: -h/2})` |
| `polygon` | `new fabric.Polygon(denormalisedPoints)` where each point is `{x: p[0]*w - w/2, y: p[1]*h - h/2}` |

The clip path is applied in local space, so it scales correctly when the layer is resized.

### Polygon Drawing Mode

Triggered by clicking "Draw Polygon" in the properties panel. A module-level flag `_polygonDrawing` is set to `true`.

**While in drawing mode:**
1. Canvas cursor changes to `crosshair`
2. Each left-click on the canvas adds a point to `_polygonPoints[]`
3. A live preview is drawn: existing points as small dots, connected by lines, with a dashed line to the current mouse position
4. When the user clicks within 10px of the first point (and at least 3 points exist), the polygon closes — `_polygonDrawing` is set back to `false`, the points are normalised and stored as `obj._maskPoints`, and the clipPath is applied
5. Pressing `Escape` cancels drawing and discards in-progress points

The live preview is drawn on a dedicated `<canvas id="poly-overlay">` element positioned absolutely over the Fabric canvas (same size, `pointer-events:none`). On each `mousemove` the overlay canvas is cleared and redrawn with dots, connecting lines, and a dashed line to the cursor. This keeps the polygon preview completely separate from Fabric's rendering cycle.

### Properties Panel — Mask Section

A "Mask" section is added to the video layer properties panel (below the existing Fit and Audio sections):

- **Shape selector** — four toggle buttons: None / Rect / Rounded / Circle, plus a Polygon row
- **Radius slider** — shown only when shape is `rounded_rect` (0–100px)
- **"Draw Polygon" button** — shown only when shape is `polygon`; starts drawing mode
- **"Clear" button** — shown next to Draw Polygon if points already exist; resets to empty polygon

### Serialisation

`canvasToTemplate()` — video layer serialisation is extended:

```javascript
if(t==='video') return {
  ...base,
  fit: obj._fit || 'contain',
  volume: obj._audioVolume ?? 1.0,
  muted: obj._audioMuted === true,
  mask: {
    shape: obj._maskShape || 'none',
    radius: obj._maskRadius ?? 20,
    points: obj._maskPoints || [],
  }
};
```

`applySavedTpl()` — video layer restore restores `_maskShape`, `_maskRadius`, `_maskPoints` from `layer.mask` and re-applies the `clipPath`.

---

## Feature 2 — Mask PNG Renderer (Backend)

A new function `render_mask_png(shape, w, h, radius, points, path)` is added to `exporter.py` using Pillow (already installed):

```python
def render_mask_png(shape: str, w: int, h: int, radius: int,
                    points: list, path: str) -> None:
    """Render a white-on-black mask PNG at w×h pixels."""
    from PIL import Image, ImageDraw
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    if shape == "rect":
        draw.rectangle([0, 0, w - 1, h - 1], fill=255)
    elif shape == "rounded_rect":
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    elif shape == "circle":
        draw.ellipse([0, 0, w - 1, h - 1], fill=255)
    elif shape == "polygon" and points:
        pts = [(int(p[0] * w), int(p[1] * h)) for p in points]
        draw.polygon(pts, fill=255)
    img.save(path)
```

The function is a pure side-effectful helper — no subprocess, no FFmpeg. It is called from `export_video` during the pre-processing phase (same phase as text PNG rendering).

---

## Feature 3 — FFmpeg Integration

### Changes to `build_filter_graph`

The function signature gains a new parameter:

```python
def build_filter_graph(layers, cw, ch, text_pngs, image_inputs, mask_inputs):
```

`mask_inputs: dict[int, int]` — maps layer index → FFmpeg input stream index of the mask PNG.

For a `video` layer with a mask (when `layer_index in mask_inputs`), the filter chain becomes:

```
# 1. Scale video as normal
[0:v]scale=w:h:...[scaled]

# 2. Scale mask to same dimensions
[Nm:v]scale=w:h[mask_Nx]

# 3. Apply alpha mask
[scaled][mask_Nx]alphamerge[masked_Nx]

# 4. Overlay masked video onto current background (FFmpeg uses alpha automatically)
[current][masked_Nx]overlay=x=X:y=Y[vN]
```

When `shape == "none"` (or no mask), the existing overlay path is used unchanged.

### Changes to `export_video`

During pre-processing (alongside text PNG rendering):

```python
mask_inputs = {}
for i, l in enumerate(layers):
    shape = l.get("mask", {}).get("shape", "none")
    if shape != "none":
        p = str(TEMP_DIR / f"{job_id}_mask{i}.png")
        lw, lh = l.get("width", cw), l.get("height", ch)
        radius = l.get("mask", {}).get("radius", 20)
        points = l.get("mask", {}).get("points", [])
        render_mask_png(shape, lw, lh, radius, points, p)
        mask_inputs[i] = len(extra_inputs) + 1
        extra_inputs.append(p)
```

Temp mask PNGs are cleaned up alongside text PNGs at the end of `export_video`.

---

## File / Component Boundaries

| File | Change |
|------|--------|
| `exporter.py` | Add `render_mask_png()`; extend `build_filter_graph(mask_inputs)`; add mask pre-processing in `export_video` |
| `tests/test_exporter.py` | Tests for `render_mask_png` (all shapes) + `build_filter_graph` with mask |
| `frontend/index.html` | Mask section in video layer properties panel; polygon drawing mode; `canvasToTemplate` + `applySavedTpl` mask serialisation |

---

## Out of Scope

- Masking blur_video layers
- Animated masks (mask that changes over time)
- Feathered / soft edges on masks
- Importing custom SVG paths (polygon drawing covers the use case)
