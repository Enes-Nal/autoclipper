from downloader import parse_progress, get_job_path
from pathlib import Path

def test_parse_progress_percentage():
    line = "[download]  45.3% of 12.34MiB at 2.50MiB/s ETA 00:03"
    result = parse_progress(line)
    assert result == {"percent": 45.3, "status": "downloading"}

def test_parse_progress_complete():
    line = "[download] 100% of 12.34MiB"
    result = parse_progress(line)
    assert result == {"percent": 100.0, "status": "downloading"}

def test_parse_progress_non_download_line():
    result = parse_progress("[info] Writing video metadata")
    assert result is None

def test_get_job_path():
    p = get_job_path("abc123")
    assert str(p) == str(Path("downloads") / "abc123.mp4")
