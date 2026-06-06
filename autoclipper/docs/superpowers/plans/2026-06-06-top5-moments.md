# Top 5 Moments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated Top 5 Moments page where users pick 5 clips, assign ranks and titles, choose a template with placeholder tokens, and export a single concatenated video with the ranking overlay burned in.

**Architecture:** `top5_exporter.py` handles placeholder resolution and per-slot FFmpeg rendering (one temp mp4 per slot) then concatenates them. Flask routes in `app.py` expose export, template CRUD, clip listing, and video upload. `frontend/top5.html` is a self-contained page.

**Tech Stack:** Python 3, Flask, FFmpeg (subprocess), Pillow (via existing `text_renderer.py`), vanilla JS/HTML.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `top5_exporter.py` | Create | Placeholder resolution, per-slot render, concat |
| `templates/top5/bottom-bar.json` | Create | Built-in starter template |
| `frontend/top5.html` | Create | Full Top 5 page UI |
| `app.py` | Modify | Add `/top5` page route + 5 new API endpoints |
| `tests/test_top5_exporter.py` | Create | Unit tests for resolver + exporter |

---

## Task 1: Placeholder Resolver

**Files:**
- Create: `top5_exporter.py`
- Create: `tests/test_top5_exporter.py`

- [ ] **Step 1: Write failing tests for `resolve_placeholders`**

Create `tests/test_top5_exporter.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_top5_exporter.py -v
```

Expected: `ModuleNotFoundError: No module named 'top5_exporter'`

- [ ] **Step 3: Implement `resolve_placeholders` in `top5_exporter.py`**

Create `top5_exporter.py`:

```python
import os, subprocess, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from exporter import build_filter_graph
from text_renderer import render_text_layer

EXPORTS_DIR = Path(__file__).parent / "exports"
TEMP_DIR    = Path(__file__).parent / "temp"
for _d in (EXPORTS_DIR, TEMP_DIR):
    _d.mkdir(exist_ok=True)


def resolve_placeholders(text: str, slots: list[dict], current_idx: int) -> str:
    """Replace <current:rank>, <current:title>, <slotN:rank>, <slotN:title> tokens."""
    text = text.replace("<current:rank>",  str(slots[current_idx]["rank"]))
    text = text.replace("<current:title>", slots[current_idx]["title"])
    for i, slot in enumerate(slots):
        n = i + 1
        text = text.replace(f"<slot{n}:rank>",  str(slot["rank"]))
        title = slot["title"] if i <= current_idx else "—"
        text = text.replace(f"<slot{n}:title>", title)
    return text
```

- [ ] **Step 4: Run tests — all should pass**

```
pytest tests/test_top5_exporter.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```
git add top5_exporter.py tests/test_top5_exporter.py
git commit -m "feat(top5): placeholder resolver with tests"
```

---

## Task 2: Per-Slot Renderer

**Files:**
- Modify: `top5_exporter.py`
- Modify: `tests/test_top5_exporter.py`

- [ ] **Step 1: Write failing test for `render_slot`**

Add to `tests/test_top5_exporter.py`:

```python
import unittest.mock as mock
from pathlib import Path

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

    with mock.patch("subprocess.run") as mock_run:
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

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=1, stderr=b"some ffmpeg error")
        from top5_exporter import render_slot
        try:
            render_slot(slot, [slot], 0, template, "testjob", tmp_path)
            assert False, "should have raised"
        except RuntimeError as e:
            assert "slot 0" in str(e)
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_top5_exporter.py::test_render_slot_calls_ffmpeg -v
```

Expected: `ImportError` or `AttributeError` — `render_slot` not defined yet

- [ ] **Step 3: Implement `render_slot` in `top5_exporter.py`**

Append to `top5_exporter.py` after `resolve_placeholders`:

```python
def render_slot(slot: dict, all_slots: list[dict], slot_idx: int,
                template: dict, job_id: str, temp_dir: Path) -> str:
    """Render one slot's clip with template overlay to a temp mp4. Returns output path."""
    layers = [dict(l) for l in template["layers"]]
    cw = template["canvas"]["width"]
    ch = template["canvas"]["height"]

    # Resolve placeholders in every text layer
    for l in layers:
        if l["type"] == "text":
            l["text"] = resolve_placeholders(l.get("text", ""), all_slots, slot_idx)

    # Render text layers to PNGs in parallel
    text_jobs = []
    for i, l in enumerate(layers):
        if l["type"] == "text":
            p = str(temp_dir / f"{job_id}_s{slot_idx}_t{i}.png")
            rl = dict(l)
            rl["auto_height"]    = l.get("_autoHeight", True)
            rl["vertical_align"] = l.get("_verticalAlign", "top")
            rl["emoji_offset"]   = l.get("_emojiOffset", 0)
            text_jobs.append((i, p, rl))

    if text_jobs:
        with ThreadPoolExecutor(max_workers=min(len(text_jobs), os.cpu_count() or 4)) as ex:
            futs = [ex.submit(render_text_layer, rl, cw, ch, p) for _, p, rl in text_jobs]
            for f in as_completed(futs):
                f.result()

    # Map text PNGs to input indices (0 = the video clip)
    extra_inputs = []
    text_pngs = {}
    for layer_idx, p, _ in text_jobs:
        text_pngs[layer_idx] = 1 + len(extra_inputs)
        extra_inputs.append(p)

    filter_parts, final_label = build_filter_graph(
        layers, cw, ch, text_pngs, {}, {}, src_video_label="0:v"
    )

    out_path = str(temp_dir / f"{job_id}_slot{slot_idx}.mp4")
    clip_path = slot["path"]
    start = float(slot.get("start", 0))
    end   = float(slot.get("end",   0))

    cmd = ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", clip_path]
    for inp in extra_inputs:
        cmd += ["-i", inp]

    if filter_parts:
        cmd += ["-filter_complex", ";".join(filter_parts), "-map", f"[{final_label}]"]
    else:
        cmd += ["-map", "0:v"]

    cmd += [
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        out_path,
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed for slot {slot_idx}:\n{result.stderr.decode()[-2000:]}")

    for _, p, _ in text_jobs:
        try:
            os.remove(p)
        except OSError:
            pass

    return out_path
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_top5_exporter.py -v
```

Expected: all passing

- [ ] **Step 5: Commit**

```
git add top5_exporter.py tests/test_top5_exporter.py
git commit -m "feat(top5): per-slot renderer"
```

---

## Task 3: Concat + Export Orchestration

**Files:**
- Modify: `top5_exporter.py`
- Modify: `tests/test_top5_exporter.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_top5_exporter.py`:

```python
def test_export_top5_calls_render_and_concat(tmp_path):
    slots = [
        {"rank": 5, "title": "A", "path": "/a.mp4", "start": 0.0, "end": 5.0},
        {"rank": 4, "title": "B", "path": "/b.mp4", "start": 0.0, "end": 5.0},
    ]
    template = {
        "canvas": {"width": 1080, "height": 1920},
        "layers": [{"id": "v", "type": "video", "x": 0, "y": 0,
                    "width": 1080, "height": 1920, "fit": "cover"}]
    }

    rendered = ["/tmp/slot0.mp4", "/tmp/slot1.mp4"]
    with mock.patch("top5_exporter.render_slot", side_effect=rendered) as mock_render, \
         mock.patch("top5_exporter.concat_segments", return_value="/out/top5.mp4") as mock_concat, \
         mock.patch("os.remove"):
        from top5_exporter import export_top5
        out = export_top5(slots, template, "abc123")

    assert mock_render.call_count == 2
    mock_concat.assert_called_once_with(rendered, "abc123")
    assert out == "/out/top5.mp4"

def test_export_top5_reports_progress():
    slots = [
        {"rank": 5, "title": "A", "path": "/a.mp4", "start": 0.0, "end": 5.0},
    ]
    template = {
        "canvas": {"width": 1080, "height": 1920},
        "layers": [{"id": "v", "type": "video", "x": 0, "y": 0,
                    "width": 1080, "height": 1920, "fit": "cover"}]
    }
    progress_events = []

    with mock.patch("top5_exporter.render_slot", return_value="/tmp/s.mp4"), \
         mock.patch("top5_exporter.concat_segments", return_value="/out/top5.mp4"), \
         mock.patch("os.remove"):
        from top5_exporter import export_top5
        export_top5(slots, template, "abc123", on_progress=progress_events.append)

    assert any(e.get("slot") == 1 for e in progress_events)
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_top5_exporter.py::test_export_top5_calls_render_and_concat -v
```

Expected: `ImportError` — `concat_segments` and `export_top5` not defined yet

- [ ] **Step 3: Implement `concat_segments` and `export_top5`**

Append to `top5_exporter.py`:

```python
def concat_segments(temp_files: list[str], job_id: str) -> str:
    """Concatenate temp mp4 files into a single exports/ output. Returns output path."""
    list_path = str(TEMP_DIR / f"{job_id}_concat.txt")
    with open(list_path, "w") as f:
        for p in temp_files:
            # FFmpeg concat demuxer requires forward slashes even on Windows
            f.write(f"file '{p.replace(chr(92), '/')}'\n")

    out_path = str(EXPORTS_DIR / f"top5_{job_id}.mp4")
    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
         "-c", "copy", out_path],
        capture_output=True,
    )
    try:
        os.remove(list_path)
    except OSError:
        pass

    if result.returncode != 0:
        raise RuntimeError(f"Concat failed:\n{result.stderr.decode()[-2000:]}")
    return out_path


def export_top5(slots: list[dict], template: dict, job_id: str,
                on_progress=None) -> str:
    """Render each slot, concat, return output path."""
    temp_files = []
    for i, slot in enumerate(slots):
        if on_progress:
            on_progress({"type": "progress", "slot": i + 1, "total": len(slots)})
        temp_files.append(render_slot(slot, slots, i, template, job_id, TEMP_DIR))

    out = concat_segments(temp_files, job_id)

    for p in temp_files:
        try:
            os.remove(p)
        except OSError:
            pass

    return out
```

- [ ] **Step 4: Run all tests**

```
pytest tests/test_top5_exporter.py -v
```

Expected: all passing

- [ ] **Step 5: Commit**

```
git add top5_exporter.py tests/test_top5_exporter.py
git commit -m "feat(top5): concat and export_top5 orchestrator"
```

---

## Task 4: Flask Endpoints

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add imports and directory setup**

At the top of `app.py`, after the existing imports, add:

```python
from top5_exporter import export_top5
```

After `UPLOADS_DIR.mkdir(exist_ok=True)`, add:

```python
TOP5_TEMPLATES_DIR = BASE_DIR / "templates" / "top5"
TOP5_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR = BASE_DIR / "downloads"
ALLOWED_VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.webm', '.avi'}
```

- [ ] **Step 2: Add `/top5` page route**

After the `index` route in `app.py`:

```python
@app.get("/top5")
def top5_page():
    return send_from_directory("frontend", "top5.html")
```

- [ ] **Step 3: Add Top 5 template CRUD endpoints**

After the existing template endpoints in `app.py`:

```python
# ── Top 5 Templates ──────────────────────────────────────────────────────────
@app.get("/api/top5/templates")
def list_top5_templates():
    results = []
    for p in sorted(TOP5_TEMPLATES_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            results.append({"name": data.get("name", p.stem), "file": p.stem,
                            "builtin": p.parent.name == "builtin"})
        except Exception:
            pass
    return jsonify(results)


@app.get("/api/top5/templates/<name>")
def get_top5_template(name):
    p = TOP5_TEMPLATES_DIR / f"{name}.json"
    if p.exists():
        return jsonify(json.loads(p.read_text(encoding="utf-8")))
    return jsonify({"error": "not found"}), 404


@app.post("/api/top5/templates")
def save_top5_template():
    data = request.json
    name = data.get("name", "untitled").replace(" ", "-").lower()
    path = TOP5_TEMPLATES_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return jsonify({"saved": name})


@app.delete("/api/top5/templates/<name>")
def delete_top5_template(name):
    p = TOP5_TEMPLATES_DIR / f"{name}.json"
    if not p.exists():
        return jsonify({"error": "not found"}), 404
    p.unlink()
    return jsonify({"deleted": name})
```

- [ ] **Step 4: Add clip library listing and video upload endpoints**

```python
# ── Clips ─────────────────────────────────────────────────────────────────────
@app.get("/api/clips")
def list_clips():
    clips = []
    if DOWNLOADS_DIR.exists():
        for p in sorted(DOWNLOADS_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            clips.append({"filename": p.name, "path": str(p),
                          "size": p.stat().st_size})
    return jsonify(clips)


@app.post("/api/upload-video")
def upload_video():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "file required"}), 400
    if not f.filename:
        return jsonify({"error": "no filename provided"}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTS:
        return jsonify({"error": f"extension {ext} not allowed"}), 400
    uid = uuid.uuid4().hex[:8]
    filename = f"{uid}{ext}"
    dest = UPLOADS_DIR / filename
    f.save(str(dest))
    return jsonify({"path": str(dest), "filename": filename})
```

- [ ] **Step 5: Add Top 5 export endpoint**

```python
# ── Top 5 Export ──────────────────────────────────────────────────────────────
@app.post("/api/top5/export")
def start_top5_export():
    body = request.json or {}
    slots    = body.get("clips", [])
    template = body.get("template", {})

    if len(slots) != 5:
        return jsonify({"error": "exactly 5 clips required"}), 400
    for i, s in enumerate(slots):
        if not s.get("path") or not os.path.exists(s["path"]):
            return jsonify({"error": f"clip {i+1} path not found"}), 400
        if not s.get("title", "").strip():
            return jsonify({"error": f"clip {i+1} title required"}), 400

    job_id = uuid.uuid4().hex[:8]
    q: queue.Queue = queue.Queue()
    _jobs[job_id] = q

    def run():
        try:
            def on_progress(event):
                q.put({"type": "progress", **event})
            out = export_top5(slots, template, job_id, on_progress=on_progress)
            q.put({"type": "done", "output_path": out, "filename": Path(out).name})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.get("/api/top5/export/<job_id>/progress")
def top5_export_progress(job_id):
    q = _jobs.get(job_id)
    if not q:
        return jsonify({"error": "unknown job"}), 404

    def stream():
        while True:
            msg = q.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["type"] in ("done", "error"):
                break

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 6: Start the server and confirm no import errors**

```
python app.py
```

Expected: `* Running on http://127.0.0.1:5000`

Stop with Ctrl+C.

- [ ] **Step 7: Commit**

```
git add app.py
git commit -m "feat(top5): Flask endpoints — export, templates, clips, video upload"
```

---

## Task 5: Built-in Bottom Bar Template

**Files:**
- Create: `templates/top5/bottom-bar.json`

- [ ] **Step 1: Create the template**

Create `templates/top5/bottom-bar.json`:

```json
{
  "name": "Bottom Bar",
  "format": "9:16",
  "canvas": { "width": 1080, "height": 1920 },
  "layers": [
    {
      "id": "video",
      "type": "video",
      "x": 0, "y": 0,
      "width": 1080, "height": 1920,
      "fit": "cover"
    },
    {
      "id": "bar_bg",
      "type": "shape",
      "x": 0, "y": 1560,
      "width": 1080, "height": 360,
      "fill": "#000000",
      "opacity": 0.82
    },
    {
      "id": "slot1",
      "type": "text",
      "x": 30, "y": 1575,
      "width": 1020,
      "text": "<slot1:rank>  <slot1:title>",
      "font_size": 48,
      "fill": "#aaaaaa",
      "text_align": "left"
    },
    {
      "id": "slot2",
      "type": "text",
      "x": 30, "y": 1635,
      "width": 1020,
      "text": "<slot2:rank>  <slot2:title>",
      "font_size": 48,
      "fill": "#aaaaaa",
      "text_align": "left"
    },
    {
      "id": "slot3",
      "type": "text",
      "x": 30, "y": 1695,
      "width": 1020,
      "text": "<slot3:rank>  <slot3:title>",
      "font_size": 48,
      "fill": "#aaaaaa",
      "text_align": "left"
    },
    {
      "id": "slot4",
      "type": "text",
      "x": 30, "y": 1755,
      "width": 1020,
      "text": "<slot4:rank>  <slot4:title>",
      "font_size": 48,
      "fill": "#aaaaaa",
      "text_align": "left"
    },
    {
      "id": "slot5",
      "type": "text",
      "x": 30, "y": 1815,
      "width": 1020,
      "text": "<slot5:rank>  <slot5:title>",
      "font_size": 48,
      "fill": "#aaaaaa",
      "text_align": "left"
    },
    {
      "id": "current_badge",
      "type": "text",
      "x": 30, "y": 1480,
      "width": 1020,
      "text": "#<current:rank>  <current:title>",
      "font_size": 64,
      "fill": "#FFD700",
      "text_align": "left"
    }
  ]
}
```

- [ ] **Step 2: Verify it loads via the API**

With the server running (`python app.py`), visit:  
`http://localhost:5000/api/top5/templates`

Expected: `[{"file": "bottom-bar", "name": "Bottom Bar", ...}]`

- [ ] **Step 3: Commit**

```
git add templates/top5/bottom-bar.json
git commit -m "feat(top5): built-in bottom-bar template"
```

---

## Task 6: Frontend — top5.html

**Files:**
- Create: `frontend/top5.html`

- [ ] **Step 1: Create the page**

Create `frontend/top5.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Top 5 Moments</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0f0f0f; color: #eee; font-family: sans-serif; padding: 24px; }
    h1 { font-size: 28px; margin-bottom: 20px; }
    .row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
    label { font-size: 13px; color: #aaa; min-width: 60px; }
    input[type=text], input[type=number] {
      background: #1e1e1e; border: 1px solid #333; color: #eee;
      padding: 6px 10px; border-radius: 6px; font-size: 14px;
    }
    input[type=number] { width: 80px; }
    input[type=text] { flex: 1; }
    .slot-card {
      background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px;
      padding: 16px; margin-bottom: 12px;
    }
    .slot-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .slot-num { font-size: 22px; font-weight: 700; color: #FFD700; min-width: 28px; }
    .clip-display { font-size: 13px; color: #aaa; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .btn { background: #2a2a2a; border: 1px solid #444; color: #eee; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
    .btn:hover { background: #333; }
    .btn-primary { background: #FFD700; color: #000; border-color: #FFD700; font-weight: 700; font-size: 16px; padding: 10px 28px; }
    .btn-primary:hover { background: #e6c200; }
    .trim-row { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
    select { background: #1e1e1e; border: 1px solid #333; color: #eee; padding: 6px 10px; border-radius: 6px; font-size: 14px; }
    .section { margin-bottom: 24px; }
    .section-title { font-size: 15px; color: #aaa; margin-bottom: 10px; }
    #status { margin-top: 16px; font-size: 14px; color: #aaa; }
    #status.error { color: #f66; }
    #status.done { color: #6f6; }
    .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 100; align-items: center; justify-content: center; }
    .modal-overlay.open { display: flex; }
    .modal { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 24px; width: 500px; max-height: 80vh; overflow-y: auto; }
    .modal h2 { margin-bottom: 16px; }
    .clip-item { display: flex; align-items: center; justify-content: space-between; padding: 10px; border: 1px solid #2a2a2a; border-radius: 8px; margin-bottom: 8px; cursor: pointer; }
    .clip-item:hover { background: #252525; }
    .clip-name { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 350px; }
    .placeholder-ref { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 16px; margin-top: 12px; }
    .placeholder-ref h3 { font-size: 14px; margin-bottom: 10px; color: #aaa; }
    .token { font-family: monospace; font-size: 12px; color: #FFD700; display: block; margin: 2px 0; }
  </style>
</head>
<body>

<h1>Top 5 Moments</h1>

<div class="section">
  <div class="section-title">Template</div>
  <div style="display:flex;gap:10px;align-items:center;">
    <select id="templateSelect"><option value="">Loading...</option></select>
    <a href="#" onclick="openTemplateEditor(); return false;" class="btn">Edit / New Template</a>
  </div>
  <div class="placeholder-ref">
    <h3>Available placeholders in templates:</h3>
    <span class="token">&lt;current:rank&gt;  — rank number of playing clip</span>
    <span class="token">&lt;current:title&gt; — title of playing clip</span>
    <span class="token">&lt;slot1:rank&gt; … &lt;slot5:rank&gt;  — rank for each slot in order</span>
    <span class="token">&lt;slot1:title&gt; … &lt;slot5:title&gt; — title (future slots show —)</span>
  </div>
</div>

<div class="section">
  <div class="section-title">Clips (played in order, slot 1 first)</div>
  <div id="slots"></div>
</div>

<button class="btn btn-primary" onclick="startExport()">Export Top 5</button>
<div id="status"></div>

<!-- Library modal -->
<div class="modal-overlay" id="libraryModal">
  <div class="modal">
    <h2>Select Clip from Library</h2>
    <div id="clipList"><em>Loading...</em></div>
    <div style="margin-top:16px;"><button class="btn" onclick="closeLibrary()">Cancel</button></div>
  </div>
</div>

<script>
const NUM_SLOTS = 5;
let slots = Array.from({length: NUM_SLOTS}, (_, i) => ({
  path: "", title: "", rank: NUM_SLOTS - i, start: 0, end: 0
}));
let libraryTargetSlot = null;

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  await loadTemplates();
  renderSlots();
}

async function loadTemplates() {
  const res = await fetch("/api/top5/templates");
  const templates = await res.json();
  const sel = document.getElementById("templateSelect");
  sel.innerHTML = templates.length
    ? templates.map(t => `<option value="${t.file}">${t.name}</option>`).join("")
    : '<option value="">No templates — create one</option>';
}

// ── Slot rendering ────────────────────────────────────────────────────────────
function renderSlots() {
  const container = document.getElementById("slots");
  container.innerHTML = "";
  slots.forEach((slot, i) => {
    const div = document.createElement("div");
    div.className = "slot-card";
    div.innerHTML = `
      <div class="slot-header">
        <span class="slot-num">${i + 1}</span>
        <span class="clip-display" id="clip-display-${i}">${slot.path ? slot.path.split(/[\\/]/).pop() : "No clip selected"}</span>
        <button class="btn" onclick="triggerUpload(${i})">Upload</button>
        <button class="btn" onclick="openLibrary(${i})">Library</button>
      </div>
      <div class="row">
        <label>Rank</label>
        <input type="number" min="1" max="99" value="${slot.rank}"
          onchange="slots[${i}].rank = parseInt(this.value) || ${i+1}">
        <label style="margin-left:16px;">Title</label>
        <input type="text" placeholder="Clip title..." value="${slot.title}"
          oninput="slots[${i}].title = this.value">
      </div>
      <div class="trim-row">
        <label>Start (s)</label>
        <input type="number" min="0" step="0.1" value="${slot.start}"
          onchange="slots[${i}].start = parseFloat(this.value) || 0">
        <label>End (s)</label>
        <input type="number" min="0" step="0.1" value="${slot.end}"
          onchange="slots[${i}].end = parseFloat(this.value) || 0">
      </div>
      <input type="file" id="file-input-${i}" accept="video/*" style="display:none"
        onchange="handleFileUpload(${i}, this)">
    `;
    container.appendChild(div);
  });
}

// ── File upload ───────────────────────────────────────────────────────────────
function triggerUpload(i) {
  document.getElementById(`file-input-${i}`).click();
}

async function handleFileUpload(i, input) {
  const file = input.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  setStatus("Uploading...");
  const res = await fetch("/api/upload-video", {method: "POST", body: fd});
  const data = await res.json();
  if (data.error) { setStatus("Upload error: " + data.error, "error"); return; }
  slots[i].path = data.path;
  document.getElementById(`clip-display-${i}`).textContent = data.filename;
  setStatus("");
}

// ── Library modal ─────────────────────────────────────────────────────────────
async function openLibrary(i) {
  libraryTargetSlot = i;
  document.getElementById("libraryModal").classList.add("open");
  const res = await fetch("/api/clips");
  const clips = await res.json();
  const list = document.getElementById("clipList");
  if (!clips.length) {
    list.innerHTML = "<em>No downloaded clips found.</em>";
    return;
  }
  list.innerHTML = clips.map(c => `
    <div class="clip-item" onclick="selectLibraryClip('${c.path.replace(/\\/g, '\\\\')}', '${c.filename}')">
      <span class="clip-name">${c.filename}</span>
      <span style="font-size:12px;color:#666;">${(c.size/1e6).toFixed(1)} MB</span>
    </div>
  `).join("");
}

function selectLibraryClip(path, filename) {
  const i = libraryTargetSlot;
  slots[i].path = path;
  document.getElementById(`clip-display-${i}`).textContent = filename;
  closeLibrary();
}

function closeLibrary() {
  document.getElementById("libraryModal").classList.remove("open");
  libraryTargetSlot = null;
}

// ── Template editor ───────────────────────────────────────────────────────────
function openTemplateEditor() {
  alert("Template editor: use the main template editor, then save to templates/top5/ with /api/top5/templates.");
}

// ── Export ────────────────────────────────────────────────────────────────────
async function startExport() {
  const templateFile = document.getElementById("templateSelect").value;
  if (!templateFile) { setStatus("Select a template first.", "error"); return; }
  for (let i = 0; i < NUM_SLOTS; i++) {
    if (!slots[i].path) { setStatus(`Slot ${i+1} has no clip.`, "error"); return; }
    if (!slots[i].title.trim()) { setStatus(`Slot ${i+1} needs a title.`, "error"); return; }
    if (slots[i].end <= slots[i].start) { setStatus(`Slot ${i+1}: end must be after start.`, "error"); return; }
  }

  const tRes = await fetch(`/api/top5/templates/${templateFile}`);
  const template = await tRes.json();
  if (template.error) { setStatus("Could not load template.", "error"); return; }

  setStatus("Starting export...");
  const res = await fetch("/api/top5/export", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({template, clips: slots})
  });
  const {job_id, error} = await res.json();
  if (error) { setStatus("Error: " + error, "error"); return; }

  const es = new EventSource(`/api/top5/export/${job_id}/progress`);
  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "progress") {
      setStatus(`Rendering slot ${msg.slot} of ${msg.total}...`);
    } else if (msg.type === "done") {
      es.close();
      setStatus(`Done! <a href="/api/exports/${msg.filename}" download style="color:#FFD700">Download ${msg.filename}</a>`, "done");
    } else if (msg.type === "error") {
      es.close();
      setStatus("Export failed: " + msg.message, "error");
    }
  };
}

function setStatus(msg, cls = "") {
  const el = document.getElementById("status");
  el.innerHTML = msg;
  el.className = cls;
}

init();
</script>
</body>
</html>
```

- [ ] **Step 2: Visit the page and verify it loads**

With the server running, open `http://localhost:5000/top5`.

Expected: Page loads with "Top 5 Moments" heading, template dropdown, 5 slot cards, Export button.

- [ ] **Step 3: Commit**

```
git add frontend/top5.html
git commit -m "feat(top5): frontend page"
```

---

## Task 7: Navigation Link

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add a link to the Top 5 page in the main UI**

Find the main navigation area in `frontend/index.html` (look for existing nav links or a header section). Add a link:

```html
<a href="/top5">Top 5 Moments</a>
```

Place it alongside any existing navigation links or buttons in the header/nav area. Match the existing style.

- [ ] **Step 2: Verify the link appears and navigates correctly**

Open `http://localhost:5000`, confirm the Top 5 link is visible and clicking it loads `/top5`.

- [ ] **Step 3: Commit**

```
git add frontend/index.html
git commit -m "feat(top5): navigation link from main page"
```

---

## Self-Review Checklist

- [x] `resolve_placeholders` — covered in Task 1 with 8 tests
- [x] `render_slot` — covered in Task 2
- [x] `export_top5` + `concat_segments` — covered in Task 3
- [x] All 5 Flask endpoints — covered in Task 4
- [x] Built-in template — covered in Task 5
- [x] Frontend page — covered in Task 6
- [x] Navigation — covered in Task 7
- [x] Type consistency: `slots` is `list[dict]` throughout; `render_slot` returns `str`; `export_top5` returns `str`
- [x] `concat_segments` uses forward-slash fix for Windows FFmpeg compat
- [x] No TBD/TODO/placeholder steps
