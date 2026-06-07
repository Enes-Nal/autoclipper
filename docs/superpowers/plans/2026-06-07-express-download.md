# Express Download Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an express workflow to the download page where the user pastes a URL, picks a template, types a title, optionally sets start time and duration, and receives a finished exported video — no editor required.

**Architecture:** A new `POST /api/express-export` route runs download then export sequentially in a background thread, streaming unified SSE progress. The frontend adds an express form panel to `index.html` that consumes that stream and shows download + compositing progress inline before offering a file-download button on completion.

**Tech Stack:** Python/Flask (backend), vanilla JS + existing SSE pattern (frontend), existing `download_video` + `export_video` functions (no new video processing code).

---

## File Map

| File | Change |
|---|---|
| `app.py` | Add `POST /api/express-export` route and `GET /api/express-export/<job_id>/progress` SSE route |
| `frontend/index.html` | Add express form UI panel (URL, template select, title, start time, duration, button, progress area) |
| `templates/builtin/blur-stack.json` | Add `"role": "title"` to the `title` text layer |
| `templates/builtin/text-header.json` | Add `"role": "title"` to the `title` text layer |
| `templates/builtin/footer-fade.json` | Add `"role": "title"` to the title text layer (if present) |
| `templates/builtin/minimal.json` | Add `"role": "title"` to the title text layer (if present) |
| `templates/builtin/side-blur.json` | Add `"role": "title"` to the title text layer (if present) |
| `templates/builtin/podcast.json` | Add `"role": "title"` to the title text layer (if present) |

---

## Task 1: Add `role: "title"` to built-in templates

**Files:**
- Modify: `templates/builtin/blur-stack.json`
- Modify: `templates/builtin/text-header.json`
- Modify: `templates/builtin/footer-fade.json`
- Modify: `templates/builtin/minimal.json`
- Modify: `templates/builtin/side-blur.json`
- Modify: `templates/builtin/podcast.json`

- [ ] **Step 1: Open each built-in template and add `"role": "title"` to the primary text layer**

For `templates/builtin/blur-stack.json`, the `title` layer becomes:
```json
{ "id": "title", "type": "text", "role": "title", "x": 40, "y": 80, "width": 1000, "text": "{title}", "font_family": "Inter", "font_weight": "900", "font_size": 72, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 6, "text_align": "center" }
```

For `templates/builtin/text-header.json`, the `title` layer becomes:
```json
{ "id": "title", "type": "text", "role": "title", "x": 40, "y": 60, "width": 1000, "text": "{title}", "font_size": 68, "fill": "#ffffff", "stroke": "#000000", "stroke_width": 4, "text_align": "center" }
```

For `templates/builtin/footer-fade.json`, `templates/builtin/minimal.json`, `templates/builtin/side-blur.json`, `templates/builtin/podcast.json`: Read each file and add `"role": "title"` to whichever layer has `"text": "{title}"`. If none exists, skip.

- [ ] **Step 2: Commit**

```bash
git add templates/builtin/
git commit -m "feat(templates): add role:title to built-in template text layers"
```

---

## Task 2: Add `POST /api/express-export` and its SSE stream route to `app.py`

**Files:**
- Modify: `app.py` (add two new routes after the existing `# ── Export` section)

- [ ] **Step 1: Write a failing test for the new route**

Create `tests/test_express_export.py`:
```python
import json, threading
from unittest.mock import patch, MagicMock
from app import app

client = app.test_client()


def _fake_download(url, job_id, on_progress=None):
    if on_progress:
        on_progress({"percent": 100, "status": "downloading"})
    return {"video_path": "/fake/video.mp4", "title": "Test"}


def _fake_export(*args, **kwargs):
    if kwargs.get("on_progress"):
        kwargs["on_progress"]("frame=100")
    return "/fake/exports/out.mp4"


def _fake_load_template(name):
    return {
        "name": "Blur Stack",
        "format": "9:16",
        "canvas": {"width": 1080, "height": 1920},
        "layers": [{"id": "title", "type": "text", "role": "title", "text": "{title}"}],
    }


def test_express_export_bad_request():
    r = client.post("/api/express-export", json={})
    assert r.status_code == 400
    assert b"url" in r.data


def test_express_export_missing_template():
    r = client.post("/api/express-export", json={"url": "https://x.com/v/1", "template_name": ""})
    assert r.status_code == 400
    assert b"template" in r.data


def test_express_export_returns_job_id():
    with patch("app.download_video", side_effect=_fake_download), \
         patch("app.export_video", side_effect=_fake_export), \
         patch("app._load_template_by_name", side_effect=_fake_load_template):
        r = client.post("/api/express-export", json={
            "url": "https://x.com/v/1",
            "template_name": "blur-stack",
            "title": "My clip",
        })
    assert r.status_code == 200
    assert "job_id" in r.get_json()


def test_parse_time_seconds():
    from app import _parse_time_to_seconds
    assert _parse_time_to_seconds("01:30") == 90.0
    assert _parse_time_to_seconds("1:00:00") == 3600.0
    assert _parse_time_to_seconds("45") == 45.0
    assert _parse_time_to_seconds("") is None
    assert _parse_time_to_seconds(None) is None
```

- [ ] **Step 2: Run the test to confirm it fails**

```
pytest tests/test_express_export.py -v
```
Expected: FAIL — `_load_template_by_name` not defined, route not found.

- [ ] **Step 3: Add `_parse_time_to_seconds`, `_load_template_by_name`, and the two routes to `app.py`**

Add this helper near the top of `app.py` (after imports):
```python
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
```

Add these two routes after the existing `# ── Export` section in `app.py`:
```python
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

            # Build segment if start/duration supplied
            segments = None
            if start_sec is not None:
                source_start = start_sec
                source_end   = (start_sec + duration_sec) if duration_sec else None
                if source_end:
                    segments = [{"sourceStart": source_start, "sourceEnd": source_end}]

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
```

- [ ] **Step 4: Run the tests**

```
pytest tests/test_express_export.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_express_export.py
git commit -m "feat(api): add /api/express-export route with unified SSE stream"
```

---

## Task 3: Add the express form UI to `frontend/index.html`

**Files:**
- Modify: `frontend/index.html`

The express form lives in a new panel that appears when the user clicks a "Quick Export" nav item in the sidebar (same pattern as the existing nav items). It replaces the center content area when active.

- [ ] **Step 1: Find the sidebar nav section and add a "Quick Export" nav item**

In `frontend/index.html`, find the sidebar nav section (look for `class="sb-nav"`). Add a new nav item after the existing ones:

```html
<div class="sb-nav-item" id="nav-express" onclick="showPanel('express')">
  <span class="sb-nav-icon">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
    </svg>
  </span>
  Quick Export
</div>
```

- [ ] **Step 2: Add the express panel HTML**

Find the area where panels/views are rendered (the `#canvas-area` or main workspace section). Add the express panel as a hidden div that becomes visible when the nav item is clicked. Place it as a sibling to existing panels, inside `#workspace` or `#main`:

```html
<!-- Express Export Panel -->
<div id="panel-express" style="display:none;flex:1;overflow-y:auto;padding:32px;align-items:center;justify-content:flex-start;flex-direction:column;gap:0">
  <div style="width:100%;max-width:480px">
    <h2 style="font-size:18px;font-weight:800;margin-bottom:6px;color:var(--tx)">Quick Export</h2>
    <p style="font-size:12px;color:var(--sub);margin-bottom:24px">Paste a URL, pick a template, and get a finished clip — no editor needed.</p>

    <div style="display:flex;flex-direction:column;gap:12px">
      <!-- URL -->
      <div>
        <label style="font-size:11px;font-weight:600;color:var(--sub);display:block;margin-bottom:4px">Video URL</label>
        <input id="eq-url" type="url" placeholder="https://youtube.com/watch?v=..." style="width:100%;padding:10px 12px;border-radius:var(--rs);border:1px solid var(--b2);background:var(--s2);color:var(--tx);font-size:13px;outline:none">
      </div>

      <!-- Template -->
      <div>
        <label style="font-size:11px;font-weight:600;color:var(--sub);display:block;margin-bottom:4px">Template</label>
        <select id="eq-template" style="width:100%;padding:10px 12px;border-radius:var(--rs);border:1px solid var(--b2);background:var(--s2);color:var(--tx);font-size:13px;outline:none">
          <option value="">Loading templates…</option>
        </select>
      </div>

      <!-- Title -->
      <div id="eq-title-wrap">
        <label style="font-size:11px;font-weight:600;color:var(--sub);display:block;margin-bottom:4px">Title</label>
        <input id="eq-title" type="text" placeholder="Enter clip title…" style="width:100%;padding:10px 12px;border-radius:var(--rs);border:1px solid var(--b2);background:var(--s2);color:var(--tx);font-size:13px;outline:none">
      </div>

      <!-- Start + Duration -->
      <div style="display:flex;gap:10px">
        <div style="flex:1">
          <label style="font-size:11px;font-weight:600;color:var(--sub);display:block;margin-bottom:4px">Start time</label>
          <input id="eq-start" type="text" placeholder="00:00" style="width:100%;padding:10px 12px;border-radius:var(--rs);border:1px solid var(--b2);background:var(--s2);color:var(--tx);font-size:13px;outline:none">
        </div>
        <div style="flex:1">
          <label style="font-size:11px;font-weight:600;color:var(--sub);display:block;margin-bottom:4px">Duration</label>
          <input id="eq-duration" type="text" placeholder="full video" style="width:100%;padding:10px 12px;border-radius:var(--rs);border:1px solid var(--b2);background:var(--s2);color:var(--tx);font-size:13px;outline:none">
        </div>
      </div>

      <!-- Button -->
      <button id="eq-btn" onclick="startExpressExport()" style="margin-top:4px;width:100%;padding:12px;border-radius:var(--r);border:none;background:var(--acc);color:#000;font-size:13px;font-weight:700;cursor:pointer">
        Download &amp; Export
      </button>

      <!-- Progress -->
      <div id="eq-progress" style="display:none;padding:14px;border-radius:var(--r);border:1px solid var(--b1);background:var(--s2);font-size:12px;color:var(--sub)">
        <div id="eq-status">Starting…</div>
        <div id="eq-actions" style="display:none;margin-top:10px;display:flex;gap:8px">
          <a id="eq-download-link" href="#" style="padding:8px 14px;border-radius:var(--rs);background:var(--acc);color:#000;font-weight:700;font-size:12px;text-decoration:none">Download file</a>
          <button id="eq-edit-btn" onclick="openInEditor()" style="padding:8px 14px;border-radius:var(--rs);border:1px solid var(--b2);background:var(--s3);color:var(--tx);font-size:12px;cursor:pointer">Edit in editor</button>
        </div>
      </div>

      <!-- Error -->
      <div id="eq-error" style="display:none;padding:12px;border-radius:var(--r);border:1px solid var(--danger);background:rgba(244,63,94,0.08);color:var(--danger);font-size:12px"></div>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add the express panel JavaScript**

Find the `<script>` block in `frontend/index.html`. Add the following functions:

```javascript
// ── Express Export ────────────────────────────────────────────────────────────
let _eqOutputPath = null;

async function loadExpressTemplates() {
  const sel = document.getElementById('eq-template');
  if (!sel) return;
  try {
    const res = await fetch('/api/templates');
    const templates = await res.json();
    sel.innerHTML = templates.map(t =>
      `<option value="${t.file}">${t.name}</option>`
    ).join('');
    updateExpressTitleVisibility();
  } catch {
    sel.innerHTML = '<option value="">Failed to load templates</option>';
  }
}

async function updateExpressTitleVisibility() {
  const sel = document.getElementById('eq-template');
  const wrap = document.getElementById('eq-title-wrap');
  if (!sel || !wrap) return;
  const name = sel.value;
  if (!name) { wrap.style.display = 'block'; return; }
  try {
    const res = await fetch(`/api/templates/${name}`);
    const tpl = await res.json();
    const hasTitle = (tpl.layers || []).some(l => l.role === 'title' || (l.type === 'text' && l.text && l.text.includes('{title}')));
    wrap.style.display = hasTitle ? 'block' : 'none';
  } catch {
    wrap.style.display = 'block';
  }
}

async function startExpressExport() {
  const url      = document.getElementById('eq-url').value.trim();
  const tplName  = document.getElementById('eq-template').value;
  const title    = document.getElementById('eq-title').value.trim();
  const start    = document.getElementById('eq-start').value.trim();
  const duration = document.getElementById('eq-duration').value.trim();

  const errEl = document.getElementById('eq-error');
  errEl.style.display = 'none';

  if (!url) { errEl.textContent = 'Please enter a video URL.'; errEl.style.display = 'block'; return; }
  if (!tplName) { errEl.textContent = 'Please select a template.'; errEl.style.display = 'block'; return; }

  const btn = document.getElementById('eq-btn');
  const progressEl = document.getElementById('eq-progress');
  const statusEl = document.getElementById('eq-status');
  const actionsEl = document.getElementById('eq-actions');

  btn.disabled = true;
  btn.textContent = 'Working…';
  progressEl.style.display = 'block';
  actionsEl.style.display = 'none';
  statusEl.textContent = 'Starting download…';
  _eqOutputPath = null;

  let jobId;
  try {
    const res = await fetch('/api/express-export', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ url, template_name: tplName, title, start_time: start, duration }),
    });
    const data = await res.json();
    if (!res.ok) { throw new Error(data.error || 'Request failed'); }
    jobId = data.job_id;
  } catch (e) {
    errEl.textContent = e.message;
    errEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Download & Export';
    return;
  }

  const es = new EventSource(`/api/express-export/${jobId}/progress`);
  es.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === 'progress') {
      if (msg.phase === 'download') {
        statusEl.textContent = msg.percent != null
          ? `Downloading… ${Math.round(msg.percent)}%`
          : 'Downloading…';
      } else if (msg.phase === 'export') {
        statusEl.textContent = 'Compositing…';
      }
    } else if (msg.type === 'done') {
      es.close();
      _eqOutputPath = msg.output_path;
      statusEl.textContent = 'Done — your clip is ready';
      actionsEl.style.display = 'flex';
      document.getElementById('eq-download-link').href = `/api/exports/${msg.filename}`;
      document.getElementById('eq-download-link').download = msg.filename;
      btn.disabled = false;
      btn.textContent = 'Download & Export';
    } else if (msg.type === 'error') {
      es.close();
      errEl.textContent = msg.message;
      errEl.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Download & Export';
      progressEl.style.display = 'none';
    }
  };
  es.onerror = () => {
    es.close();
    errEl.textContent = 'Connection lost. Check the server.';
    errEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Download & Export';
  };
}

function openInEditor() {
  if (_eqOutputPath) {
    // Load output into the editor by switching to the main panel and triggering a load
    showPanel('editor');
    // The editor's existing loadVideoFromPath (or equivalent) should be called here.
    // If no such global exists, just navigate to the root — the user can drag-drop.
    if (typeof loadVideoFile === 'function') {
      loadVideoFile(_eqOutputPath);
    }
  }
}
```

- [ ] **Step 4: Wire up the template `<select>` change handler and panel activation**

In the same `<script>` block, find where panels are shown/hidden (look for `showPanel` function or equivalent). Ensure that when the express panel is shown, templates are loaded. Add to the panel show logic:

```javascript
// Inside showPanel() or wherever panels are toggled — add this case:
// if (name === 'express') { loadExpressTemplates(); }
```

Also add a `change` listener to the template select so title visibility updates when the user picks a different template. Add this near `loadExpressTemplates`:

```javascript
document.getElementById('eq-template')?.addEventListener('change', updateExpressTitleVisibility);
```

- [ ] **Step 5: Verify the panel appears and templates load**

Start the server (`python app.py`), open `http://localhost:5000`, click "Quick Export" in the sidebar. Confirm:
- The form panel is visible
- The template dropdown lists all templates
- Switching to a template without a text layer hides the Title field

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat(ui): add Quick Export express panel to sidebar"
```

---

## Task 4: End-to-end smoke test

**Files:**
- No new files

- [ ] **Step 1: Start the server**

```
python app.py
```

- [ ] **Step 2: Fill the express form**

Open `http://localhost:5000`, click "Quick Export". Enter:
- URL: any short YouTube or Twitter/X video URL
- Template: "Blur Stack"
- Title: "Test clip"
- Start time: `00:00`
- Duration: `00:15`

Click "Download & Export".

- [ ] **Step 3: Confirm progress updates appear**

The progress area below the button should show "Downloading… 45%", then "Compositing…", then "Done — your clip is ready".

- [ ] **Step 4: Confirm the Download file button works**

Click "Download file" — the browser should download a `.mp4` file.

- [ ] **Step 5: Commit**

```bash
git commit --allow-empty -m "chore: express export end-to-end verified"
```
