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
