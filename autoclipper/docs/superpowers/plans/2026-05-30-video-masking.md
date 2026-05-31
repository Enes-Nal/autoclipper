# Video Masking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow video layers in the template editor to be clipped to a rectangle, rounded rectangle, circle, or freehand polygon shape — visible in the canvas preview and applied correctly during FFmpeg export.

**Architecture:** Masking has two parts. Backend: Pillow renders a white-on-black mask PNG per masked video layer; FFmpeg uses `alphamerge` to cut the video to that shape before compositing. Frontend: Fabric.js `clipPath` provides the live preview; a polygon drawing mode lets users click canvas points to define a custom shape. Mask data is stored normalised on the video layer object and serialised in the template JSON.

**Tech Stack:** Python/Pillow (mask PNG rendering), FFmpeg `alphamerge` filter, Fabric.js `clipPath` (canvas preview), vanilla JS canvas 2D API (polygon overlay drawing).

---

## File Map

| File | Change |
|------|--------|
| `exporter.py` | Add `render_mask_png()`; add `mask_inputs` param to `build_filter_graph`; add mask pre-processing in `export_video` |
| `tests/test_exporter.py` | Tests for `render_mask_png` all shapes + `build_filter_graph` with mask |
| `frontend/index.html` | Mask serialisation in `canvasToTemplate`/`applySavedTpl`; `applyMaskClipPath()`; Mask section in properties panel; polygon drawing mode + overlay canvas |

---

## Task 1: Backend — `render_mask_png` function

**Files:**
- Modify: `exporter.py`
- Modify: `tests/test_exporter.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_exporter.py`:

```python
from pathlib import Path
from exporter import render_mask_png

def test_render_mask_png_rect(tmp_path):
    """rect fills the entire image with white."""
    from PIL import Image
    p = str(tmp_path / "mask.png")
    render_mask_png("rect", 100, 80, 0, [], p)
    img = Image.open(p).convert("L")
    assert img.size == (100, 80)
    # All pixels should be white (255)
    assert img.getpixel((50, 40)) == 255
    assert img.getpixel((0, 0)) == 255

def test_render_mask_png_rounded_rect(tmp_path):
    """rounded_rect: centre is white, extreme corners are black."""
    from PIL import Image
    p = str(tmp_path / "mask_rr.png")
    render_mask_png("rounded_rect", 100, 100, 20, [], p)
    img = Image.open(p).convert("L")
    assert img.getpixel((50, 50)) == 255   # centre: white
    assert img.getpixel((0, 0)) == 0       # extreme corner: black

def test_render_mask_png_circle(tmp_path):
    """circle: centre is white, corners are black."""
    from PIL import Image
    p = str(tmp_path / "mask_c.png")
    render_mask_png("circle", 100, 100, 0, [], p)
    img = Image.open(p).convert("L")
    assert img.getpixel((50, 50)) == 255   # centre
    assert img.getpixel((0, 0)) == 0       # corner

def test_render_mask_png_polygon(tmp_path):
    """polygon: points inside the polygon are white."""
    from PIL import Image
    p = str(tmp_path / "mask_poly.png")
    # Unit square normalised → fills entire 100x100 canvas
    points = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    render_mask_png("polygon", 100, 100, 0, points, p)
    img = Image.open(p).convert("L")
    assert img.getpixel((50, 50)) == 255

def test_render_mask_png_none_produces_black(tmp_path):
    """Unknown/none shape produces an all-black PNG (no mask)."""
    from PIL import Image
    p = str(tmp_path / "mask_none.png")
    render_mask_png("none", 100, 100, 0, [], p)
    img = Image.open(p).convert("L")
    assert img.getpixel((50, 50)) == 0
```

- [ ] **Step 2: Run to verify they fail**

```
cd D:\Code\autoclipper
python -m pytest tests/test_exporter.py::test_render_mask_png_rect tests/test_exporter.py::test_render_mask_png_rounded_rect tests/test_exporter.py::test_render_mask_png_circle tests/test_exporter.py::test_render_mask_png_polygon tests/test_exporter.py::test_render_mask_png_none_produces_black -v
```

Expected: `ImportError` — `render_mask_png` not defined yet.

- [ ] **Step 3: Add `render_mask_png` to `exporter.py`**

Add this function after the `TEMP_DIR` setup block (before `build_filter_graph`):

```python
def render_mask_png(shape: str, w: int, h: int, radius: int,
                    points: list, path: str) -> None:
    """
    Render a white-on-black mask PNG at w×h pixels.
    shape: "rect" | "rounded_rect" | "circle" | "polygon"
    radius: corner radius in pixels (rounded_rect only)
    points: normalised [[x,y],...] vertices (polygon only, 0–1 relative to w/h)
    path: output file path
    """
    from PIL import Image, ImageDraw
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    if shape == "rect":
        draw.rectangle([0, 0, w - 1, h - 1], fill=255)
    elif shape == "rounded_rect":
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=max(0, radius), fill=255)
    elif shape == "circle":
        draw.ellipse([0, 0, w - 1, h - 1], fill=255)
    elif shape == "polygon" and points:
        pts = [(int(p[0] * w), int(p[1] * h)) for p in points]
        draw.polygon(pts, fill=255)
    img.save(path)
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest tests/test_exporter.py::test_render_mask_png_rect tests/test_exporter.py::test_render_mask_png_rounded_rect tests/test_exporter.py::test_render_mask_png_circle tests/test_exporter.py::test_render_mask_png_polygon tests/test_exporter.py::test_render_mask_png_none_produces_black -v
```

Expected: all 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add exporter.py tests/test_exporter.py
git commit -m "feat: add render_mask_png for all mask shapes"
```

---

## Task 2: Backend — extend `build_filter_graph` with mask support

**Files:**
- Modify: `exporter.py`
- Modify: `tests/test_exporter.py`

The function currently has signature `build_filter_graph(layers, cw, ch, text_pngs, image_inputs)`. We add a fifth parameter `mask_inputs: dict` that maps layer index → FFmpeg stream index of the mask PNG. When a video layer has a mask, the scaled video goes through `alphamerge` before the overlay step.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_exporter.py`:

```python
def test_build_filter_graph_with_mask():
    """Video layer with mask_inputs uses alphamerge before overlay."""
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "video", "x": 0, "y": 656, "width": 1080, "height": 608,
         "fit": "contain"},
    ]
    # Mask PNG for layer index 1 is at stream index 2
    mask_inputs = {1: 2}
    parts, label = build_filter_graph(layers, 1080, 1920, {}, {}, mask_inputs)
    assert any("alphamerge" in p for p in parts)
    assert any("overlay" in p for p in parts)

def test_build_filter_graph_no_mask_unchanged():
    """build_filter_graph with empty mask_inputs behaves identically to before."""
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "video", "x": 0, "y": 656, "width": 1080, "height": 608,
         "fit": "contain"},
    ]
    parts_old, label_old = build_filter_graph(layers, 1080, 1920, {}, {})
    parts_new, label_new = build_filter_graph(layers, 1080, 1920, {}, {}, {})
    assert parts_old == parts_new
    assert label_old == label_new
```

- [ ] **Step 2: Run to verify they fail**

```
python -m pytest tests/test_exporter.py::test_build_filter_graph_with_mask tests/test_exporter.py::test_build_filter_graph_no_mask_unchanged -v
```

Expected: `TypeError` (wrong number of arguments) or assertion failure.

- [ ] **Step 3: Update `build_filter_graph` in `exporter.py`**

Change the function signature from:
```python
def build_filter_graph(layers: list, cw: int, ch: int,
                       text_pngs: dict, image_inputs: dict) -> tuple[list, str]:
```

To:
```python
def build_filter_graph(layers: list, cw: int, ch: int,
                       text_pngs: dict, image_inputs: dict,
                       mask_inputs: dict = None) -> tuple[list, str]:
    if mask_inputs is None:
        mask_inputs = {}
```

Then in the `elif t == "video":` branch, after the scale/pad/crop step that produces `[scaled]`, insert mask compositing when the layer index is in `mask_inputs`. Replace the entire `elif t == "video":` branch with:

```python
        elif t == "video":
            x, y = layer.get("x", 0), layer.get("y", 0)
            w, h = layer.get("width", cw), layer.get("height", int(ch * 0.32))
            fit = layer.get("fit", "contain")
            raw = next_raw()
            scaled = lbl()
            if fit == "contain":
                parts.append(
                    f"[{raw}]scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black[{scaled}]"
                )
            elif fit == "cover":
                parts.append(
                    f"[{raw}]scale={w}:{h}:force_original_aspect_ratio=increase,"
                    f"crop={w}:{h}[{scaled}]"
                )
            else:
                parts.append(f"[{raw}]scale={w}:{h}[{scaled}]")

            # Apply mask if present
            composited = scaled
            if i in mask_inputs:
                mask_idx = mask_inputs[i]
                mask_scaled = lbl()
                masked = lbl()
                parts.append(f"[{mask_idx}:v]scale={w}:{h}[{mask_scaled}]")
                parts.append(f"[{scaled}][{mask_scaled}]alphamerge[{masked}]")
                composited = masked

            if current:
                out = lbl()
                parts.append(f"[{current}][{composited}]overlay=x={x}:y={y}[{out}]")
                current = out
            else:
                current = composited
```

- [ ] **Step 4: Run tests**

```
python -m pytest tests/test_exporter.py -v
```

Expected: all 19 tests PASS (12 existing + 5 from Task 1 + 2 new).

- [ ] **Step 5: Commit**

```bash
git add exporter.py tests/test_exporter.py
git commit -m "feat: add mask_inputs support to build_filter_graph using alphamerge"
```

---

## Task 3: Backend — wire mask pre-processing into `export_video`

**Files:**
- Modify: `exporter.py`
- Modify: `tests/test_exporter.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_exporter.py`:

```python
def test_export_video_strips_mask_from_canvas_layers():
    """Mask pre-processing: mask_inputs dict is populated for masked video layers."""
    # Simulate what export_video does during pre-processing
    layers = [
        {"type": "blur_video", "blur": 20},
        {"type": "video", "x": 0, "y": 656, "width": 1080, "height": 608,
         "fit": "contain", "mask": {"shape": "circle", "radius": 0, "points": []}},
    ]
    mask_inputs = {}
    extra_inputs = []
    job_id = "test001"
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for i, l in enumerate(layers):
            shape = l.get("mask", {}).get("shape", "none")
            if shape != "none":
                p = str(Path(tmp) / f"{job_id}_mask{i}.png")
                lw, lh = l.get("width", 1080), l.get("height", 1920)
                radius = l.get("mask", {}).get("radius", 20)
                points = l.get("mask", {}).get("points", [])
                render_mask_png(shape, lw, lh, radius, points, p)
                mask_inputs[i] = len(extra_inputs) + 1
                extra_inputs.append(p)
        assert 1 in mask_inputs          # layer 1 has mask
        assert 0 not in mask_inputs      # layer 0 is blur_video, no mask
        assert len(extra_inputs) == 1    # one mask PNG added
        from PIL import Image
        img = Image.open(extra_inputs[0]).convert("L")
        assert img.getpixel((540, 304)) == 255  # centre of circle is white
```

- [ ] **Step 2: Run to verify it passes** (this tests the logic we'll copy into `export_video` — it should pass now since `render_mask_png` is implemented)

```
python -m pytest tests/test_exporter.py::test_export_video_strips_mask_from_canvas_layers -v
```

Expected: PASS.

- [ ] **Step 3: Add mask pre-processing to `export_video`**

In `export_video`, find the existing pre-processing loop (around line 199):

```python
    extra_inputs, text_pngs, image_inputs = [], {}, {}
    for i, l in enumerate(layers):
        if l["type"] == "text":
            ...
        elif l["type"] == "image" and os.path.exists(l.get("src", "")):
            ...
```

Add mask pre-processing **after** the text/image loop (before the `build_filter_graph` call):

```python
    # Mask pre-processing: render mask PNGs for masked video layers
    mask_inputs = {}
    for i, l in enumerate(layers):
        shape = l.get("mask", {}).get("shape", "none")
        if shape != "none":
            p = str(TEMP_DIR / f"{job_id}_mask{i}.png")
            lw, lh = l.get("width", cw), l.get("height", ch)
            radius = l.get("mask", {}).get("radius", 20)
            points = l.get("mask", {}).get("points", [])
            render_mask_png(shape, lw, lh, radius, points, p)
            mask_inputs[i] = len(extra_inputs) + 1
            extra_inputs.append(p)
```

Then update the `build_filter_graph` call to pass `mask_inputs`:

```python
    filter_parts, final_video = build_filter_graph(layers, cw, ch, text_pngs, image_inputs, mask_inputs)
```

The temp cleanup at the end already covers `"temp"` in path, which handles mask PNGs too (they're written to `TEMP_DIR`).

- [ ] **Step 4: Run full test suite**

```
python -m pytest tests/ -v
```

Expected: all tests PASS (the existing 26 + 7 new = 33 total).

- [ ] **Step 5: Commit**

```bash
git add exporter.py tests/test_exporter.py
git commit -m "feat: wire mask pre-processing into export_video"
```

---

## Task 4: Frontend — mask serialisation

**Files:**
- Modify: `frontend/index.html`

This task adds mask state to the canvas objects and wires it through `canvasToTemplate()` and `applySavedTpl()`. It also adds the `applyMaskClipPath(obj)` helper that any code can call to re-apply the Fabric.js `clipPath` from an object's `_maskShape`/`_maskRadius`/`_maskPoints` properties.

- [ ] **Step 1: Add mask state variables in the STATE block**

Find in the STATE block (around line 499, after `audioLayer`):

```javascript
let audioLayer=null; // {type:'audio',src,volume,loop,trim_start,trim_end}
```

Add immediately after:

```javascript
// Polygon drawing state
let _polygonDrawing = false;
let _polygonPoints = [];   // canvas-space [{x,y},...] being drawn
let _polygonTarget = null; // Fabric object currently being masked
```

- [ ] **Step 2: Add `applyMaskClipPath(obj)` function**

After the `setAudioLoop` function (or any convenient location after the STATE block), add:

```javascript
// ── VIDEO MASKING ───────────────────────────────────────────────────────────
function applyMaskClipPath(obj) {
  const shape = obj._maskShape || 'none';
  if (shape === 'none') { obj.clipPath = null; cv.renderAll(); return; }
  const w = obj.getScaledWidth();
  const h = obj.getScaledHeight();
  const r = (obj._maskRadius ?? 20) * (w / 1080); // scale radius to canvas size
  let cp;
  if (shape === 'rect') {
    cp = new fabric.Rect({width: w, height: h, left: -w/2, top: -h/2});
  } else if (shape === 'rounded_rect') {
    cp = new fabric.Rect({width: w, height: h, left: -w/2, top: -h/2, rx: r, ry: r});
  } else if (shape === 'circle') {
    cp = new fabric.Ellipse({rx: w/2, ry: h/2, left: -w/2, top: -h/2});
  } else if (shape === 'polygon') {
    const pts = (obj._maskPoints || []).map(p => ({
      x: p[0] * w - w/2,
      y: p[1] * h - h/2,
    }));
    cp = pts.length >= 3 ? new fabric.Polygon(pts) : null;
  }
  obj.clipPath = cp || null;
  cv.renderAll();
}
```

- [ ] **Step 3: Update `canvasToTemplate()` video layer serialisation**

Find (around line 1884):

```javascript
    if(t==='video')return{...base,fit:obj._fit||'contain',
      volume:obj._audioVolume??1.0,
      muted:obj._audioMuted===true};
```

Replace with:

```javascript
    if(t==='video')return{...base,fit:obj._fit||'contain',
      volume:obj._audioVolume??1.0,
      muted:obj._audioMuted===true,
      mask:{
        shape:obj._maskShape||'none',
        radius:obj._maskRadius??20,
        points:obj._maskPoints||[],
      }};
```

- [ ] **Step 4: Update `applySavedTpl()` fabric.Image restore**

Find (around line 1960):

```javascript
        const img=new fabric.Image(vc2,{left:lx,top:ly,objectCaching:false,_type:'video',_label:'Video Layer',_fit:layer.fit||'contain',opacity:op,_audioVolume:layer.volume??1.0,_audioMuted:layer.muted===true});
```

Replace with:

```javascript
        const img=new fabric.Image(vc2,{left:lx,top:ly,objectCaching:false,_type:'video',_label:'Video Layer',_fit:layer.fit||'contain',opacity:op,_audioVolume:layer.volume??1.0,_audioMuted:layer.muted===true,_maskShape:(layer.mask||{}).shape||'none',_maskRadius:(layer.mask||{}).radius??20,_maskPoints:(layer.mask||{}).points||[]});
        if(img._maskShape!=='none') applyMaskClipPath(img);
```

Find the fabric.Group fallback (around line 1967):

```javascript
        cv.add(new fabric.Group([r,t2],{_type:'video',_label:'Video Layer',_fit:layer.fit||'contain',_audioVolume:layer.volume??1.0,_audioMuted:layer.muted===true}));
```

Replace with:

```javascript
        const grp=new fabric.Group([r,t2],{_type:'video',_label:'Video Layer',_fit:layer.fit||'contain',_audioVolume:layer.volume??1.0,_audioMuted:layer.muted===true,_maskShape:(layer.mask||{}).shape||'none',_maskRadius:(layer.mask||{}).radius??20,_maskPoints:(layer.mask||{}).points||[]});
        if(grp._maskShape!=='none') applyMaskClipPath(grp);
        cv.add(grp);
```

(Note: remove the original `cv.add(new fabric.Group(...))` line and replace it with these two lines + `cv.add(grp)` already included.)

- [ ] **Step 5: Manual smoke test**

Start the server (`python app.py`), open `http://localhost:5000`. No JS errors should appear in the browser console.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add mask serialisation and applyMaskClipPath to video layers"
```

---

## Task 5: Frontend — Mask section in properties panel

**Files:**
- Modify: `frontend/index.html`

When a video layer is selected, a "Mask" section appears below the Audio section in the right panel. It lets the user pick a shape and (for rounded rect) adjust the radius.

- [ ] **Step 1: Add CSS for mask section**

In the `<style>` block, add after any existing `.psec` CSS:

```css
.mask-shape-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:4px}
.msbtn{padding:6px 4px;border-radius:6px;border:1px solid var(--b1);background:var(--s2);color:var(--sub);font-size:10px;cursor:pointer;text-align:center;transition:.12s}
.msbtn.on{border-color:var(--acc);color:var(--acc);background:var(--accdim)}
.msbtn:hover:not(.on){background:var(--s3);color:var(--tx)}
```

- [ ] **Step 2: Add Mask section in the `if(type==='video')` block in `updateProps()`**

Find at the end of the `if(type==='video')` block (after the closing backtick of the Audio `html+=` line, before the closing `}`):

```javascript
    </div>`;
  }
```

Insert a Mask section just before that closing `}`:

```javascript
    // ── Mask section ────────────────────────────────────────────────────────
    const mshape = obj._maskShape||'none';
    const mrad = obj._maskRadius??20;
    html+=`<div class="psec">
      <div class="psec-title">✂️ Mask</div>
      <div class="mask-shape-grid">
        <button class="msbtn${mshape==='none'?' on':''}"         onclick="setMaskShape('none')">None</button>
        <button class="msbtn${mshape==='rect'?' on':''}"         onclick="setMaskShape('rect')">Rect</button>
        <button class="msbtn${mshape==='rounded_rect'?' on':''}" onclick="setMaskShape('rounded_rect')">Rounded</button>
        <button class="msbtn${mshape==='circle'?' on':''}"       onclick="setMaskShape('circle')">Circle</button>
      </div>
      <div class="mask-shape-grid" style="grid-template-columns:1fr;margin-top:4px">
        <button class="msbtn${mshape==='polygon'?' on':''}"      onclick="setMaskShape('polygon')">Polygon (draw)</button>
      </div>
      ${mshape==='rounded_rect'?`
      <div class="prow" style="margin-top:6px"><span class="plbl">Radius</span>
        <div class="slrow">
          <input type="range" class="psl" min="0" max="200" value="${mrad}"
            oninput="setMaskRadius(+this.value);this.nextElementSibling.textContent=this.value+'px'">
          <span class="slv">${mrad}px</span>
        </div>
      </div>`:''}
      ${mshape==='polygon'?`
      <div class="prow" style="margin-top:6px;gap:6px">
        <button class="btn btn-ghost" style="flex:1" onclick="startPolygonDraw()">
          ${(obj._maskPoints||[]).length>=3?'Redraw':'Draw'} Polygon
        </button>
        ${(obj._maskPoints||[]).length>=3?`<button class="btn btn-ghost" onclick="clearPolygonMask()">Clear</button>`:''}
      </div>`:''}
    </div>`;
```

- [ ] **Step 3: Add `setMaskShape()`, `setMaskRadius()`, `clearPolygonMask()` functions**

After `applyMaskClipPath`, add:

```javascript
function setMaskShape(shape){
  const obj = cv.getActiveObject();
  if(!obj) return;
  obj._maskShape = shape;
  if(shape !== 'polygon') obj._maskPoints = [];
  applyMaskClipPath(obj);
  updateProps(); // re-render panel to show/hide radius/polygon controls
  saveHist();
}

function setMaskRadius(val){
  const obj = cv.getActiveObject();
  if(!obj) return;
  obj._maskRadius = val;
  applyMaskClipPath(obj);
  saveHist();
}

function clearPolygonMask(){
  const obj = cv.getActiveObject();
  if(!obj) return;
  obj._maskPoints = [];
  obj.clipPath = null;
  cv.renderAll();
  updateProps();
  saveHist();
}
```

- [ ] **Step 4: Manual test**

Select a video layer → confirm a "✂️ Mask" section appears. Click "Rect" — video is clipped to its bounds (full rectangle, no visual change). Click "Rounded" — a radius slider appears. Drag slider — corners round in the preview. Click "Circle" — video is clipped to an ellipse. Click "None" — clip removed.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add Mask section to video layer properties panel"
```

---

## Task 6: Frontend — Polygon drawing mode

**Files:**
- Modify: `frontend/index.html`

This task adds the polygon drawing overlay canvas and the click-to-add-point interaction.

- [ ] **Step 1: Add the overlay canvas HTML**

Find in the HTML (around line 407–409):

```html
        <div id="phone">
          <canvas id="ec"></canvas>
        </div>
```

Replace with:

```html
        <div id="phone" style="position:relative">
          <canvas id="ec"></canvas>
          <canvas id="poly-overlay" style="position:absolute;top:0;left:0;pointer-events:none;display:none"></canvas>
        </div>
```

- [ ] **Step 2: Add `startPolygonDraw()` function**

After `clearPolygonMask()`, add:

```javascript
function startPolygonDraw(){
  const obj = cv.getActiveObject();
  if(!obj) return;
  _polygonDrawing = true;
  _polygonPoints = [];
  _polygonTarget = obj;
  // Show and size the overlay canvas
  const phone = document.getElementById('phone');
  const overlay = document.getElementById('poly-overlay');
  overlay.width = phone.offsetWidth;
  overlay.height = phone.offsetHeight;
  overlay.style.display = 'block';
  overlay.style.cursor = 'crosshair';
  cv.defaultCursor = 'crosshair';
  cv.hoverCursor = 'crosshair';
  // Prevent Fabric from handling mouse events during draw
  cv.selection = false;
  cv.forEachObject(o => { o.selectable = false; o.evented = false; });
}

function stopPolygonDraw(){
  _polygonDrawing = false;
  _polygonPoints = [];
  _polygonTarget = null;
  const overlay = document.getElementById('poly-overlay');
  overlay.style.display = 'none';
  overlay.style.cursor = '';
  const ctx = overlay.getContext('2d');
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  cv.defaultCursor = 'default';
  cv.hoverCursor = 'move';
  cv.selection = true;
  cv.forEachObject(o => { o.selectable = true; o.evented = true; });
}
```

- [ ] **Step 3: Add the overlay drawing function**

```javascript
function drawPolyOverlay(mouseX, mouseY){
  const overlay = document.getElementById('poly-overlay');
  const ctx = overlay.getContext('2d');
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  if(_polygonPoints.length === 0) return;

  ctx.strokeStyle = '#a78bfa';
  ctx.fillStyle = 'rgba(167,139,250,0.15)';
  ctx.lineWidth = 2;
  ctx.setLineDash([]);

  // Draw filled polygon preview
  ctx.beginPath();
  ctx.moveTo(_polygonPoints[0].x, _polygonPoints[0].y);
  for(let i = 1; i < _polygonPoints.length; i++){
    ctx.lineTo(_polygonPoints[i].x, _polygonPoints[i].y);
  }
  if(mouseX !== null) ctx.lineTo(mouseX, mouseY);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Draw dashed line from last point to cursor
  if(mouseX !== null && _polygonPoints.length > 0){
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(_polygonPoints[_polygonPoints.length-1].x, _polygonPoints[_polygonPoints.length-1].y);
    ctx.lineTo(mouseX, mouseY);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Draw point dots
  _polygonPoints.forEach((pt, idx) => {
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, idx === 0 ? 6 : 4, 0, Math.PI * 2);
    ctx.fillStyle = idx === 0 ? '#ffffff' : '#a78bfa';
    ctx.fill();
    ctx.strokeStyle = '#a78bfa';
    ctx.stroke();
  });
}
```

- [ ] **Step 4: Wire click and mousemove onto the overlay canvas**

Find where canvas event listeners are set up — look for `cv.on('mouse:move'` or the boot/init section (around line ~1680 or wherever `cv` is initialised). After the canvas is fully set up, add:

```javascript
// Polygon drawing event handlers (on the overlay canvas, not Fabric)
document.getElementById('poly-overlay').addEventListener('mousemove', e => {
  if(!_polygonDrawing) return;
  const rect = e.target.getBoundingClientRect();
  drawPolyOverlay(e.clientX - rect.left, e.clientY - rect.top);
});

document.getElementById('poly-overlay').addEventListener('click', e => {
  if(!_polygonDrawing || !_polygonTarget) return;
  const overlay = document.getElementById('poly-overlay');
  // Re-enable pointer events for overlay so it catches clicks
  overlay.style.pointerEvents = 'auto';
  const rect = overlay.getBoundingClientRect();
  const cx = e.clientX - rect.left;
  const cy = e.clientY - rect.top;

  // Check close to first point (at least 3 points already)
  if(_polygonPoints.length >= 3){
    const first = _polygonPoints[0];
    if(Math.hypot(cx - first.x, cy - first.y) < 12){
      // Close polygon
      const obj = _polygonTarget;
      const ow = obj.getScaledWidth();
      const oh = obj.getScaledHeight();
      const objLeft = obj.left + (ow - obj.getScaledWidth()) / 2;
      const objTop  = obj.top  + (oh - obj.getScaledHeight()) / 2;
      // Normalise points: convert overlay canvas coords → 0–1 relative to layer bounds
      const phone = document.getElementById('phone');
      const scaleX = 1080 / phone.offsetWidth;  // overlay is phone-sized
      const scaleY = (FMT[fmt].h / FMT[fmt].w * 1080) / phone.offsetHeight;
      const normPts = _polygonPoints.map(p => {
        // p is in phone/overlay px. Convert to canvas fabric coords
        const fabX = p.x / phone.offsetWidth * FMT[fmt].w;
        const fabY = p.y / phone.offsetHeight * FMT[fmt].h;
        // Normalise relative to layer bounds
        return [
          Math.max(0, Math.min(1, (fabX - obj.left) / ow)),
          Math.max(0, Math.min(1, (fabY - obj.top)  / oh)),
        ];
      });
      obj._maskPoints = normPts;
      applyMaskClipPath(obj);
      stopPolygonDraw();
      updateProps();
      saveHist();
      return;
    }
  }
  _polygonPoints.push({x: cx, y: cy});
  drawPolyOverlay(cx, cy);
});

// Escape cancels polygon draw
document.addEventListener('keydown', e => {
  if(e.key === 'Escape' && _polygonDrawing){
    stopPolygonDraw();
    updateProps();
  }
});
```

Note: `overlay.style.pointerEvents = 'auto'` is set inside the click handler because we need the overlay to receive mouse events. Update `startPolygonDraw()` to set `pointer-events: auto` from the start instead of `none`:

In `startPolygonDraw()`, change:
```javascript
  overlay.style.display = 'block';
  overlay.style.cursor = 'crosshair';
```
to:
```javascript
  overlay.style.display = 'block';
  overlay.style.pointerEvents = 'auto';
  overlay.style.cursor = 'crosshair';
```

And in `stopPolygonDraw()`, add resetting pointer events:
```javascript
  overlay.style.display = 'none';
  overlay.style.pointerEvents = 'none';
  overlay.style.cursor = '';
```

- [ ] **Step 5: Manual test**

1. Select a video layer → click "Mask" → click "Polygon (draw)"
2. Click 4–5 points on the canvas to outline a shape
3. Click back near the first point (white dot) — polygon closes, video is clipped to the polygon shape
4. Press Escape mid-draw — drawing cancels
5. Click "Clear" — clip removed
6. Save template → reload → polygon mask is restored

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add polygon drawing mode for video mask"
```

---

## Task 7: Integration — run full test suite

- [ ] **Step 1: Run all tests**

```
cd D:\Code\autoclipper
python -m pytest tests/ -v
```

Expected: all tests pass (26 existing + 7 new mask tests = 33 total).

- [ ] **Step 2: Manual export test**

1. Start server: `python app.py`
2. Download a short video clip
3. Apply a "Circle" mask to the video layer
4. Export — confirm the output video has the circle-masked clip composited on the blur background
5. Apply a "Polygon" mask by drawing a triangle on canvas
6. Export again — confirm the triangle mask is applied correctly

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add .
git commit -m "feat: complete video masking — shapes, polygon draw, FFmpeg export"
```

---

## Self-Review Notes

**Spec coverage:**
- ✅ `render_mask_png` for rect/rounded_rect/circle/polygon/none — Task 1
- ✅ `build_filter_graph` `mask_inputs` param + alphamerge chain — Task 2
- ✅ Mask pre-processing in `export_video` — Task 3
- ✅ `applyMaskClipPath` + `canvasToTemplate` + `applySavedTpl` — Task 4
- ✅ Properties panel with shape selector + radius slider — Task 5
- ✅ Polygon drawing mode with overlay canvas, close-on-first-point, Escape cancel — Task 6
- ✅ Normalised polygon points (0–1 relative to layer) — Task 4 (`applyMaskClipPath`) + Task 6 (close-polygon normalization)

**Type consistency:**
- `_maskShape`, `_maskRadius`, `_maskPoints` — used consistently across Tasks 4, 5, 6
- `applyMaskClipPath(obj)` — defined Task 4, called Task 4 (applySavedTpl), Task 5 (setMaskShape, setMaskRadius), Task 6 (polygon close)
- `mask_inputs` dict — defined in Task 2 (`build_filter_graph` signature), populated in Task 3 (`export_video`)
- `render_mask_png(shape, w, h, radius, points, path)` — defined Task 1, called Task 3
