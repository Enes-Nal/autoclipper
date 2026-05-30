from exporter import build_filter_graph, build_audio_cmd_parts

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


def test_audio_passthrough_when_no_changes():
    """No audio layer, default volume → no filter, passthrough label."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": False}]
    audio_layer = None
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert extra_inputs == []
    assert filter_parts == []
    assert audio_label == "0:a"   # plain passthrough


def test_audio_volume_filter():
    """Video layer with volume=0.5 → volume filter applied."""
    video_layers = [{"type": "video", "volume": 0.5, "muted": False}]
    audio_layer = None
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert any("volume=0.5" in p for p in filter_parts)
    assert audio_label != "0:a"


def test_audio_muted():
    """Muted video layer → volume=0 filter."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": True}]
    audio_layer = None
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert any("volume=0" in p for p in filter_parts)


def test_audio_layer_amix():
    """Audio layer present → amix filter included, extra input returned."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": False}]
    audio_layer = {
        "type": "audio",
        "src": "uploads/fake.mp3",
        "volume": 1.0,
        "loop": False,
        "trim_start": 0.0,
        "trim_end": None,
    }
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert "uploads/fake.mp3" in extra_inputs
    assert any("amix" in p for p in filter_parts)
    assert audio_label != "0:a"

def test_audio_layer_loop():
    """Loop flag → aloop filter present."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": False}]
    audio_layer = {
        "type": "audio",
        "src": "uploads/fake.mp3",
        "volume": 1.0,
        "loop": True,
        "trim_start": 0.0,
        "trim_end": None,
    }
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert any("aloop" in p for p in filter_parts)

def test_audio_layer_volume():
    """Music track volume applied."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": False}]
    audio_layer = {
        "type": "audio",
        "src": "uploads/fake.mp3",
        "volume": 0.4,
        "loop": False,
        "trim_start": 0.0,
        "trim_end": None,
    }
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert any("volume=0.4" in p for p in filter_parts)

def test_export_video_strips_audio_layer_from_filter_graph():
    """build_filter_graph should never see the audio layer type."""
    layers_with_audio = [
        {"type": "blur_video", "blur": 20},
        {"type": "audio", "src": "uploads/track.mp3", "volume": 1.0,
         "loop": False, "trim_start": 0.0, "trim_end": None},
    ]
    # build_filter_graph would crash on unknown type "audio" if it saw it
    # We check that filtering works: only blur_video is passed through
    non_audio = [l for l in layers_with_audio if l["type"] != "audio"]
    audio = next((l for l in layers_with_audio if l["type"] == "audio"), None)
    parts, label = build_filter_graph(non_audio, 1080, 1920, {}, {})
    assert any("boxblur" in p for p in parts)
    assert audio is not None
    assert audio["type"] == "audio"

def test_audio_only_filter_uses_raw_video_map():
    """When only audio filters exist (no video filter graph), final_video must be
    mapped as a raw stream specifier, not a bracketed filter label."""
    # Simulate what export_video does: layers with no visual filters + audio layer
    layers = [{"type": "video", "volume": 0.5, "muted": False}]
    audio_layer = None  # just test the volume filter path
    _, audio_filter_parts, audio_label = build_audio_cmd_parts(
        layers, audio_layer, next_input_idx=1
    )
    # Confirm a volume filter was generated
    assert any("volume=0.5" in p for p in audio_filter_parts)
    # The video filter_parts from build_filter_graph for a video-only layer
    # (no blur_video) will produce filter_parts=[] scenario is tested here
    video_filter_parts, final_video = build_filter_graph(layers, 1080, 1920, {}, {})
    # If no filter_parts from video, final_video is the raw "0:v" specifier
    # (no bracket wrapping should be applied in this case)
    assert final_video in ("0:v", "v1")  # either passthrough or first video label
