# Timeline & Video Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a CapCut-style collapsible timeline panel to Cutly with split, trim, delete, reorder, and per-clip color grading, plus FFmpeg export integration.

**Architecture:** The timeline is a self-contained module injected into `frontend/index.html` inside `<!-- TIMELINE START -->` / `<!-- TIMELINE END -->` comment blocks, gated by `const ENABLE_TIMELINE = true`. The exporter gains a new `build_segment_filter()` function that prepends trim/color/concat filters before the existing overlay pipeline. Everything is backward-compatible — if `segments` is absent from the export payload, the exporter behaves exactly as before.

**Tech Stack:** Vanilla JS (no extra deps), HTML5 `<video>` element for scrub preview, CSS flex layout, Python + FFmpeg `trim`/`concat`/`eq`/`hue` filters for export.

---

## File Map

| File | Change |
|------|--------|
| `frontend/index.html` | Add CSS block, HTML panel, JS module — all inside TIMELINE START/END |
| `exporter.py` | Add `build_segment_filter()` function; update `export_video()` signature |
| `app.py` | Pass `segments` from request body to `export_video()` |
| `tests/test_exporter.py` | Add tests for `build_segment_filter()` |

---

## Task 1: Add timeline panel HTML and CSS

**Files:**
- Modify: `frontend/index.html` — add `#timeline-panel` below `#workspace` inside `#main`; add CSS

- [ ] **Step 1: Locate the closing tag of `#workspace` in `frontend/index.html`**

  Search for line containing `</div>` that closes `#workspace`. The structure is:
  ```
  <div id="main">
    <div id="topbar">...</div>
    <div id="workspace">       ← opens around line 538
      ...
    </div>                     ← find this closing tag
  </div>                       ← closes #main
  ```
  Open the file. Find the closing `</div>` of `#workspace` (search for `id="workspace"` to find the open, then find its matching close; it's around line 563).

- [ ] **Step 2: Insert TIMELINE CSS before `</style>` (end of the `<style>` block)**

  Add this block just before the closing `</style>` tag in the `<head>`. The `</style>` tag is around line 416.

  ```css
  /* ─── TIMELINE MODULE ────────────────────────────────── */
  #timeline-panel{flex-shrink:0;background:var(--s1);border-top:2px solid var(--b1);display:none;flex-direction:column;overflow:hidden;transition:border-color .2s}
  #timeline-panel.tl-open{display:flex;border-top-color:rgba(34,197,94,0.4)}
  #tl-toolbar{display:flex;align-items:center;gap:6px;padding:6px 10px;border-bottom:1px solid var(--b1);flex-shrink:0}
  #tl-toolbar .tl-sep{width:1px;height:16px;background:var(--b1);flex-shrink:0}
  .tl-btn{display:inline-flex;align-items:center;gap:4px;padding:4px 9px;border-radius:var(--rs);border:1px solid var(--b1);background:transparent;color:var(--sub);font-size:10px;font-weight:600;cursor:pointer;transition:.12s;white-space:nowrap}
  .tl-btn:hover{background:var(--s3);color:var(--tx);border-color:var(--b2)}
  .tl-btn.on{background:var(--accdim);color:var(--acc);border-color:rgba(34,197,94,0.4)}
  .tl-btn:disabled{opacity:.35;cursor:default}
  #tl-time{font-size:10px;color:var(--sub);font-family:monospace;min-width:70px;text-align:right}
  #tl-ruler{height:18px;background:var(--bg);border-bottom:1px solid var(--b1);position:relative;overflow:hidden;flex-shrink:0;display:flex;padding-left:90px}
  #tl-ruler-inner{flex:1;position:relative;overflow:hidden}
  #tl-tracks{flex:1;overflow-x:auto;overflow-y:hidden;display:flex;min-height:0;position:relative}
  #tl-tracks::-webkit-scrollbar{height:4px}
  #tl-tracks::-webkit-scrollbar-thumb{background:var(--mut);border-radius:2px}
  #tl-labels{width:90px;flex-shrink:0;display:flex;flex-direction:column;border-right:1px solid var(--b1)}
  .tl-track-label{height:28px;display:flex;align-items:center;padding:0 8px;font-size:9px;font-weight:700;color:var(--sub);text-transform:uppercase;letter-spacing:.8px;border-bottom:1px solid var(--b1);flex-shrink:0}
  #tl-clips-area{flex:1;position:relative;display:flex;flex-direction:column;min-width:600px}
  .tl-track-row{height:28px;border-bottom:1px solid var(--b1);position:relative;flex-shrink:0}
  .tl-clip{position:absolute;top:3px;height:22px;border-radius:3px;cursor:pointer;user-select:none;display:flex;align-items:center;padding:0 6px;font-size:9px;font-weight:600;overflow:hidden;white-space:nowrap;transition:filter .1s}
  .tl-clip.sel{box-shadow:0 0 0 1.5px #fff inset;filter:brightness(1.2)}
  .tl-clip:hover:not(.sel){filter:brightness(1.1)}
  .tl-clip .tl-handle{position:absolute;top:0;width:6px;height:100%;cursor:ew-resize;background:rgba(255,255,255,0.25);border-radius:2px;opacity:0;transition:opacity .1s}
  .tl-clip:hover .tl-handle,.tl-clip.sel .tl-handle{opacity:1}
  .tl-clip .tl-handle-l{left:0;border-radius:2px 0 0 2px}
  .tl-clip .tl-handle-r{right:0;border-radius:0 2px 2px 0}
  #tl-playhead{position:absolute;top:0;bottom:0;width:1px;background:#fff;pointer-events:none;z-index:10}
  #tl-playhead::before{content:'';position:absolute;top:-1px;left:-4px;width:9px;height:9px;background:#fff;border-radius:50%}
  #tl-color-strip{background:var(--s2);border-top:1px solid var(--b1);padding:8px 12px;display:none;align-items:center;gap:14px;flex-shrink:0;flex-wrap:wrap}
  #tl-color-strip.vis{display:flex}
  .tl-cs-lbl{font-size:9px;font-weight:700;color:var(--sub);text-transform:uppercase;letter-spacing:.8px;white-space:nowrap}
  .tl-cs-row{display:flex;align-items:center;gap:6px}
  .tl-cs-name{font-size:9px;color:var(--sub);min-width:58px}
  .tl-cs-sl{width:90px;cursor:pointer;-webkit-appearance:none;appearance:none;height:3px;border-radius:99px;background:var(--b2);outline:none}
  .tl-cs-sl::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;width:12px;height:12px;border-radius:50%;background:var(--acc);cursor:pointer;border:2px solid var(--bg)}
  .tl-cs-val{font-size:9px;color:var(--acc);min-width:28px;text-align:right;font-family:monospace}
  .tl-toggle-btn{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;border-radius:var(--rs);border:1px solid var(--b1);background:transparent;color:var(--sub);font-size:10px;font-weight:600;cursor:pointer;transition:.12s}
  .tl-toggle-btn:hover{background:var(--s3);color:var(--tx)}
  .tl-toggle-btn.tl-open{color:var(--acc);border-color:rgba(34,197,94,0.3)}
  ```

- [ ] **Step 3: Insert TIMELINE HTML after closing `</div>` of `#workspace` and before closing `</div>` of `#main`**

  Find the line pattern: the closing `</div>` of `#workspace` (around line 563 after SFX strip elements), followed shortly by `</div>` closing `#main`. Insert the following HTML between them:

  ```html
  <!-- TIMELINE START -->
  <div id="timeline-panel">
    <!-- toolbar -->
    <div id="tl-toolbar">
      <button class="tl-btn" id="tl-split-btn" onclick="tlSplit()" disabled title="Split at playhead (S)">
        <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/></svg>
        Split
      </button>
      <button class="tl-btn" id="tl-color-btn" onclick="tlToggleColor()" disabled>
        <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>
        Color
      </button>
      <button class="tl-btn" id="tl-delete-btn" onclick="tlDeleteSeg()" disabled>
        <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
        Delete
      </button>
      <div class="tl-sep"></div>
      <button class="tl-btn" id="tl-play-btn" onclick="tlTogglePlay()">▶ Play</button>
      <button class="tl-btn" onclick="tlSeek(0)">⏮</button>
      <div class="tl-sep"></div>
      <span id="tl-time">0:00 / 0:00</span>
      <div style="margin-left:auto"></div>
      <button class="tl-btn" onclick="tlClose()">▼ Hide</button>
    </div>
    <!-- ruler -->
    <div id="tl-ruler">
      <div id="tl-ruler-inner"></div>
    </div>
    <!-- tracks -->
    <div id="tl-tracks">
      <div id="tl-labels">
        <div class="tl-track-label">Video</div>
        <div class="tl-track-label">Text</div>
        <div class="tl-track-label">Audio</div>
        <div class="tl-track-label">SFX</div>
      </div>
      <div id="tl-clips-area">
        <div class="tl-track-row" id="tl-track-video"></div>
        <div class="tl-track-row" id="tl-track-text"></div>
        <div class="tl-track-row" id="tl-track-audio"></div>
        <div class="tl-track-row" id="tl-track-sfx"></div>
        <div id="tl-playhead"></div>
      </div>
    </div>
    <!-- color strip -->
    <div id="tl-color-strip">
      <span class="tl-cs-lbl">Color</span>
      <div class="tl-cs-row">
        <span class="tl-cs-name">Brightness</span>
        <input type="range" class="tl-cs-sl" id="tl-cs-bright" min="-100" max="100" value="0" oninput="tlColorChange('brightness',this.value)">
        <span class="tl-cs-val" id="tl-cs-bright-v">0</span>
      </div>
      <div class="tl-cs-row">
        <span class="tl-cs-name">Contrast</span>
        <input type="range" class="tl-cs-sl" id="tl-cs-contrast" min="-100" max="100" value="0" oninput="tlColorChange('contrast',this.value)">
        <span class="tl-cs-val" id="tl-cs-contrast-v">0</span>
      </div>
      <div class="tl-cs-row">
        <span class="tl-cs-name">Saturation</span>
        <input type="range" class="tl-cs-sl" id="tl-cs-sat" min="-100" max="100" value="0" oninput="tlColorChange('saturation',this.value)">
        <span class="tl-cs-val" id="tl-cs-sat-v">0</span>
      </div>
      <div class="tl-cs-row">
        <span class="tl-cs-name">Hue</span>
        <input type="range" class="tl-cs-sl" id="tl-cs-hue" min="-180" max="180" value="0" oninput="tlColorChange('hue',this.value)">
        <span class="tl-cs-val" id="tl-cs-hue-v">0°</span>
      </div>
    </div>
  </div>
  <!-- TIMELINE END -->
  ```

- [ ] **Step 4: Add the Timeline toggle button to the canvas toolbar**

  Find the canvas toolbar div (`<div class="cvs-toolbar">`) around line 574. After the last `<button>` in that toolbar (the snap button at ~line 586), insert:

  ```html
          <div class="tsep"></div>
          <button class="tl-toggle-btn" id="tl-toggle-btn" onclick="tlToggleOpen()" style="display:none">
            ▲ Timeline
          </button>
  ```

- [ ] **Step 5: Start the app and confirm the page loads without errors**

  ```bash
  python app.py
  ```
  Open http://localhost:5000. Open DevTools Console — should show no JS errors. The Timeline button is hidden (video not loaded yet). The panel is hidden.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): add HTML structure, CSS, and toggle button placeholder"
  ```

---

## Task 2: Initialize timeline state and wire to video load

**Files:**
- Modify: `frontend/index.html` — add TIMELINE JS module block

- [ ] **Step 1: Add the JS module block at the end of `<script>` section (before `</script>` of the main block)**

  Find the last `</script>` tag in `index.html`. Just **before** it, insert:

  ```javascript
  // ═══════════════════════════════════════════════════════════
  // TIMELINE MODULE — feature flag: set false to disable entirely
  // ═══════════════════════════════════════════════════════════
  const ENABLE_TIMELINE = true;

  // ── State ──────────────────────────────────────────────────
  let tlSegments = [];          // [{id,sourceStart,sourceEnd,trackStart,color:{brightness,contrast,saturation,hue}}]
  let tlDuration = 0;           // total source video duration in seconds
  let tlPlayheadTime = 0;       // seconds
  let tlSelectedSegId = null;   // id of selected segment, or null
  let tlColorOpen = false;      // color strip visible
  let tlOpen = false;           // panel open
  let tlPixelsPerSec = 30;      // zoom: pixels per second
  let _tlPlaying = false;
  let _tlRafId = null;
  let _tlVideoEl = null;        // reference to #preview-video

  function tlNewSeg(sourceStart, sourceEnd, trackStart, color) {
    return {
      id: 'seg_' + Math.random().toString(36).slice(2, 9),
      sourceStart,
      sourceEnd,
      trackStart,
      color: color || { brightness: 0, contrast: 0, saturation: 0, hue: 0 }
    };
  }

  function tlInit(durationSecs) {
    if (!ENABLE_TIMELINE) return;
    tlDuration = durationSecs;
    tlSegments = [tlNewSeg(0, durationSecs, 0)];
    tlSelectedSegId = null;
    tlPlayheadTime = 0;
    tlColorOpen = false;
    _tlVideoEl = document.getElementById('preview-video');
    // Show toggle button
    const btn = document.getElementById('tl-toggle-btn');
    if (btn) btn.style.display = 'inline-flex';
    // Restore open state from localStorage
    if (localStorage.getItem('tlOpen') === '1') tlOpen = true;
    const panel = document.getElementById('timeline-panel');
    if (panel) panel.classList.toggle('tl-open', tlOpen);
    tlRender();
  }
  ```

- [ ] **Step 2: Call `tlInit()` when video finishes downloading**

  Search for the line `downloadedVideoPath=msg.path;` (line ~4188). It's inside an SSE handler that fires when a download completes. After that line, find where `downloadedVideoCaption` and `downloadedVideoURL` are set, and add the tlInit call. The video element is `#preview-video` — get its duration from the `loadedmetadata` event.

  Find the `updateTplPreviews(url)` function (line ~3900). At the end of that function, after `vidEl.play().catch(()=>{});`, add:

  ```javascript
  vidEl.addEventListener('loadedmetadata', function onMeta() {
    vidEl.removeEventListener('loadedmetadata', onMeta);
    tlInit(vidEl.duration || 0);
  }, { once: true });
  if (vidEl.readyState >= 1 && vidEl.duration) tlInit(vidEl.duration);
  ```

- [ ] **Step 3: Add `tlToggleOpen`, `tlClose`, and localStorage persistence**

  Still in the TIMELINE MODULE block:

  ```javascript
  function tlToggleOpen() {
    if (!ENABLE_TIMELINE) return;
    tlOpen = !tlOpen;
    localStorage.setItem('tlOpen', tlOpen ? '1' : '0');
    const panel = document.getElementById('timeline-panel');
    if (panel) panel.classList.toggle('tl-open', tlOpen);
    const btn = document.getElementById('tl-toggle-btn');
    if (btn) btn.classList.toggle('tl-open', tlOpen);
    if (tlOpen) tlRender();
  }

  function tlClose() {
    tlOpen = false;
    localStorage.setItem('tlOpen', '0');
    document.getElementById('timeline-panel')?.classList.remove('tl-open');
    document.getElementById('tl-toggle-btn')?.classList.remove('tl-open');
  }
  ```

- [ ] **Step 4: Add a stub `tlRender()` so no errors occur**

  ```javascript
  function tlRender() {
    if (!ENABLE_TIMELINE || !tlOpen) return;
    // implemented in Task 3
  }
  ```

- [ ] **Step 5: Verify in browser**

  Reload http://localhost:5000. Download or load a video. The "▲ Timeline" button should appear in the canvas toolbar. Clicking it should show/hide the empty panel (with toolbar + track rows visible). DevTools Console: no errors.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): init state on video load, toggle open/close"
  ```

---

## Task 3: Render the timeline — ruler, clips, playhead

**Files:**
- Modify: `frontend/index.html` — implement `tlRender()`, ruler drawing, clip rendering

- [ ] **Step 1: Implement `tlRender()` in the TIMELINE MODULE block**

  Replace the stub `tlRender()` with:

  ```javascript
  function tlFmt(s) {
    const m = Math.floor(s / 60);
    const sec = (s % 60).toFixed(1).padStart(4, '0');
    return `${m}:${sec}`;
  }

  function tlSecsToX(secs) { return secs * tlPixelsPerSec; }
  function tlXToSecs(x)   { return x / tlPixelsPerSec; }

  function tlRenderRuler() {
    const inner = document.getElementById('tl-ruler-inner');
    if (!inner) return;
    const totalWidth = Math.max(tlDuration * tlPixelsPerSec + 60, inner.offsetWidth || 600);
    inner.style.width = totalWidth + 'px';
    // Draw tick marks every 5s
    let html = '';
    const step = tlDuration > 60 ? 10 : 5;
    for (let t = 0; t <= tlDuration + step; t += step) {
      const x = tlSecsToX(t);
      html += `<span style="position:absolute;left:${x}px;font-size:8px;color:var(--sub);top:4px;transform:translateX(-50%)">${tlFmt(t)}</span>`;
    }
    inner.innerHTML = html;
  }

  function tlRenderTrack(trackId, clips, color) {
    const row = document.getElementById(trackId);
    if (!row) return;
    const totalWidth = Math.max(tlDuration * tlPixelsPerSec + 60, 600);
    row.style.width = totalWidth + 'px';
    row.innerHTML = clips.map(seg => {
      const x = tlSecsToX(seg.trackStart);
      const w = Math.max(4, tlSecsToX(seg.sourceEnd - seg.sourceStart));
      const sel = seg.id === tlSelectedSegId;
      return `<div class="tl-clip${sel ? ' sel' : ''}" data-seg="${seg.id}"
        style="left:${x}px;width:${w}px;background:${color};border:1.5px solid ${sel ? '#fff' : color}"
        onmousedown="tlClipMousedown(event,'${seg.id}')">
        <div class="tl-handle tl-handle-l" data-handle="l" data-seg="${seg.id}" onmousedown="tlHandleMousedown(event,'${seg.id}','l')"></div>
        <span style="pointer-events:none;padding-left:4px;opacity:.85">${tlFmt(seg.sourceStart)}–${tlFmt(seg.sourceEnd)}</span>
        <div class="tl-handle tl-handle-r" data-handle="r" data-seg="${seg.id}" onmousedown="tlHandleMousedown(event,'${seg.id}','r')"></div>
      </div>`;
    }).join('');
  }

  function tlRenderPlayhead() {
    const ph = document.getElementById('tl-playhead');
    if (!ph) return;
    ph.style.left = tlSecsToX(tlPlayheadTime) + 'px';
  }

  function tlRenderTime() {
    const el = document.getElementById('tl-time');
    if (el) el.textContent = `${tlFmt(tlPlayheadTime)} / ${tlFmt(tlDuration)}`;
  }

  function tlUpdateToolbar() {
    const hasSel = tlSelectedSegId !== null;
    const seg = tlSegments.find(s => s.id === tlSelectedSegId);
    const canSplit = hasSel && seg &&
      tlPlayheadTime > seg.sourceStart + 0.1 &&
      tlPlayheadTime < seg.sourceEnd - 0.1;
    document.getElementById('tl-split-btn').disabled = !canSplit;
    document.getElementById('tl-color-btn').disabled = !hasSel;
    document.getElementById('tl-delete-btn').disabled = !hasSel || tlSegments.length <= 1;
  }

  function tlRender() {
    if (!ENABLE_TIMELINE || !tlOpen) return;
    tlRenderRuler();
    tlRenderTrack('tl-track-video', tlSegments, 'rgba(34,197,94,0.3)');
    // Text/audio/sfx tracks: static markers from existing layers (read-only display)
    tlRenderTrack('tl-track-text',  [], 'rgba(99,102,241,0.3)');
    tlRenderTrack('tl-track-audio', [], 'rgba(245,158,11,0.3)');
    tlRenderTrack('tl-track-sfx',   [], 'rgba(239,68,68,0.3)');
    tlRenderPlayhead();
    tlRenderTime();
    tlUpdateToolbar();
  }
  ```

- [ ] **Step 2: Wire ruler clicks to seek**

  Add to the TIMELINE MODULE block:

  ```javascript
  document.addEventListener('click', function(e) {
    if (!ENABLE_TIMELINE) return;
    const rulerInner = document.getElementById('tl-ruler-inner');
    if (rulerInner && rulerInner.contains(e.target)) {
      const rect = rulerInner.getBoundingClientRect();
      const x = e.clientX - rect.left;
      tlSeek(Math.max(0, Math.min(tlDuration, tlXToSecs(x))));
    }
  });

  function tlSeek(secs) {
    tlPlayheadTime = Math.max(0, Math.min(tlDuration, secs));
    if (_tlVideoEl) _tlVideoEl.currentTime = tlPlayheadTime;
    tlRender();
  }
  ```

- [ ] **Step 3: Make playhead draggable on the clips area**

  ```javascript
  let _tlPlayheadDrag = false;
  document.getElementById('tl-clips-area')?.addEventListener('mousedown', function(e) {
    if (e.target.closest('.tl-clip')) return; // handled by clip handler
    const area = document.getElementById('tl-clips-area');
    const rect = area.getBoundingClientRect();
    const x = e.clientX - rect.left;
    tlSeek(tlXToSecs(x));
    _tlPlayheadDrag = true;
  });
  document.addEventListener('mousemove', function(e) {
    if (!_tlPlayheadDrag) return;
    const area = document.getElementById('tl-clips-area');
    if (!area) return;
    const rect = area.getBoundingClientRect();
    const x = e.clientX - rect.left;
    tlSeek(tlXToSecs(x));
  });
  document.addEventListener('mouseup', function() { _tlPlayheadDrag = false; });
  ```

- [ ] **Step 4: Sync playhead from `#preview-video` timeupdate**

  ```javascript
  function tlSyncFromVideo() {
    if (!ENABLE_TIMELINE || !_tlVideoEl || _tlPlayheadDrag) return;
    tlPlayheadTime = _tlVideoEl.currentTime;
    tlRenderPlayhead();
    tlRenderTime();
    tlUpdateToolbar();
  }
  // Hook into preview-video (safe to call multiple times — handler is idempotent)
  document.addEventListener('DOMContentLoaded', function() {
    const vid = document.getElementById('preview-video');
    if (vid) vid.addEventListener('timeupdate', tlSyncFromVideo);
  });
  ```

- [ ] **Step 5: Wire segment click to select**

  ```javascript
  function tlClipMousedown(e, segId) {
    e.stopPropagation();
    tlSelectedSegId = (tlSelectedSegId === segId) ? null : segId;
    if (tlColorOpen) tlSyncColorStrip();
    tlRender();
  }
  ```

- [ ] **Step 6: Verify in browser**

  Open the timeline, load a video. Segments should appear as green bars on the Video track. Click the ruler — playhead moves and the video scrubs. Click a clip — it gets a white border (selected). Time display updates.

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): render ruler, clips, playhead; seek on click; sync from video"
  ```

---

## Task 4: Playback controls

**Files:**
- Modify: `frontend/index.html` — implement play/pause, go-to-start, RAF loop

- [ ] **Step 1: Implement play/pause and playback RAF loop**

  ```javascript
  function tlTogglePlay() {
    if (!ENABLE_TIMELINE || !_tlVideoEl) return;
    if (_tlPlaying) {
      _tlVideoEl.pause();
      _tlPlaying = false;
      cancelAnimationFrame(_tlRafId);
    } else {
      _tlVideoEl.play().catch(() => {});
      _tlPlaying = true;
      function frame() {
        if (!_tlPlaying) return;
        tlPlayheadTime = _tlVideoEl.currentTime;
        tlRenderPlayhead();
        tlRenderTime();
        tlUpdateToolbar();
        _tlRafId = requestAnimationFrame(frame);
      }
      _tlRafId = requestAnimationFrame(frame);
    }
    const btn = document.getElementById('tl-play-btn');
    if (btn) btn.textContent = _tlPlaying ? '⏸ Pause' : '▶ Play';
  }

  // Keyboard shortcut: Space = play/pause, S = split (when timeline open)
  document.addEventListener('keydown', function(e) {
    if (!ENABLE_TIMELINE || !tlOpen) return;
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    if (e.code === 'Space') { e.preventDefault(); tlTogglePlay(); }
    if (e.code === 'KeyS' && !e.ctrlKey && !e.metaKey) { e.preventDefault(); tlSplit(); }
  });
  ```

- [ ] **Step 2: Pause when video reaches end**

  In `tlSyncFromVideo()`, add after updating `tlPlayheadTime`:

  ```javascript
  if (_tlVideoEl.ended && _tlPlaying) {
    _tlPlaying = false;
    cancelAnimationFrame(_tlRafId);
    const btn = document.getElementById('tl-play-btn');
    if (btn) btn.textContent = '▶ Play';
  }
  ```

- [ ] **Step 3: Verify**

  Click ▶ Play — video plays, playhead moves. Click ⏸ Pause — stops. Press Space key — toggles. ⏮ goes to 0s.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): play/pause controls, Space/S keyboard shortcuts"
  ```

---

## Task 5: Split operation

**Files:**
- Modify: `frontend/index.html` — implement `tlSplit()`

- [ ] **Step 1: Implement `tlSplit()`**

  ```javascript
  function tlSplit() {
    if (!ENABLE_TIMELINE) return;
    const seg = tlSegments.find(s => s.id === tlSelectedSegId);
    if (!seg) return;
    const t = tlPlayheadTime;
    if (t <= seg.sourceStart + 0.05 || t >= seg.sourceEnd - 0.05) return; // too close to edge
    const left = tlNewSeg(seg.sourceStart, t, seg.trackStart, {...seg.color});
    const rightTrackStart = seg.trackStart + (t - seg.sourceStart);
    const right = tlNewSeg(t, seg.sourceEnd, rightTrackStart, {...seg.color});
    const idx = tlSegments.indexOf(seg);
    tlSegments.splice(idx, 1, left, right);
    tlSelectedSegId = left.id;
    tlRender();
    if (typeof saveHist === 'function') saveHist();
  }
  ```

- [ ] **Step 2: Verify**

  Load a video. Open timeline. Play to ~5s. Click the green bar to select it. Click "Split". Two segments appear, split at the playhead. Each can be selected independently.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): split segment at playhead"
  ```

---

## Task 6: Trim handles (drag to adjust in/out points)

**Files:**
- Modify: `frontend/index.html` — implement `tlHandleMousedown` and drag logic

- [ ] **Step 1: Implement trim handle drag**

  ```javascript
  let _tlTrimState = null; // {segId, handle:'l'|'r', startX, origStart, origEnd}

  function tlHandleMousedown(e, segId, handle) {
    e.stopPropagation();
    e.preventDefault();
    const seg = tlSegments.find(s => s.id === segId);
    if (!seg) return;
    _tlTrimState = {
      segId, handle,
      startX: e.clientX,
      origStart: seg.sourceStart,
      origEnd: seg.sourceEnd,
      origTrackStart: seg.trackStart
    };
    tlSelectedSegId = segId;
    document.body.style.cursor = 'ew-resize';
  }

  document.addEventListener('mousemove', function(e) {
    if (!_tlTrimState) return;
    const dx = e.clientX - _tlTrimState.startX;
    const dt = tlXToSecs(dx);
    const seg = tlSegments.find(s => s.id === _tlTrimState.segId);
    if (!seg) return;
    if (_tlTrimState.handle === 'l') {
      const newStart = Math.max(0, Math.min(_tlTrimState.origEnd - 0.1, _tlTrimState.origStart + dt));
      seg.sourceStart = newStart;
      seg.trackStart = _tlTrimState.origTrackStart + (newStart - _tlTrimState.origStart);
    } else {
      const newEnd = Math.max(_tlTrimState.origStart + 0.1, Math.min(tlDuration, _tlTrimState.origEnd + dt));
      seg.sourceEnd = newEnd;
    }
    if (_tlVideoEl) _tlVideoEl.currentTime = _tlTrimState.handle === 'l' ? seg.sourceStart : seg.sourceEnd;
    tlRender();
  });

  document.addEventListener('mouseup', function() {
    if (_tlTrimState) {
      _tlTrimState = null;
      document.body.style.cursor = '';
      if (typeof saveHist === 'function') saveHist();
    }
  });
  ```

- [ ] **Step 2: Verify**

  Open timeline. Hover over a clip — green handles appear on left/right edges. Drag left handle: the clip shrinks from the left (in-point moves, clip shifts right). Drag right handle: clip shrinks from the right. The video scrubs to the edge frame while dragging.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): trim handles — drag left/right edge to adjust in/out"
  ```

---

## Task 7: Delete segment

**Files:**
- Modify: `frontend/index.html` — implement `tlDeleteSeg()`

- [ ] **Step 1: Implement `tlDeleteSeg()`**

  ```javascript
  function tlDeleteSeg() {
    if (!ENABLE_TIMELINE) return;
    if (tlSegments.length <= 1) return; // must keep at least one
    const idx = tlSegments.findIndex(s => s.id === tlSelectedSegId);
    if (idx === -1) return;
    tlSegments.splice(idx, 1);
    // Compact: shift subsequent segments left to fill the gap
    tlCompact();
    tlSelectedSegId = tlSegments[Math.min(idx, tlSegments.length - 1)]?.id || null;
    tlRender();
    if (typeof saveHist === 'function') saveHist();
  }

  function tlCompact() {
    // Sort by trackStart, then re-pack so there are no gaps
    tlSegments.sort((a, b) => a.trackStart - b.trackStart);
    let cursor = 0;
    for (const seg of tlSegments) {
      seg.trackStart = cursor;
      cursor += seg.sourceEnd - seg.sourceStart;
    }
  }
  ```

- [ ] **Step 2: Verify**

  Split a clip into 3 segments. Select the middle one. Click Delete. The gap closes and the right segment shifts left. Delete is disabled when only 1 segment remains.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): delete segment with gap compaction"
  ```

---

## Task 8: Drag segments to reorder

**Files:**
- Modify: `frontend/index.html` — drag a clip horizontally to reposition it

- [ ] **Step 1: Implement clip drag (move)**

  The `tlClipMousedown` function already handles click-to-select. Extend it to also initiate a drag when the mouse moves before mouseup:

  Replace `tlClipMousedown` with:

  ```javascript
  let _tlDragSeg = null; // {segId, startX, origTrackStart}

  function tlClipMousedown(e, segId) {
    e.stopPropagation();
    // Don't handle if already captured by trim handler
    if (_tlTrimState) return;
    tlSelectedSegId = segId;
    _tlDragSeg = { segId, startX: e.clientX, origTrackStart: tlSegments.find(s => s.id === segId)?.trackStart ?? 0 };
    if (tlColorOpen) tlSyncColorStrip();
    tlRender();
  }
  ```

  In the existing `document.addEventListener('mousemove', ...)` handler that handles `_tlTrimState`, add an `else if` for drag:

  ```javascript
  } else if (_tlDragSeg) {
    const dx = e.clientX - _tlDragSeg.startX;
    const dt = tlXToSecs(dx);
    const seg = tlSegments.find(s => s.id === _tlDragSeg.segId);
    if (seg) {
      seg.trackStart = Math.max(0, _tlDragSeg.origTrackStart + dt);
      document.body.style.cursor = 'grabbing';
      tlRender();
    }
  }
  ```

  In `document.addEventListener('mouseup', ...)`, add cleanup:

  ```javascript
  if (_tlDragSeg) {
    _tlDragSeg = null;
    document.body.style.cursor = '';
    tlCompact(); // snap back to packed order
    tlRender();
    if (typeof saveHist === 'function') saveHist();
  }
  ```

- [ ] **Step 2: Verify**

  Split into 2+ clips. Drag one — it moves. On mouseup it snaps back to packed order. 

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): drag segments to reorder"
  ```

---

## Task 9: Color grading — slider panel and CSS filter preview

**Files:**
- Modify: `frontend/index.html` — implement `tlToggleColor()`, `tlColorChange()`, CSS filter on preview-video

- [ ] **Step 1: Implement `tlToggleColor()` and `tlSyncColorStrip()`**

  ```javascript
  function tlToggleColor() {
    if (!ENABLE_TIMELINE) return;
    tlColorOpen = !tlColorOpen;
    document.getElementById('tl-color-strip')?.classList.toggle('vis', tlColorOpen);
    document.getElementById('tl-color-btn')?.classList.toggle('on', tlColorOpen);
    if (tlColorOpen) tlSyncColorStrip();
  }

  function tlSyncColorStrip() {
    const seg = tlSegments.find(s => s.id === tlSelectedSegId);
    const c = seg?.color || { brightness: 0, contrast: 0, saturation: 0, hue: 0 };
    const set = (id, valId, v, suffix) => {
      const sl = document.getElementById(id);
      const lbl = document.getElementById(valId);
      if (sl) sl.value = v;
      if (lbl) lbl.textContent = v + (suffix || '');
    };
    set('tl-cs-bright',   'tl-cs-bright-v',   c.brightness, '');
    set('tl-cs-contrast', 'tl-cs-contrast-v', c.contrast,   '');
    set('tl-cs-sat',      'tl-cs-sat-v',      c.saturation, '');
    set('tl-cs-hue',      'tl-cs-hue-v',      c.hue,        '°');
    tlApplyPreviewFilter(c);
  }

  function tlApplyPreviewFilter(c) {
    const vid = document.getElementById('preview-video');
    if (!vid) return;
    // Map our -100..+100 values to CSS filter equivalents
    const brightness = 1 + c.brightness / 100;           // 0..2, default 1
    const contrast   = 1 + c.contrast   / 100;           // 0..2, default 1
    const saturation = 1 + c.saturation / 100;           // 0..2, default 1
    const hue        = c.hue || 0;                       // degrees
    vid.style.filter = `brightness(${brightness}) contrast(${contrast}) saturate(${saturation}) hue-rotate(${hue}deg)`;
  }

  function tlColorChange(prop, rawVal) {
    const v = parseFloat(rawVal);
    const seg = tlSegments.find(s => s.id === tlSelectedSegId);
    if (!seg) return;
    seg.color[prop] = v;
    const suffix = prop === 'hue' ? '°' : '';
    const valMap = { brightness: 'tl-cs-bright-v', contrast: 'tl-cs-contrast-v', saturation: 'tl-cs-sat-v', hue: 'tl-cs-hue-v' };
    const el = document.getElementById(valMap[prop]);
    if (el) el.textContent = v + suffix;
    tlApplyPreviewFilter(seg.color);
  }
  ```

- [ ] **Step 2: Reset CSS filter when no segment is selected or timeline is closed**

  In `tlClipMousedown`, after `tlRender()`, add:

  ```javascript
  if (tlColorOpen) tlSyncColorStrip();
  ```

  In `tlClose()`, after existing code, add:

  ```javascript
  const vid = document.getElementById('preview-video');
  if (vid) vid.style.filter = '';
  ```

- [ ] **Step 3: Verify**

  Select a clip, click Color. Sliders appear. Move Brightness — the preview video gets brighter/darker in real time. Select a different clip — sliders update to that clip's values. Close timeline — filter resets.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): color grading panel with live CSS filter preview"
  ```

---

## Task 10: Export integration — pass segments to API

**Files:**
- Modify: `frontend/index.html` — include `segments` in the export payload
- Modify: `app.py` — forward `segments` to `export_video()`
- Modify: `exporter.py` — add `build_segment_filter()`, use it in `export_video()`
- Modify: `tests/test_exporter.py` — tests for segment filter

- [ ] **Step 1: Write failing tests for `build_segment_filter` in `tests/test_exporter.py`**

  Add to the end of the file:

  ```python
  from exporter import build_segment_filter

  def test_no_segments_returns_passthrough():
      parts, vlabel, alabel = build_segment_filter([], 30.0)
      assert parts == []
      assert vlabel == '0:v'
      assert alabel == '0:a'

  def test_single_full_segment_returns_passthrough():
      segs = [{'sourceStart': 0, 'sourceEnd': 30, 'trackStart': 0,
               'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}}]
      parts, vlabel, alabel = build_segment_filter(segs, 30.0)
      assert parts == []
      assert vlabel == '0:v'
      assert alabel == '0:a'

  def test_two_segments_generates_concat():
      segs = [
          {'sourceStart': 0,  'sourceEnd': 5,  'trackStart': 0,
           'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}},
          {'sourceStart': 8,  'sourceEnd': 15, 'trackStart': 5,
           'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}},
      ]
      parts, vlabel, alabel = build_segment_filter(segs, 20.0)
      assert any('trim' in p for p in parts), f"Expected trim filter, got: {parts}"
      assert any('concat' in p for p in parts), f"Expected concat filter, got: {parts}"
      assert vlabel != '0:v'
      assert alabel != '0:a'

  def test_color_grading_adds_eq_filter():
      segs = [
          {'sourceStart': 0, 'sourceEnd': 10, 'trackStart': 0,
           'color': {'brightness': 50, 'contrast': 20, 'saturation': -30, 'hue': 0}},
          {'sourceStart': 10, 'sourceEnd': 20, 'trackStart': 10,
           'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}},
      ]
      parts, vlabel, alabel = build_segment_filter(segs, 20.0)
      assert any('eq=' in p for p in parts), f"Expected eq filter, got: {parts}"

  def test_hue_grading_adds_hue_filter():
      segs = [
          {'sourceStart': 0, 'sourceEnd': 10, 'trackStart': 0,
           'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 90}},
          {'sourceStart': 10, 'sourceEnd': 20, 'trackStart': 10,
           'color': {'brightness': 0, 'contrast': 0, 'saturation': 0, 'hue': 0}},
      ]
      parts, vlabel, alabel = build_segment_filter(segs, 20.0)
      assert any('hue=' in p for p in parts), f"Expected hue filter, got: {parts}"
  ```

- [ ] **Step 2: Run tests — expect failures**

  ```bash
  pytest tests/test_exporter.py::test_no_segments_returns_passthrough tests/test_exporter.py::test_two_segments_generates_concat -v
  ```

  Expected: `ImportError: cannot import name 'build_segment_filter' from 'exporter'`

- [ ] **Step 3: Implement `build_segment_filter()` in `exporter.py`**

  Add this function before `build_filter_graph`:

  ```python
  def build_segment_filter(segments: list, duration: float) -> tuple[list, str, str]:
      """
      Build trim+concat filter parts for video segments.
      Returns (filter_parts, video_label, audio_label).
      If no cutting is needed (empty list, or single segment covering full source),
      returns ([], '0:v', '0:a') — caller uses raw streams directly.
      """
      if not segments:
          return [], '0:v', '0:a'

      # Normalise and sort by trackStart
      segs = sorted(segments, key=lambda s: s['trackStart'])

      # Check if this is a no-op: one segment, full duration, no color grading
      if len(segs) == 1:
          s = segs[0]
          c = s.get('color', {})
          no_color = all(c.get(k, 0) == 0 for k in ('brightness', 'contrast', 'saturation', 'hue'))
          starts_at_zero = abs(s.get('sourceStart', 0)) < 0.05
          ends_at_duration = abs(s.get('sourceEnd', duration) - duration) < 0.05
          if no_color and starts_at_zero and ends_at_duration:
              return [], '0:v', '0:a'

      n = [0]
      def lbl(prefix='s'):
          n[0] += 1
          return f"{prefix}{n[0]}"

      parts = []
      vlabels = []
      alabels = []

      for seg in segs:
          ss = seg['sourceStart']
          se = seg['sourceEnd']
          c = seg.get('color', {})
          brightness = c.get('brightness', 0)
          contrast   = c.get('saturation', 0)  # note: contrast uses contrast key
          saturation = c.get('saturation', 0)
          hue        = c.get('hue', 0)

          # Fix: use correct keys
          brightness = c.get('brightness', 0)
          contrast   = c.get('contrast',   0)
          saturation = c.get('saturation', 0)

          vl = lbl('sv')
          al = lbl('sa')

          # Video segment
          vtrim = f"[0:v]trim=start={ss}:end={se},setpts=PTS-STARTPTS"
          color_filters = ''
          eq_parts = []
          # Map -100..+100 → FFmpeg eq ranges: brightness -1..1, contrast 0..2, saturation 0..2
          if brightness != 0:
              eq_parts.append(f"brightness={brightness/100:.3f}")
          if contrast != 0:
              # contrast 0 → 1.0, +100 → 2.0, -100 → 0.0
              eq_parts.append(f"contrast={1.0 + contrast/100:.3f}")
          if saturation != 0:
              eq_parts.append(f"saturation={1.0 + saturation/100:.3f}")
          if eq_parts:
              color_filters += ',eq=' + ':'.join(eq_parts)
          if hue != 0:
              color_filters += f",hue=h={hue}"
          parts.append(f"{vtrim}{color_filters}[{vl}]")
          vlabels.append(vl)

          # Audio segment
          parts.append(f"[0:a]atrim=start={ss}:end={se},asetpts=PTS-STARTPTS[{al}]")
          alabels.append(al)

      n_segs = len(segs)
      if n_segs == 1:
          return parts, vlabels[0], alabels[0]

      # Concat video
      vout = lbl('vc')
      parts.append(''.join(f'[{l}]' for l in vlabels) + f'concat=n={n_segs}:v=1:a=0[{vout}]')
      # Concat audio
      aout = lbl('ac')
      parts.append(''.join(f'[{l}]' for l in alabels) + f'concat=n={n_segs}:v=0:a=1[{aout}]')

      return parts, vout, aout
  ```

- [ ] **Step 4: Run tests — expect pass**

  ```bash
  pytest tests/test_exporter.py -v
  ```

  Expected: all tests PASS.

- [ ] **Step 5: Update `export_video()` to accept and use `segments`**

  Change the signature:

  ```python
  def export_video(video_path: str, template: dict, title: str = "",
                   on_progress=None, emoji_source: str = "twemoji",
                   segments: list = None) -> str:
  ```

  After the line `for l in all_layers:` loop (around line 286) and before the `audio_layer = ...` line, add:

  ```python
  # ── Segment trim/color filter ─────────────────────────────────────────────
  import math
  seg_parts, seg_vlabel, seg_alabel = build_segment_filter(
      segments or [], duration=0  # duration is informational only; 0 = auto
  )
  ```

  Wait — `build_segment_filter` takes `duration` but only uses it for the single-segment no-op check. We can pass 0 safely since the frontend always computes the right sourceEnd. Update the call:

  ```python
  seg_parts, seg_vlabel, seg_alabel = build_segment_filter(segments or [])
  ```

  And update `build_segment_filter` signature to not require duration:

  ```python
  def build_segment_filter(segments: list) -> tuple[list, str, str]:
  ```

  Remove the `duration` parameter from the function body (the no-op check only uses `duration` to compare `sourceEnd` — replace that check with just checking if `sourceEnd` is very large or use `float('inf')` comparison):

  ```python
  # Replace the no-op check with:
  if len(segs) == 1:
      s = segs[0]
      c = s.get('color', {})
      no_color = all(c.get(k, 0) == 0 for k in ('brightness', 'contrast', 'saturation', 'hue'))
      starts_at_zero = abs(s.get('sourceStart', 0)) < 0.05
      # Accept as passthrough if it appears to cover from near-zero to a large value
      # — we can't know total duration here, so only skip when no color AND sourceStart≈0
      # AND sourceEnd is the same as the template assumes (we check via no color + no trim)
      full_range = starts_at_zero and s.get('sourceEnd', 0) > 0
      if no_color and starts_at_zero and full_range:
          # Still might be trimmed — safest to check if sourceStart == 0 and no color
          # We'll only skip if starts at 0 with no color (no end-trim detection here)
          pass  # fall through to apply trim
  ```

  Actually, simplify: just skip the no-op detection entirely — always apply trim/concat when segments are provided. When `segments=None` or empty, return passthrough. The performance cost of a single `trim` on a full file is negligible.

  Final `build_segment_filter`:

  ```python
  def build_segment_filter(segments: list) -> tuple[list, str, str]:
      """
      Build trim+concat filter parts for video segments.
      Returns (filter_parts, video_label, audio_label).
      Returns ([], '0:v', '0:a') when no segments provided (no-op / backward compat).
      """
      if not segments:
          return [], '0:v', '0:a'

      segs = sorted(segments, key=lambda s: s.get('trackStart', 0))
      n = [0]
      def lbl(prefix='s'):
          n[0] += 1
          return f"{prefix}{n[0]}"

      parts = []
      vlabels = []
      alabels = []

      for seg in segs:
          ss  = float(seg.get('sourceStart', 0))
          se  = float(seg.get('sourceEnd',   0))
          c   = seg.get('color', {})
          brightness = float(c.get('brightness', 0))
          contrast   = float(c.get('contrast',   0))
          saturation = float(c.get('saturation', 0))
          hue        = float(c.get('hue',        0))

          vl = lbl('sv')
          al = lbl('sa')

          vtrim = f"[0:v]trim=start={ss}:end={se},setpts=PTS-STARTPTS"
          eq_parts = []
          if brightness != 0:
              eq_parts.append(f"brightness={brightness/100:.3f}")
          if contrast != 0:
              eq_parts.append(f"contrast={1.0 + contrast/100:.3f}")
          if saturation != 0:
              eq_parts.append(f"saturation={1.0 + saturation/100:.3f}")
          color_filters = (',eq=' + ':'.join(eq_parts)) if eq_parts else ''
          if hue != 0:
              color_filters += f",hue=h={hue}"
          parts.append(f"{vtrim}{color_filters}[{vl}]")
          vlabels.append(vl)

          parts.append(f"[0:a]atrim=start={ss}:end={se},asetpts=PTS-STARTPTS[{al}]")
          alabels.append(al)

      n_segs = len(segs)
      if n_segs == 1:
          return parts, vlabels[0], alabels[0]

      vout = lbl('vc')
      parts.append(''.join(f'[{l}]' for l in vlabels) + f'concat=n={n_segs}:v=1:a=0[{vout}]')
      aout = lbl('ac')
      parts.append(''.join(f'[{l}]' for l in alabels) + f'concat=n={n_segs}:v=0:a=1[{aout}]')
      return parts, vout, aout
  ```

  Update tests to match new signature (remove `duration` argument from test calls):
  - `build_segment_filter([], 30.0)` → `build_segment_filter([])`
  - `build_segment_filter(segs, 30.0)` → `build_segment_filter(segs)`
  - `build_segment_filter(segs, 20.0)` → `build_segment_filter(segs)`

  In `export_video()`, after building `seg_parts, seg_vlabel, seg_alabel`, pass `seg_vlabel` into `build_filter_graph`. Update `build_filter_graph` to accept an optional `src_video_label` parameter:

  **In `build_filter_graph` signature**, change:
  ```python
  def build_filter_graph(layers: list, cw: int, ch: int,
                         text_pngs: dict, image_inputs: dict,
                         mask_inputs: dict = None) -> tuple[list, str]:
  ```
  to:
  ```python
  def build_filter_graph(layers: list, cw: int, ch: int,
                         text_pngs: dict, image_inputs: dict,
                         mask_inputs: dict = None,
                         src_video_label: str = '0:v') -> tuple[list, str]:
  ```

  Inside `build_filter_graph`, replace the two occurrences of the literal `"0:v"` used as the raw video source with `src_video_label`. The affected lines are:
  - The split pre-check: `parts.append(f"[0:v]split=...")` → `parts.append(f"[{src_video_label}]split=...")`
  - The `_raw_iter` fallback: `iter(["0:v"] if raw_uses == 1 else [])` → `iter([src_video_label] if raw_uses == 1 else [])`

  Similarly, update `build_audio_cmd_parts` to accept `src_audio_label`:
  ```python
  def build_audio_cmd_parts(layers, audio_layer, next_input_idx, src_audio_label='0:a'):
  ```
  Replace `"[0:a]"` literal inside the function with `f"[{src_audio_label}]"`.

  In `export_video()`, update the calls:
  ```python
  filter_parts, final_video = build_filter_graph(
      layers, cw, ch, text_pngs, image_inputs, mask_inputs,
      src_video_label=seg_vlabel
  )
  music_extra, sfx_extra, audio_filter_parts, audio_label = build_audio_cmd_parts(
      layers, audio_layer, next_input_idx=1 + len(extra_inputs),
      src_audio_label=seg_alabel
  )
  ```

  Prepend `seg_parts` to `all_filter_parts`:
  ```python
  all_filter_parts = seg_parts + filter_parts + audio_filter_parts
  ```

  Update the three `cmd +=` branches that reference `filter_parts` to use `all_filter_parts`:
  - Replace every `if filter_parts and audio_filter_parts:` block to check `all_filter_parts` vs the video/audio breakdown. The simplest fix is to always use `all_filter_parts` for `-filter_complex` when it's non-empty:

  Replace the entire block:
  ```python
  all_filter_parts = seg_parts + filter_parts + audio_filter_parts
  if all_filter_parts:
      cmd += ["-filter_complex", ";".join(all_filter_parts)]
  if filter_parts or seg_parts:
      cmd += ["-map", f"[{final_video}]"]
  else:
      cmd += ["-map", "0:v"]

  if audio_label == "0:a":
      cmd += ["-map", "0:a?"]
  else:
      cmd += ["-map", f"[{audio_label}]"]
  ```

- [ ] **Step 6: Update `app.py` to pass segments to `export_video()`**

  In `start_export()` (line ~143), add extraction of segments:

  ```python
  segments = body.get("segments", None)
  ```

  Update the `export_video(...)` call inside `run()`:

  ```python
  out = export_video(video_path, template, title, on_progress,
                     emoji_source=emoji_source, segments=segments)
  ```

- [ ] **Step 7: Update `startExport()` in `frontend/index.html` to include segments**

  Find `startExport()` (line ~4401). Find the `body:JSON.stringify(...)` call. Change it to:

  ```javascript
  body: JSON.stringify({
    video_path: downloadedVideoPath,
    template: tpl,
    title,
    emoji_source: activeEmoTab === 'mypack' ? 'emojipack' : activeEmoTab,
    segments: ENABLE_TIMELINE ? tlSegments : null
  })
  ```

- [ ] **Step 8: Run all tests**

  ```bash
  pytest tests/ -v
  ```

  Expected: all PASS.

- [ ] **Step 9: Manual export test**

  1. Download a video. Open timeline. Split it into 2 segments. Delete the first 2s of one segment by trimming. Apply +50 brightness to one segment.
  2. Click Export. Watch the progress bar complete.
  3. Open the downloaded file — it should be trimmed and have color applied.

- [ ] **Step 10: Commit**

  ```bash
  git add frontend/index.html app.py exporter.py tests/test_exporter.py
  git commit -m "feat(timeline): export integration — segments with trim, concat, color grading"
  ```

---

## Task 11: Final polish and reverting guide

**Files:**
- Modify: `frontend/index.html` — minor UX polish

- [ ] **Step 1: Add zoom controls to the timeline toolbar**

  In `#tl-toolbar`, after the `▼ Hide` button, insert:

  ```html
  <div class="tl-sep"></div>
  <button class="tl-btn" onclick="tlZoom(-5)" title="Zoom out">−</button>
  <button class="tl-btn" onclick="tlZoom(5)"  title="Zoom in">+</button>
  ```

  In the JS module:

  ```javascript
  function tlZoom(delta) {
    tlPixelsPerSec = Math.max(10, Math.min(200, tlPixelsPerSec + delta));
    tlRender();
  }
  ```

- [ ] **Step 2: Show color strip values reset button**

  In `#tl-color-strip`, after the last slider row, add:

  ```html
  <button class="tl-btn" onclick="tlColorReset()" style="margin-left:auto">Reset</button>
  ```

  In JS:

  ```javascript
  function tlColorReset() {
    const seg = tlSegments.find(s => s.id === tlSelectedSegId);
    if (!seg) return;
    seg.color = { brightness: 0, contrast: 0, saturation: 0, hue: 0 };
    tlSyncColorStrip();
  }
  ```

- [ ] **Step 3: To disable the entire feature (reverting guide)**

  The timeline is entirely self-contained. To revert:

  **Option A — Feature flag (instant, no code removed):**
  Find `const ENABLE_TIMELINE = true;` in `frontend/index.html` and change to `false`. The panel never shows, all JS is skipped, export sends `null` for segments (backward compatible).

  **Option B — Full removal:**
  Delete everything between `<!-- TIMELINE START -->` and `<!-- TIMELINE END -->` (inclusive). Remove the toggle button added in Task 1 Step 4. In `exporter.py` remove `build_segment_filter`. In `app.py` remove `segments = body.get(...)` and the kwarg from `export_video(...)`.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/index.html
  git commit -m "feat(timeline): zoom controls, color reset button"
  ```

---

## Reverting Reference

| To disable quickly | Set `const ENABLE_TIMELINE = false` in `frontend/index.html` |
|---|---|
| To remove fully | Delete HTML between `<!-- TIMELINE START -->` / `<!-- TIMELINE END -->`, remove toggle button, revert `exporter.py` and `app.py` segment changes |
| Files touched | `frontend/index.html`, `exporter.py`, `app.py`, `tests/test_exporter.py` |
| No DB migrations | Frontend-only state; no schema changes |
