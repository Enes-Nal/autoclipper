# Text Element Resizable Bounding Box Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give text elements a proper 8-handle resizable bounding box where width controls word-wrap, with an optional fixed-height mode and matching export output.

**Architecture:** Intercept Fabric.js `object:scaling` for text objects, convert scale deltas into direct `width`/`height` mutations (resetting scale to 1), then sync visible handles based on `_autoHeight`. Add vertical alignment support to `text_renderer.py`. No new files — all changes go into the three existing files.

**Tech Stack:** Fabric.js (canvas), Python Pillow (text_renderer.py), pytest

---

### Task 1: Add `syncTextHandles` and blue handle style to text objects

**Files:**
- Modify: `frontend/index.html` (around line 1954–1958 and line 2380–2387)

This task adds the utility function `syncTextHandles(obj)` that sets handle visibility based on `_autoHeight`, updates `object:added` to call it, and applies the blue handle/border style at text creation time.

- [ ] **Step 1: Find the `object:added` handler** — it's around line 1953–1958:

```js
cv.on('object:added',e=>{
  if(e.target._type==='text'){
    // Show ml/mr so users can drag to resize the text frame width.
    // Hide mt/mb (height is auto-sized by Textbox).
    e.target.setControlsVisibility({mt:false,mb:false});
  }
});
```

- [ ] **Step 2: Add `syncTextHandles` just above the `cv.on('object:added'` call (around line 1953). Replace that `cv.on('object:added'...)` block with:**

```js
function syncTextHandles(obj) {
  if (obj._autoHeight !== false) {
    obj.setControlsVisibility({mt:false,mb:false,tl:false,tr:false,bl:false,br:false});
  } else {
    obj.setControlsVisibility({mt:true,mb:true,tl:true,tr:true,bl:true,br:true});
  }
}

cv.on('object:added',e=>{
  if(e.target._type==='text'){
    e.target.set({
      borderColor:'#2563eb',
      cornerColor:'#2563eb',
      cornerSize:9,
      transparentCorners:false,
    });
    syncTextHandles(e.target);
  }
});
```

- [ ] **Step 3: Find `addText()` around line 2378–2388:**

```js
function addText(){
  const {w}=FMT[fmt];
  const t=new fabric.Textbox('Your title here 🔥',{
    left:sc(40),top:sc(80),width:w-sc(80),
    fontSize:sc(52),fontFamily:'"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji","Inter",sans-serif',
    fontWeight:'900',fill:'#ffffff',stroke:'#000',strokeWidth:sc(3),
    paintFirst:'stroke',textAlign:'center',_type:'text',_label:'Text Block',
    _isTitle:true,_overflow:'wrap',
  });
  cv.add(t);cv.setActiveObject(t);cv.renderAll();
}
```

- [ ] **Step 4: Add `_autoHeight: true` and `_verticalAlign: 'top'` to the Textbox initialisation in `addText()`:**

```js
function addText(){
  const {w}=FMT[fmt];
  const t=new fabric.Textbox('Your title here 🔥',{
    left:sc(40),top:sc(80),width:w-sc(80),
    fontSize:sc(52),fontFamily:'"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji","Inter",sans-serif',
    fontWeight:'900',fill:'#ffffff',stroke:'#000',strokeWidth:sc(3),
    paintFirst:'stroke',textAlign:'center',_type:'text',_label:'Text Block',
    _isTitle:true,_overflow:'wrap',_autoHeight:true,_verticalAlign:'top',
  });
  cv.add(t);cv.setActiveObject(t);cv.renderAll();
}
```

- [ ] **Step 5: Find the template text creation around line 3907 (search for `new fabric.Textbox(displayText`). It also needs `_autoHeight:true,_verticalAlign:'top'` added to the properties object. Add them after `_isTitle:isTitle,`:**

```js
_isTitle:isTitle,_autoHeight:true,_verticalAlign:'top',
```

- [ ] **Step 6: Open the app in a browser. Add a text element. Confirm the selection border is blue and only left/right handles are visible.**

- [ ] **Step 7: Commit**

```
git add frontend/index.html
git commit -m "feat: syncTextHandles, blue handles, _autoHeight/_verticalAlign defaults on text"
```

---

### Task 2: Scale interception — convert resize to width/height mutation

**Files:**
- Modify: `frontend/index.html` (around line 1944–1958 and line 2165)

Right now, resizing any object (including text) updates `scaleX`/`scaleY`. For text objects we must convert that into `width`/`height` changes and reset scale to 1 so the export always reads true pixel dimensions.

- [ ] **Step 1: Find the `object:scaling` handler around line 1944:**

```js
cv.on('object:scaling', e => {
  if (e.target?._isMaskEditor) { syncMaskFromEditor(e.target); return; }
  const corner = e.transform?.corner;
  const isSide = corner==='ml'||corner==='mr'||corner==='mt'||corner==='mb';
  if (isSide && e.e?.shiftKey) {
    const obj = e.target;
    const aspect = obj.width / obj.height;
    if (corner==='ml'||corner==='mr') {
      obj.scaleY = obj.scaleX / aspect;
    } else {
      obj.scaleX = obj.scaleY * aspect;
    }
  }
  onSnapScale(e);
  if (e.target?._type==='video') _updateMaskEditorForVideo(e.target);
});
```

- [ ] **Step 2: Add text resize interception at the top of `object:scaling`, immediately after the mask-editor guard:**

```js
cv.on('object:scaling', e => {
  if (e.target?._isMaskEditor) { syncMaskFromEditor(e.target); return; }

  // Text: convert scale → width/height, keep scale=1
  if (e.target?._type === 'text') {
    const obj = e.target;
    const newW = Math.max(20, obj.width * obj.scaleX);
    obj.width = newW;
    if (obj._autoHeight === false) {
      const newH = Math.max(20, obj.height * obj.scaleY);
      obj.height = newH;
    }
    obj.scaleX = 1;
    obj.scaleY = 1;
    obj.setCoords();
    return;
  }

  const corner = e.transform?.corner;
  const isSide = corner==='ml'||corner==='mr'||corner==='mt'||corner==='mb';
  if (isSide && e.e?.shiftKey) {
    const obj = e.target;
    const aspect = obj.width / obj.height;
    if (corner==='ml'||corner==='mr') {
      obj.scaleY = obj.scaleX / aspect;
    } else {
      obj.scaleX = obj.scaleY * aspect;
    }
  }
  onSnapScale(e);
  if (e.target?._type==='video') _updateMaskEditorForVideo(e.target);
});
```

- [ ] **Step 3: Find and remove the uniform-scale lock for text in `onSnapScale` at line 2165:**

```js
  if(obj._type==='text'){const sc=Math.max(obj.scaleX,obj.scaleY);obj.scaleX=sc;obj.scaleY=sc;}
```

Delete that line entirely.

- [ ] **Step 4: Find `ssz` around line 3643:**

```js
function ssz(ax,v){const o=cv?.getActiveObject();if(!o)return;if(ax==='w'){o.scaleX=v/o.width;if(o._type==='text')o.scaleY=o.scaleX;}else{o.scaleY=v/o.height;if(o._type==='text')o.scaleX=o.scaleY;}o.setCoords();cv.renderAll();}
```

Replace with a version that sets `width`/`height` directly for text:

```js
function ssz(ax,v){const o=cv?.getActiveObject();if(!o)return;if(o._type==='text'){if(ax==='w'){o.width=Math.max(20,v);}else if(o._autoHeight===false){o.height=Math.max(20,v);}o.scaleX=1;o.scaleY=1;}else{if(ax==='w'){o.scaleX=v/o.width;}else{o.scaleY=v/o.height;}}o.setCoords();cv.renderAll();}
```

- [ ] **Step 5: Open the app. Add a text element. Drag the left or right handle. Confirm text wraps as the box narrows. Confirm `scaleX`/`scaleY` stay at 1 (check in browser devtools: `canvas.getActiveObject().scaleX` should be `1`).**

- [ ] **Step 6: Commit**

```
git add frontend/index.html
git commit -m "feat: text resize converts scale to width/height, remove uniform-scale lock"
```

---

### Task 3: Dimension label during resize

**Files:**
- Modify: `frontend/index.html` (HTML section for `#canvas-area`, and JS near `object:scaling` / `mouse:up`)

A small pill label showing `W × H` in canvas pixels, shown while dragging a text handle, hidden otherwise.

- [ ] **Step 1: Find the `<div id="canvas-area"` in the HTML (search for `id="canvas-area"`). Inside it (as a direct child, after the canvas element), add:**

```html
<div id="resize-label" style="display:none;position:absolute;pointer-events:none;background:rgba(0,0,0,.75);color:#fff;font-size:11px;font-weight:700;padding:3px 7px;border-radius:5px;z-index:99;white-space:nowrap"></div>
```

- [ ] **Step 2: In the `object:scaling` handler (inside the `if (e.target?._type === 'text')` block added in Task 2), after `obj.setCoords();`, add code to position and show the label:**

```js
    // Show dimension label
    const lbl = document.getElementById('resize-label');
    if (lbl) {
      const zoom = cv.getZoom();
      const vpt = cv.viewportTransform;
      const screenX = obj.left * zoom + vpt[4];
      const screenY = (obj.top + (obj._autoHeight === false ? obj.height : obj.getScaledHeight())) * zoom + vpt[5] + 4;
      lbl.textContent = `${Math.round(obj.width)} × ${Math.round(obj._autoHeight === false ? obj.height : obj.getScaledHeight())}`;
      lbl.style.left = screenX + 'px';
      lbl.style.top = screenY + 'px';
      lbl.style.display = '';
    }
```

- [ ] **Step 3: Find the `cv.on('mouse:up'` event (or add one if absent — search for `mouse:up`). Add label hiding:**

```js
cv.on('mouse:up', () => {
  const lbl = document.getElementById('resize-label');
  if (lbl) lbl.style.display = 'none';
});
```

If a `mouse:up` handler already exists, add the two lines inside it.

- [ ] **Step 4: Open the app. Add text. Drag a resize handle. Confirm a dark pill label appears near the bottom of the text box showing dimensions like `540 × 120`. Confirm it disappears on mouse release.**

- [ ] **Step 5: Commit**

```
git add frontend/index.html
git commit -m "feat: show dimension label while resizing text bounding box"
```

---

### Task 4: Properties panel — Fixed height toggle and vertical align

**Files:**
- Modify: `frontend/index.html` (inside `updateProps()`, the `if(type==='text')` block, around line 3100–3127)

Add a "Fixed height" checkbox and (when fixed mode is on) vertical align buttons.

- [ ] **Step 1: Find the closing of the text psec in `updateProps()`. It ends around line 3127 with:**

```js
    <div class="psec"><div class="psec-title">...Emoji...
      <button class="emo-btn" onclick="toggleEmojiPicker(this)">😊 Add Emoji</button>
      <p class="pnote">Inserts emoji at cursor. Without a text selection, adds as a standalone image layer.</p>
    </div>`;
  }
```

- [ ] **Step 2: In `updateProps()`, inside `if(type==='text'){...}`, find the line that reads the overflow and align values (around line 3066–3067):**

```js
    const fill=typeof obj.fill==='string'?obj.fill:'#ffffff';
    const fs=Math.round(obj.fontSize||48),sw=Math.round(obj.strokeWidth||0);
```

Add two new variables immediately after that block:

```js
    const isFixed = obj._autoHeight === false;
    const vAlign = obj._verticalAlign || 'top';
```

- [ ] **Step 3: Inside the same `if(type==='text')` block, locate the Overflow row (around line 3101–3105):**

```js
    <div class="prow"><span class="plbl">Overflow</span>
      <div class="tog" id="overflow-tog">
        ${['wrap','truncate','shrink'].map(m=>`<button class="togbtn${(obj._overflow||'wrap')===m?' on':''}" onclick="togOn(this);sp('_overflow','${m}')">${m[0].toUpperCase()+m.slice(1)}</button>`).join('')}
      </div>
    </div>
```

**After** that row (still inside the same template literal), add the Fixed height checkbox and the conditional vertical align row:

```js
    <div class="prow"><span class="plbl">Fixed H</span>
      <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
        <input type="checkbox" ${isFixed?'checked':''} onchange="toggleTextFixedHeight(this.checked)">
        <span style="font-size:11px;color:var(--sub)">Fixed height</span>
      </label>
    </div>
    ${isFixed?`
    <div class="prow"><span class="plbl">V.Align</span>
      <div class="tog">
        <button class="togbtn${vAlign==='top'?' on':''}" onclick="togOn(this);setTextVAlign('top')">Top</button>
        <button class="togbtn${vAlign==='middle'?' on':''}" onclick="togOn(this);setTextVAlign('middle')">Mid</button>
        <button class="togbtn${vAlign==='bottom'?' on':''}" onclick="togOn(this);setTextVAlign('bottom')">Bot</button>
      </div>
    </div>`:''}
```

- [ ] **Step 4: Add the two handler functions somewhere near the other text utility functions (e.g. after `ssz`):**

```js
function toggleTextFixedHeight(on){
  const o=cv?.getActiveObject();if(!o||o._type!=='text')return;
  o._autoHeight=!on;
  if(on){
    // capture current rendered height as the starting fixed height
    o.height=Math.round(o.getScaledHeight());
    o.scaleY=1;
  }
  syncTextHandles(o);
  o.setCoords();cv.renderAll();updateProps();saveHist();
}

function setTextVAlign(v){
  const o=cv?.getActiveObject();if(!o||o._type!=='text')return;
  o._verticalAlign=v;
  cv.renderAll();saveHist();
}
```

- [ ] **Step 5: Also update the H input in the Transform section of `updateProps()` to remove the hardcoded readonly for text. Find (around line 2980):**

```js
        <input class="pin" value="${H}" onchange="ssz('h',+this.value)" ${type==='text'?'readonly style="opacity:.4;cursor:default"':''}>
```

Replace with a version that is only readonly when in autoHeight mode:

```js
        <input class="pin" value="${H}" onchange="ssz('h',+this.value)" ${type==='text'&&obj._autoHeight!==false?'readonly style="opacity:.4;cursor:default"':''}>
```

- [ ] **Step 6: Open the app. Select a text element. Confirm "Fixed height" checkbox appears unchecked. Check it — confirm all 8 handles appear and the height input becomes editable. Confirm vertical align buttons (Top / Mid / Bot) appear. Uncheck — confirm only left/right handles are visible again.**

- [ ] **Step 7: Commit**

```
git add frontend/index.html
git commit -m "feat: fixed height toggle and vertical align controls in text properties panel"
```

---

### Task 5: Vertical alignment in `text_renderer.py`

**Files:**
- Modify: `text_renderer.py` (inside `render_text_layer`, after line list is built, around line 256)
- Test: `tests/test_text_renderer.py`

- [ ] **Step 1: Write failing tests in `tests/test_text_renderer.py`. Add these at the end of the file:**

```python
def _topmost_nonzero_row(arr):
    """Return the topmost row that has any non-transparent pixel."""
    for row in range(arr.shape[0]):
        if arr[row, :, 3].max() > 0:
            return row
    return arr.shape[0]

def test_vertical_align_top_fixed():
    """In fixed frame mode with vertical_align=top, text starts near the top of the frame."""
    layer = {
        "type": "text", "x": 0, "y": 100,
        "width": 400, "height": 300,
        "text": "Hello",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
        "vertical_align": "top",
        "auto_height": False,
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            arr = np.array(img)
        top_row = _topmost_nonzero_row(arr)
        # Top-aligned text should start near y=100 (within 10px of font ascender)
        assert 90 <= top_row <= 115, f"Expected text near row 100, got {top_row}"
    finally:
        os.unlink(path)

def test_vertical_align_middle_fixed():
    """In fixed frame mode with vertical_align=middle, text is vertically centred in the frame."""
    layer = {
        "type": "text", "x": 0, "y": 0,
        "width": 400, "height": 400,
        "text": "Hello",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
        "vertical_align": "middle",
        "auto_height": False,
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            arr = np.array(img)
        top_row = _topmost_nonzero_row(arr)
        # Middle-aligned in a 400px frame: text block (~58px) starts around row 171
        # Allow ±20px tolerance
        assert 150 <= top_row <= 200, f"Expected text near row 171, got {top_row}"
    finally:
        os.unlink(path)

def test_vertical_align_bottom_fixed():
    """In fixed frame mode with vertical_align=bottom, text is near the bottom of the frame."""
    layer = {
        "type": "text", "x": 0, "y": 0,
        "width": 400, "height": 400,
        "text": "Hello",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
        "vertical_align": "bottom",
        "auto_height": False,
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            arr = np.array(img)
        top_row = _topmost_nonzero_row(arr)
        # Bottom-aligned in a 400px frame: single line (~58px) starts around row 342
        # Allow ±20px tolerance
        assert 320 <= top_row <= 400, f"Expected text near row 342, got {top_row}"
    finally:
        os.unlink(path)

def test_vertical_align_ignored_in_autoheight():
    """vertical_align has no effect when auto_height=True (default behaviour)."""
    base = {
        "type": "text", "x": 0, "y": 0,
        "width": 400, "height": 400,
        "text": "Hello",
        "font_size": 48, "fill": "#ffffff",
        "stroke": "#000000", "stroke_width": 0,
        "text_align": "left",
        "auto_height": True,
    }
    results = {}
    for v in ("top", "middle", "bottom"):
        layer = {**base, "vertical_align": v}
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        render_text_layer(layer, 1080, 1920, path)
        with Image.open(path) as img:
            results[v] = _topmost_nonzero_row(np.array(img))
        os.unlink(path)
    assert results["top"] == results["middle"] == results["bottom"], \
        "vertical_align must not affect autoHeight rendering"
```

- [ ] **Step 2: Run the new tests to confirm they fail:**

```
pytest tests/test_text_renderer.py::test_vertical_align_top_fixed tests/test_text_renderer.py::test_vertical_align_middle_fixed tests/test_text_renderer.py::test_vertical_align_bottom_fixed tests/test_text_renderer.py::test_vertical_align_ignored_in_autoheight -v
```

Expected: all 4 FAIL (function exists but ignores `vertical_align`).

- [ ] **Step 3: In `text_renderer.py`, find the draw loop setup around line 256–257:**

```python
    # ── Draw each line, clipping at frame bottom ──────────────────────────────
    y_cursor = frame_y - bbox[1]
```

Replace `y_cursor` initialization with vertical-alignment logic:

```python
    # ── Compute y_start based on vertical_align (fixed frame only) ───────────
    vertical_align = layer.get("vertical_align", "top")
    auto_height = layer.get("auto_height", True)
    total_text_h = len(lines) * line_h

    if not auto_height and vertical_align != "top":
        if vertical_align == "middle":
            y_offset = max(0, (frame_h - total_text_h) // 2)
        else:  # bottom
            y_offset = max(0, frame_h - total_text_h)
    else:
        y_offset = 0

    # ── Draw each line, clipping at frame bottom ──────────────────────────────
    y_cursor = frame_y + y_offset - bbox[1]
```

- [ ] **Step 4: Run the tests again:**

```
pytest tests/test_text_renderer.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```
git add text_renderer.py tests/test_text_renderer.py
git commit -m "feat: vertical alignment in render_text_layer (middle/bottom for fixed frames)"
```

---

### Task 6: Pass `auto_height` and `vertical_align` from exporter to renderer

**Files:**
- Modify: `exporter.py` (around line 295–298, where `render_text_layer` is called)

The snapshot layer dict already contains all Fabric.js object properties. We need to map the JS property names (`_autoHeight`, `_verticalAlign`) to the Python names (`auto_height`, `vertical_align`) before calling `render_text_layer`.

- [ ] **Step 1: In `exporter.py`, find the text layer rendering block around line 294–299:**

```python
    for i, l in enumerate(layers):
        if l["type"] == "text":
            p = str(TEMP_DIR / f"{job_id}_t{i}.png")
            render_text_layer(l, cw, ch, p, emoji_source=emoji_source)
            text_pngs[i] = len(extra_inputs) + 1
            extra_inputs.append(p)
```

- [ ] **Step 2: Replace with a version that builds an augmented layer dict with the mapped properties:**

```python
    for i, l in enumerate(layers):
        if l["type"] == "text":
            p = str(TEMP_DIR / f"{job_id}_t{i}.png")
            render_layer = dict(l)
            render_layer["auto_height"] = l.get("_autoHeight", True)
            render_layer["vertical_align"] = l.get("_verticalAlign", "top")
            render_text_layer(render_layer, cw, ch, p, emoji_source=emoji_source)
            text_pngs[i] = len(extra_inputs) + 1
            extra_inputs.append(p)
```

- [ ] **Step 3: Run the existing exporter tests to make sure nothing regresses:**

```
pytest tests/test_exporter.py -v
```

Expected: all existing tests PASS.

- [ ] **Step 4: Commit**

```
git add exporter.py
git commit -m "feat: pass auto_height and vertical_align from snapshot to render_text_layer"
```

---

### Task 7: End-to-end smoke test

No new test files — manual verification in the app.

- [ ] **Step 1: Start the app (`python app.py` or however it's normally run).**

- [ ] **Step 2: Add a text element. Drag the left/right handles. Confirm:**
  - Text wraps as the box narrows.
  - The blue outline and handles are visible.
  - The dimension label appears during drag and disappears on release.
  - `scaleX`/`scaleY` remain at 1 (browser devtools: `canvas.getActiveObject().scaleX`).

- [ ] **Step 3: Enable "Fixed height" in the properties panel. Confirm:**
  - All 8 handles appear.
  - The H input in the Transform section becomes editable.
  - Top / Mid / Bot vertical align buttons appear.

- [ ] **Step 4: Set vertical align to "Mid". Export. Confirm the exported image shows the text vertically centred within the fixed frame.**

- [ ] **Step 5: Set vertical align to "Bot". Export. Confirm text sits at the bottom of the frame.**

- [ ] **Step 6: Disable "Fixed height". Export. Confirm text renders at the top (autoHeight ignores vertical_align).**

- [ ] **Step 7: Run the full test suite:**

```
pytest tests/ -v
```

Expected: all tests PASS.
