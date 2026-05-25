import os, tempfile
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
