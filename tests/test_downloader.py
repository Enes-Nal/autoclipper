from downloader import parse_progress, get_job_path
from pathlib import Path
from unittest.mock import patch, MagicMock
from downloader import extract_thumbnail, DOWNLOADS_DIR

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
    assert p.name == "abc123.mp4"
    assert p.parent.name == "downloads"


def test_extract_thumbnail_returns_path_on_success(tmp_path):
    """extract_thumbnail runs ffmpeg and returns the thumbnail path."""
    fake_video = tmp_path / "abc123.mp4"
    fake_video.write_bytes(b"fake")
    expected_thumb = tmp_path / "abc123_thumb.jpg"

    with patch("downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        expected_thumb.write_bytes(b"fake_thumb")  # simulate ffmpeg creating the file
        result = extract_thumbnail(str(fake_video), "abc123", base_dir=tmp_path)

    assert result == str(expected_thumb)
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "-ss" in args
    assert str(fake_video) in args
    assert str(expected_thumb) in args


def test_extract_thumbnail_returns_none_on_failure(tmp_path):
    """extract_thumbnail returns None when ffmpeg fails."""
    fake_video = tmp_path / "abc123.mp4"
    fake_video.write_bytes(b"fake")

    with patch("downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = extract_thumbnail(str(fake_video), "abc123", base_dir=tmp_path)

    assert result is None


def test_extract_thumbnail_returns_none_when_file_missing(tmp_path):
    """extract_thumbnail returns None if ffmpeg exits 0 but produces no file."""
    fake_video = tmp_path / "abc123.mp4"
    fake_video.write_bytes(b"fake")

    with patch("downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # Do NOT create the thumb file — simulates very short video
        result = extract_thumbnail(str(fake_video), "abc123", base_dir=tmp_path)

    assert result is None


def test_download_video_includes_thumbnail(tmp_path):
    """download_video() return dict includes a 'thumbnail' key with correct URL."""
    from downloader import download_video

    fake_mp4 = tmp_path / "testjob.mp4"
    thumb_file = tmp_path / "testjob_thumb.jpg"

    def fake_popen(cmd, **kwargs):
        fake_mp4.write_bytes(b"fake")
        m = MagicMock()
        m.stdout = iter(["[download]  100% of 1.00MiB\n"])
        m.returncode = 0
        m.wait = lambda: None
        return m

    with patch("downloader.subprocess.Popen", side_effect=fake_popen), \
         patch("downloader.get_video_title", return_value="Test Title"), \
         patch("downloader.subprocess.run") as mock_run, \
         patch("downloader.get_job_path", return_value=fake_mp4), \
         patch("downloader.DOWNLOADS_DIR", tmp_path):
        # First call to subprocess.run is ffprobe (probe_video), second is ffmpeg (thumbnail)
        probe_result = MagicMock(returncode=0, stdout='{"streams":[{"width":1920,"height":1080,"duration":"10.0"}]}')
        thumb_result = MagicMock(returncode=0)
        mock_run.side_effect = [probe_result, thumb_result]
        thumb_file.write_bytes(b"fake_thumb")  # simulate ffmpeg creating the file

        result = download_video("https://example.com/video", "testjob")

    assert "thumbnail" in result
    assert result["thumbnail"] == "/api/downloads/testjob_thumb.jpg"
