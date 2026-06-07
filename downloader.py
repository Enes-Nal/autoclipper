import subprocess, json, re, shutil
from pathlib import Path

# WinGet symlinks fail when spawned from non-interactive processes; resolve to the real exe.
_which = shutil.which("yt-dlp") or "yt-dlp"
_YTDLP = str(Path(_which).resolve()) if Path(_which).is_symlink() else _which

_which_ff = shutil.which("ffmpeg") or "ffmpeg"
_FFMPEG = str(Path(_which_ff).resolve()) if Path(_which_ff).is_symlink() else _which_ff

_which_ffp = shutil.which("ffprobe") or "ffprobe"
_FFPROBE = str(Path(_which_ffp).resolve()) if Path(_which_ffp).is_symlink() else _which_ffp

DOWNLOADS_DIR = Path(__file__).parent / "downloads"

def get_job_path(job_id: str) -> Path:
    return DOWNLOADS_DIR / f"{job_id}.mp4"

def parse_progress(line: str) -> dict | None:
    """Parse a yt-dlp stdout line, return progress dict or None."""
    m = re.search(r'\[download\]\s+([\d.]+)%', line)
    if m:
        return {"percent": float(m.group(1)), "status": "downloading"}
    return None

def get_video_title(url: str) -> str:
    """Fetch the video title from yt-dlp without downloading."""
    try:
        result = subprocess.run(
            [_YTDLP, "--skip-download", "--print", "title", url],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout.strip()
    except Exception:
        return ""

def download_video(url: str, job_id: str, on_progress=None) -> dict:
    """Run yt-dlp, call on_progress(dict) for each progress line. Returns video info."""
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    output = get_job_path(job_id)
    title = get_video_title(url)
    cmd = [
        _YTDLP,
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--newline",
        "--output", str(output),
        url,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output_lines: list[str] = []
    for line in proc.stdout:
        output_lines.append(line.rstrip())
        p = parse_progress(line.strip())
        if p and on_progress:
            on_progress(p)
    proc.wait()
    if proc.returncode != 0:
        detail = "\n".join(output_lines[-20:])
        raise RuntimeError(f"yt-dlp exited {proc.returncode}\n{detail}")
    info = {"path": str(output), "title": title, **probe_video(str(output))}
    thumb = extract_thumbnail(str(output), job_id)
    if thumb:
        thumb_filename = Path(thumb).name
        info["thumbnail"] = "/api/downloads/" + thumb_filename
    else:
        info["thumbnail"] = None
    return info

def probe_video(path: str) -> dict:
    """Return width, height, duration via ffprobe."""
    cmd = [_FFPROBE, "-v", "quiet", "-print_format", "json",
           "-show_streams", "-select_streams", "v:0", path]
    out = subprocess.run(cmd, capture_output=True, text=True)
    s = json.loads(out.stdout)["streams"][0]
    return {"width": s["width"], "height": s["height"],
            "duration": float(s.get("duration", 0))}

def extract_thumbnail(video_path: str, job_id: str, base_dir: Path | None = None) -> str | None:
    """Extract a single frame at t=1s from the video and save as {job_id}_thumb.jpg.

    Returns the thumbnail path string on success, or None on failure.
    """
    if base_dir is None:
        base_dir = DOWNLOADS_DIR
    thumb_path = Path(base_dir) / f"{job_id}_thumb.jpg"
    cmd = [
        _FFMPEG, "-y",
        "-ss", "1",
        "-i", video_path,
        "-vframes", "1",
        "-vf", "scale=320:-1",
        "-q:v", "5",
        str(thumb_path),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        return None
    if not thumb_path.exists():
        return None
    return str(thumb_path)
