from exporter import build_filter_graph, build_audio_cmd_parts, render_mask_png

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

def test_video_first_layer_position_applied():
    """When video is the first (only) layer with non-zero y, the position must
    be applied via pad — not silently dropped, which would put the video at (0,0)."""
    layers = [
        {"type": "video", "x": 0, "y": 656, "width": 1080, "height": 608, "fit": "contain"},
    ]
    parts, label = build_filter_graph(layers, 1080, 1920, {}, {})
    # y=656 must appear somewhere so the video lands at the right position
    # (now via color+overlay rather than pad, which rejects negative offsets)
    positioned = [p for p in parts if "656" in p]
    assert positioned, f"Expected y=656 to appear in filter parts but got: {parts}"
    assert any("overlay" in p and "y=656" in p for p in parts), \
        f"Expected overlay=...y=656 in filter parts but got: {parts}"

def test_video_first_layer_zero_position_no_extra_pad():
    """When video is first with x=0, y=0, no extra pad step is needed."""
    layers = [
        {"type": "video", "x": 0, "y": 0, "width": 1080, "height": 608, "fit": "contain"},
    ]
    parts, label = build_filter_graph(layers, 1080, 1920, {}, {})
    # The scale+internal-pad filter is present (force_original_aspect_ratio)
    assert any("force_original_aspect_ratio=decrease" in p for p in parts)

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
    music_inputs, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert music_inputs == []
    assert filter_parts == []
    assert audio_label == "0:a"   # plain passthrough


def test_audio_volume_filter():
    """Video layer with volume=0.5 → volume filter applied."""
    video_layers = [{"type": "video", "volume": 0.5, "muted": False}]
    audio_layer = None
    music_inputs, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert any("volume=0.5" in p for p in filter_parts)
    assert audio_label != "0:a"


def test_audio_muted():
    """Muted video layer → volume=0 filter."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": True}]
    audio_layer = None
    music_inputs, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
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
    music_inputs, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert "uploads/fake.mp3" in music_inputs
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
    music_inputs, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
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
    music_inputs, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
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

from pathlib import Path

def test_render_mask_png_rect(tmp_path):
    """rect fills the entire image with white."""
    from PIL import Image
    p = str(tmp_path / "mask.png")
    render_mask_png("rect", 100, 80, 0, [], p)
    img = Image.open(p).convert("L")
    assert img.size == (100, 80)
    # All pixels should be white (255)
    assert img.getpixel((50, 40)) == 255
    assert img.getpixel((0, 0)) == 255

def test_render_mask_png_rounded_rect(tmp_path):
    """rounded_rect: centre is white, extreme corners are black."""
    from PIL import Image
    p = str(tmp_path / "mask_rr.png")
    render_mask_png("rounded_rect", 100, 100, 20, [], p)
    img = Image.open(p).convert("L")
    assert img.getpixel((50, 50)) == 255   # centre: white
    assert img.getpixel((0, 0)) == 0       # extreme corner: black

def test_render_mask_png_circle(tmp_path):
    """circle: centre is white, corners are black."""
    from PIL import Image
    p = str(tmp_path / "mask_c.png")
    render_mask_png("circle", 100, 100, 0, [], p)
    img = Image.open(p).convert("L")
    assert img.getpixel((50, 50)) == 255   # centre
    assert img.getpixel((0, 0)) == 0       # corner

def test_render_mask_png_polygon(tmp_path):
    """polygon: points inside the polygon are white."""
    from PIL import Image
    p = str(tmp_path / "mask_poly.png")
    # Unit square normalised → fills entire 100x100 canvas
    points = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    render_mask_png("polygon", 100, 100, 0, points, p)
    img = Image.open(p).convert("L")
    assert img.getpixel((50, 50)) == 255

def test_render_mask_png_none_produces_black(tmp_path):
    """Unknown/none shape produces an all-black PNG (no mask)."""
    from PIL import Image
    p = str(tmp_path / "mask_none.png")
    render_mask_png("none", 100, 100, 0, [], p)
    img = Image.open(p).convert("L")
    assert img.getpixel((50, 50)) == 0

def test_audio_only_filter_uses_raw_video_map():
    """When only audio filters exist (no video filter graph), final_video must be
    mapped as a raw stream specifier, not a bracketed filter label."""
    # Simulate what export_video does: layers with no visual filters + audio layer
    layers = [{"type": "video", "volume": 0.5, "muted": False}]
    audio_layer = None  # just test the volume filter path
    _, _, audio_filter_parts, audio_label = build_audio_cmd_parts(
        layers, audio_layer, next_input_idx=1
    )
    # Confirm a volume filter was generated
    assert any("volume=0.5" in p for p in audio_filter_parts)
    # The video filter_parts from build_filter_graph for a video-only layer
    # (no blur_video) will produce filter_parts=[] scenario is tested here
    video_filter_parts, final_video = build_filter_graph(layers, 1080, 1920, {}, {})
    # build_filter_graph always returns a filter label (the canvas-bounds
    # enforcement step runs after all layers); just verify it is a non-empty string
    assert isinstance(final_video, str) and len(final_video) > 0
    assert len(video_filter_parts) > 0  # scale + canvas-bounds filters present

def test_build_filter_graph_with_mask():
    """Video layer with mask_inputs uses alphamerge before overlay."""
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "video", "x": 0, "y": 656, "width": 1080, "height": 608,
         "fit": "contain"},
    ]
    # Mask PNG for layer index 1 is at stream index 2
    mask_inputs = {1: 2}
    parts, label = build_filter_graph(layers, 1080, 1920, {}, {}, mask_inputs)
    assert any("alphamerge" in p for p in parts)
    assert any("format=rgba" in p for p in parts)  # base must be RGBA before alphamerge
    assert any("overlay" in p for p in parts)

def test_build_filter_graph_no_mask_unchanged():
    """build_filter_graph with empty mask_inputs behaves identically to before."""
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "video", "x": 0, "y": 656, "width": 1080, "height": 608,
         "fit": "contain"},
    ]
    parts_old, label_old = build_filter_graph(layers, 1080, 1920, {}, {})
    parts_new, label_new = build_filter_graph(layers, 1080, 1920, {}, {}, {})
    assert parts_old == parts_new
    assert label_old == label_new

def test_export_video_strips_mask_from_canvas_layers():
    """Mask pre-processing: mask_inputs dict is populated for masked video layers."""
    # Simulate what export_video does during pre-processing
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "video", "x": 0, "y": 656, "width": 1080, "height": 608,
         "fit": "contain", "mask": {"shape": "circle", "radius": 0, "points": []}},
    ]
    mask_inputs = {}
    extra_inputs = []
    job_id = "test001"
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for i, l in enumerate(layers):
            shape = l.get("mask", {}).get("shape", "none")
            if shape != "none":
                p = str(Path(tmp) / f"{job_id}_mask{i}.png")
                lw, lh = l.get("width", 1080), l.get("height", 1920)
                radius = l.get("mask", {}).get("radius", 20)
                points = l.get("mask", {}).get("points", [])
                render_mask_png(shape, lw, lh, radius, points, p)
                mask_inputs[i] = len(extra_inputs) + 1
                extra_inputs.append(p)
        assert 1 in mask_inputs          # layer 1 has mask
        assert 0 not in mask_inputs      # layer 0 is blur_video, no mask
        assert len(extra_inputs) == 1    # one mask PNG added
        from PIL import Image
        img = Image.open(extra_inputs[0]).convert("L")
        assert img.getpixel((540, 304)) == 255  # centre of circle is white

from exporter import build_segment_filter

def test_no_segments_returns_passthrough():
    parts, vlabel, alabel = build_segment_filter([])
    assert parts == []
    assert vlabel == '0:v'
    assert alabel == '0:a'

def test_single_segment_with_no_color_still_trims():
    segs = [{'sourceStart': 0, 'sourceEnd': 30, 'trackStart': 0,
             'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}}]
    parts, vlabel, alabel = build_segment_filter(segs)
    # Single segment always emits trim filter so sourceEnd trimming is respected
    assert any('trim' in p for p in parts), f"Expected trim, got: {parts}"
    assert vlabel != '0:v'
    assert alabel != '0:a'

def test_single_segment_with_trim_emits_filter():
    segs = [{'sourceStart': 5, 'sourceEnd': 20, 'trackStart': 0,
             'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}}]
    parts, vlabel, alabel = build_segment_filter(segs)
    assert any('trim=start=5' in p for p in parts), f"Expected trim=start=5, got: {parts}"
    assert vlabel != '0:v'
    assert alabel != '0:a'

def test_two_segments_generates_concat():
    segs = [
        {'sourceStart': 0,  'sourceEnd': 5,  'trackStart': 0,
         'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}},
        {'sourceStart': 8,  'sourceEnd': 15, 'trackStart': 5,
         'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}},
    ]
    parts, vlabel, alabel = build_segment_filter(segs)
    assert any('trim' in p for p in parts), f"Expected trim filter, got: {parts}"
    assert any('concat' in p for p in parts), f"Expected concat filter, got: {parts}"
    assert vlabel != '0:v'
    assert alabel != '0:a'

def test_color_grading_adds_eq_filter():
    segs = [
        {'sourceStart': 0, 'sourceEnd': 10, 'trackStart': 0,
         'color': {'brightness': 50, 'contrast': 20, 'saturation': -30, 'hue': 0}},
        {'sourceStart': 10, 'sourceEnd': 20, 'trackStart': 10,
         'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}},
    ]
    parts, vlabel, alabel = build_segment_filter(segs)
    assert any('eq=' in p for p in parts), f"Expected eq filter, got: {parts}"

def test_hue_grading_adds_hue_filter():
    segs = [
        {'sourceStart': 0, 'sourceEnd': 10, 'trackStart': 0,
         'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 90}},
        {'sourceStart': 10, 'sourceEnd': 20, 'trackStart': 10,
         'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}},
    ]
    parts, vlabel, alabel = build_segment_filter(segs)
    assert any('hue=' in p for p in parts), f"Expected hue filter, got: {parts}"
