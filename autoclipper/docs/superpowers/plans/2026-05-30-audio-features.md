# Audio Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add video layer volume/mute, an uploadable audio layer with waveform trimmer, and a synced preview audio strip to the autoclipper template editor.

**Architecture:** Audio layers live outside the Fabric.js canvas (stored in a `audioLayer` JS variable and appended to the template JSON at serialization time). The backend gains a file-upload route and FFmpeg audio mixing logic. The frontend gains an audio trimmer modal, a preview strip below the canvas, and a new Audio section in the video-layer properties panel.

**Tech Stack:** Python/Flask (backend), FFmpeg (audio mixing/looping/trimming), Web Audio API `AudioContext.decodeAudioData` (waveform rendering), vanilla JS + existing Fabric.js canvas (frontend), `<audio>` element (preview playback).

---

## File Map

| File | What changes |
|------|-------------|
| `app.py` | Add `POST /api/upload-audio` route; add `GET /api/uploads/<filename>` static serve |
| `exporter.py` | Add `build_audio_cmd_parts()` helper; update `export_video()` to call it |
| `tests/test_exporter.py` | Add tests for audio mixing, volume, mute, loop, no-audio fallback |
| `frontend/index.html` | All frontend changes (state, layers panel, properties panel, trimmer modal, preview strip) |

---

## Task 1: Backend — upload-audio route

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_upload_audio.py`:

```python
import io, pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_upload_audio_missing_file(client):
    resp = client.post('/api/upload-audio')
    assert resp.status_code == 400
    assert b'file' in resp.data

def test_upload_audio_wrong_extension(client):
    data = {'file': (io.BytesIO(b'fake'), 'track.exe')}
    resp = client.post('/api/upload-audio', data=data, content_type='multipart/form-data')
    assert resp.status_code == 400
    assert b'extension' in resp.data.lower()

def test_upload_audio_success(client, tmp_path, monkeypatch):
    import app as app_module
    monkeypatch.setattr(app_module, 'UPLOADS_DIR', tmp_path)
    data = {'file': (io.BytesIO(b'\xff\xfb\x90\x00'), 'song.mp3')}
    resp = client.post('/api/upload-audio', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    body = resp.get_json()
    assert 'path' in body
    assert body['path'].startswith('uploads/')
    assert body['path'].endswith('.mp3')
```

- [ ] **Step 2: Run to verify it fails**

```
cd D:\Code\autoclipper
pytest tests/test_upload_audio.py -v
```

Expected: ImportError or 404 (route not defined yet).

- [ ] **Step 3: Add `UPLOADS_DIR` and the route to `app.py`**

After the `EXPORTS_DIR` line (line 13 of `app.py`), add:

```python
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
```

After the `@app.get("/api/exports/<filename>")` route (end of file, before `if __name__`), add:

```python
ALLOWED_AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}

@app.post("/api/upload-audio")
def upload_audio():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "file required"}), 400
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
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_upload_audio.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_upload_audio.py
git commit -m "feat: add POST /api/upload-audio and GET /api/uploads/<filename> routes"
```

---

## Task 2: Backend — video layer volume/mute in exporter

**Files:**
- Modify: `exporter.py`
- Modify: `tests/test_exporter.py`

The current `export_video` always uses `-map 0:a?`. We need to optionally apply a `volume` filter when a video layer has `volume != 1.0` or `muted == true`. We also need to wire it into a potential `amix` later (Task 3). The cleanest approach is a new helper `build_audio_cmd_parts()` that returns the extra filter strings and the audio output label.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_exporter.py`:

```python
from exporter import build_audio_cmd_parts

def test_audio_passthrough_when_no_changes():
    """No audio layer, default volume → no filter, passthrough label."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": False}]
    audio_layer = None
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert extra_inputs == []
    assert filter_parts == []
    assert audio_label == "0:a"   # plain passthrough

def test_audio_volume_filter():
    """Video layer with volume=0.5 → volume filter applied."""
    video_layers = [{"type": "video", "volume": 0.5, "muted": False}]
    audio_layer = None
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert any("volume=0.5" in p for p in filter_parts)
    assert audio_label != "0:a"

def test_audio_muted():
    """Muted video layer → volume=0 filter."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": True}]
    audio_layer = None
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert any("volume=0" in p for p in filter_parts)
```

- [ ] **Step 2: Run to verify they fail**

```
pytest tests/test_exporter.py::test_audio_passthrough_when_no_changes tests/test_exporter.py::test_audio_volume_filter tests/test_exporter.py::test_audio_muted -v
```

Expected: ImportError (function not defined yet).

- [ ] **Step 3: Add `build_audio_cmd_parts` to `exporter.py`**

Add this function after `build_filter_graph` (before `export_video`):

```python
def build_audio_cmd_parts(
    layers: list,
    audio_layer: dict | None,
    next_input_idx: int,
) -> tuple[list, list, str]:
    """
    Build FFmpeg audio filter parts for video layer volume/mute and an optional
    audio layer (music track).

    Returns:
        extra_inputs  – additional file paths to pass as -i arguments
        filter_parts  – filter_complex fragment strings (no semicolons)
        audio_label   – the label/stream to use for -map audio output,
                        e.g. "0:a", "va1", or "aout"
    """
    extra_inputs = []
    filter_parts = []
    n = [0]

    def albl():
        n[0] += 1
        return f"a{n[0]}"

    # ── Step 1: Video audio volume/mute ──────────────────────────────────────
    # Find the first video layer with non-default audio settings.
    video_vol = 1.0
    video_muted = False
    for l in layers:
        if l.get("type") == "video":
            video_vol = float(l.get("volume", 1.0))
            video_muted = bool(l.get("muted", False))
            break

    effective_vol = 0.0 if video_muted else video_vol
    if effective_vol != 1.0:
        out = albl()
        filter_parts.append(f"[0:a]volume={effective_vol}[{out}]")
        vid_audio_label = out
    else:
        vid_audio_label = "0:a"

    # ── Step 2: Audio layer (music track) ───────────────────────────────────
    if audio_layer is None:
        return extra_inputs, filter_parts, vid_audio_label

    src = audio_layer.get("src", "")
    music_vol = float(audio_layer.get("volume", 1.0))
    loop = bool(audio_layer.get("loop", False))
    trim_start = float(audio_layer.get("trim_start", 0.0))
    trim_end = audio_layer.get("trim_end")  # None means full duration

    music_input_idx = next_input_idx + len(extra_inputs)
    extra_inputs.append(src)

    raw_music = f"{music_input_idx}:a"
    cur = albl()

    # Apply trim (seek on input side via -ss/-to is handled in export_video;
    # here we apply atrim inside filter_complex for the looping case)
    if loop:
        looped = albl()
        filter_parts.append(
            f"[{raw_music}]aloop=loop=-1:size=2147483647[{looped}]"
        )
        cur_label = looped
    else:
        cur_label = raw_music

    # Volume on music track
    if music_vol != 1.0:
        volout = albl()
        filter_parts.append(f"[{cur_label}]volume={music_vol}[{volout}]")
        cur_label = volout

    # Mix with video audio
    mixed = albl()
    filter_parts.append(
        f"[{vid_audio_label}][{cur_label}]"
        f"amix=inputs=2:duration=first:dropout_transition=0[{mixed}]"
    )

    return extra_inputs, filter_parts, mixed
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_exporter.py::test_audio_passthrough_when_no_changes tests/test_exporter.py::test_audio_volume_filter tests/test_exporter.py::test_audio_muted -v
```

Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add exporter.py tests/test_exporter.py
git commit -m "feat: add build_audio_cmd_parts for video volume/mute and audio layer mixing"
```

---

## Task 3: Backend — wire audio into export_video

**Files:**
- Modify: `exporter.py`
- Modify: `tests/test_exporter.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_exporter.py`:

```python
from exporter import build_audio_cmd_parts

def test_audio_layer_amix():
    """Audio layer present → amix filter included, extra input returned."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": False}]
    audio_layer = {
        "type": "audio",
        "src": "uploads/fake.mp3",
        "volume": 1.0,
        "loop": False,
        "trim_start": 0.0,
        "trim_end": None,
    }
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert "uploads/fake.mp3" in extra_inputs
    assert any("amix" in p for p in filter_parts)
    assert audio_label != "0:a"

def test_audio_layer_loop():
    """Loop flag → aloop filter present."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": False}]
    audio_layer = {
        "type": "audio",
        "src": "uploads/fake.mp3",
        "volume": 1.0,
        "loop": True,
        "trim_start": 0.0,
        "trim_end": None,
    }
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert any("aloop" in p for p in filter_parts)

def test_audio_layer_volume():
    """Music track volume applied."""
    video_layers = [{"type": "video", "volume": 1.0, "muted": False}]
    audio_layer = {
        "type": "audio",
        "src": "uploads/fake.mp3",
        "volume": 0.4,
        "loop": False,
        "trim_start": 0.0,
        "trim_end": None,
    }
    extra_inputs, filter_parts, audio_label = build_audio_cmd_parts(
        video_layers, audio_layer, next_input_idx=1
    )
    assert any("volume=0.4" in p for p in filter_parts)
```

- [ ] **Step 2: Run to verify they fail**

```
pytest tests/test_exporter.py::test_audio_layer_amix tests/test_exporter.py::test_audio_layer_loop tests/test_exporter.py::test_audio_layer_volume -v
```

Expected: FAIL (ImportError or assertion errors before the function is wired).

- [ ] **Step 3: Verify tests pass now** (they should — `build_audio_cmd_parts` is already implemented)

```
pytest tests/test_exporter.py::test_audio_layer_amix tests/test_exporter.py::test_audio_layer_loop tests/test_exporter.py::test_audio_layer_volume -v
```

Expected: all 3 PASS (the function from Task 2 already handles this).

- [ ] **Step 4: Update `export_video` to call `build_audio_cmd_parts`**

In `exporter.py`, replace the `export_video` function. The key changes are:
1. Extract the `audio` layer from `layers` (if present) before building the filter graph
2. Strip the `audio` layer from the layers list passed to `build_filter_graph` (it's not a video layer)
3. Call `build_audio_cmd_parts` and incorporate its results into the FFmpeg command
4. Use `-ss`/`-to` on the audio input when trim_start > 0 or trim_end is not None

Replace the full `export_video` function with:

```python
def export_video(video_path: str, template: dict, title: str = "",
                 on_progress=None) -> str:
    """Build and run the FFmpeg command. Returns output file path."""
    job_id = uuid.uuid4().hex[:8]
    all_layers = [dict(l) for l in template["layers"]]
    cw = template["canvas"]["width"]
    ch = template["canvas"]["height"]

    for l in all_layers:
        if l["type"] == "text":
            l["text"] = l.get("text", "").replace("{title}", title)

    # Separate audio layer (not a canvas/video layer)
    audio_layer = next((l for l in all_layers if l["type"] == "audio"), None)
    layers = [l for l in all_layers if l["type"] != "audio"]

    extra_inputs, text_pngs, image_inputs = [], {}, {}
    for i, l in enumerate(layers):
        if l["type"] == "text":
            p = str(TEMP_DIR / f"{job_id}_t{i}.png")
            render_text_layer(l, cw, ch, p)
            text_pngs[i] = len(extra_inputs) + 1
            extra_inputs.append(p)
        elif l["type"] == "image" and os.path.exists(l.get("src", "")):
            image_inputs[i] = len(extra_inputs) + 1
            extra_inputs.append(l["src"])

    filter_parts, final_video = build_filter_graph(layers, cw, ch, text_pngs, image_inputs)

    # next free input index = 1 (video) + len(extra_inputs)
    audio_extra, audio_filter_parts, audio_label = build_audio_cmd_parts(
        layers, audio_layer, next_input_idx=1 + len(extra_inputs)
    )

    out_path = str(EXPORTS_DIR / f"{job_id}.mp4")

    cmd = ["ffmpeg", "-y", "-i", video_path]
    for inp in extra_inputs:
        cmd += ["-i", inp]

    # Audio layer input: apply seek/trim at input level when not looping
    if audio_layer and audio_extra:
        src = audio_layer.get("src", "")
        trim_start = float(audio_layer.get("trim_start", 0.0))
        trim_end = audio_layer.get("trim_end")
        loop = bool(audio_layer.get("loop", False))
        if not loop and (trim_start > 0 or trim_end is not None):
            if trim_start > 0:
                cmd += ["-ss", str(trim_start)]
            if trim_end is not None:
                cmd += ["-to", str(trim_end)]
        cmd += ["-i", src]

    all_filter_parts = filter_parts + audio_filter_parts
    if all_filter_parts:
        cmd += ["-filter_complex", ";".join(all_filter_parts), "-map", f"[{final_video}]"]
    else:
        cmd += ["-map", "0:v"]

    if audio_label == "0:a":
        cmd += ["-map", "0:a?"]
    else:
        cmd += ["-map", f"[{audio_label}]"]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        out_path,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    stderr_lines = []
    for line in proc.stderr:
        line = line.rstrip()
        stderr_lines.append(line)
        if on_progress:
            on_progress(line)
    proc.wait()
    if proc.returncode != 0:
        code = proc.returncode
        if code > 2**31 - 1:
            code -= 2**32
        last_err = "\n".join(stderr_lines[-30:]) or str(proc.returncode)
        raise RuntimeError(f"FFmpeg exited {code}:\n{last_err}")

    for p in extra_inputs:
        if "temp" in p:
            try:
                os.remove(p)
            except OSError:
                pass

    return out_path
```

- [ ] **Step 5: Run the full test suite**

```
pytest tests/test_exporter.py -v
```

Expected: all tests PASS (existing tests + new audio tests).

- [ ] **Step 6: Commit**

```bash
git add exporter.py tests/test_exporter.py
git commit -m "feat: wire build_audio_cmd_parts into export_video for audio layer + volume support"
```

---

## Task 4: Frontend — audio layer state + serialisation

**Files:**
- Modify: `frontend/index.html`

The audio layer is **not** a Fabric.js canvas object. It's stored in a module-level variable `audioLayer` (null when absent). We need to:
1. Declare `audioLayer` in the STATE block
2. Update `canvasToTemplate()` to append the audio layer to the layers array
3. Update `applySavedTpl()` to extract and restore the audio layer

- [ ] **Step 1: Declare `audioLayer` in STATE block**

In `frontend/index.html`, find the STATE block (around line 498):

```javascript
let downloadedVideoPath=null, downloadedVideoURL=null;
```

Add immediately after:

```javascript
let audioLayer=null; // {type:'audio',src,volume,loop,trim_start,trim_end}
```

- [ ] **Step 2: Update `canvasToTemplate()` to include audio layer**

Find in `canvasToTemplate()` (around line 1388):

```javascript
  return{name:document.getElementById('proj-name-input').value||'My Template',format:fmt,canvas:{width:1080,height:fmt==='9:16'?1920:1080},layers};
```

Replace with:

```javascript
  const allLayers = audioLayer ? [...layers, {...audioLayer}] : layers;
  return{name:document.getElementById('proj-name-input').value||'My Template',format:fmt,canvas:{width:1080,height:fmt==='9:16'?1920:1080},layers:allLayers};
```

- [ ] **Step 3: Update `applySavedTpl()` to restore audio layer**

In `applySavedTpl()`, find the loop `for(const layer of(tpl.layers||[])){` (around line 1421).

Add this block right before the for loop:

```javascript
  // Restore audio layer (not a canvas object)
  audioLayer = (tpl.layers||[]).find(l=>l.type==='audio') || null;
```

- [ ] **Step 4: Add helper `getAudioLayer()` and `setAudioLayer()`**

After the `audioLayer` variable declaration, add:

```javascript
function getAudioLayer(){ return audioLayer; }
function setAudioLayer(data){ audioLayer=data; syncLayers(); updatePreviewStrip(); }
function removeAudioLayer(){ audioLayer=null; syncLayers(); updatePreviewStrip(); }
```

(We'll implement `updatePreviewStrip` in Task 9 — add a stub for now so it doesn't crash):

```javascript
function updatePreviewStrip(){ /* implemented in Task 9 */ }
```

- [ ] **Step 5: Manual smoke test**

Start the dev server (`python app.py`), open `http://localhost:5000`, load a template, and verify the page loads without JS errors. No visible change yet.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add audioLayer state variable and wire into canvasToTemplate/applySavedTpl"
```

---

## Task 5: Frontend — layers panel audio row + Add Audio button

**Files:**
- Modify: `frontend/index.html`

`syncLayers()` currently only renders canvas objects. We'll extend it to:
1. Render an audio layer row when `audioLayer !== null`
2. Render an "Add Audio" button (hidden if audio layer already exists)

- [ ] **Step 1: Add CSS for audio layer row**

Find the existing `.lrow` CSS (it'll be in the `<style>` block near the top of `index.html`). After the `.lrow` block, add:

```css
.lrow-audio{display:flex;align-items:center;gap:6px;padding:7px 8px;border-radius:6px;background:var(--card);cursor:pointer;border:1px solid var(--b1);margin-bottom:2px}
.lrow-audio.on{border-color:var(--acc);background:var(--sel)}
.lrow-audio .lname{flex:1;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lrow-audio .ledit{font-size:10px;color:var(--acc);background:var(--b2);padding:2px 7px;border-radius:4px;border:none;cursor:pointer;flex-shrink:0}
#add-audio-btn{display:flex;align-items:center;justify-content:center;gap:6px;padding:8px;border-radius:6px;border:1px dashed var(--b1);color:var(--sub);font-size:12px;cursor:pointer;margin-top:6px;background:none;width:100%}
#add-audio-btn:hover{border-color:var(--acc);color:var(--acc)}
```

- [ ] **Step 2: Add the "Add Audio" button HTML in the layers panel**

Find in the HTML (around line 363):

```html
          <div class="lp-sect">Layers</div>
          <div id="layer-list"></div>
```

Replace with:

```html
          <div class="lp-sect">Layers</div>
          <div id="layer-list"></div>
          <div id="audio-layer-row" style="display:none"></div>
          <button id="add-audio-btn" onclick="triggerAudioUpload()">🎵 Add Audio</button>
          <input type="file" id="audio-pick" accept=".mp3,.wav,.ogg,.m4a,.aac" style="display:none" onchange="onAudioFile(event)">
```

- [ ] **Step 3: Update `syncLayers()` to render audio row and toggle Add Audio button**

Find `syncLayers()` (around line 1078). At the very end of the function, after `list.appendChild(row)` loop closes, add:

```javascript
  // Audio layer row
  const audioRowEl = document.getElementById('audio-layer-row');
  const addAudioBtn = document.getElementById('add-audio-btn');
  if (audioLayer) {
    const fname = audioLayer.src.split('/').pop();
    audioRowEl.style.display = '';
    audioRowEl.innerHTML = `<div class="lrow-audio" id="audio-lrow-inner">
      <span style="font-size:14px">🎵</span>
      <span class="lname" title="${fname}">${fname}</span>
      <button class="ledit" onclick="openTrimmerModal()">Edit ✂️</button>
      <span class="leye" onclick="removeAudioLayer()" title="Remove" style="cursor:pointer;font-size:14px;color:var(--sub)">🗑️</span>
    </div>`;
    addAudioBtn.style.display = 'none';
  } else {
    audioRowEl.style.display = 'none';
    audioRowEl.innerHTML = '';
    addAudioBtn.style.display = '';
  }
```

- [ ] **Step 4: Add `triggerAudioUpload()` and `onAudioFile()` functions**

After `syncLayers()`, add:

```javascript
function triggerAudioUpload(){
  document.getElementById('audio-pick').click();
}

async function onAudioFile(e){
  const file = e.target.files[0];
  if(!file) return;
  const fd = new FormData();
  fd.append('file', file);
  try {
    const resp = await fetch('/api/upload-audio', {method:'POST', body:fd});
    const data = await resp.json();
    if(!resp.ok) { alert(data.error||'Upload failed'); return; }
    setAudioLayer({
      type: 'audio',
      src: data.path,
      volume: 1.0,
      loop: false,
      trim_start: 0.0,
      trim_end: null,
    });
    saveHist();
  } catch(err) {
    alert('Upload failed: ' + err.message);
  }
  // Reset the file input so the same file can be re-selected
  e.target.value = '';
}
```

- [ ] **Step 5: Manual test**

Start the server, open the editor, click "Add Audio", upload an `.mp3`. Verify the audio layer row appears, the "Add Audio" button hides, and the 🗑️ button removes the layer.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add audio layer row and Add Audio button to layers panel"
```

---

## Task 6: Frontend — video layer Audio section in properties panel

**Files:**
- Modify: `frontend/index.html`

When a `video` type layer is selected, `updateProps()` appends a Video Layer section. We extend it to also show an Audio section.

- [ ] **Step 1: Find the video props block in `updateProps()`**

Around line 1165 in `index.html`:

```javascript
  if(type==='video'){
    const fit=obj._fit||'contain';
    html+=`<div class="psec">...Video Layer...</div>`;
  }
```

- [ ] **Step 2: Append the Audio section inside the `if(type==='video')` block**

Replace the existing `if(type==='video'){...}` block with:

```javascript
  if(type==='video'){
    const fit=obj._fit||'contain';
    html+=`<div class="psec"><div class="psec-title"><svg class="psec-title-icon film-path" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="12" height="12"><path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"/></svg>Video Layer</div>
    <div class="prow"><span class="plbl">Fit</span>
      <div class="tog">
        <button class="togbtn ${fit==='contain'?'on':''}" onclick="togOn(this);cv.getActiveObject()._fit='contain'">Contain</button>
        <button class="togbtn ${fit==='cover'?'on':''}"   onclick="togOn(this);cv.getActiveObject()._fit='cover'">Cover</button>
        <button class="togbtn ${fit==='fill'?'on':''}"    onclick="togOn(this);cv.getActiveObject()._fit='fill'">Fill</button>
      </div>
    </div></div>`;

    // ── Audio section ────────────────────────────────────────────────────────
    const volPct = Math.round((obj._audioVolume??1)*100);
    const isMuted = obj._audioMuted===true;
    html+=`<div class="psec">
      <div class="psec-title">🔊 Audio</div>
      <div class="prow">
        <span class="plbl">Volume</span>
        <div class="slrow" style="gap:6px">
          <button class="togbtn${isMuted?' on':''}" style="padding:2px 8px;font-size:16px" title="${isMuted?'Unmute':'Mute'}"
            onclick="toggleVideoMute(this)">
            ${isMuted?'🔇':'🔊'}
          </button>
          <input type="range" class="psl" min="0" max="100" value="${isMuted?0:volPct}" ${isMuted?'disabled':''}
            oninput="setVideoVolume(this.value);this.nextElementSibling.textContent=this.value+'%'">
          <span class="slv">${isMuted?'0':volPct}%</span>
        </div>
      </div>
    </div>`;
  }
```

- [ ] **Step 3: Add `toggleVideoMute()` and `setVideoVolume()` functions**

After `updateProps()`, add:

```javascript
function toggleVideoMute(btn){
  const obj = cv.getActiveObject();
  if(!obj) return;
  obj._audioMuted = !obj._audioMuted;
  btn.textContent = obj._audioMuted ? '🔇' : '🔊';
  btn.classList.toggle('on', obj._audioMuted);
  const slider = btn.nextElementSibling;
  const lbl = slider.nextElementSibling;
  slider.disabled = obj._audioMuted;
  lbl.textContent = obj._audioMuted ? '0%' : Math.round((obj._audioVolume??1)*100)+'%';
  saveHist();
}

function setVideoVolume(val){
  const obj = cv.getActiveObject();
  if(!obj) return;
  obj._audioVolume = val/100;
  saveHist();
}
```

- [ ] **Step 4: Update `canvasToTemplate()` video layer serialisation**

Find in `canvasToTemplate()`:

```javascript
    if(t==='video')return{...base,fit:obj._fit||'contain'};
```

Replace with:

```javascript
    if(t==='video')return{...base,fit:obj._fit||'contain',
      volume:obj._audioVolume??1.0,
      muted:obj._audioMuted===true};
```

- [ ] **Step 5: Update `applySavedTpl()` video layer restore**

Find in `applySavedTpl()`:

```javascript
    } else if(layer.type==='video'){
```

After the `const img=new fabric.Image(...)` / `fabric.Group` creation and before `cv.add(...)`, ensure the layer's volume/muted are set. Find the fabric.Image creation for video layers (around line 1432–1442) and add `_audioVolume` and `_audioMuted` to the image/group `set()` call. The pattern is:

```javascript
        const img=new fabric.Image(vc2,{left:lx,top:ly,objectCaching:false,_type:'video',_label:'Video Layer',_fit:layer.fit||'contain',opacity:op});
```

Replace with:

```javascript
        const img=new fabric.Image(vc2,{left:lx,top:ly,objectCaching:false,_type:'video',_label:'Video Layer',_fit:layer.fit||'contain',opacity:op,_audioVolume:layer.volume??1.0,_audioMuted:layer.muted===true});
```

And for the Group fallback a few lines later:

```javascript
        cv.add(new fabric.Group([r,t2],{_type:'video',_label:'Video Layer',_fit:layer.fit||'contain'}));
```

Replace with:

```javascript
        cv.add(new fabric.Group([r,t2],{_type:'video',_label:'Video Layer',_fit:layer.fit||'contain',_audioVolume:layer.volume??1.0,_audioMuted:layer.muted===true}));
```

- [ ] **Step 6: Manual test**

Select a video layer → verify the Audio section appears with a 🔊 mute toggle and volume slider. Toggle mute, adjust volume. Save template, reload, confirm values are preserved.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add Audio section (volume/mute) to video layer properties panel"
```

---

## Task 7: Frontend — audio layer properties panel

**Files:**
- Modify: `frontend/index.html`

When the user clicks the audio layer row, we need to show its properties in the right panel. Since audio layers are not Fabric.js objects, we handle this differently — clicking the row calls a dedicated function.

- [ ] **Step 1: Add `showAudioLayerProps()` function**

After `updateProps()`, add:

```javascript
function showAudioLayerProps(){
  if(!audioLayer) return;
  document.getElementById('del-btn').style.display='';
  const volPct = Math.round((audioLayer.volume??1)*100);
  const loop = audioLayer.loop===true;
  document.getElementById('right').innerHTML=`
    <div class="psec">
      <div class="psec-title">🎵 Audio Layer</div>
      <div class="prow"><span class="plbl">File</span>
        <span style="font-size:11px;color:var(--sub);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${audioLayer.src.split('/').pop()}</span>
      </div>
      <div class="prow"><span class="plbl">Volume</span>
        <div class="slrow">
          <input type="range" class="psl" min="0" max="100" value="${volPct}"
            oninput="audioLayer.volume=this.value/100;this.nextElementSibling.textContent=this.value+'%';saveHist()">
          <span class="slv">${volPct}%</span>
        </div>
      </div>
      <div class="prow"><span class="plbl">End</span>
        <div class="tog">
          <button class="togbtn${!loop?' on':''}" onclick="setAudioLoop(false,this)">Trim</button>
          <button class="togbtn${loop?' on':''}"  onclick="setAudioLoop(true,this)">Loop</button>
        </div>
      </div>
      <div class="prow">
        <button class="btn btn-ghost" style="width:100%;margin-top:4px" onclick="openTrimmerModal()">✂️ Edit Trim / Preview…</button>
      </div>
    </div>`;
}

function setAudioLoop(val, btn){
  if(!audioLayer) return;
  audioLayer.loop = val;
  togOn(btn);
  saveHist();
}
```

- [ ] **Step 2: Wire click on the audio layer row to `showAudioLayerProps()`**

In Task 5 Step 3, the audio row innerHTML has `<div class="lrow-audio" id="audio-lrow-inner">`. Update that innerHTML to add an onclick:

```javascript
    audioRowEl.innerHTML = `<div class="lrow-audio" id="audio-lrow-inner" onclick="showAudioLayerProps()">
      <span style="font-size:14px">🎵</span>
      <span class="lname" title="${fname}">${fname}</span>
      <button class="ledit" onclick="event.stopPropagation();openTrimmerModal()">Edit ✂️</button>
      <span class="leye" onclick="event.stopPropagation();removeAudioLayer()" title="Remove" style="cursor:pointer;font-size:14px;color:var(--sub)">🗑️</span>
    </div>`;
```

- [ ] **Step 3: Make "Delete" button work for audio layer**

Find the `delSel()` function (around line 1062):

```javascript
function delSel(){
  const o=cv?.getActiveObject();if(!o)return;
```

Update to:

```javascript
function delSel(){
  // Check if audio layer props are showing (no canvas selection)
  if(!cv?.getActiveObject() && audioLayer){
    removeAudioLayer();
    clearProps();
    return;
  }
  const o=cv?.getActiveObject();if(!o)return;
```

- [ ] **Step 4: Manual test**

Upload an audio file, click the audio row → the right panel should show the audio properties with a volume slider, Trim/Loop toggle, and "Edit Trim" button.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add audio layer properties panel"
```

---

## Task 8: Frontend — audio trimmer modal

**Files:**
- Modify: `frontend/index.html`

This is the waveform + drag-handles modal that opens on "Edit ✂️".

- [ ] **Step 1: Add CSS for the trimmer modal**

In the `<style>` block, add:

```css
#trimmer-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;align-items:center;justify-content:center}
#trimmer-modal.open{display:flex}
.trimmer-box{background:var(--card);border-radius:12px;padding:20px;width:560px;max-width:95vw;display:flex;flex-direction:column;gap:12px}
.trimmer-header{display:flex;align-items:center;gap:10px}
.trimmer-filename{flex:1;font-size:12px;color:var(--sub);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.trimmer-time{color:var(--sub);font-size:11px}
#trimmer-canvas{width:100%;height:64px;border-radius:6px;background:var(--b2);cursor:crosshair;display:block}
.trimmer-labels{display:flex;gap:16px;font-size:11px;color:var(--sub)}
.trimmer-labels span{color:var(--acc)}
.trimmer-loop-row{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--sub)}
.trimmer-loop-row .tog{margin-left:auto}
.trimmer-actions{display:flex;justify-content:flex-end;gap:8px}
```

- [ ] **Step 2: Add trimmer modal HTML**

After the Export modal closing `</div>` (around line 474), add:

```html
<!-- AUDIO TRIMMER MODAL -->
<div id="trimmer-modal">
  <div class="trimmer-box">
    <div class="trimmer-header">
      <button class="btn btn-ghost" id="trimmer-play-btn" onclick="trimmerTogglePlay()" style="padding:5px 12px">▶ Play</button>
      <span class="trimmer-filename" id="trimmer-filename">track.mp3</span>
      <span class="trimmer-time" id="trimmer-time">0:00 / 0:00</span>
    </div>
    <canvas id="trimmer-canvas"></canvas>
    <div class="trimmer-labels">
      Start: <span id="trimmer-start-lbl">0:00</span>
      &nbsp;&nbsp;End: <span id="trimmer-end-lbl">—</span>
    </div>
    <div class="trimmer-loop-row">
      <span>When video ends:</span>
      <div class="tog trimmer-loop-row">
        <button class="togbtn on" id="trimmer-trim-btn" onclick="trimmerSetLoop(false)">Trim</button>
        <button class="togbtn"    id="trimmer-loop-btn" onclick="trimmerSetLoop(true)">Loop</button>
      </div>
    </div>
    <div class="trimmer-actions">
      <button class="btn btn-ghost" onclick="closeTrimmerModal()">Cancel</button>
      <button class="btn btn-primary" onclick="applyTrimmer()">Apply</button>
    </div>
  </div>
</div>
<audio id="trimmer-audio" style="display:none"></audio>
```

- [ ] **Step 3: Add trimmer JS state and helpers**

After the `audioLayer` variable declaration, add:

```javascript
// Trimmer modal state
let _trimmerDraft = null; // working copy of audioLayer during edit
let _trimmerWaveform = null; // Float32Array of normalised peak data
let _trimmerDuration = 0;
let _trimmerDragging = null; // 'start' | 'end' | null
let _trimmerRAF = null;
```

- [ ] **Step 4: Add `openTrimmerModal()` function**

```javascript
async function openTrimmerModal(){
  if(!audioLayer) return;
  _trimmerDraft = {...audioLayer};
  document.getElementById('trimmer-modal').classList.add('open');
  document.getElementById('trimmer-filename').textContent = audioLayer.src.split('/').pop();

  const audioEl = document.getElementById('trimmer-audio');
  audioEl.src = '/api/' + audioLayer.src;
  audioEl.load();

  // Update loop toggle UI
  document.getElementById('trimmer-trim-btn').classList.toggle('on', !_trimmerDraft.loop);
  document.getElementById('trimmer-loop-btn').classList.toggle('on', _trimmerDraft.loop);

  // Decode waveform
  try {
    const resp = await fetch('/api/' + audioLayer.src);
    const buf = await resp.arrayBuffer();
    const ctx = new AudioContext();
    const decoded = await ctx.decodeAudioData(buf);
    _trimmerDuration = decoded.duration;
    const raw = decoded.getChannelData(0);
    const W = document.getElementById('trimmer-canvas').offsetWidth || 520;
    const samples = Math.floor(W);
    const blockSize = Math.floor(raw.length / samples);
    _trimmerWaveform = new Float32Array(samples);
    for(let i=0;i<samples;i++){
      let peak=0;
      const off=i*blockSize;
      for(let j=0;j<blockSize;j++) peak=Math.max(peak,Math.abs(raw[off+j]));
      _trimmerWaveform[i]=peak;
    }
    await ctx.close();
    drawTrimmerWaveform();
  } catch(e) {
    console.warn('Waveform decode failed', e);
  }

  audioEl.addEventListener('timeupdate', onTrimmerTimeUpdate);
  document.getElementById('trimmer-canvas').addEventListener('mousedown', onTrimmerMouseDown);
  document.addEventListener('mousemove', onTrimmerMouseMove);
  document.addEventListener('mouseup', onTrimmerMouseUp);
}

function closeTrimmerModal(){
  const audioEl = document.getElementById('trimmer-audio');
  audioEl.pause();
  audioEl.removeEventListener('timeupdate', onTrimmerTimeUpdate);
  document.getElementById('trimmer-canvas').removeEventListener('mousedown', onTrimmerMouseDown);
  document.removeEventListener('mousemove', onTrimmerMouseMove);
  document.removeEventListener('mouseup', onTrimmerMouseUp);
  if(_trimmerRAF){ cancelAnimationFrame(_trimmerRAF); _trimmerRAF=null; }
  document.getElementById('trimmer-modal').classList.remove('open');
  _trimmerDraft=null; _trimmerWaveform=null; _trimmerDuration=0;
}

function applyTrimmer(){
  if(!_trimmerDraft) return;
  setAudioLayer({...audioLayer, ..._trimmerDraft});
  showAudioLayerProps();
  closeTrimmerModal();
  saveHist();
}
```

- [ ] **Step 5: Add waveform draw + drag + playback functions**

```javascript
function fmtTime(s){
  if(!isFinite(s)||s<0) return '—';
  const m=Math.floor(s/60), sec=Math.floor(s%60);
  return `${m}:${sec.toString().padStart(2,'0')}`;
}

function drawTrimmerWaveform(){
  const canvas = document.getElementById('trimmer-canvas');
  const ctx2 = canvas.getContext('2d');
  const W = canvas.width = canvas.offsetWidth;
  const H = canvas.height = 64;
  ctx2.clearRect(0,0,W,H);

  if(!_trimmerWaveform) return;

  // Draw bars
  const barW = W / _trimmerWaveform.length;
  ctx2.fillStyle = 'rgba(167,139,250,0.35)';
  for(let i=0;i<_trimmerWaveform.length;i++){
    const bh = Math.max(2, _trimmerWaveform[i]*H);
    ctx2.fillRect(i*barW, (H-bh)/2, Math.max(1,barW-1), bh);
  }

  // Selection region
  const dur = _trimmerDuration||1;
  const s0 = (_trimmerDraft?.trim_start||0) / dur;
  const s1 = _trimmerDraft?.trim_end!=null ? _trimmerDraft.trim_end/dur : 1;
  ctx2.fillStyle = 'rgba(167,139,250,0.25)';
  ctx2.fillRect(s0*W, 0, (s1-s0)*W, H);
  // Left handle
  ctx2.fillStyle = '#a78bfa';
  ctx2.fillRect(s0*W-2, 0, 4, H);
  // Right handle
  ctx2.fillRect(s1*W-2, 0, 4, H);

  // Playhead
  const audioEl = document.getElementById('trimmer-audio');
  const pt = audioEl.currentTime / (dur||1);
  ctx2.fillStyle = '#ffffff';
  ctx2.fillRect(pt*W-1, 0, 2, H);

  // Labels
  document.getElementById('trimmer-start-lbl').textContent = fmtTime(_trimmerDraft?.trim_start||0);
  document.getElementById('trimmer-end-lbl').textContent = fmtTime(_trimmerDraft?.trim_end);
}

function onTrimmerTimeUpdate(){
  const audioEl = document.getElementById('trimmer-audio');
  const total = _trimmerDuration||audioEl.duration||0;
  document.getElementById('trimmer-time').textContent =
    fmtTime(audioEl.currentTime) + ' / ' + fmtTime(total);
  drawTrimmerWaveform();
}

function trimmerTogglePlay(){
  const audioEl = document.getElementById('trimmer-audio');
  const btn = document.getElementById('trimmer-play-btn');
  if(audioEl.paused){
    audioEl.currentTime = _trimmerDraft?.trim_start||0;
    audioEl.play();
    btn.textContent = '⏸ Pause';
    function raf(){ if(!audioEl.paused){ drawTrimmerWaveform(); _trimmerRAF=requestAnimationFrame(raf);} }
    _trimmerRAF = requestAnimationFrame(raf);
  } else {
    audioEl.pause();
    btn.textContent = '▶ Play';
    if(_trimmerRAF){ cancelAnimationFrame(_trimmerRAF); _trimmerRAF=null; }
  }
}

function trimmerSetLoop(val){
  if(!_trimmerDraft) return;
  _trimmerDraft.loop = val;
  document.getElementById('trimmer-trim-btn').classList.toggle('on', !val);
  document.getElementById('trimmer-loop-btn').classList.toggle('on', val);
}

function onTrimmerMouseDown(e){
  if(!_trimmerDraft||!_trimmerDuration) return;
  const canvas = document.getElementById('trimmer-canvas');
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) / rect.width;
  const dur = _trimmerDuration;
  const s0 = (_trimmerDraft.trim_start||0) / dur;
  const s1 = _trimmerDraft.trim_end!=null ? _trimmerDraft.trim_end/dur : 1;
  const tol = 0.015; // 1.5% tolerance for handle hit
  if(Math.abs(x-s0)<tol) _trimmerDragging='start';
  else if(Math.abs(x-s1)<tol) _trimmerDragging='end';
}

function onTrimmerMouseMove(e){
  if(!_trimmerDragging||!_trimmerDraft||!_trimmerDuration) return;
  const canvas = document.getElementById('trimmer-canvas');
  const rect = canvas.getBoundingClientRect();
  let x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  let t = Math.round(x * _trimmerDuration * 10) / 10; // snap to 0.1s
  if(_trimmerDragging==='start'){
    _trimmerDraft.trim_start = Math.min(t, (_trimmerDraft.trim_end??_trimmerDuration) - 0.1);
  } else {
    _trimmerDraft.trim_end = Math.max(t, (_trimmerDraft.trim_start||0) + 0.1);
    if(_trimmerDraft.trim_end >= _trimmerDuration - 0.05) _trimmerDraft.trim_end = null;
  }
  drawTrimmerWaveform();
}

function onTrimmerMouseUp(){ _trimmerDragging=null; }
```

- [ ] **Step 6: Manual test**

Upload an audio file → click "Edit ✂️" → modal opens with a waveform. Drag the left/right handles — Start/End labels update. Click Play — audio plays from `trim_start`. Click Apply — modal closes, values saved.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add audio trimmer modal with waveform, drag handles, and playback"
```

---

## Task 9: Frontend — preview audio strip

**Files:**
- Modify: `frontend/index.html`

A horizontal strip below the canvas showing a read-only mini waveform, a play/pause button that syncs the hidden `<video id="preview-video">` with a new `<audio id="strip-audio">` element, and preview-only volume/mute controls.

- [ ] **Step 1: Add CSS for the preview strip**

In the `<style>` block:

```css
#audio-strip{display:none;background:var(--card);border-top:1px solid var(--b1);padding:8px 14px;align-items:center;gap:10px}
#audio-strip.visible{display:flex}
#strip-canvas{flex:1;height:32px;border-radius:4px;background:var(--b2);display:block;min-width:0}
.strip-vol{display:flex;align-items:center;gap:6px;flex-shrink:0}
.strip-vol label{font-size:10px;color:var(--sub)}
#strip-vol-slider{width:70px;accent-color:var(--acc)}
```

- [ ] **Step 2: Add the strip HTML below the canvas area**

Find in `index.html` (around line 400):

```html
    </div>
    </div>

    <!-- RIGHT PANEL -->
```

Insert the strip between the canvas area closing tag and the RIGHT PANEL comment:

```html
    </div>
    </div>

    <!-- AUDIO PREVIEW STRIP -->
    <div id="audio-strip">
      <button class="tbar-btn" id="strip-play-btn" onclick="stripTogglePlay()" style="flex-shrink:0">▶</button>
      <canvas id="strip-canvas"></canvas>
      <div class="strip-vol">
        <button class="tbar-btn" id="strip-mute-btn" onclick="stripToggleMute()" style="font-size:14px">🔊</button>
        <input type="range" id="strip-vol-slider" min="0" max="100" value="80" oninput="stripSetVolume(this.value)">
        <label>preview only</label>
      </div>
    </div>

    <!-- RIGHT PANEL -->
```

- [ ] **Step 3: Add `<audio id="strip-audio">` element**

After the existing `<audio id="trimmer-audio">` element, add:

```html
<audio id="strip-audio" style="display:none"></audio>
```

- [ ] **Step 4: Add strip JS state**

After the trimmer state variables, add:

```javascript
// Preview strip state
let _stripVolume = 0.8;
let _stripMuted = false;
let _stripWaveform = null;
let _stripRAF = null;
```

- [ ] **Step 5: Implement `updatePreviewStrip()` (replace the stub from Task 4)**

Find and replace the stub `function updatePreviewStrip(){ /* implemented in Task 9 */ }` with:

```javascript
async function updatePreviewStrip(){
  const strip = document.getElementById('audio-strip');
  const stripAudio = document.getElementById('strip-audio');

  if(!audioLayer){
    strip.classList.remove('visible');
    stripAudio.src='';
    _stripWaveform=null;
    return;
  }

  strip.classList.add('visible');
  stripAudio.src = '/api/' + audioLayer.src;
  stripAudio.volume = _stripMuted ? 0 : _stripVolume;
  stripAudio.load();

  // Decode waveform for strip
  try {
    const resp = await fetch('/api/' + audioLayer.src);
    const buf = await resp.arrayBuffer();
    const ctx = new AudioContext();
    const decoded = await ctx.decodeAudioData(buf);
    const raw = decoded.getChannelData(0);
    const W = document.getElementById('strip-canvas').offsetWidth || 400;
    const samples = Math.floor(W);
    const blockSize = Math.floor(raw.length / samples);
    _stripWaveform = new Float32Array(samples);
    for(let i=0;i<samples;i++){
      let peak=0;
      const off=i*blockSize;
      for(let j=0;j<blockSize;j++) peak=Math.max(peak,Math.abs(raw[off+j]));
      _stripWaveform[i]=peak;
    }
    await ctx.close();
    drawStripWaveform();
  } catch(e) {
    console.warn('Strip waveform decode failed', e);
  }
}

function drawStripWaveform(){
  const canvas = document.getElementById('strip-canvas');
  if(!canvas) return;
  const ctx2 = canvas.getContext('2d');
  const W = canvas.width = canvas.offsetWidth;
  const H = canvas.height = 32;
  ctx2.clearRect(0,0,W,H);

  if(_stripWaveform){
    const barW = W / _stripWaveform.length;
    ctx2.fillStyle = 'rgba(167,139,250,0.4)';
    for(let i=0;i<_stripWaveform.length;i++){
      const bh = Math.max(2, _stripWaveform[i]*H);
      ctx2.fillRect(i*barW, (H-bh)/2, Math.max(1,barW-1), bh);
    }
  }

  // Playhead
  const stripAudio = document.getElementById('strip-audio');
  const dur = stripAudio.duration||1;
  const pt = (stripAudio.currentTime||0)/dur;
  if(isFinite(pt)){
    ctx2.fillStyle='#ffffff';
    ctx2.fillRect(pt*W-1,0,2,H);
  }
}
```

- [ ] **Step 6: Add strip playback controls**

```javascript
function stripTogglePlay(){
  const vidEl = document.getElementById('preview-video');
  const stripAudio = document.getElementById('strip-audio');
  const btn = document.getElementById('strip-play-btn');

  if(!audioLayer || !downloadedVideoURL) return;

  if(vidEl.paused){
    vidEl.play().catch(()=>{});
    stripAudio.currentTime = vidEl.currentTime;
    stripAudio.play().catch(()=>{});
    btn.textContent='⏸';
    function raf(){ drawStripWaveform(); _stripRAF=requestAnimationFrame(raf); }
    _stripRAF=requestAnimationFrame(raf);
  } else {
    vidEl.pause();
    stripAudio.pause();
    btn.textContent='▶';
    if(_stripRAF){ cancelAnimationFrame(_stripRAF); _stripRAF=null; }
  }
}

function stripToggleMute(){
  _stripMuted = !_stripMuted;
  const stripAudio = document.getElementById('strip-audio');
  const btn = document.getElementById('strip-mute-btn');
  stripAudio.volume = _stripMuted ? 0 : _stripVolume;
  btn.textContent = _stripMuted ? '🔇' : '🔊';
}

function stripSetVolume(val){
  _stripVolume = val/100;
  const stripAudio = document.getElementById('strip-audio');
  if(!_stripMuted) stripAudio.volume = _stripVolume;
}
```

- [ ] **Step 7: Sync strip audio to video `timeupdate`**

Find the `refreshVideoLayers` function (around line 946) and add after it:

```javascript
// Keep strip audio in sync with video
document.getElementById('preview-video').addEventListener('timeupdate', ()=>{
  const vidEl = document.getElementById('preview-video');
  const stripAudio = document.getElementById('strip-audio');
  if(!stripAudio.src || !audioLayer) return;
  if(Math.abs(stripAudio.currentTime - vidEl.currentTime) > 0.3){
    stripAudio.currentTime = vidEl.currentTime;
  }
});
```

- [ ] **Step 8: Manual test**

Upload an audio file. The strip should appear below the canvas. Click ▶ — both the video preview and audio should play in sync. Adjust the preview volume slider — audio volume changes without affecting export settings. Click 🔊 to mute — audio mutes but video keeps playing.

- [ ] **Step 9: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add preview audio strip with mini waveform, synced playback, and preview-only volume"
```

---

## Task 10: Integration smoke test

**Goal:** Verify the full round-trip: upload audio → set volume/trim → export → output has mixed audio.

- [ ] **Step 1: Start the server**

```
cd D:\Code\autoclipper
python app.py
```

Open `http://localhost:5000`.

- [ ] **Step 2: Download a test video**

Use the Download modal to download a short video (e.g., a 10-second Twitter clip).

- [ ] **Step 3: Upload audio and configure**

Click "Add Audio", upload an `.mp3`. Open the trimmer, set a trim region, click Apply. Set the audio volume to 50%.

- [ ] **Step 4: Set video layer volume**

Select the Video Layer. In the Audio section of the properties panel, drag the volume slider to 80%.

- [ ] **Step 5: Export and verify**

Click Export, wait for completion, download the output. Open in a media player and verify:
- The video audio is audible (at ~80% of original)
- The music track is audible mixed on top (at 50%)
- The music plays only within the trim region if trim was set

- [ ] **Step 6: Run full test suite**

```
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 7: Final commit**

```bash
git add .
git commit -m "feat: complete audio features — volume/mute, audio layer, trimmer, preview strip"
```

---

## Self-Review Notes

- **Spec coverage:** All 4 features covered: ✅ video volume/mute (Tasks 2+6), ✅ audio layer type (Tasks 1+4+5+7), ✅ trimmer modal (Task 8), ✅ preview strip (Task 9).
- **Export fallback:** Task 3 Step 4 preserves the existing `-map 0:a?` passthrough when no audio changes are needed.
- **No-audio-track video:** `build_audio_cmd_parts` returns `audio_label = "0:a"` for passthrough; if the source video has no audio track, FFmpeg's `0:a?` (optional) silently omits it — the music-only path is handled by mapping `[aout]` directly.
- **`audioLayer` not a canvas object:** Confirmed — stored separately, appended in `canvasToTemplate`, extracted in `applySavedTpl`.
- **Preview volume isolation:** `_stripVolume` / `_stripMuted` are JS variables only, never written to `audioLayer` or template JSON.
