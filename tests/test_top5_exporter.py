import unittest.mock as mock
from pathlib import Path

from top5_exporter import resolve_placeholders

SLOTS = [
    {"rank": 5, "title": "Clip Five", "path": "a.mp4", "start": 0, "end": 10},
    {"rank": 3, "title": "Clip Three", "path": "b.mp4", "start": 0, "end": 10},
    {"rank": 4, "title": "Clip Four", "path": "c.mp4", "start": 0, "end": 10},
    {"rank": 1, "title": "Clip One", "path": "d.mp4", "start": 0, "end": 10},
    {"rank": 2, "title": "Clip Two", "path": "e.mp4", "start": 0, "end": 10},
]

def test_current_tokens_resolve_to_active_slot():
    result = resolve_placeholders("<current:rank> <current:title>", SLOTS, 0)
    assert result == "5 Clip Five"

def test_current_tokens_for_second_slot():
    result = resolve_placeholders("<current:rank> <current:title>", SLOTS, 1)
    assert result == "3 Clip Three"

def test_past_slot_title_visible():
    # slot1 (idx 0) is past when current_idx=2 — title should show
    result = resolve_placeholders("<slot1:title>", SLOTS, 2)
    assert result == "Clip Five"

def test_future_slot_title_is_dash():
    # slot5 (idx 4) is future when current_idx=1
    result = resolve_placeholders("<slot5:title>", SLOTS, 1)
    assert result == "—"

def test_current_slot_title_visible():
    # slot3 (idx 2) is current when current_idx=2
    result = resolve_placeholders("<slot3:title>", SLOTS, 2)
    assert result == "Clip Four"

def test_slot_rank_always_resolves():
    result = resolve_placeholders("<slot2:rank>", SLOTS, 0)
    assert result == "3"

def test_no_placeholders_unchanged():
    result = resolve_placeholders("Hello World", SLOTS, 0)
    assert result == "Hello World"

def test_multiple_tokens_in_one_string():
    text = "<slot1:rank>  <slot1:title> | <slot2:rank>  <slot2:title>"
    result = resolve_placeholders(text, SLOTS, 3)
    assert result == "5  Clip Five | 3  Clip Three"


def test_render_slot_calls_ffmpeg(tmp_path):
    template = {
        "canvas": {"width": 1080, "height": 1920},
        "layers": [
            {"id": "bg", "type": "shape", "x": 0, "y": 0,
             "width": 1080, "height": 1920, "fill": "#000000", "opacity": 1.0},
            {"id": "vid", "type": "video", "x": 0, "y": 0,
             "width": 1080, "height": 1920, "fit": "cover"},
        ]
    }
    slot = {"rank": 5, "title": "Test Clip", "path": "/fake/clip.mp4", "start": 0.0, "end": 5.0}

    with mock.patch("top5_exporter.subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0, stderr=b"")
        from top5_exporter import render_slot
        out = render_slot(slot, [slot], 0, template, "testjob", tmp_path)

    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "ffmpeg" in cmd
    assert "/fake/clip.mp4" in cmd
    assert "-ss" in cmd
    assert "0.0" in cmd
    assert "-to" in cmd
    assert "5.0" in cmd
    assert out == str(tmp_path / "testjob_slot0.mp4")

def test_render_slot_raises_on_ffmpeg_error(tmp_path):
    template = {
        "canvas": {"width": 1080, "height": 1920},
        "layers": [
            {"id": "vid", "type": "video", "x": 0, "y": 0,
             "width": 1080, "height": 1920, "fit": "cover"},
        ]
    }
    slot = {"rank": 5, "title": "Test", "path": "/fake.mp4", "start": 0.0, "end": 5.0}

    with mock.patch("top5_exporter.subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=1, stderr=b"some ffmpeg error")
        from top5_exporter import render_slot
        try:
            render_slot(slot, [slot], 0, template, "testjob", tmp_path)
            assert False, "should have raised"
        except RuntimeError as e:
            assert "slot 0" in str(e)
