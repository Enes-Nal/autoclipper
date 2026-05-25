# autoclipper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web app that downloads videos via yt-dlp, lets users create reusable clip templates in a canvas editor, and exports TikTok-ready clips via FFmpeg.

**Architecture:** Python Flask backend serves a single `frontend/index.html`. Templates are JSON files. FFmpeg processes video at export time using a filter graph built from the template. Fabric.js handles the canvas editor in the browser.

**Tech Stack:** Python 3.11, Flask, yt-dlp, FFmpeg, Pillow, Fabric.js 5.x, Inter font

**Spec:** `docs/superpowers/specs/2026-05-25-autoclipper-design.md`

---

## File Map

| File | Responsibility |
|---|---|
| `app.py` | Flask app, all API routes, SSE streaming |
| `downloader.py` | yt-dlp wrapper, progress parsing |
| `exporter.py` | FFmpeg filter graph builder + runner |
| `text_renderer.py` | Pillow emoji/text → transparent PNG |
| `frontend/index.html` | Single-page editor UI (Fabric.js, all JS inline) |
| `templates/builtin/*.json` | Six built-in template definitions |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Ignore downloads/, exports/, temp/, __pycache__ |
| `tests/test_exporter.py` | Unit tests for filter graph builder |
| `tests/test_downloader.py` | Unit tests for progress parsing |
| `tests/test_text_renderer.py` | Unit tests for has_emoji, render output |

---

## Task 1: Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create directories

- [ ] **Create requirements.txt**

```
flask>=3.0
flask-cors>=4.0
yt-dlp>=2024.1
pillow>=10.0
pytest>=8.0
```

- [ ] **Create .gitignore**

```
downloads/
exports/
temp/
__pycache__/
*.pyc
.env
fonts/NotoColorEmoji.ttf
```

- [ ] **Create directories**

```bash
mkdir -p downloads exports temp fonts templates/builtin tests frontend assets
```

- [ ] **Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Commit**

```bash
git add requirements.txt .gitignore
git commit -m "feat: scaffold project structure"
```

---

## Task 2: Downloader

**Files:**
- Create: `downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Write failing tests**

```python
# tests/test_downloader.py
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
```

- [ ] **Run tests to confirm they fail**

```bash
pytest tests/test_downloader.py -v
```
Expected: `ModuleNotFoundError: No module named 'downloader'`

- [ ] **Implement downloader.py**

```python
# downloader.py
import subprocess, json, re, uuid
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
```

- [ ] **Run tests — expect pass**

```bash
pytest tests/test_downloader.py -v
```

- [ ] **Commit**

```bash
git add downloader.py tests/test_downloader.py
git commit -m "feat: add yt-dlp downloader with progress parsing"
```

---

## Task 3: Text Renderer

**Files:**
- Create: `text_renderer.py`
- Create: `tests/test_text_renderer.py`

- [ ] **Write failing tests**

```python
# tests/test_text_renderer.py
import os, tempfile
from text_renderer import has_emoji, render_text_layer
from PIL import Image

def test_has_emoji_true():
    assert has_emoji("Hello 🔥") is True

def test_has_emoji_false():
    assert has_emoji("Hello world") is False

def test_render_text_layer_creates_png():
    layer = {"type": "text", "x": 40, "y": 80, "text": "Test 🔥",
             "font_size": 48, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 4}
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        img = Image.open(path)
        assert img.size == (1080, 1920)
        assert img.mode == "RGBA"
    finally:
        os.unlink(path)
```

- [ ] **Run to confirm failure**

```bash
pytest tests/test_text_renderer.py -v
```

- [ ] **Implement text_renderer.py**

```python
# text_renderer.py
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path("fonts")
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FA9F"
    "\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF]",
    flags=re.UNICODE,
)

def has_emoji(text: str) -> bool:
    return bool(EMOJI_RE.search(text))

def _load_font(font_size: int) -> ImageFont.FreeTypeFont:
    for name in ("Inter-Black.ttf", "Inter-Bold.ttf"):
        p = FONTS_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), font_size)
    return ImageFont.load_default()

def render_text_layer(layer: dict, canvas_w: int, canvas_h: int, output_path: str):
    """Render a text layer (with emoji) to a transparent RGBA PNG."""
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(layer.get("font_size", 72))
    fill = layer.get("fill", "#ffffff")
    stroke = layer.get("stroke", "#000000")
    stroke_w = int(layer.get("stroke_width", 0))
    text = layer.get("text", "")
    x, y = layer.get("x", 0), layer.get("y", 0)
    draw.text(
        (x, y), text, font=font, fill=fill,
        stroke_width=stroke_w, stroke_fill=stroke,
    )
    img.save(output_path, "PNG")
```

- [ ] **Download Inter font for tests** (skip if already present)

```bash
python -c "
import urllib.request, os
os.makedirs('fonts', exist_ok=True)
url = 'https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Black.ttf'
urllib.request.urlretrieve(url, 'fonts/Inter-Black.ttf')
print('done')
"
```

- [ ] **Run tests — expect pass**

```bash
pytest tests/test_text_renderer.py -v
```

- [ ] **Commit**

```bash
git add text_renderer.py tests/test_text_renderer.py
git commit -m "feat: add Pillow text/emoji renderer"
```

---

## Task 4: FFmpeg Exporter

**Files:**
- Create: `exporter.py`
- Create: `tests/test_exporter.py`

- [ ] **Write failing tests**

```python
# tests/test_exporter.py
from exporter import build_filter_graph

def _template(layers):
    return {"canvas": {"width": 1080, "height": 1920}, "layers": layers}

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

def test_text_drawtext_layer():
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "text", "x": 40, "y": 80, "text": "Hello world",
         "font_size": 72, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 6},
    ]
    parts, label = build_filter_graph(layers, 1080, 1920, {}, {})
    assert any("drawtext" in p for p in parts)
```

- [ ] **Run to confirm failure**

```bash
pytest tests/test_exporter.py -v
```

- [ ] **Implement exporter.py**

```python
# exporter.py
import subprocess, uuid, os
from pathlib import Path
from text_renderer import render_text_layer, has_emoji

EXPORTS_DIR = Path("exports")
TEMP_DIR = Path("temp")
for d in (EXPORTS_DIR, TEMP_DIR):
    d.mkdir(exist_ok=True)

def build_filter_graph(layers: list, cw: int, ch: int,
                        text_pngs: dict, image_inputs: dict) -> tuple[list, str]:
    """
    Pure function: build FFmpeg filter_complex parts from template layers.
    text_pngs: {layer_index: input_stream_index}
    image_inputs: {layer_index: input_stream_index}
    Returns (filter_parts_list, final_label).
    """
    parts = []
    current = None
    n = [0]

    def lbl():
        n[0] += 1
        return f"v{n[0]}"

    for i, layer in enumerate(layers):
        t = layer["type"]

        if t == "blur_video":
            blur = layer.get("blur", 20)
            out = lbl()
            parts.append(
                f"[0:v]scale={cw}:{ch}:force_original_aspect_ratio=increase,"
                f"crop={cw}:{ch},boxblur=lx={blur}:ly={blur},setsar=1[{out}]"
            )
            current = out

        elif t == "video":
            x, y = layer.get("x", 0), layer.get("y", 0)
            w, h = layer.get("width", cw), layer.get("height", int(ch * 0.32))
            fit = layer.get("fit", "contain")
            scaled = lbl()
            if fit == "contain":
                parts.append(
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black[{scaled}]"
                )
            elif fit == "cover":
                parts.append(
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
                    f"crop={w}:{h}[{scaled}]"
                )
            else:
                parts.append(f"[0:v]scale={w}:{h}[{scaled}]")
            if current:
                out = lbl()
                parts.append(f"[{current}][{scaled}]overlay=x={x}:y={y}[{out}]")
                current = out
            else:
                current = scaled

        elif t == "text":
            if i in text_pngs:
                idx = text_pngs[i]
                out = lbl()
                parts.append(f"[{current}][{idx}:v]overlay=x=0:y=0[{out}]")
                current = out
            else:
                text = layer.get("text", "").replace("'", "\\'").replace(":", "\\:")
                x, y = layer.get("x", 0), layer.get("y", 0)
                fs = layer.get("font_size", 72)
                fc = layer.get("fill", "#ffffff").lstrip("#")
                bc = layer.get("stroke", "#000000").lstrip("#")
                bw = layer.get("stroke_width", 0)
                ff = "fonts/Inter-Black.ttf"
                out = lbl()
                dt = (f"fontfile={ff}:text='{text}':x={x}:y={y}:fontsize={fs}:"
                      f"fontcolor=0x{fc}:bordercolor=0x{bc}:borderw={bw}")
                parts.append(f"[{current}]drawtext={dt}[{out}]")
                current = out

        elif t == "image" and i in image_inputs:
            idx = image_inputs[i]
            x, y = layer.get("x", 0), layer.get("y", 0)
            out = lbl()
            parts.append(f"[{current}][{idx}:v]overlay=x={x}:y={y}[{out}]")
            current = out

        elif t == "shape":
            x, y = layer.get("x", 0), layer.get("y", 0)
            w, h2 = layer.get("width", cw), layer.get("height", 60)
            fc = layer.get("fill", "#000000").lstrip("#")
            op = layer.get("opacity", 1.0)
            out = lbl()
            parts.append(
                f"[{current}]drawbox=x={x}:y={y}:w={w}:h={h2}:"
                f"color=0x{fc}@{op}:t=fill[{out}]"
            )
            current = out

    return parts, current or "0:v"

def export_video(video_path: str, template: dict, title: str = "",
                 on_progress=None) -> str:
    """Build and run the FFmpeg command. Returns output file path."""
    job_id = uuid.uuid4().hex[:8]
    layers = [dict(l) for l in template["layers"]]
    cw = template["canvas"]["width"]
    ch = template["canvas"]["height"]

    # Substitute {title}
    for l in layers:
        if l["type"] == "text":
            l["text"] = l.get("text", "").replace("{title}", title)

    # Pre-render emoji text layers
    extra_inputs, text_pngs, image_inputs = [], {}, {}
    for i, l in enumerate(layers):
        if l["type"] == "text" and has_emoji(l.get("text", "")):
            p = str(TEMP_DIR / f"{job_id}_t{i}.png")
            render_text_layer(l, cw, ch, p)
            text_pngs[i] = len(extra_inputs) + 1
            extra_inputs.append(p)
        elif l["type"] == "image" and os.path.exists(l.get("src", "")):
            image_inputs[i] = len(extra_inputs) + 1
            extra_inputs.append(l["src"])

    filter_parts, final = build_filter_graph(layers, cw, ch, text_pngs, image_inputs)
    out_path = str(EXPORTS_DIR / f"{job_id}.mp4")

    cmd = ["ffmpeg", "-y", "-i", video_path]
    for inp in extra_inputs:
        cmd += ["-i", inp]
    cmd += [
        "-filter_complex", ";".join(filter_parts),
        "-map", f"[{final}]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        out_path,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        if on_progress:
            on_progress(line.strip())
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg exited {proc.returncode}")

    for p, _ in [(p, None) for p in extra_inputs if "temp" in p]:
        try: os.remove(p)
        except: pass

    return out_path
```

- [ ] **Run tests — expect pass**

```bash
pytest tests/test_exporter.py -v
```

- [ ] **Commit**

```bash
git add exporter.py tests/test_exporter.py
git commit -m "feat: add FFmpeg filter graph builder and exporter"
```

---

## Task 5: Flask API

**Files:**
- Create: `app.py`

- [ ] **Implement app.py**

```python
# app.py
import json, uuid, threading, queue, os
from pathlib import Path
from flask import Flask, request, jsonify, send_file, Response, send_from_directory
from flask_cors import CORS
from downloader import download_video, get_job_path
from exporter import export_video

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

TEMPLATES_DIR = Path("templates")
EXPORTS_DIR   = Path("exports")

# In-memory job store: job_id -> Queue of SSE dicts
_jobs: dict[str, queue.Queue] = {}

# ── Static ──────────────────────────────────────────────────
@app.get("/")
def index():
    return send_from_directory("frontend", "index.html")

# ── Templates ───────────────────────────────────────────────
@app.get("/api/templates")
def list_templates():
    results = []
    for p in sorted(TEMPLATES_DIR.rglob("*.json")):
        data = json.loads(p.read_text())
        results.append({"name": data.get("name", p.stem), "file": p.stem,
                         "builtin": "builtin" in str(p)})
    return jsonify(results)

@app.get("/api/templates/<name>")
def get_template(name):
    for base in (TEMPLATES_DIR, TEMPLATES_DIR / "builtin"):
        p = base / f"{name}.json"
        if p.exists():
            return jsonify(json.loads(p.read_text()))
    return jsonify({"error": "not found"}), 404

@app.post("/api/templates")
def save_template():
    data = request.json
    name = data.get("name", "untitled").replace(" ", "-").lower()
    TEMPLATES_DIR.mkdir(exist_ok=True)
    path = TEMPLATES_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2))
    return jsonify({"saved": name})

# ── Download ─────────────────────────────────────────────────
@app.post("/api/download")
def start_download():
    url = request.json.get("url", "")
    if not url:
        return jsonify({"error": "url required"}), 400
    job_id = uuid.uuid4().hex[:8]
    q: queue.Queue = queue.Queue()
    _jobs[job_id] = q

    def run():
        try:
            def on_progress(p):
                q.put({"type": "progress", **p})
            info = download_video(url, job_id, on_progress)
            q.put({"type": "done", **info})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})

@app.get("/api/download/<job_id>/progress")
def download_progress(job_id):
    q = _jobs.get(job_id)
    if not q:
        return jsonify({"error": "unknown job"}), 404

    def stream():
        while True:
            msg = q.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["type"] in ("done", "error"):
                break

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ── Export ───────────────────────────────────────────────────
@app.post("/api/export")
def start_export():
    body = request.json
    video_path = body.get("video_path", "")
    template   = body.get("template", {})
    title      = body.get("title", "")
    if not video_path or not os.path.exists(video_path):
        return jsonify({"error": "video_path not found"}), 400

    job_id = uuid.uuid4().hex[:8]
    q: queue.Queue = queue.Queue()
    _jobs[job_id] = q

    def run():
        try:
            def on_progress(line):
                q.put({"type": "progress", "line": line})
            out = export_video(video_path, template, title, on_progress)
            q.put({"type": "done", "output_path": out,
                   "filename": Path(out).name})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})

@app.get("/api/export/<job_id>/progress")
def export_progress(job_id):
    q = _jobs.get(job_id)
    if not q:
        return jsonify({"error": "unknown job"}), 404

    def stream():
        while True:
            msg = q.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["type"] in ("done", "error"):
                break

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/api/exports/<filename>")
def download_export(filename):
    return send_from_directory(str(EXPORTS_DIR), filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
```

- [ ] **Smoke test Flask starts**

```bash
python app.py &
curl http://localhost:5000/api/templates
kill %1
```
Expected: JSON array (empty or with builtin templates)

- [ ] **Commit**

```bash
git add app.py
git commit -m "feat: add Flask API with SSE download/export routes"
```

---

## Task 6: Built-in Templates

**Files:**
- Create: `templates/builtin/blur-stack.json`
- Create: `templates/builtin/text-header.json`
- Create: `templates/builtin/footer-fade.json`
- Create: `templates/builtin/minimal.json`
- Create: `templates/builtin/side-blur.json`
- Create: `templates/builtin/podcast.json`

- [ ] **Write blur-stack.json**

```json
{
  "name": "Blur Stack",
  "format": "9:16",
  "canvas": { "width": 1080, "height": 1920 },
  "layers": [
    { "id": "blur-bg", "type": "blur_video", "blur": 20, "opacity": 0.92 },
    { "id": "video",   "type": "video",      "x": 0, "y": 656, "width": 1080, "height": 608, "fit": "contain" },
    { "id": "title",   "type": "text",       "x": 40, "y": 80, "width": 1000, "text": "{title}", "font_family": "Inter", "font_weight": "900", "font_size": 72, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 6, "text_align": "center" },
    { "id": "logo",    "type": "image",      "x": 860, "y": 1820, "width": 180, "src": "assets/watermark.png", "opacity": 0.8 }
  ]
}
```

- [ ] **Write text-header.json**

```json
{
  "name": "Text Header",
  "format": "9:16",
  "canvas": { "width": 1080, "height": 1920 },
  "layers": [
    { "id": "bar",   "type": "shape", "x": 0, "y": 0,   "width": 1080, "height": 320, "fill": "#000000", "opacity": 1.0 },
    { "id": "video", "type": "video", "x": 0, "y": 320,  "width": 1080, "height": 1600, "fit": "cover" },
    { "id": "title", "type": "text",  "x": 40, "y": 60, "width": 1000, "text": "{title}", "font_size": 68, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 4, "text_align": "center" }
  ]
}
```

- [ ] **Write footer-fade.json**

```json
{
  "name": "Footer Fade",
  "format": "9:16",
  "canvas": { "width": 1080, "height": 1920 },
  "layers": [
    { "id": "video",   "type": "video",  "x": 0, "y": 0, "width": 1080, "height": 1920, "fit": "cover" },
    { "id": "bar",     "type": "shape",  "x": 0, "y": 1500, "width": 1080, "height": 420, "fill": "#000000", "opacity": 0.75 },
    { "id": "title",   "type": "text",   "x": 40, "y": 1540, "width": 1000, "text": "{title}", "font_size": 72, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 5, "text_align": "center" }
  ]
}
```

- [ ] **Write minimal.json**

```json
{
  "name": "Minimal",
  "format": "9:16",
  "canvas": { "width": 1080, "height": 1920 },
  "layers": [
    { "id": "bg",    "type": "shape", "x": 0, "y": 0, "width": 1080, "height": 1920, "fill": "#000000", "opacity": 1.0 },
    { "id": "video", "type": "video", "x": 54, "y": 480,  "width": 972,  "height": 960, "fit": "contain" },
    { "id": "title", "type": "text",  "x": 40, "y": 120,  "width": 1000, "text": "{title}", "font_size": 60, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 3, "text_align": "center" }
  ]
}
```

- [ ] **Write side-blur.json**

```json
{
  "name": "Side Blur",
  "format": "1:1",
  "canvas": { "width": 1080, "height": 1080 },
  "layers": [
    { "id": "blur-bg", "type": "blur_video", "blur": 25, "opacity": 0.9 },
    { "id": "video",   "type": "video", "x": 162, "y": 162, "width": 756, "height": 756, "fit": "contain" },
    { "id": "title",   "type": "text",  "x": 40,  "y": 30,  "width": 1000, "text": "{title}", "font_size": 56, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 4, "text_align": "center" }
  ]
}
```

- [ ] **Write podcast.json**

```json
{
  "name": "Podcast",
  "format": "9:16",
  "canvas": { "width": 1080, "height": 1920 },
  "layers": [
    { "id": "video", "type": "video", "x": 0, "y": 0,    "width": 1080, "height": 1920, "fit": "cover" },
    { "id": "bar",   "type": "shape", "x": 0, "y": 1400,  "width": 1080, "height": 520,  "fill": "#000000", "opacity": 0.82 },
    { "id": "title", "type": "text",  "x": 40, "y": 1440, "width": 1000, "text": "{title}", "font_size": 68, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 5, "text_align": "center" }
  ]
}
```

- [ ] **Commit**

```bash
git add templates/
git commit -m "feat: add six built-in clip templates"
```

---

## Task 7: Frontend — Full UI

**Files:**
- Create: `frontend/index.html`

This is the largest task. The UI matches the provided screenshot: left sidebar with project nav, top bar, central canvas with phone frame, right properties panel, bottom toolbar.

- [ ] **Create frontend/index.html** (copy full content below)

Full file content in implementation — see Task 7 notes. Key sections:
1. CSS variables + reset + layout (left sidebar 220px, top bar 52px, canvas flex:1, right panel 280px)
2. Left sidebar: logo, New Project button, nav links, projects list, storage bar, user info
3. Top bar: file icon + project name + format toggle + undo/redo + Preview + Save Template
4. URL/download modal: triggered by New Project button
5. Canvas area: Fabric.js phone frame, zoom toolbar below
6. Right panel: Align buttons, Transform sliders, type-specific controls, iOS Emoji picker
7. Fabric.js: snap (fixed coord bug), alignment, history, layer sync, properties

- [ ] **Verify Flask serves it**

```bash
python app.py
```
Open http://localhost:5000 in browser. Should show the editor UI.

- [ ] **Commit**

```bash
git add frontend/index.html
git commit -m "feat: add complete frontend editor UI"
```

---

## Task 8: Integration Verification

- [ ] **Run all backend tests**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Start the app**

```bash
python app.py
```

- [ ] **Check template library loads**

Open http://localhost:5000, click Templates tab in left panel, verify 6 built-in templates appear.

- [ ] **Check canvas editor**

Add a Text element, double-click to edit, use emoji picker, verify emoji appears inline. Drag an element to phone edge, verify pink snap glow appears.

- [ ] **Test download flow (requires yt-dlp + FFmpeg in PATH)**

Paste a short Twitter/YouTube URL, click Download, verify progress bar fills, video path returned.

- [ ] **Test export flow**

After download, click Export with Template, verify progress streams and output .mp4 is created in exports/.

- [ ] **Final commit**

```bash
git add .
git commit -m "feat: complete autoclipper v1"
```
