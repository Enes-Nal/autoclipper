# Render + Cloudflare R2 Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy autoclipper to Render's free tier with Cloudflare R2 providing persistent storage for user templates and exported videos.

**Architecture:** A new `storage.py` module wraps all R2 interaction via `boto3` (S3-compatible). On startup, templates are synced from R2 to local disk so all existing file-path-based template code runs unchanged. After any export completes, the output file is uploaded to R2 and a 1-hour presigned URL is returned to the frontend via the SSE `done` event. All R2 calls are no-ops when env vars are absent, preserving local dev behavior.

**Tech Stack:** Python/Flask (existing), boto3 (new), gunicorn (new for prod), Cloudflare R2 (S3-compatible), Render (hosting)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `storage.py` | Create | All R2 interaction: template sync, template push/delete, export upload + presign |
| `app.py` | Modify | Startup sync, template write-through to R2, export endpoints return presigned URL |
| `frontend/index.html` | Modify | Use `download_url` from SSE done event instead of `/api/exports/<filename>` |
| `frontend/top5.html` | Modify | Same frontend fix for top5 export |
| `requirements.txt` | Modify | Add `boto3>=1.34` and `gunicorn>=21.0` |
| `build.sh` | Create | Install ffmpeg + pip deps on Render |
| `render.yaml` | Create | Render service definition with env var placeholders |
| `tests/test_storage.py` | Create | Unit tests for storage.py (mocked boto3) |

---

## Task 1: Create `storage.py`

**Files:**
- Create: `storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_storage.py`:

```python
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_storage_env(monkeypatch):
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://fake.r2.example.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "testbucket")


# ── is_configured ─────────────────────────────────────────────────────────────

def test_is_configured_true(monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)
    assert storage.is_configured() is True


def test_is_configured_false_when_env_missing():
    for var in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
        os.environ.pop(var, None)
    import importlib
    import storage
    importlib.reload(storage)
    assert storage.is_configured() is False


# ── sync_templates_from_r2 ───────────────────────────────────────────────────

def test_sync_templates_downloads_missing_file(tmp_path, monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)

    fake_client = MagicMock()
    fake_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "templates/my-template.json", "LastModified": MagicMock()}]
    }

    with patch.object(storage, "_client", fake_client):
        storage.sync_templates_from_r2(tmp_path)

    fake_client.download_file.assert_called_once_with(
        "testbucket", "templates/my-template.json", str(tmp_path / "my-template.json")
    )


def test_sync_templates_noop_when_not_configured(tmp_path, monkeypatch):
    for var in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
        monkeypatch.delenv(var, raising=False)
    import importlib
    import storage
    importlib.reload(storage)

    # Should not raise and should not touch tmp_path
    storage.sync_templates_from_r2(tmp_path)
    assert list(tmp_path.iterdir()) == []


# ── push_template ─────────────────────────────────────────────────────────────

def test_push_template_uploads_file(tmp_path, monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)

    tpl = tmp_path / "my-template.json"
    tpl.write_text(json.dumps({"name": "my-template"}))

    fake_client = MagicMock()
    with patch.object(storage, "_client", fake_client):
        storage.push_template(tpl, tmp_path)

    fake_client.upload_file.assert_called_once_with(
        str(tpl), "testbucket", "templates/my-template.json"
    )


def test_push_template_noop_when_not_configured(tmp_path, monkeypatch):
    for var in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
        monkeypatch.delenv(var, raising=False)
    import importlib
    import storage
    importlib.reload(storage)

    tpl = tmp_path / "x.json"
    tpl.write_text("{}")
    storage.push_template(tpl, tmp_path)  # must not raise


# ── delete_template ───────────────────────────────────────────────────────────

def test_delete_template_calls_delete_object(monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)

    fake_client = MagicMock()
    with patch.object(storage, "_client", fake_client):
        storage.delete_template("templates/my-template.json")

    fake_client.delete_object.assert_called_once_with(
        Bucket="testbucket", Key="templates/my-template.json"
    )


# ── upload_export ─────────────────────────────────────────────────────────────

def test_upload_export_returns_presigned_url(tmp_path, monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)

    export_file = tmp_path / "output.mp4"
    export_file.write_bytes(b"fake video")

    fake_client = MagicMock()
    fake_client.generate_presigned_url.return_value = "https://r2.example.com/presigned"

    with patch.object(storage, "_client", fake_client):
        url = storage.upload_export(export_file)

    assert url == "https://r2.example.com/presigned"
    fake_client.upload_file.assert_called_once_with(
        str(export_file), "testbucket", f"exports/{export_file.name}"
    )
    assert not export_file.exists()  # local file deleted after upload


def test_upload_export_returns_none_when_not_configured(tmp_path, monkeypatch):
    for var in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
        monkeypatch.delenv(var, raising=False)
    import importlib
    import storage
    importlib.reload(storage)

    export_file = tmp_path / "output.mp4"
    export_file.write_bytes(b"fake video")

    result = storage.upload_export(export_file)
    assert result is None
    assert export_file.exists()  # not deleted when R2 unconfigured
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd D:/Code/autoclipper
pytest tests/test_storage.py -v
```

Expected: errors like `ModuleNotFoundError: No module named 'storage'`

- [ ] **Step 3: Create `storage.py`**

```python
import os
import logging
from pathlib import Path

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

_ENDPOINT = os.environ.get("R2_ENDPOINT_URL", "")
_KEY      = os.environ.get("R2_ACCESS_KEY_ID", "")
_SECRET   = os.environ.get("R2_SECRET_ACCESS_KEY", "")
_BUCKET   = os.environ.get("R2_BUCKET_NAME", "")

_client = None
if _ENDPOINT and _KEY and _SECRET and _BUCKET:
    _client = boto3.client(
        "s3",
        endpoint_url=_ENDPOINT,
        aws_access_key_id=_KEY,
        aws_secret_access_key=_SECRET,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def is_configured() -> bool:
    return _client is not None


def sync_templates_from_r2(templates_dir: Path) -> None:
    """Download any templates present in R2 but missing locally."""
    if not is_configured():
        return
    try:
        resp = _client.list_objects_v2(Bucket=_BUCKET, Prefix="templates/")
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            filename = Path(key).name
            if not filename:
                continue
            local_path = templates_dir / filename
            if not local_path.exists():
                templates_dir.mkdir(parents=True, exist_ok=True)
                _client.download_file(_BUCKET, key, str(local_path))
                logger.info("synced template from R2: %s", key)
    except Exception:
        logger.warning("R2 template sync failed", exc_info=True)


def push_template(local_path: Path, templates_dir: Path) -> None:
    """Upload a template file to R2. Silent no-op if R2 not configured."""
    if not is_configured():
        return
    try:
        key = f"templates/{local_path.relative_to(templates_dir).as_posix()}"
        _client.upload_file(str(local_path), _BUCKET, key)
        logger.info("pushed template to R2: %s", key)
    except Exception:
        logger.warning("R2 template push failed: %s", local_path, exc_info=True)


def delete_template(key: str) -> None:
    """Delete a template object from R2. Silent no-op if R2 not configured."""
    if not is_configured():
        return
    try:
        _client.delete_object(Bucket=_BUCKET, Key=key)
        logger.info("deleted template from R2: %s", key)
    except Exception:
        logger.warning("R2 template delete failed: %s", key, exc_info=True)


def upload_export(local_path: Path) -> str | None:
    """Upload export file to R2, delete local copy, return 1-hour presigned URL.

    Returns None if R2 is not configured (caller serves local file instead).
    """
    if not is_configured():
        return None
    key = f"exports/{local_path.name}"
    try:
        _client.upload_file(str(local_path), _BUCKET, key)
        local_path.unlink()
        url = _client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _BUCKET, "Key": key},
            ExpiresIn=3600,
        )
        return url
    except Exception:
        logger.error("R2 export upload failed: %s", local_path, exc_info=True)
        raise
```

- [ ] **Step 4: Add boto3 to requirements.txt**

Open `requirements.txt` and add:
```
boto3>=1.34
```

- [ ] **Step 5: Run tests to verify they pass**

```
pip install boto3
pytest tests/test_storage.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add storage.py tests/test_storage.py requirements.txt
git commit -m "feat: add storage.py for Cloudflare R2 integration"
```

---

## Task 2: Wire template sync into `app.py` startup

**Files:**
- Modify: `app.py` (top of file, after `TEMPLATES_DIR` is defined)

- [ ] **Step 1: Add import and startup sync**

In `app.py`, after the existing imports (around line 10), add:

```python
import storage
```

Then find this block (around line 14):
```python
BASE_DIR      = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
```

After `TEMPLATES_DIR` is defined, add a startup sync using Flask's `before_request` with a once-flag. Insert this after the `SFX_DIR.mkdir(exist_ok=True)` line (around line 22):

```python
_startup_done = False

@app.before_request
def _startup():
    global _startup_done
    if not _startup_done:
        _startup_done = True
        storage.sync_templates_from_r2(TEMPLATES_DIR)
```

- [ ] **Step 2: Verify app still starts**

```
python app.py
```

Expected: starts on port 5000 without errors. Ctrl+C to stop.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: sync templates from R2 on startup"
```

---

## Task 3: Wire template write-through in `app.py`

**Files:**
- Modify: `app.py` — `save_template`, `rename_template`, `delete_template`, `save_top5_template`, `delete_top5_template`

Each template mutation already writes/deletes a local file. After each local operation, push or delete from R2 in a background thread so the HTTP response isn't delayed.

- [ ] **Step 1: Update `save_template`**

Find `save_template` (the `@app.post("/api/templates")` handler). After `path.write_text(...)`:

```python
@app.post("/api/templates")
def save_template():
    data = request.json
    name = data.get("name", "untitled").replace(" ", "-").lower()
    TEMPLATES_DIR.mkdir(exist_ok=True)
    path = TEMPLATES_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    threading.Thread(target=storage.push_template, args=(path, TEMPLATES_DIR), daemon=True).start()
    return jsonify({"saved": name})
```

- [ ] **Step 2: Update `rename_template`**

Find `rename_template` (the `@app.patch("/api/templates/<name>")` handler). After the local rename completes, push the new file and delete the old key:

```python
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
        threading.Thread(target=storage.delete_template, args=(f"templates/{name}.json",), daemon=True).start()
    threading.Thread(target=storage.push_template, args=(new_p, TEMPLATES_DIR), daemon=True).start()
    return jsonify({"renamed": new_name})
```

- [ ] **Step 3: Update `delete_template`**

Find `delete_template` (the `@app.delete("/api/templates/<name>")` handler):

```python
@app.delete("/api/templates/<name>")
def delete_template(name):
    p = TEMPLATES_DIR / f"{name}.json"
    if not p.exists() or "builtin" in str(p):
        return jsonify({"error": "not found"}), 404
    p.unlink()
    threading.Thread(target=storage.delete_template, args=(f"templates/{name}.json",), daemon=True).start()
    return jsonify({"deleted": name})
```

- [ ] **Step 4: Update `save_top5_template`**

Find `save_top5_template` (the `@app.post("/api/top5/templates")` handler). After `path.write_text(...)`:

```python
@app.post("/api/top5/templates")
def save_top5_template():
    data = request.json
    name = data.get("name", "untitled").replace(" ", "-").lower()
    path = TOP5_TEMPLATES_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    threading.Thread(target=storage.push_template, args=(path, TEMPLATES_DIR), daemon=True).start()
    return jsonify({"saved": name})
```

- [ ] **Step 5: Update `delete_top5_template`**

Find `delete_top5_template` (the `@app.delete("/api/top5/templates/<name>")` handler). After `p.unlink()`:

```python
@app.delete("/api/top5/templates/<name>")
def delete_top5_template(name):
    p = TOP5_TEMPLATES_DIR / f"{name}.json"
    if not p.exists():
        return jsonify({"error": "not found"}), 404
    p.unlink()
    rel_key = f"templates/top5/{name}.json"
    threading.Thread(target=storage.delete_template, args=(rel_key,), daemon=True).start()
    return jsonify({"deleted": name})
```

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: write-through template changes to R2"
```

---

## Task 4: Wire R2 upload into all three export endpoints

**Files:**
- Modify: `app.py` — the `run()` inner functions inside `start_export`, `start_top5_export`, `start_express_export`

Each export endpoint has an inner `run()` that puts a `done` event on the queue with `output_path` and `filename`. Replace those with an R2 upload; if R2 is not configured, fall back to the existing local-file behavior.

- [ ] **Step 1: Update `start_export` inner `run()`**

Find the `run()` inside `start_export`. Replace the `q.put({"type": "done", ...})` line:

```python
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
            out_path = Path(out)
            download_url = storage.upload_export(out_path)
            if download_url:
                q.put({"type": "done", "filename": out_path.name, "download_url": download_url})
            else:
                q.put({"type": "done", "output_path": out, "filename": out_path.name})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})
```

- [ ] **Step 2: Update `start_top5_export` inner `run()`**

Find the `run()` inside `start_top5_export`. Replace the `q.put({"type": "done", ...})` line:

```python
    def run():
        try:
            def on_progress(event):
                q.put({"type": "progress", **event})
            out = export_top5(slots, template, job_id, on_progress=on_progress)
            out_path = Path(out)
            download_url = storage.upload_export(out_path)
            if download_url:
                q.put({"type": "done", "filename": out_path.name, "download_url": download_url})
            else:
                q.put({"type": "done", "output_path": out, "filename": out_path.name})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})
```

- [ ] **Step 3: Update `start_express_export` inner `run()`**

Find the `run()` inside `start_express_export`. Replace the final `q.put({"type": "done", ...})` line:

```python
            out_path = Path(out)
            download_url = storage.upload_export(out_path)
            if download_url:
                q.put({"type": "done", "filename": out_path.name, "download_url": download_url})
            else:
                q.put({"type": "done", "output_path": out, "filename": out_path.name})
```

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: upload exports to R2 and return presigned download URL"
```

---

## Task 5: Update frontend to use `download_url`

**Files:**
- Modify: `frontend/index.html` — lines ~4727-4732 (main export done handler) and ~6385-6391 (express export done handler)
- Modify: `frontend/top5.html` — line ~221 (top5 export done handler)

The frontend currently constructs download links as `/api/exports/${msg.filename}`. When R2 is active, `msg.download_url` will be present instead. We use it if available, falling back to the local path otherwise so local dev still works.

- [ ] **Step 1: Update main export done handler in `index.html`**

Find this block (around line 4727):
```js
        else if(msg.type==='done'){
          st.innerHTML=`Exported: <a href="/api/exports/${msg.filename}" style="color:var(--acc)" download>${msg.filename}</a>`;
          ...
          const a=document.createElement('a');a.href=`/api/exports/${msg.filename}`;a.download=msg.filename;document.body.appendChild(a);a.click();document.body.removeChild(a);
```

Replace the two `/api/exports/${msg.filename}` references with:
```js
        else if(msg.type==='done'){
          const dlUrl = msg.download_url || `/api/exports/${msg.filename}`;
          st.innerHTML=`Exported: <a href="${dlUrl}" style="color:var(--acc)" download="${msg.filename}">${msg.filename}</a>`;
          ...
          const a=document.createElement('a');a.href=dlUrl;a.download=msg.filename;document.body.appendChild(a);a.click();document.body.removeChild(a);
```

- [ ] **Step 2: Update express export done handler in `index.html`**

Find this block (around line 6385):
```js
    } else if (msg.type === 'done') {
      _eqOutputPath = msg.output_path;
      ...
      document.getElementById('eq-download-link').href = `/api/exports/${msg.filename}`;
      document.getElementById('eq-download-link').download = msg.filename;
```

Replace with:
```js
    } else if (msg.type === 'done') {
      _eqOutputPath = msg.output_path || msg.download_url;
      const dlUrl = msg.download_url || `/api/exports/${msg.filename}`;
      document.getElementById('eq-download-link').href = dlUrl;
      document.getElementById('eq-download-link').download = msg.filename;
```

- [ ] **Step 3: Update top5 done handler in `top5.html`**

Find this block (around line 221):
```js
    } else if (msg.type === "done") {
      ...
      setStatus(`Done! <a href="/api/exports/${msg.filename}" download style="color:#FFD700">Download ${msg.filename}</a>`, "done")
```

Replace with:
```js
    } else if (msg.type === "done") {
      const dlUrl = msg.download_url || `/api/exports/${msg.filename}`;
      setStatus(`Done! <a href="${dlUrl}" download="${msg.filename}" style="color:#FFD700">Download ${msg.filename}</a>`, "done")
```

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/top5.html
git commit -m "feat: use R2 presigned URL for export download when available"
```

---

## Task 6: Add Render deployment files

**Files:**
- Create: `build.sh`
- Create: `render.yaml`
- Modify: `requirements.txt` — add gunicorn

- [ ] **Step 1: Create `build.sh`**

```bash
#!/usr/bin/env bash
set -e
apt-get install -y ffmpeg
pip install -r requirements.txt
```

Make it executable. On Windows you can just create the file — Render will run it on Linux.

- [ ] **Step 2: Create `render.yaml`**

```yaml
services:
  - type: web
    name: autoclipper
    env: python
    region: oregon
    plan: free
    buildCommand: bash build.sh
    startCommand: gunicorn app:app --workers 2 --threads 4 --timeout 300
    envVars:
      - key: R2_ENDPOINT_URL
        sync: false
      - key: R2_ACCESS_KEY_ID
        sync: false
      - key: R2_SECRET_ACCESS_KEY
        sync: false
      - key: R2_BUCKET_NAME
        sync: false
```

- [ ] **Step 3: Add gunicorn to `requirements.txt`**

```
gunicorn>=21.0
```

- [ ] **Step 4: Commit**

```bash
git add build.sh render.yaml requirements.txt
git commit -m "chore: add Render deployment config and build script"
```

---

## Task 7: Manual smoke test before deploy

No automated test can cover the full download→export→R2 pipeline. Run through this manually in local dev to confirm nothing is broken before pushing to Render.

- [ ] **Step 1: Start the app locally (without R2 env vars)**

```
python app.py
```

- [ ] **Step 2: Open http://localhost:5000 — verify the editor loads**

- [ ] **Step 3: Save a template and verify it appears in `templates/` on disk**

- [ ] **Step 4: Run a short export and verify the download triggers**

The done event should have `output_path` (no `download_url`) since R2 is not configured — this is the fallback path.

- [ ] **Step 5: Run the full test suite**

```
pytest tests/ -v
```

Expected: all existing tests pass plus the new `test_storage.py` tests.

- [ ] **Step 6: Commit any fixes found during smoke test**

---

## Task 8: Deploy to Render

These are manual steps in the Render dashboard and Cloudflare dashboard.

- [ ] **Step 1: Create R2 bucket in Cloudflare**

1. Log into [dash.cloudflare.com](https://dash.cloudflare.com)
2. Go to R2 → Create bucket → name it (e.g. `autoclipper`)
3. Note your Account ID from the sidebar URL

- [ ] **Step 2: Create R2 API token**

1. In Cloudflare dashboard → R2 → Manage R2 API tokens → Create API token
2. Permissions: Object Read & Write, scope to your bucket
3. Note: Access Key ID, Secret Access Key, Endpoint URL (`https://<account-id>.r2.cloudflarestorage.com`)

- [ ] **Step 3: Push branch to GitHub**

```bash
git push origin HEAD
```

- [ ] **Step 4: Create Render service**

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repo, select this branch
3. Render will detect `render.yaml` — confirm the settings

- [ ] **Step 5: Set environment variables in Render dashboard**

Add all four R2 env vars (from Step 2):
- `R2_ENDPOINT_URL`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`

- [ ] **Step 6: Deploy and verify**

1. Trigger deploy in Render dashboard
2. Watch build logs — confirm ffmpeg installs and pip succeeds
3. Open the deployed URL, save a template, do a test export
4. Verify the export download link works (it should be an R2 presigned URL)
