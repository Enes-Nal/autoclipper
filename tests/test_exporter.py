from exporter import build_filter_graph

def test_blur_video_layer():
    parts, label = build_filter_graph(
        [{"type": "blur_video", "blur": 20}], 1080, 1920, {}, {}
    )
    assert any("boxblur" in p for p in parts)
    assert label is not None

def test_video_contain_layer():
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "video", "x": 0, "y": 656, "width": 1080, "height": 608, "fit": "contain"},
    ]
    parts, label = build_filter_graph(layers, 1080, 1920, {}, {})
    assert any("force_original_aspect_ratio=decrease" in p for p in parts)
    assert any("overlay" in p for p in parts)

def test_shape_layer():
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "shape", "x": 0, "y": 0, "width": 1080, "height": 120,
         "fill": "#000000", "opacity": 0.8},
    ]
    parts, label = build_filter_graph(layers, 1080, 1920, {}, {})
    assert any("drawbox" in p for p in parts)

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
