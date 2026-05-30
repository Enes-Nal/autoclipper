# Text Alignment & Frame-Constrained Wrapping — Design Spec

**Date:** 2026-05-29  
**Status:** Approved

## Problem

Text layers in the editor support L/C/R alignment (via `textAlign`) and have explicit width/height bounds on the canvas. However, the video export ignores both: text is drawn at a fixed (x, y) point with no wrapping and no alignment. The result is that exported videos look different from the canvas preview.

## Goal

Make exported text match what the user sees on canvas:
- Text wraps at the frame's width
- Text is clipped at the frame's height
- Text is left-, center-, or right-aligned within the frame

## What's in Scope

- `text_renderer.py`: add word-wrap, alignment, and height clipping to `render_text_layer`
- `exporter.py`: route all text layers through PIL (remove the FFmpeg `drawtext` branch)

## What's Out of Scope

- Vertical alignment (top/middle/bottom) within the frame
- Automatic font-size shrinking to fit
- UI changes (alignment buttons and export serialization already work correctly)

## Approach: Unify on PIL

Today there are two export paths for text:
- **PIL** (`render_text_layer`): used when the text contains emoji
- **FFmpeg `drawtext`**: used for all other text

FFmpeg's `drawtext` filter has no native word-wrap support. Rather than implement two separate alignment+wrapping solutions, all text layers will be rendered to a transparent PNG via PIL and composited by FFmpeg as an image overlay — exactly what the emoji path does today.

## Design

### `text_renderer.py` — `render_text_layer`

**Inputs used** (already in layer dict, already exported by frontend):
- `x`, `y` — top-left of the text frame
- `width`, `height` — frame bounds
- `text_align` — `"left"` | `"center"` | `"right"` (default `"center"`)
- `font_size`, `fill`, `stroke`, `stroke_width`, `text` — unchanged

**Word-wrap algorithm:**
1. Split `text` on spaces into words.
2. Greedily build lines: append words until adding the next word would exceed `width` (measured with `font.getlength()`).
3. Each full line is added to a `lines[]` list.

**Per-line rendering:**
- `line_h = bbox_height * 1.2` (bbox from `font.getbbox("Ay")`, 1.2× leading)
- Starting `y_cursor = layer["y"]`
- For each line:
  - If `y_cursor + line_h > layer["y"] + layer["height"]`: stop (height clip)
  - Compute `x_cursor`:
    - `left`: `layer["x"]`
    - `center`: `layer["x"] + (layer["width"] - line_width) / 2`
    - `right`: `layer["x"] + layer["width"] - line_width`
  - Call `draw.text((x_cursor, y_cursor), line, ...)` with existing stroke params
  - `y_cursor += line_h`

### `exporter.py` — `build_filter_graph` / `export_video`

**Remove:** the `else` branch in the `elif t == "text"` block (~lines 83–93) that builds a `drawtext` filter string.

**Change:** in `export_video`, remove the `has_emoji()` guard so every text layer is pre-rendered to PNG:

```python
# Before
if l["type"] == "text" and has_emoji(l.get("text", "")):

# After
if l["type"] == "text":
```

The `build_filter_graph` text branch already handles the PNG overlay path (`if i in text_pngs:`). With all text layers always in `text_pngs`, the `else` drawtext branch is dead code and will be removed.

## Data Format

No changes. Templates already store `width`, `height`, and `text_align` for text layers. No migration needed.

## Testing

- Text with no wrap (short string) should render at the correct alignment position
- Text that exceeds frame width should wrap onto multiple lines
- Text that exceeds frame height should clip — bottom lines not drawn
- All three alignments (left/center/right) should render correctly in the exported MP4
- Emoji text should continue to work as before
