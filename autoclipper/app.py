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


@app.get("/api/exports/<filename>")
def download_export(filename):
    return send_from_directory(str(EXPORTS_DIR.resolve()), filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
