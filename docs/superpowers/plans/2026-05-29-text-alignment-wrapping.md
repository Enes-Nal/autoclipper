# Text Alignment & Frame-Constrained Wrapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make exported video text respect the canvas text frame — wrapping at frame width, clipping at frame height, and honoring left/center/right alignment.

**Architecture:** All text layers are pre-rendered to transparent PNGs via PIL and composited by FFmpeg as image overlays. The FFmpeg `drawtext` branch is removed entirely. `render_text_layer` gains word-wrap, horizontal alignment, and height clipping.

**Tech Stack:** Python, Pillow (PIL), FFmpeg (via subprocess)

---

## File Map

| File | Change |
|------|--------|
| `text_renderer.py` | Add word-wrap, alignment, height clipping to `render_text_layer` |
| `exporter.py` | Remove `has_emoji` guard (all text → PIL); remove `drawtext` else-branch |
| `tests/test_text_renderer.py` | Add tests for wrap, clip, alignment |
| `tests/test_exporter.py` | Update `test_text_drawtext_layer` → assert overlay path, not drawtext |

---

## Task 1: Tests for word-wrap and height clipping in `render_text_layer`

**Files:**
- Modify: `tests/test_text_renderer.py`

- [ ] **Step 1: Add failing test for word-wrap**

Append to `tests/test_text_renderer.py`:

```python
import numpy as np

def test_render_text_layer_wraps_long_text():
    """Long text in a narrow frame should produce pixels on a second line."""
    layer = {
        "type": "text",
        "x": 0, "y": 0,
        "width": 200, "height": 300,
        "text": "This is a very long line of text that must wrap",
        "font_size": 40, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            arr = np.array(img)
        # Alpha channel (channel 3) should have non-zero pixels below row 60
        # (i.e., a second line of text was drawn)
        assert arr[60:120, :, 3].max() > 0, "Expected a second line of text"
    finally:
        os.unlink(path)
```

- [ ] **Step 2: Add failing test for height clipping**

Append to `tests/test_text_renderer.py`:

```python
def test_render_text_layer_clips_at_frame_height():
    """Text must not be drawn below y + height."""
    layer = {
        "type": "text",
        "x": 0, "y": 0,
        "width": 200, "height": 45,   # only tall enough for ~1 line at font 40
        "text": "Line one\nLine two\nLine three\nLine four",
        "font_size": 40, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            arr = np.array(img)
        # No visible pixels below y + height (row 45)
        assert arr[45:, :, 3].max() == 0, "Text must not exceed frame height"
    finally:
        os.unlink(path)
```

- [ ] **Step 3: Run tests to confirm they fail**

```
cd D:\Code\autoclipper
python -m pytest tests/test_text_renderer.py::test_render_text_layer_wraps_long_text tests/test_text_renderer.py::test_render_text_layer_clips_at_frame_height -v
```

Expected: both FAIL (current implementation draws at a single point with no wrap/clip).

---

## Task 2: Tests for alignment in `render_text_layer`

**Files:**
- Modify: `tests/test_text_renderer.py`

- [ ] **Step 1: Add failing test for left vs right alignment**

Append to `tests/test_text_renderer.py`:

```python
def _leftmost_nonzero_col(arr):
    """Return the leftmost column that has any non-transparent pixel."""
    for col in range(arr.shape[1]):
        if arr[:, col, 3].max() > 0:
            return col
    return arr.shape[1]

def test_render_text_layer_alignment():
    """Left-aligned text should start further left than right-aligned text."""
    base = {
        "type": "text",
        "x": 100, "y": 0,
        "width": 400, "height": 200,
        "text": "Hello",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
    }
    results = {}
    for align in ("left", "center", "right"):
        layer = {**base, "text_align": align}
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            results[align] = _leftmost_nonzero_col(np.array(img))
        os.unlink(path)

    assert results["left"] < results["center"], "Left should start before center"
    assert results["center"] < results["right"], "Center should start before right"
```

- [ ] **Step 2: Run test to confirm it fails**

```
cd D:\Code\autoclipper
python -m pytest tests/test_text_renderer.py::test_render_text_layer_alignment -v
```

Expected: FAIL.

---

## Task 3: Implement word-wrap, alignment, and height clipping in `render_text_layer`

**Files:**
- Modify: `text_renderer.py`

- [ ] **Step 1: Replace `render_text_layer` with the new implementation**

Replace the entire `render_text_layer` function in `text_renderer.py` with:

```python
def render_text_layer(layer: dict, canvas_w: int, canvas_h: int, output_path: str):
    """Render a text layer (with optional emoji) to a transparent RGBA PNG.

    Respects frame width (word-wrap), frame height (clip), and text_align.
    """
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(layer.get("font_size", 72))
    fill = layer.get("fill", "#ffffff")
    stroke = layer.get("stroke", "#000000")
    stroke_w = int(layer.get("stroke_width", 0))
    text = layer.get("text", "")
    align = layer.get("text_align", "center")

    frame_x = layer.get("x", 0)
    frame_y = layer.get("y", 0)
    frame_w = layer.get("width", canvas_w)
    frame_h = layer.get("height", canvas_h)

    # Line height: bounding box of a tall character * 1.2 leading
    bbox = font.getbbox("Ay")
    line_h = int((bbox[3] - bbox[1]) * 1.2)

    # Build wrapped lines respecting frame_w
    raw_lines = text.split("\n")
    lines = []
    for raw in raw_lines:
        words = raw.split(" ")
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if font.getlength(candidate) <= frame_w:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

    # Draw each line, clipping at frame_h
    y_cursor = frame_y
    for line in lines:
        if y_cursor + line_h > frame_y + frame_h:
            break
        line_w = font.getlength(line)
        if align == "left":
            x_cursor = frame_x
        elif align == "right":
            x_cursor = frame_x + frame_w - line_w
        else:  # center
            x_cursor = frame_x + (frame_w - line_w) / 2
        draw.text(
            (x_cursor, y_cursor), line, font=font, fill=fill,
            stroke_width=stroke_w, stroke_fill=stroke,
        )
        y_cursor += line_h

    img.save(output_path, "PNG")
```

- [ ] **Step 2: Run all text renderer tests**

```
cd D:\Code\autoclipper
python -m pytest tests/test_text_renderer.py -v
```

Expected: all 6 tests PASS (3 existing + 3 new).

- [ ] **Step 3: Commit**

```
git add text_renderer.py tests/test_text_renderer.py
git commit -m "feat: add word-wrap, alignment, and height clipping to render_text_layer"
```

---

## Task 4: Update `exporter.py` — all text through PIL

**Files:**
- Modify: `exporter.py`

- [ ] **Step 1: Remove `has_emoji` guard in `export_video`**

In `exporter.py`, find this block (around line 132):

```python
        if l["type"] == "text" and has_emoji(l.get("text", "")):
```

Change it to:

```python
        if l["type"] == "text":
```

- [ ] **Step 2: Remove the `drawtext` else-branch in `build_filter_graph`**

In `build_filter_graph`, find the `elif t == "text":` block. It currently looks like:

```python
        elif t == "text":
            if i in text_pngs:
                idx = text_pngs[i]
                out = lbl()
                parts.append(f"[{current}][{idx}:v]overlay=x=0:y=0[{out}]")
                current = out
            else:
                text = layer.get("text", "").replace("'", "\\'").replace(":", "\\:")
                x, y = layer.get("x", 0), layer.get("y", 0)
                fs = layer.get("font_size", 72)
                fc = layer.get("fill", "#ffffff").lstrip("#")
                bc = layer.get("stroke", "#000000").lstrip("#")
                bw = layer.get("stroke_width", 0)
                ff = "fonts/Inter-Black.ttf"
                out = lbl()
                dt = (f"fontfile={ff}:text='{text}':x={x}:y={y}:fontsize={fs}:"
                      f"fontcolor=0x{fc}:bordercolor=0x{bc}:borderw={bw}")
                parts.append(f"[{current}]drawtext={dt}[{out}]")
                current = out
```

Replace it with:

```python
        elif t == "text":
            if i in text_pngs:
                idx = text_pngs[i]
                out = lbl()
                parts.append(f"[{current}][{idx}:v]overlay=x=0:y=0[{out}]")
                current = out
```

- [ ] **Step 3: Verify `has_emoji` import is still present** (it's still used for nothing now — remove the import too)

In `exporter.py` line 3, change:

```python
from text_renderer import render_text_layer, has_emoji
```

to:

```python
from text_renderer import render_text_layer
```

- [ ] **Step 4: Run exporter tests (expect one failure — to be fixed in Task 5)**

```
cd D:\Code\autoclipper
python -m pytest tests/test_exporter.py -v
```

Expected: `test_text_drawtext_layer` FAILS (asserts `drawtext` in parts — no longer true). All other tests PASS.

- [ ] **Step 5: Commit work-in-progress**

```
git add exporter.py
git commit -m "feat: route all text layers through PIL renderer, remove drawtext branch"
```

---

## Task 5: Update `test_exporter.py` — fix broken test

**Files:**
- Modify: `tests/test_exporter.py`

- [ ] **Step 1: Replace `test_text_drawtext_layer` with a test for the PNG overlay path**

In `tests/test_exporter.py`, replace:

```python
def test_text_drawtext_layer():
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "text", "x": 40, "y": 80, "text": "Hello world",
         "font_size": 72, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 6},
    ]
    parts, label = build_filter_graph(layers, 1080, 1920, {}, {})
    assert any("drawtext" in p for p in parts)
```

with:

```python
def test_text_layer_uses_png_overlay():
    """Text layers must be composited via overlay (PNG path), not drawtext."""
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "text", "x": 40, "y": 80, "width": 600, "height": 200,
         "text": "Hello world", "font_size": 72, "fill": "#ffffff",
         "stroke": "#000000", "stroke_width": 6, "text_align": "center"},
    ]
    # layer index 1 is the text layer — pass it as pre-rendered PNG at stream index 2
    text_pngs = {1: 2}
    parts, label = build_filter_graph(layers, 1080, 1920, text_pngs, {})
    assert any("overlay" in p for p in parts), "Text must use overlay, not drawtext"
    assert not any("drawtext" in p for p in parts), "drawtext must not be used"
```

- [ ] **Step 2: Run all exporter tests**

```
cd D:\Code\autoclipper
python -m pytest tests/test_exporter.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 3: Run full test suite**

```
cd D:\Code\autoclipper
python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```
git add tests/test_exporter.py
git commit -m "test: update exporter test to assert PNG overlay path for text layers"
```
