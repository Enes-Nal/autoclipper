import json, uuid, threading, queue, os
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from downloader import download_video
from exporter import export_video
from top5_exporter import export_top5

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

BASE_DIR      = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
EXPORTS_DIR   = BASE_DIR / "exports"
UPLOADS_DIR   = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

TOP5_TEMPLATES_DIR = BASE_DIR / "templates" / "top5"
TOP5_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR = BASE_DIR / "downloads"
ALLOWED_VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.webm', '.avi'}

ALLOWED_AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}

SFX_DIR = BASE_DIR / "sfx"
SFX_LIB_PATH = BASE_DIR / "sfx_library.json"
_sfx_lib_lock = threading.Lock()
SFX_DIR.mkdir(exist_ok=True)
ALLOWED_SFX_EXTS = {'.mp3', '.wav', '.ogg'}

# In-memory job store: job_id -> Queue of SSE event dicts
_jobs: dict[str, queue.Queue] = {}


def _parse_time_to_seconds(t) -> float | None:
    """Parse '00:30', '1:00:00', or '45' into seconds. Returns None if empty/None."""
    if not t:
        return None
    t = str(t).strip()
    if not t:
        return None
    parts = t.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return None
    return None


def _load_template_by_name(name: str) -> dict | None:
    """Load a template JSON by file stem, searching builtin then user templates."""
    for base in (TEMPLATES_DIR / "builtin", TEMPLATES_DIR):
        p = base / f"{name}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


# ── Static ──────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return send_from_directory("frontend", "index.html")


@app.get("/top5")
def top5_page():
    return send_from_directory("frontend", "top5.html")


# ── Templates ───────────────────────────────────────────────────────────────
@app.get("/api/templates")
def list_templates():
    results = []
    for p in sorted(TEMPLATES_DIR.rglob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            results.append({
                "name": data.get("name", p.stem),
                "file": p.stem,
                "format": data.get("format", "9:16"),
                "builtin": "builtin" in str(p),
            })
        except Exception:
            pass
    return jsonify(results)


@app.get("/api/templates/<name>")
def get_template(name):
    for base in (TEMPLATES_DIR, TEMPLATES_DIR / "builtin"):
        p = base / f"{name}.json"
        if p.exists():
            return jsonify(json.loads(p.read_text(encoding="utf-8")))
    return jsonify({"error": "not found"}), 404


@app.post("/api/templates")
def save_template():
    data = request.json
    name = data.get("name", "untitled").replace(" ", "-").lower()
    TEMPLATES_DIR.mkdir(exist_ok=True)
    path = TEMPLATES_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return jsonify({"saved": name})


@app.patch("/api/templates/<name>")
def rename_template(name):
    p = TEMPLATES_DIR / f"{name}.json"
    if not p.exists() or "builtin" in str(p):
        return jsonify({"error": "not found"}), 404
    new_name = (request.json or {}).get("name", "").replace(" ", "-").lower()
    if not new_name:
        return jsonify({"error": "name required"}), 400
    data = json.loads(p.read_text(encoding="utf-8"))
    data["name"] = (request.json or {}).get("name", new_name)
    new_p = TEMPLATES_DIR / f"{new_name}.json"
    new_p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if new_p != p:
        p.unlink()
    return jsonify({"renamed": new_name})


@app.delete("/api/templates/<name>")
def delete_template(name):
    p = TEMPLATES_DIR / f"{name}.json"
    if not p.exists() or "builtin" in str(p):
        return jsonify({"error": "not found"}), 404
    p.unlink()
    return jsonify({"deleted": name})


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


# ── Download ─────────────────────────────────────────────────────────────────
@app.post("/api/download")
def start_download():
    url = (request.json or {}).get("url", "")
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

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Export ────────────────────────────────────────────────────────────────────
@app.post("/api/export")
def start_export():
    body = request.json or {}
    clips        = body.get("clips", None)
    video_path   = body.get("video_path", "")
    template     = body.get("template", {})
    title        = body.get("title", "")
    emoji_source = body.get("emoji_source", "twemoji")
    segments     = body.get("segments", None)

    if clips is not None and not clips:
        return jsonify({"error": "clips array must not be empty"}), 400

    # Validate: need either clips or video_path
    if clips:
        for c in clips:
            vp = c.get("video_path", "")
            if not vp or not os.path.exists(vp):
                return jsonify({"error": f"video_path not found: {vp}"}), 400
    elif not video_path or not os.path.exists(video_path):
        return jsonify({"error": "video_path not found"}), 400

    job_id = uuid.uuid4().hex[:8]
    q: queue.Queue = queue.Queue()
    _jobs[job_id] = q

    def run():
        try:
            def on_progress(line):
                q.put({"type": "progress", "line": line})
            out = export_video(
                video_path=video_path if clips is None else None,
                template=template,
                title=title,
                on_progress=on_progress,
                emoji_source=emoji_source,
                segments=segments if clips is None else None,
                clips=clips,
            )
            q.put({"type": "done", "output_path": out, "filename": Path(out).name})
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

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/emoji-pack/<filename>")
def serve_emoji_pack(filename):
    return send_from_directory(str((BASE_DIR / "EmojiPack").resolve()), filename)


@app.get("/api/downloads/<filename>")
def serve_download(filename):
    return send_from_directory(str((BASE_DIR / "downloads").resolve()), filename)


@app.get("/api/exports/<filename>")
def download_export(filename):
    return send_from_directory(str(EXPORTS_DIR.resolve()), filename, as_attachment=True)


@app.post("/api/upload-audio")
def upload_audio():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "file required"}), 400
    if not f.filename:
        return jsonify({"error": "no filename provided"}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        return jsonify({"error": f"extension {ext} not allowed"}), 400
    uid = uuid.uuid4().hex[:8]
    filename = f"{uid}{ext}"
    dest = UPLOADS_DIR / filename
    f.save(str(dest))
    return jsonify({"path": f"uploads/{filename}"})



@app.get("/api/uploads/<filename>")
def serve_upload(filename):
    return send_from_directory(str(UPLOADS_DIR.resolve()), filename)


# ── SFX Library ───────────────────────────────────────────────────────────────
def _read_sfx_lib():
    if SFX_LIB_PATH.exists():
        return json.loads(SFX_LIB_PATH.read_text(encoding="utf-8"))
    return {"sounds": []}


def _write_sfx_lib(data):
    SFX_LIB_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                             encoding="utf-8")


@app.get("/api/sfx")
def list_sfx():
    return jsonify(_read_sfx_lib())


@app.post("/api/sfx/upload")
def upload_sfx():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "file required"}), 400
    if not f.filename:
        return jsonify({"error": "no filename provided"}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_SFX_EXTS:
        return jsonify({"error": f"extension {ext} not allowed"}), 400
    sfx_id = uuid.uuid4().hex[:12]
    filename = f"{sfx_id}{ext}"
    dest = SFX_DIR / filename
    f.save(str(dest))
    name = Path(f.filename).stem
    with _sfx_lib_lock:
        lib = _read_sfx_lib()
        entry = {"id": sfx_id, "name": name, "path": f"sfx/{filename}"}
        lib["sounds"].append(entry)
        _write_sfx_lib(lib)
    return jsonify(entry)


@app.get("/api/sfx/files/<filename>")
def serve_sfx(filename):
    return send_from_directory(str(SFX_DIR.resolve()), filename)


@app.patch("/api/sfx/<sfx_id>/rename")
def rename_sfx(sfx_id):
    new_name = (request.json or {}).get("name", "").strip()
    if not new_name:
        return jsonify({"error": "name required"}), 400
    with _sfx_lib_lock:
        lib = _read_sfx_lib()
        entry = next((s for s in lib["sounds"] if s["id"] == sfx_id), None)
        if not entry:
            return jsonify({"error": "not found"}), 404
        entry["name"] = new_name
        _write_sfx_lib(lib)
    return jsonify(entry)


@app.delete("/api/sfx/<sfx_id>")
def delete_sfx(sfx_id):
    with _sfx_lib_lock:
        lib = _read_sfx_lib()
        entry = next((s for s in lib["sounds"] if s["id"] == sfx_id), None)
        if not entry:
            return jsonify({"error": "not found"}), 404
        lib["sounds"] = [s for s in lib["sounds"] if s["id"] != sfx_id]
        _write_sfx_lib(lib)
    file_path = BASE_DIR / entry["path"]
    if file_path.exists():
        file_path.unlink()
    return jsonify({"deleted": sfx_id})


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


# ── Express Export ────────────────────────────────────────────────────────────
@app.post("/api/express-export")
def start_express_export():
    body = request.json or {}
    url           = body.get("url", "").strip()
    template_name = body.get("template_name", "").strip()
    title         = body.get("title", "")
    start_raw     = body.get("start_time", "")
    duration_raw  = body.get("duration", "")

    if not url:
        return jsonify({"error": "url required"}), 400
    if not template_name:
        return jsonify({"error": "template_name required"}), 400

    template = _load_template_by_name(template_name)
    if template is None:
        return jsonify({"error": f"template not found: {template_name}"}), 404

    start_sec    = _parse_time_to_seconds(start_raw)
    duration_sec = _parse_time_to_seconds(duration_raw)

    job_id = uuid.uuid4().hex[:8]
    q: queue.Queue = queue.Queue()
    _jobs[job_id] = q

    def run():
        try:
            # Phase 1: download
            def on_dl(p):
                q.put({"type": "progress", "phase": "download", **p})

            info = download_video(url, job_id, on_dl)
            video_path = info.get("video_path") or str(DOWNLOADS_DIR / f"{job_id}.mp4")
            q.put({"type": "progress", "phase": "download", "percent": 100, "status": "done"})

            # Build segment if start time is supplied
            segments = None
            if start_sec is not None:
                seg = {"sourceStart": start_sec}
                if duration_sec is not None:
                    seg["sourceEnd"] = start_sec + duration_sec
                segments = [seg]

            # Phase 2: export
            def on_exp(line):
                q.put({"type": "progress", "phase": "export", "line": line})

            out = export_video(
                video_path=video_path,
                template=template,
                title=title,
                on_progress=on_exp,
                segments=segments,
            )
            q.put({"type": "done", "output_path": out, "filename": Path(out).name})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.get("/api/express-export/<job_id>/progress")
def express_export_progress(job_id):
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


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
