from exporter import build_audio_cmd_parts


def test_sfx_single_layer_adelay():
    """Single SFX layer at 1.35s → adelay=1350|1350 filter, sfx path in sfx_inputs."""
    layers = [
        {"type": "video", "volume": 1.0, "muted": False},
        {"type": "sfx", "src": "sfx/whoosh.mp3", "start_time": 1.35,
         "volume": 1.0, "muted": False},
    ]
    music_inputs, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        layers, None, next_input_idx=2
    )
    assert sfx_inputs == ["sfx/whoosh.mp3"]
    assert music_inputs == []
    assert any("adelay=1350|1350" in p for p in filter_parts)
    assert any("amix" in p for p in filter_parts)


def test_sfx_muted_layer_excluded():
    """Muted SFX layer is excluded from sfx_inputs and filter_parts."""
    layers = [
        {"type": "video", "volume": 1.0, "muted": False},
        {"type": "sfx", "src": "sfx/pop.mp3", "start_time": 0.5,
         "volume": 1.0, "muted": True},
    ]
    music_inputs, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        layers, None, next_input_idx=2
    )
    assert sfx_inputs == []
    assert not any("adelay" in p for p in filter_parts)
    assert audio_label == "0:a"


def test_sfx_volume_applied():
    """SFX layer with volume=0.5 → volume=0.5 in filter chain."""
    layers = [
        {"type": "video", "volume": 1.0, "muted": False},
        {"type": "sfx", "src": "sfx/ding.mp3", "start_time": 0.0,
         "volume": 0.5, "muted": False},
    ]
    _, sfx_inputs, filter_parts, _ = build_audio_cmd_parts(
        layers, None, next_input_idx=2
    )
    assert sfx_inputs == ["sfx/ding.mp3"]
    assert any("volume=0.5" in p for p in filter_parts)


def test_sfx_multiple_layers_all_included():
    """Two SFX layers → both paths in sfx_inputs, two adelay entries."""
    layers = [
        {"type": "video", "volume": 1.0, "muted": False},
        {"type": "sfx", "src": "sfx/a.mp3", "start_time": 1.0,
         "volume": 1.0, "muted": False},
        {"type": "sfx", "src": "sfx/b.mp3", "start_time": 2.5,
         "volume": 1.0, "muted": False},
    ]
    _, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        layers, None, next_input_idx=2
    )
    assert sfx_inputs == ["sfx/a.mp3", "sfx/b.mp3"]
    adelay_parts = [p for p in filter_parts if "adelay" in p]
    assert len(adelay_parts) == 2
    assert any("adelay=1000|1000" in p for p in filter_parts)
    assert any("adelay=2500|2500" in p for p in filter_parts)
    amix_parts = [p for p in filter_parts if "amix" in p]
    assert len(amix_parts) == 1
    assert "inputs=3" in amix_parts[0]   # video + sfx_a + sfx_b


def test_sfx_with_music_layer_all_mixed():
    """SFX + music layer → all three streams in a single amix."""
    layers = [
        {"type": "video", "volume": 1.0, "muted": False},
        {"type": "sfx", "src": "sfx/whoosh.mp3", "start_time": 0.5,
         "volume": 1.0, "muted": False},
    ]
    audio_layer = {
        "type": "audio", "src": "uploads/song.mp3",
        "volume": 1.0, "loop": False,
        "trim_start": 0.0, "trim_end": None,
    }
    music_inputs, sfx_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        layers, audio_layer, next_input_idx=2
    )
    assert sfx_inputs == ["sfx/whoosh.mp3"]
    assert music_inputs == ["uploads/song.mp3"]
    amix_parts = [p for p in filter_parts if "amix" in p]
    assert len(amix_parts) == 1
    assert "inputs=3" in amix_parts[0]   # video + sfx + music


def test_sfx_stream_index_offset():
    """SFX stream index accounts for next_input_idx (video + extra_inputs before it)."""
    layers = [
        {"type": "video", "volume": 1.0, "muted": False},
        {"type": "sfx", "src": "sfx/pop.mp3", "start_time": 1.0,
         "volume": 1.0, "muted": False},
    ]
    # next_input_idx=5 means 4 inputs before this (video + 3 text/image/mask pngs)
    _, sfx_inputs, filter_parts, _ = build_audio_cmd_parts(
        layers, None, next_input_idx=5
    )
    assert any("[5:a]" in p for p in filter_parts), \
        "SFX should use stream index 5 when next_input_idx=5"


def test_sfx_normalize_zero():
    """amix uses normalize=0 to prevent volume ducking."""
    layers = [
        {"type": "video", "volume": 1.0, "muted": False},
        {"type": "sfx", "src": "sfx/pop.mp3", "start_time": 0.0,
         "volume": 1.0, "muted": False},
    ]
    _, _, filter_parts, _ = build_audio_cmd_parts(layers, None, next_input_idx=2)
    amix_parts = [p for p in filter_parts if "amix" in p]
    assert any("normalize=0" in p for p in amix_parts)
