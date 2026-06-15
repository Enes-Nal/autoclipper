import json, threading
from unittest.mock import patch, MagicMock
from app import app

client = app.test_client()


def _fake_download(url, job_id, on_progress=None):
    if on_progress:
        on_progress({"percent": 100, "status": "downloading"})
    return {"video_path": "/fake/video.mp4", "title": "Test"}


def _fake_export(*args, **kwargs):
    if kwargs.get("on_progress"):
        kwargs["on_progress"]("frame=100")
    return "/fake/exports/out.mp4"


def _fake_load_template(name):
    return {
        "name": "Blur Stack",
        "format": "9:16",
        "canvas": {"width": 1080, "height": 1920},
        "layers": [{"id": "title", "type": "text", "role": "title", "text": "{title}"}],
    }


def test_express_export_bad_request():
    r = client.post("/api/express-export", json={})
    assert r.status_code == 400
    assert b"url" in r.data


def test_express_export_missing_template():
    r = client.post("/api/express-export", json={"url": "https://x.com/v/1", "template_name": ""})
    assert r.status_code == 400
    assert b"template" in r.data


def test_express_export_returns_job_id():
    with patch("app.download_video", side_effect=_fake_download), \
         patch("app.export_video", side_effect=_fake_export), \
         patch("app._load_template_by_name", side_effect=_fake_load_template):
        r = client.post("/api/express-export", json={
            "url": "https://x.com/v/1",
            "template_name": "blur-stack",
            "title": "My clip",
        })
    assert r.status_code == 200
    assert "job_id" in r.get_json()


def test_express_export_start_only_creates_segment():
    """start_time without duration should still trim from start to end of video."""
    captured = {}

    def _fake_export_capture(*args, **kwargs):
        captured['segments'] = kwargs.get('segments')
        return "/fake/exports/out.mp4"

    with patch("app.download_video", side_effect=_fake_download), \
         patch("app.export_video", side_effect=_fake_export_capture), \
         patch("app._load_template_by_name", side_effect=_fake_load_template):
        client.post("/api/express-export", json={
            "url": "https://x.com/v/1",
            "template_name": "blur-stack",
            "title": "My clip",
            "start_time": "00:30",
        })

    import time; time.sleep(0.2)  # let background thread run
    assert captured.get('segments') is not None
    assert captured['segments'][0]['sourceStart'] == 30.0
    assert 'sourceEnd' not in captured['segments'][0]


def test_parse_time_seconds():
    from app import _parse_time_to_seconds
    assert _parse_time_to_seconds("01:30") == 90.0
    assert _parse_time_to_seconds("1:00:00") == 3600.0
    assert _parse_time_to_seconds("45") == 45.0
    assert _parse_time_to_seconds("") is None
    assert _parse_time_to_seconds(None) is None
