import json, uuid, threading, queue, os
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from downloader import download_video
from exporter import export_video

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

BASE_DIR      = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
EXPORTS_DIR   = BASE_DIR / "exports"
UPLOADS_DIR   = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
ALLOWED_AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}

SFX_DIR = BASE_DIR / "sfx"
SFX_LIB_PATH = BASE_DIR / "sfx_library.json"
_sfx_lib_lock = threading.Lock()
SFX_DIR.mkdir(exist_ok=True)
ALLOWED_SFX_EXTS = {'.mp3', '.wav', '.ogg'}

# In-memory job store: job_id -> Queue of SSE event dicts
_jobs: dict[str, queue.Queue] = {}


# ── Static ──────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return send_from_directory("frontend", "index.html")


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


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
