import subprocess, json, re
from pathlib import Path

DOWNLOADS_DIR = Path("downloads")

def get_job_path(job_id: str) -> Path:
    return DOWNLOADS_DIR / f"{job_id}.mp4"

def parse_progress(line: str) -> dict | None:
    """Parse a yt-dlp stdout line, return progress dict or None."""
    m = re.search(r'\[download\]\s+([\d.]+)%', line)
    if m:
        return {"percent": float(m.group(1)), "status": "downloading"}
    return None

def download_video(url: str, job_id: str, on_progress=None) -> dict:
    """Run yt-dlp, call on_progress(dict) for each progress line. Returns video info."""
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    output = get_job_path(job_id)
    cmd = [
        "yt-dlp",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--newline",
        "--output", str(output),
        url,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        p = parse_progress(line.strip())
        if p and on_progress:
            on_progress(p)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp exited {proc.returncode}")
    return {"path": str(output), **probe_video(str(output))}

def probe_video(path: str) -> dict:
    """Return width, height, duration via ffprobe."""
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
           "-show_streams", "-select_streams", "v:0", path]
    out = subprocess.run(cmd, capture_output=True, text=True)
    s = json.loads(out.stdout)["streams"][0]
    return {"width": s["width"], "height": s["height"],
            "duration": float(s.get("duration", 0))}
