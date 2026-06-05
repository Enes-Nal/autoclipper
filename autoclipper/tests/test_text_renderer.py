import os, tempfile
import numpy as np
from text_renderer import has_emoji, render_text_layer
from PIL import Image

def test_has_emoji_true():
    assert has_emoji("Hello 🔥") is True

def test_has_emoji_false():
    assert has_emoji("Hello world") is False

def test_render_text_layer_creates_png():
    layer = {"type": "text", "x": 40, "y": 80, "text": "Test 🔥",
             "font_size": 48, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 4}
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            assert img.size == (1080, 1920)
            assert img.mode == "RGBA"
    finally:
        os.unlink(path)

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

def test_render_text_layer_wide_word_does_not_crash():
    """A single word wider than the frame should render without crashing."""
    layer = {
        "type": "text",
        "x": 0, "y": 0,
        "width": 10,   # narrower than any real word
        "height": 200,
        "text": "Superlongwordthatcannotfit",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            assert img.size == (1080, 1920)
            assert img.mode == "RGBA"
    finally:
        os.unlink(path)

def _topmost_nonzero_row(arr):
    """Return the topmost row that has any non-transparent pixel."""
    for row in range(arr.shape[0]):
        if arr[row, :, 3].max() > 0:
            return row
    return arr.shape[0]

def test_vertical_align_top_fixed():
    """In fixed frame mode with vertical_align=top, text starts near the top of the frame."""
    layer = {
        "type": "text", "x": 0, "y": 100,
        "width": 400, "height": 300,
        "text": "Hello",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
        "vertical_align": "top",
        "auto_height": False,
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            arr = np.array(img)
        top_row = _topmost_nonzero_row(arr)
        # Top-aligned text should start near y=100 (within 10px of font ascender)
        assert 90 <= top_row <= 115, f"Expected text near row 100, got {top_row}"
    finally:
        os.unlink(path)

def test_vertical_align_middle_fixed():
    """In fixed frame mode with vertical_align=middle, text is vertically centred in the frame."""
    layer = {
        "type": "text", "x": 0, "y": 0,
        "width": 400, "height": 400,
        "text": "Hello",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
        "vertical_align": "middle",
        "auto_height": False,
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            arr = np.array(img)
        top_row = _topmost_nonzero_row(arr)
        # Middle-aligned in a 400px frame: text block (~58px) starts around row 171
        # Allow +-20px tolerance
        assert 150 <= top_row <= 200, f"Expected text near row 171, got {top_row}"
    finally:
        os.unlink(path)

def test_vertical_align_bottom_fixed():
    """In fixed frame mode with vertical_align=bottom, text is near the bottom of the frame."""
    layer = {
        "type": "text", "x": 0, "y": 0,
        "width": 400, "height": 400,
        "text": "Hello",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
        "vertical_align": "bottom",
        "auto_height": False,
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            arr = np.array(img)
        top_row = _topmost_nonzero_row(arr)
        # Bottom-aligned in a 400px frame: single line (~58px) starts around row 342
        # Allow +-20px tolerance
        assert 320 <= top_row <= 400, f"Expected text near row 342, got {top_row}"
    finally:
        os.unlink(path)

def test_vertical_align_ignored_in_autoheight():
    """vertical_align has no effect when auto_height=True (default behaviour)."""
    base = {
        "type": "text", "x": 0, "y": 0,
        "width": 400, "height": 400,
        "text": "Hello",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
        "auto_height": True,
    }
    results = {}
    for v in ("top", "middle", "bottom"):
        layer = {**base, "vertical_align": v}
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            results[v] = _topmost_nonzero_row(np.array(img))
        os.unlink(path)
    assert results["top"] == results["middle"] == results["bottom"], \
        "vertical_align must not affect autoHeight rendering"
