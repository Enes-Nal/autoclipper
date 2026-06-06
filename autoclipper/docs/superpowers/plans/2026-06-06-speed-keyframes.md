# Speed Keyframes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-segment speed keyframes to the timeline — users place dots on a speed lane, speed interpolates between them, preview uses `playbackRate`, export approximates via FFmpeg sub-clips.

**Architecture:** Speed keyframes live as `speedKeyframes: [{t, speed}]` on each segment (t = seconds relative to `sourceStart`). A SVG speed lane below the clip track visualizes the curve; a bottom strip (like the color strip) lists keyframes for editing. Export splits each segment into constant-speed sub-clips at keyframe boundaries and concatenates them.

**Tech Stack:** Vanilla JS, HTML/CSS (single-file frontend), Python + FFmpeg (export), pytest

---

## File Map

| File | Change |
|------|--------|
| `frontend/index.html` | All JS and HTML changes (single-file app) |
| `exporter.py` | Add `_speed_kfs_to_subsegs()`, update `build_segment_inputs()` |
| `tests/test_exporter.py` | New tests for speed sub-seg logic |

---

## Task 1: Data model + interpolation helper

**Files:**
- Modify: `frontend/index.html:4988-4997` (`tlNewSeg`)
- Modify: `frontend/index.html` (after `tlNewSeg`, add helper)

- [ ] **Step 1: Add `speedKeyframes` field to `tlNewSeg`**

Find `tlNewSeg` at line ~4988 and replace:
```js
function tlNewSeg(sourceStart, sourceEnd, trackStart, color, clipId) {
  return {
    id: 'seg_' + Math.random().toString(36).slice(2, 9),
    clipId: clipId || null,
    sourceStart,
    sourceEnd,
    trackStart,
    color: color || { brightness: 0, contrast: 0, saturation: 0, hue: 0 },
    speedKeyframes: []
  };
}
```

- [ ] **Step 2: Add `tlInterpolateSpeed` helper directly after `tlNewSeg`**

```js
function tlInterpolateSpeed(keyframes, t) {
  if (!keyframes || keyframes.length === 0) return 1;
  const sorted = [...keyframes].sort((a, b) => a.t - b.t);
  if (t <= sorted[0].t) return sorted[0].speed;
  if (t >= sorted[sorted.length - 1].t) return sorted[sorted.length - 1].speed;
  for (let i = 0; i < sorted.length - 1; i++) {
    const a = sorted[i], b = sorted[i + 1];
    if (t >= a.t && t <= b.t) {
      const frac = (t - a.t) / (b.t - a.t);
      return a.speed + frac * (b.speed - a.speed);
    }
  }
  return 1;
}
```

- [ ] **Step 3: Verify in browser console**

Open the app, open DevTools console, run:
```js
console.log(tlInterpolateSpeed([], 5));                                         // 1
console.log(tlInterpolateSpeed([{t:0,speed:1},{t:10,speed:0.5}], 5));           // 0.75
console.log(tlInterpolateSpeed([{t:0,speed:1},{t:10,speed:0.5}], 0));           // 1
console.log(tlInterpolateSpeed([{t:0,speed:1},{t:10,speed:0.5}], 10));          // 0.5
console.log(tlInterpolateSpeed([{t:0,speed:1},{t:10,speed:0.5}], 15));          // 0.5
```
Expected: all assertions match comments.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat(speed): add speedKeyframes to segment data model + tlInterpolateSpeed helper"
```

---

## Task 2: Speed lane HTML + CSS

**Files:**
- Modify: `frontend/index.html:415-443` (CSS section)
- Modify: `frontend/index.html:716-730` (tracks HTML)

- [ ] **Step 1: Add CSS for speed lane**

Find the CSS block near line 415 (`#timeline-panel`, `#tl-clips-area`, etc.) and add:

```css
#tl-track-speed{position:relative;height:64px;background:#111;border-top:1px solid var(--b1);min-width:600px;cursor:crosshair;flex-shrink:0}
.tl-speed-svg{position:absolute;top:0;left:0;width:100%;height:100%;overflow:visible;pointer-events:none}
.tl-speed-dot{cursor:grab;pointer-events:all}
.tl-speed-dot:active{cursor:grabbing}
.tl-speed-grid-line{stroke:var(--b1);stroke-width:1;stroke-dasharray:3 3}
.tl-speed-baseline{stroke:rgba(34,197,94,0.2);stroke-width:1}
#tl-speed-strip{background:var(--s2);border-top:1px solid var(--b1);padding:8px 12px;display:none;align-items:center;gap:10px;flex-shrink:0;flex-wrap:wrap}
#tl-speed-strip.vis{display:flex}
.tl-speed-kf-row{display:flex;align-items:center;gap:6px;padding:3px 6px;border-radius:4px;background:var(--s1)}
.tl-speed-kf-t{font-size:9px;color:var(--sub);width:34px;flex-shrink:0}
.tl-speed-kf-sl{flex:1;accent-color:var(--acc)}
.tl-speed-kf-val{font-size:10px;font-weight:700;font-family:monospace;width:36px;text-align:right;color:var(--tx)}
.tl-speed-kf-del{background:none;border:none;color:var(--sub);cursor:pointer;font-size:12px;padding:0 2px;line-height:1}
.tl-speed-kf-del:hover{color:var(--danger)}
.tl-speed-preset{padding:2px 6px;border:1px solid var(--b1);border-radius:4px;background:var(--s2);color:var(--sub);font-size:10px;cursor:pointer}
.tl-speed-preset:hover{border-color:var(--acc);color:var(--acc)}
```

- [ ] **Step 2: Add "Speed" label row in `#tl-labels` and speed track + strip in HTML**

Find the `#tl-labels` / `#tl-clips-area` block (~line 716) and replace it with:

```html
  <!-- tracks -->
  <div id="tl-tracks">
    <div id="tl-labels">
      <div class="tl-track-label">Video</div>
      <div class="tl-track-label">Text</div>
      <div class="tl-track-label">Audio</div>
      <div class="tl-track-label">SFX</div>
      <div class="tl-track-label" style="height:64px;line-height:64px">Speed</div>
    </div>
    <div id="tl-clips-area">
      <div class="tl-track-row" id="tl-track-video"></div>
      <div class="tl-track-row" id="tl-track-text"></div>
      <div class="tl-track-row" id="tl-track-audio"></div>
      <div class="tl-track-row" id="tl-track-sfx"></div>
      <div id="tl-track-speed"></div>
      <div id="tl-playhead"></div>
    </div>
  </div>
  <!-- speed strip -->
  <div id="tl-speed-strip">
    <span class="tl-cs-lbl">Speed</span>
    <div id="tl-speed-kf-list" style="display:flex;gap:4px;flex-wrap:wrap;flex:1"></div>
    <div style="display:flex;gap:3px;flex-shrink:0">
      <button class="tl-speed-preset" onclick="tlSpeedPreset(0.25)">0.25×</button>
      <button class="tl-speed-preset" onclick="tlSpeedPreset(0.5)">0.5×</button>
      <button class="tl-speed-preset" style="border-color:rgba(34,197,94,0.4);color:var(--acc)" onclick="tlSpeedPreset(1)">1×</button>
      <button class="tl-speed-preset" onclick="tlSpeedPreset(2)">2×</button>
      <button class="tl-speed-preset" onclick="tlSpeedPreset(4)">4×</button>
    </div>
    <button class="tl-btn" onclick="tlSpeedAddKf()" style="flex-shrink:0">+ Add</button>
    <button class="tl-btn" onclick="tlToggleSpeed()" style="margin-left:auto;flex-shrink:0">Close</button>
  </div>
```

- [ ] **Step 3: Add "Speed" toolbar button in `#tl-toolbar` (after the Color button, ~line 692)**

```html
    <button class="tl-btn" id="tl-speed-btn" onclick="tlToggleSpeed()" disabled>
      <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m13 2-2 2.5h3L12 7"/><path d="M10 14 4 4"/><path d="m15.5 6.5-5 5"/><path d="M18 11a8 8 0 1 1-8.9-7.9"/></svg>
      Speed
    </button>
```

(Place this after the Color `<button>` block and before the Delete `<button>` block.)

- [ ] **Step 4: Check the timeline renders without JS errors**

Open the app, toggle the timeline open. The Speed label and empty speed lane should be visible. No console errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat(speed): add speed lane HTML, CSS, toolbar button, and speed strip scaffold"
```

---

## Task 3: Speed lane rendering

**Files:**
- Modify: `frontend/index.html` (JS section — add after `tlRenderTrack`)

- [ ] **Step 1: Add `tlRenderSpeedLane()` function**

Add this function directly after `tlRenderTrack`:

```js
const TL_SPEED_MIN = 0.1, TL_SPEED_MAX = 8;

function tlSpeedToY(speed, h) {
  return h * (1 - (speed - TL_SPEED_MIN) / (TL_SPEED_MAX - TL_SPEED_MIN));
}
function tlYToSpeed(y, h) {
  const raw = TL_SPEED_MIN + (1 - y / h) * (TL_SPEED_MAX - TL_SPEED_MIN);
  return Math.max(TL_SPEED_MIN, Math.min(TL_SPEED_MAX, raw));
}

function tlRenderSpeedLane() {
  const lane = document.getElementById('tl-track-speed');
  if (!lane) return;
  const totalWidth = Math.max(tlTotalDuration() * tlPixelsPerSec + 60, 600);
  lane.style.width = totalWidth + 'px';

  const H = 64;
  const y1x  = tlSpeedToY(1,   H);
  const y05x = tlSpeedToY(0.5, H);
  const y2x  = tlSpeedToY(2,   H);

  // Build polyline points and dot data across all segments
  let points = [];
  let dots = [];
  const sorted = [...tlSegments].sort((a, b) => a.trackStart - b.trackStart);

  for (const seg of sorted) {
    const dur = seg.sourceEnd - seg.sourceStart;
    const kfs = seg.speedKeyframes || [];

    if (kfs.length === 0) {
      // Flat line at 1×
      const x0 = tlSecsToX(seg.trackStart);
      const x1 = tlSecsToX(seg.trackStart + dur);
      points.push([x0, tlSpeedToY(1, H)], [x1, tlSpeedToY(1, H)]);
    } else {
      const sortedKfs = [...kfs].sort((a, b) => a.t - b.t);
      // Leftmost point: extrapolate flat from first kf to segment start
      const x0 = tlSecsToX(seg.trackStart);
      points.push([x0, tlSpeedToY(sortedKfs[0].speed, H)]);
      for (const kf of sortedKfs) {
        const x = tlSecsToX(seg.trackStart + kf.t);
        const y = tlSpeedToY(kf.speed, H);
        points.push([x, y]);
        dots.push({ segId: seg.id, kfT: kf.t, x, y });
      }
      // Rightmost: extrapolate flat from last kf to segment end
      const x1 = tlSecsToX(seg.trackStart + dur);
      points.push([x1, tlSpeedToY(sortedKfs[sortedKfs.length - 1].speed, H)]);
    }
  }

  const ptStr = points.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');

  const dotsSvg = dots.map(d =>
    `<circle class="tl-speed-dot" cx="${d.x.toFixed(1)}" cy="${d.y.toFixed(1)}" r="5"
      fill="var(--acc)" stroke="#0d0d0d" stroke-width="1.5"
      onmousedown="tlSpeedDotMousedown(event,'${d.segId}',${d.kfT})"
      oncontextmenu="tlSpeedDotRightClick(event,'${d.segId}',${d.kfT})"
    />`
  ).join('');

  lane.innerHTML = `
    <svg class="tl-speed-svg" style="pointer-events:none" viewBox="0 0 ${totalWidth} ${H}" preserveAspectRatio="none"
         width="${totalWidth}" height="${H}">
      <line x1="0" y1="${y05x.toFixed(1)}" x2="${totalWidth}" y2="${y05x.toFixed(1)}" class="tl-speed-grid-line"/>
      <line x1="0" y1="${y1x.toFixed(1)}"  x2="${totalWidth}" y2="${y1x.toFixed(1)}"  class="tl-speed-baseline"/>
      <line x1="0" y1="${y2x.toFixed(1)}"  x2="${totalWidth}" y2="${y2x.toFixed(1)}"  class="tl-speed-grid-line"/>
      <polyline points="${ptStr}" fill="none" stroke="var(--acc)" stroke-width="1.5" opacity="0.8"/>
      ${dotsSvg}
    </svg>`;

  // Re-attach dot event listeners (inline handlers reference globals)
  lane.querySelectorAll('.tl-speed-dot').forEach(el => { el.style.pointerEvents = 'all'; });
  lane.addEventListener('click', tlSpeedLaneClick, { once: false });
}
```

- [ ] **Step 2: Call `tlRenderSpeedLane()` from `tlRender()`**

Find `tlRender()` (~line 5050) and add `tlRenderSpeedLane();` after the existing `tlRenderTrack(...)` calls:

```js
function tlRender() {
  if (!ENABLE_TIMELINE || !tlOpen) return;
  tlRenderRuler();
  tlRenderTrack('tl-track-video', tlSegments, 'rgba(34,197,94,0.3)');
  tlRenderTrack('tl-track-text',  [], 'rgba(99,102,241,0.3)');
  tlRenderTrack('tl-track-audio', [], 'rgba(245,158,11,0.3)');
  tlRenderTrack('tl-track-sfx',   [], 'rgba(239,68,68,0.3)');
  tlRenderSpeedLane();
  tlRenderPlayhead();
  tlRenderTime();
  tlUpdateToolbar();
}
```

- [ ] **Step 3: Verify speed lane renders**

Open the app, load a video, open the timeline. The speed lane should show a flat green line at the 1× position with 0.5× and 2× dashed grid lines.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat(speed): render speed lane SVG curve below clip track"
```

---

## Task 4: Speed lane interactions (click to add, drag, right-click delete)

**Files:**
- Modify: `frontend/index.html` (JS section)

- [ ] **Step 1: Add lane click handler to add keyframes**

Add after `tlRenderSpeedLane`:

```js
function tlSpeedLaneClick(e) {
  if (e.target.classList.contains('tl-speed-dot')) return; // dot click — skip
  const lane = document.getElementById('tl-track-speed');
  if (!lane) return;
  const rect = lane.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  const clickTimeline = tlXToSecs(x);
  const speed = tlYToSpeed(y, 64);

  // Find which segment this timeline position belongs to
  const seg = tlSegments.find(s => {
    const dur = s.sourceEnd - s.sourceStart;
    return clickTimeline >= s.trackStart && clickTimeline < s.trackStart + dur;
  });
  if (!seg) return;

  const t = clickTimeline - seg.trackStart; // relative to segment start
  // Avoid duplicate t values (within 0.05s)
  const dup = seg.speedKeyframes.find(k => Math.abs(k.t - t) < 0.05);
  if (dup) { dup.speed = parseFloat(speed.toFixed(3)); }
  else { seg.speedKeyframes.push({ t: parseFloat(t.toFixed(3)), speed: parseFloat(speed.toFixed(3)) }); }

  tlSelectedSegId = seg.id;
  tlRender();
  if (tlSpeedOpen) tlRenderSpeedStrip();
  if (typeof saveHist === 'function') saveHist();
}
```

- [ ] **Step 2: Add dot drag state and dot mousedown handler**

```js
let _tlSpeedDrag = null; // { segId, kfT, startX, startY, origT, origSpeed }

function tlSpeedDotMousedown(e, segId, kfT) {
  e.stopPropagation();
  e.preventDefault();
  const seg = tlSegments.find(s => s.id === segId);
  const kf  = seg?.speedKeyframes.find(k => Math.abs(k.t - kfT) < 0.001);
  if (!kf) return;
  _tlSpeedDrag = { segId, kfT, startX: e.clientX, startY: e.clientY, origT: kf.t, origSpeed: kf.speed };
  tlSelectedSegId = segId;
  tlRender();
}
```

- [ ] **Step 3: Add dot drag to global `mousemove` handler**

Inside the existing `document.addEventListener('mousemove', ...)` (~line 5351), add a new `else if` branch after the `_tlDragSeg` branch:

```js
  } else if (_tlSpeedDrag) {
    const seg = tlSegments.find(s => s.id === _tlSpeedDrag.segId);
    if (!seg) return;
    const kf = seg.speedKeyframes.find(k => Math.abs(k.t - _tlSpeedDrag.kfT) < 0.001);
    if (!kf) return;

    const dx = e.clientX - _tlSpeedDrag.startX;
    const dy = e.clientY - _tlSpeedDrag.startY;
    const dur = seg.sourceEnd - seg.sourceStart;

    // Horizontal: move t, clamp to [0, dur]
    const newT = Math.max(0, Math.min(dur, _tlSpeedDrag.origT + tlXToSecs(dx)));
    // Vertical: change speed
    const lane = document.getElementById('tl-track-speed');
    const H = lane ? lane.offsetHeight : 64;
    const newSpeed = Math.max(TL_SPEED_MIN, Math.min(TL_SPEED_MAX,
      _tlSpeedDrag.origSpeed - (dy / H) * (TL_SPEED_MAX - TL_SPEED_MIN)
    ));

    kf.t = parseFloat(newT.toFixed(3));
    kf.speed = parseFloat(newSpeed.toFixed(3));
    _tlSpeedDrag.kfT = kf.t; // track new t for subsequent moves

    tlRender();
    if (tlSpeedOpen) tlRenderSpeedStrip();
  }
```

- [ ] **Step 4: Add dot drag release to global `mouseup` handler**

Inside the existing `document.addEventListener('mouseup', ...)` (~line 5384), add:

```js
  if (_tlSpeedDrag) {
    _tlSpeedDrag = null;
    tlRender();
    if (typeof saveHist === 'function') saveHist();
  }
```

- [ ] **Step 5: Add right-click to delete keyframe**

```js
function tlSpeedDotRightClick(e, segId, kfT) {
  e.preventDefault();
  e.stopPropagation();
  const seg = tlSegments.find(s => s.id === segId);
  if (!seg) return;
  seg.speedKeyframes = seg.speedKeyframes.filter(k => Math.abs(k.t - kfT) >= 0.001);
  tlRender();
  if (tlSpeedOpen) tlRenderSpeedStrip();
  if (typeof saveHist === 'function') saveHist();
}
```

- [ ] **Step 6: Verify interactions**

Load a video, open timeline. Click the speed lane — a green dot should appear. Drag it left/right (moves time), drag up/down (changes speed). Right-click a dot — it disappears. Curve redraws in real time.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat(speed): speed lane click-to-add, drag, right-click-delete keyframes"
```

---

## Task 5: Speed strip (keyframe list panel)

**Files:**
- Modify: `frontend/index.html` (JS section)

- [ ] **Step 1: Add `tlSpeedOpen` state variable**

Near the other `tl*` state variables (~line 4960), add:

```js
let tlSpeedOpen = false;
```

- [ ] **Step 2: Add `tlToggleSpeed()` function**

```js
function tlToggleSpeed() {
  if (!ENABLE_TIMELINE) return;
  tlSpeedOpen = !tlSpeedOpen;
  document.getElementById('tl-speed-strip')?.classList.toggle('vis', tlSpeedOpen);
  document.getElementById('tl-speed-btn')?.classList.toggle('on', tlSpeedOpen);
  if (tlSpeedOpen) tlRenderSpeedStrip();
}
```

- [ ] **Step 3: Add `tlRenderSpeedStrip()` function**

```js
function tlRenderSpeedStrip() {
  const list = document.getElementById('tl-speed-kf-list');
  if (!list) return;
  const seg = tlSegments.find(s => s.id === tlSelectedSegId);
  if (!seg) { list.innerHTML = '<span style="font-size:10px;color:var(--sub)">Select a segment</span>'; return; }

  const kfs = [...(seg.speedKeyframes || [])].sort((a, b) => a.t - b.t);
  if (kfs.length === 0) {
    list.innerHTML = '<span style="font-size:10px;color:var(--sub)">No keyframes — click the speed lane or use presets</span>';
    return;
  }

  list.innerHTML = kfs.map((kf, i) => {
    const mm = String(Math.floor(kf.t / 60)).padStart(1,'0');
    const ss = (kf.t % 60).toFixed(1).padStart(4,'0');
    const pct = ((kf.speed - TL_SPEED_MIN) / (TL_SPEED_MAX - TL_SPEED_MIN) * 100).toFixed(1);
    return `<div class="tl-speed-kf-row">
      <span class="tl-speed-kf-t">${mm}:${ss}</span>
      <input type="range" class="tl-speed-kf-sl" min="${TL_SPEED_MIN}" max="${TL_SPEED_MAX}" step="0.05"
        value="${kf.speed}" style="width:80px"
        oninput="tlSpeedKfChange('${seg.id}',${kf.t},parseFloat(this.value));this.nextElementSibling.textContent=parseFloat(this.value).toFixed(2)+'×'">
      <span class="tl-speed-kf-val">${kf.speed.toFixed(2)}×</span>
      <button class="tl-speed-kf-del" onclick="tlSpeedKfDelete('${seg.id}',${kf.t})">✕</button>
    </div>`;
  }).join('');
}
```

- [ ] **Step 4: Add `tlSpeedKfChange`, `tlSpeedKfDelete`, `tlSpeedAddKf`, `tlSpeedPreset`**

```js
function tlSpeedKfChange(segId, kfT, newSpeed) {
  const seg = tlSegments.find(s => s.id === segId);
  const kf  = seg?.speedKeyframes.find(k => Math.abs(k.t - kfT) < 0.001);
  if (!kf) return;
  kf.speed = parseFloat(newSpeed.toFixed(3));
  tlRender();
}

function tlSpeedKfDelete(segId, kfT) {
  const seg = tlSegments.find(s => s.id === segId);
  if (!seg) return;
  seg.speedKeyframes = seg.speedKeyframes.filter(k => Math.abs(k.t - kfT) >= 0.001);
  tlRender();
  tlRenderSpeedStrip();
  if (typeof saveHist === 'function') saveHist();
}

function tlSpeedAddKf() {
  const seg = tlSegments.find(s => s.id === tlSelectedSegId);
  if (!seg) return;
  // Add at current playhead position (source-relative), speed 1
  const srcT = Math.max(0, Math.min(seg.sourceEnd - seg.sourceStart,
    tlPlayheadTime - seg.trackStart));
  const dup = seg.speedKeyframes.find(k => Math.abs(k.t - srcT) < 0.05);
  if (!dup) seg.speedKeyframes.push({ t: parseFloat(srcT.toFixed(3)), speed: 1 });
  tlRender();
  tlRenderSpeedStrip();
  if (typeof saveHist === 'function') saveHist();
}

function tlSpeedPreset(speed) {
  const seg = tlSegments.find(s => s.id === tlSelectedSegId);
  if (!seg) return;
  seg.speedKeyframes = [{ t: 0, speed }];
  tlRender();
  tlRenderSpeedStrip();
  if (typeof saveHist === 'function') saveHist();
}
```

- [ ] **Step 5: Call `tlRenderSpeedStrip()` when selected segment changes**

In `tlClipMousedown` (~line 5167), after `tlRender()`:
```js
  if (tlSpeedOpen) tlRenderSpeedStrip();
```

- [ ] **Step 6: Enable/disable Speed button in `tlUpdateToolbar()`**

In `tlUpdateToolbar()` (~line 5115), add after the existing `colorBtn.disabled` line:
```js
  const speedBtn = document.getElementById('tl-speed-btn');
  if (speedBtn) speedBtn.disabled = !hasSel;
```

- [ ] **Step 7: Verify speed strip**

Select a segment, click Speed button. Strip opens. Click lane to add keyframes — they appear as rows in the strip with sliders. Drag sliders — curve updates. Click ✕ — keyframe removed. Presets replace all keyframes with a single constant value.

- [ ] **Step 8: Commit**

```bash
git add frontend/index.html
git commit -m "feat(speed): speed strip keyframe list with add/edit/delete/presets"
```

---

## Task 6: Segment badge

**Files:**
- Modify: `frontend/index.html` (`tlRenderTrack` function, ~line 5085)

- [ ] **Step 1: Add `tlSpeedBadge()` helper**

Add directly before `tlRenderTrack`:

```js
function tlSpeedBadge(seg) {
  const kfs = seg.speedKeyframes || [];
  if (kfs.length === 0) return '';
  const speeds = kfs.map(k => k.speed);
  const allSame = speeds.every(s => Math.abs(s - speeds[0]) < 0.01);
  const v = allSame ? speeds[0] : null;
  const isNormal = allSame && Math.abs(speeds[0] - 1) < 0.01;
  if (isNormal) return '';
  const label = v !== null ? `${v.toFixed(2).replace(/\.?0+$/,'')}×` : '~';
  const color = v === null ? '#f59e0b' : (v < 1 ? '#f59e0b' : '#ef4444');
  return `<span style="background:${color}22;border:1px solid ${color}55;border-radius:3px;padding:1px 4px;font-size:9px;font-weight:700;color:${color};flex-shrink:0">${label}</span>`;
}
```

- [ ] **Step 2: Update `tlRenderTrack` to include the badge**

Replace the `row.innerHTML = clips.map(seg => {...})` block in `tlRenderTrack` (~line 5090):

```js
  row.innerHTML = clips.map(seg => {
    const x = tlSecsToX(seg.trackStart);
    const w = Math.max(4, tlSecsToX(seg.sourceEnd - seg.sourceStart));
    const sel = seg.id === tlSelectedSegId;
    const badge = tlSpeedBadge(seg);
    return `<div class="tl-clip${sel ? ' sel' : ''}" data-seg="${seg.id}"
      style="left:${x}px;width:${w}px;background:${color};border:1.5px solid ${sel ? '#fff' : color}"
      onmousedown="tlClipMousedown(event,'${seg.id}')">
      <div class="tl-handle tl-handle-l" onmousedown="tlHandleMousedown(event,'${seg.id}','l')"></div>
      <span style="pointer-events:none;padding-left:4px;opacity:.85;overflow:hidden;flex:1">${tlFmt(seg.sourceStart)}-${tlFmt(seg.sourceEnd)}</span>
      ${badge}
      <div class="tl-handle tl-handle-r" onmousedown="tlHandleMousedown(event,'${seg.id}','r')"></div>
    </div>`;
  }).join('');
```

- [ ] **Step 3: Verify badge**

Set a segment to 0.5× via preset. The segment strip should show an amber `0.5×` badge. Set two different keyframes. Badge should show `~`. Reset to 1× — badge disappears.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat(speed): speed badge on segment strip (amber for slow, red for fast)"
```

---

## Task 7: Preview playback rate

**Files:**
- Modify: `frontend/index.html` (`tlTogglePlay` RAF loop, ~line 5194)

- [ ] **Step 1: Update the RAF loop to set `playbackRate`**

Inside `tlTogglePlay()`, find the `frame` inner function (~line 5206). Replace:

```js
    const frame = () => {
      if (!_tlPlaying) return;
      const vt = _tlVideoEl.currentTime;
      const activeSeg = tlSegments.find(s => vt >= s.sourceStart && vt < s.sourceEnd);
      if (activeSeg) {
        tlPlayheadTime = activeSeg.trackStart + (vt - activeSeg.sourceStart);
      } else {
        const sorted = [...tlSegments].sort((a, b) => a.sourceStart - b.sourceStart);
        const nextSeg = sorted.find(s => s.sourceStart > vt);
        if (nextSeg) {
          _tlVideoEl.currentTime = nextSeg.sourceStart;
          tlPlayheadTime = nextSeg.trackStart;
        } else {
          _tlVideoEl.pause();
          _tlPlaying = false;
          _tlVideoEl.playbackRate = 1;
          const btn = document.getElementById('tl-play-btn');
          if (btn) btn.textContent = '▶ Play';
          tlRenderPlayhead();
          tlRenderTime();
          tlUpdateToolbar();
          return;
        }
      }
      // Apply speed keyframes
      if (activeSeg) {
        const srcT = _tlVideoEl.currentTime - activeSeg.sourceStart;
        const rate = tlInterpolateSpeed(activeSeg.speedKeyframes || [], srcT);
        if (Math.abs(_tlVideoEl.playbackRate - rate) > 0.01) _tlVideoEl.playbackRate = rate;
      }
      tlRenderPlayhead();
      tlRenderTime();
      tlUpdateToolbar();
      _tlRafId = requestAnimationFrame(frame);
    };
```

- [ ] **Step 2: Reset `playbackRate` when pausing**

In the pause branch of `tlTogglePlay` (~line 5197):
```js
    _tlVideoEl.pause();
    _tlVideoEl.playbackRate = 1;
    _tlPlaying = false;
    cancelAnimationFrame(_tlRafId);
```

- [ ] **Step 3: Verify playback rate**

Set a segment's first keyframe to 0.5× (using preset or lane click). Hit play. Video should play at half speed. Open DevTools and watch `document.getElementById('preview-video').playbackRate` — it should update to ~0.5 during playback and return to 1 on pause.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat(speed): apply speed keyframes to playbackRate during preview playback"
```

---

## Task 8: Split preserves speed keyframes

**Files:**
- Modify: `frontend/index.html` (`tlSplit` function, ~line 5243)

- [ ] **Step 1: Update `tlSplit` to distribute keyframes to left/right segments**

Replace the `tlSplit` function body:

```js
function tlSplit() {
  if (!ENABLE_TIMELINE) return;
  const seg = tlSegments.find(s => s.id === tlSelectedSegId);
  if (!seg) return;
  const splitVideoTime = tlTimelineToVideoTime(tlPlayheadTime);
  if (splitVideoTime <= seg.sourceStart + 0.05 || splitVideoTime >= seg.sourceEnd - 0.05) return;

  const splitRelT = splitVideoTime - seg.sourceStart; // relative to segment
  const speedAtSplit = tlInterpolateSpeed(seg.speedKeyframes || [], splitRelT);

  // Left: keyframes with t < splitRelT, plus a closing keyframe at the split point
  const leftKfs = (seg.speedKeyframes || [])
    .filter(k => k.t < splitRelT - 0.001)
    .map(k => ({ ...k }));
  leftKfs.push({ t: parseFloat(splitRelT.toFixed(3)), speed: parseFloat(speedAtSplit.toFixed(3)) });

  // Right: keyframes with t > splitRelT, re-zeroed to new segment start
  const rightKfs = (seg.speedKeyframes || [])
    .filter(k => k.t > splitRelT + 0.001)
    .map(k => ({ t: parseFloat((k.t - splitRelT).toFixed(3)), speed: k.speed }));
  rightKfs.unshift({ t: 0, speed: parseFloat(speedAtSplit.toFixed(3)) });

  const left  = tlNewSeg(seg.sourceStart, splitVideoTime, seg.trackStart, Object.assign({}, seg.color));
  left.speedKeyframes = leftKfs;
  const rightTrackStart = seg.trackStart + (splitVideoTime - seg.sourceStart);
  const right = tlNewSeg(splitVideoTime, seg.sourceEnd, rightTrackStart, Object.assign({}, seg.color));
  right.speedKeyframes = rightKfs;

  const idx = tlSegments.indexOf(seg);
  tlSegments.splice(idx, 1, left, right);
  tlSelectedSegId = left.id;
  tlRender();
  if (tlSpeedOpen) tlRenderSpeedStrip();
  if (typeof saveHist === 'function') saveHist();
}
```

- [ ] **Step 2: Verify split preserves speed**

Add keyframes: 0s→1×, 5s→0.5×, 10s→2×. Split at 7.5s. Left segment should have keyframes 0→1×, 5→0.5×, 7.5→interpolated. Right segment should have keyframes 0→interpolated, 2.5→2× (re-zeroed).

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat(speed): split distributes speed keyframes to left/right segments"
```

---

## Task 9: Export — speed sub-clips

**Files:**
- Modify: `exporter.py`
- Modify: `tests/test_exporter.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_exporter.py`:

```python
from exporter import _speed_kfs_to_subsegs, build_segment_inputs

def test_speed_kfs_no_keyframes():
    seg = {'sourceStart': 0, 'sourceEnd': 10, 'speedKeyframes': []}
    result = _speed_kfs_to_subsegs(seg)
    assert result == [(0.0, 10.0, 1.0)]

def test_speed_kfs_single_keyframe():
    seg = {'sourceStart': 0, 'sourceEnd': 10, 'speedKeyframes': [{'t': 0, 'speed': 0.5}]}
    result = _speed_kfs_to_subsegs(seg)
    assert len(result) == 1
    assert result[0][2] == pytest.approx(0.5)

def test_speed_kfs_two_keyframes():
    # 1× for first 5s, 0.5× for last 5s
    seg = {'sourceStart': 0, 'sourceEnd': 10,
           'speedKeyframes': [{'t': 0, 'speed': 1.0}, {'t': 5, 'speed': 0.5}]}
    result = _speed_kfs_to_subsegs(seg)
    # First interval midpoint at 2.5s → speed 1.0; second midpoint at 7.5s → speed 0.5
    assert any(abs(s[2] - 1.0) < 0.01 for s in result)
    assert any(abs(s[2] - 0.5) < 0.01 for s in result)

def test_speed_kfs_intervals_cover_full_range():
    seg = {'sourceStart': 2, 'sourceEnd': 8,
           'speedKeyframes': [{'t': 0, 'speed': 1.0}, {'t': 3, 'speed': 2.0}]}
    result = _speed_kfs_to_subsegs(seg)
    assert result[0][0] == pytest.approx(2.0)   # starts at sourceStart
    assert result[-1][1] == pytest.approx(8.0)  # ends at sourceEnd

def test_build_segment_inputs_speed_subclips():
    seg = {
        'sourceStart': 0, 'sourceEnd': 10, 'trackStart': 0,
        'color': {},
        'speedKeyframes': [{'t': 0, 'speed': 0.5}, {'t': 5, 'speed': 2.0}]
    }
    main_pre, extra, filter_parts, v_lbl, a_lbl, n = build_segment_inputs('vid.mp4', [seg])
    # Should produce multiple inputs (sub-clips)
    assert n > 1
    # setpts should appear in filter for speed adjustment
    assert any('setpts' in p for p in filter_parts)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd D:\Code\autoclipper
python -m pytest tests/test_exporter.py::test_speed_kfs_no_keyframes tests/test_exporter.py::test_speed_kfs_single_keyframe tests/test_exporter.py::test_speed_kfs_two_keyframes -v
```
Expected: `ImportError: cannot import name '_speed_kfs_to_subsegs'`

- [ ] **Step 3: Add `_speed_kfs_to_subsegs` to `exporter.py`**

Add after `_color_filter_suffix`:

```python
def _speed_kfs_to_subsegs(seg: dict) -> list[tuple[float, float, float]]:
    """
    Convert a segment's speedKeyframes into [(start, end, speed)] constant-speed intervals.
    start/end are absolute source times. speed is the constant multiplier for the interval.
    """
    kfs = seg.get('speedKeyframes', []) or []
    ss  = float(seg.get('sourceStart', 0))
    se  = float(seg.get('sourceEnd',   0))

    if not kfs:
        return [(ss, se, 1.0)]

    sorted_kfs = sorted(kfs, key=lambda k: float(k['t']))

    def interp(t_rel: float) -> float:
        if t_rel <= sorted_kfs[0]['t']:
            return float(sorted_kfs[0]['speed'])
        if t_rel >= sorted_kfs[-1]['t']:
            return float(sorted_kfs[-1]['speed'])
        for i in range(len(sorted_kfs) - 1):
            a, b = sorted_kfs[i], sorted_kfs[i + 1]
            if float(a['t']) <= t_rel <= float(b['t']):
                frac = (t_rel - float(a['t'])) / (float(b['t']) - float(a['t']))
                return float(a['speed']) + frac * (float(b['speed']) - float(a['speed']))
        return 1.0

    # Breakpoints in absolute source time: segment start, each keyframe, segment end
    abs_breakpoints = sorted(set(
        [ss] + [ss + float(k['t']) for k in sorted_kfs] + [se]
    ))
    # Clamp to [ss, se]
    abs_breakpoints = [max(ss, min(se, p)) for p in abs_breakpoints]
    abs_breakpoints = sorted(set(abs_breakpoints))

    result = []
    for i in range(len(abs_breakpoints) - 1):
        a, b = abs_breakpoints[i], abs_breakpoints[i + 1]
        if b - a < 0.01:  # skip sub-10ms intervals
            continue
        mid_rel = ((a + b) / 2) - ss
        speed = interp(mid_rel)
        result.append((a, b, round(speed, 4)))

    return result if result else [(ss, se, 1.0)]
```

- [ ] **Step 4: Update `build_segment_inputs` to use `_speed_kfs_to_subsegs`**

In `build_segment_inputs`, find the single-segment fast path (~line 80) and the multi-segment loop (~line 104). Replace the entire function with:

```python
def build_segment_inputs(video_path: str, segments: list) -> tuple[list, list, list, str, str, int]:
    if not segments:
        return [], [], [], '0:v', '0:a', 1

    segs = sorted(segments, key=lambda s: s.get('trackStart', 0))

    n = [0]
    def lbl(prefix='s'):
        n[0] += 1
        return f"{prefix}{n[0]}"

    def has_speed(seg):
        kfs = seg.get('speedKeyframes') or []
        if not kfs:
            return False
        return any(abs(float(k.get('speed', 1)) - 1.0) > 0.001 for k in kfs)

    # Expand each segment into constant-speed sub-segments
    all_subsegs = []  # list of (ss, se, speed, color)
    for seg in segs:
        c = seg.get('color', {})
        for (a, b, speed) in _speed_kfs_to_subsegs(seg):
            all_subsegs.append({'sourceStart': a, 'sourceEnd': b, 'speed': speed, 'color': c})

    n_inputs = len(all_subsegs)
    filter_parts = []
    vlabels = []
    alabels = []
    extra_vid_inputs = []
    main_pre_args = []

    for i, sub in enumerate(all_subsegs):
        ss    = sub['sourceStart']
        se    = sub['sourceEnd']
        speed = sub['speed']
        c     = sub['color']
        pre_args = ["-ss", str(ss), "-to", str(se)]
        if i == 0:
            main_pre_args = pre_args
        else:
            extra_vid_inputs.append((pre_args, video_path))

        vl = lbl('sv')
        al = lbl('sa')
        color_suffix = _color_filter_suffix(c)
        pts_expr = f"PTS*(1/{speed:.6f})" if abs(speed - 1.0) > 0.001 else "PTS-STARTPTS"
        filter_parts.append(f"[{i}:v]setpts={pts_expr}{color_suffix}[{vl}]")
        filter_parts.append(f"[{i}:a]asetpts=PTS*(1/{speed:.6f})[{al}]" if abs(speed - 1.0) > 0.001
                            else f"[{i}:a]asetpts=PTS-STARTPTS[{al}]")
        vlabels.append(vl)
        alabels.append(al)

    if n_inputs == 1 and not filter_parts[0].endswith(f'[{vlabels[0]}]'):
        # Shouldn't happen but safety net
        pass

    if n_inputs == 1:
        # Single sub-seg: check if any filter needed
        has_filter = abs(all_subsegs[0]['speed'] - 1.0) > 0.001 or bool(_color_filter_suffix(all_subsegs[0]['color']))
        if not has_filter:
            return main_pre_args, [], [], '0:v', '0:a', 1
        return main_pre_args, [], filter_parts, vlabels[0], alabels[0], 1

    # Multiple sub-segs: concat
    vout = lbl('vc')
    aout = lbl('ac')
    filter_parts.append(''.join(f'[{l}]' for l in vlabels) + f'concat=n={n_inputs}:v=1:a=0[{vout}]')
    filter_parts.append(''.join(f'[{l}]' for l in alabels) + f'concat=n={n_inputs}:v=0:a=1[{aout}]')
    return main_pre_args, extra_vid_inputs, filter_parts, vout, aout, n_inputs
```

- [ ] **Step 5: Add `import pytest` to test file**

At the top of `tests/test_exporter.py`, ensure `import pytest` is present.

- [ ] **Step 6: Run all tests**

```
python -m pytest tests/test_exporter.py -v
```
Expected: all tests pass, including the new speed tests.

- [ ] **Step 7: Verify existing export still works**

Run the app, load a video with no speed keyframes, export. The export should complete successfully with the same output as before. Check the FFmpeg command logged to console has no extra inputs for a speed-1 segment.

- [ ] **Step 8: Verify speed export**

Set a segment to 0.5× using the Speed preset. Export. Check the FFmpeg command contains `setpts=PTS*(1/0.500000)` and `asetpts=PTS*(1/0.500000)`. The exported video should play at half speed.

- [ ] **Step 9: Commit**

```bash
git add exporter.py tests/test_exporter.py
git commit -m "feat(speed): export speed keyframes as FFmpeg sub-clip approximation"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Data model: `speedKeyframes: [{t, speed}]` on segment — Task 1
- ✅ `tlInterpolateSpeed` helper — Task 1
- ✅ Speed lane SVG + grid lines — Task 3
- ✅ Click to add keyframe — Task 4
- ✅ Drag dot (t and speed) — Task 4
- ✅ Right-click to delete — Task 4
- ✅ Speed strip with keyframe list — Task 5
- ✅ Preset buttons — Task 5
- ✅ "+ Add" button at playhead position — Task 5
- ✅ Strip opens/closes via Speed toolbar button — Task 5
- ✅ Segment badge (amber slow, red fast, ~ for mixed) — Task 6
- ✅ Preview `playbackRate` — Task 7
- ✅ Reset `playbackRate` on pause — Task 7
- ✅ Split distributes keyframes — Task 8
- ✅ Export sub-clips — Task 9
- ✅ Backwards-compatible: empty `speedKeyframes` hits 1× fast path — Task 9

**Type/name consistency:**
- `tlInterpolateSpeed` — defined Task 1, used Tasks 7 and 8 ✅
- `TL_SPEED_MIN` / `TL_SPEED_MAX` — defined Task 3, used Tasks 4 and 5 ✅
- `tlSpeedOpen` — defined Task 5, used Tasks 5 and 6 ✅
- `_speed_kfs_to_subsegs` — defined and tested Task 9 ✅
- `tlRenderSpeedStrip` — defined Task 5, called Tasks 4, 5, 8 ✅
