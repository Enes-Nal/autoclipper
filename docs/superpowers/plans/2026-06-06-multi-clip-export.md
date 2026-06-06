# Multi-Clip Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the user to download multiple source videos, arrange them sequentially on the timeline, and export them as a single concatenated video.

**Architecture:** A new `tlClips` array tracks all source videos; each timeline segment gains a `clipId` field. The single `<video id="preview-video">` element swaps its `src` at clip boundaries during playback. The export backend accepts a `clips` array and concatenates all clip segments using FFmpeg.

**Tech Stack:** Vanilla JS (frontend/index.html), Python/Flask (app.py, exporter.py), FFmpeg

---

## File Map

| File | Changes |
|---|---|
| `frontend/index.html` | All JS/HTML changes: data model, UI, playback, export payload |
| `app.py` | Export route accepts `clips` param |
| `exporter.py` | `build_segment_inputs` gets `input_offset`; `export_video` gets `clips` param |
| `tests/test_exporter.py` | Multi-clip export tests |

---

### Task 1: Add `tlClips` data model, helper functions, and `clipId` to segments

**Files:**
- Modify: `frontend/index.html` (around line 4927 — state block, and `tlNewSeg` at ~4939)

- [ ] **Step 1: Add `tlClips` and `_tlActiveClipId` globals + helpers after the existing state block**

Find the state block (around line 4927):
```js
let tlSegments = [];
let tlDuration = 0;
```
Add after `let _tlVideoEl = null;`:
```js
let tlClips = [];           // [{id, path, url, caption, duration}]
let _tlActiveClipId = null; // clipId currently loaded in preview-video src
```

- [ ] **Step 2: Add helper functions after the state block (after line ~4937)**

Add these four functions immediately after `let _tlActiveClipId = null;`:
```js
function tlClipById(clipId) {
  return tlClips.find(c => c.id === clipId) || null;
}
function tlClipIndex(clipId) {
  return tlClips.findIndex(c => c.id === clipId);
}
function tlClipColor(clipId) {
  const colors = [
    'rgba(34,197,94,0.3)',
    'rgba(99,102,241,0.3)',
    'rgba(245,158,11,0.3)',
  ];
  const idx = tlClipIndex(clipId);
  return colors[idx % colors.length] || colors[0];
}
function tlClipDuration(clipId) {
  return tlClipById(clipId)?.duration ?? 0;
}
```

- [ ] **Step 3: Add `clipId` param to `tlNewSeg`**

Find `tlNewSeg` (~line 4939):
```js
function tlNewSeg(sourceStart, sourceEnd, trackStart, color) {
  return {
    id: 'seg_' + Math.random().toString(36).slice(2, 9),
    sourceStart,
    sourceEnd,
    trackStart,
    color: color || { brightness: 0, contrast: 0, saturation: 0, hue: 0 }
  };
}
```
Replace with:
```js
function tlNewSeg(sourceStart, sourceEnd, trackStart, color, clipId) {
  return {
    id: 'seg_' + Math.random().toString(36).slice(2, 9),
    clipId: clipId || null,
    sourceStart,
    sourceEnd,
    trackStart,
    color: color || { brightness: 0, contrast: 0, saturation: 0, hue: 0 }
  };
}
```

- [ ] **Step 4: Commit**
```bash
git add frontend/index.html
git commit -m "feat(timeline): add tlClips data model and clipId to segments"
```

---

### Task 2: Refactor `tlInit` to accept a clip object and update the download done handler

**Files:**
- Modify: `frontend/index.html` (`tlInit` ~line 4949; download done handler ~line 4319)

- [ ] **Step 1: Refactor `tlInit` to accept a clip object**

Find `tlInit` (~line 4949):
```js
function tlInit(durationSecs) {
  if (!ENABLE_TIMELINE) return;
  tlDuration = durationSecs;
  tlSegments = [tlNewSeg(0, durationSecs, 0)];
  tlSelectedSegId = null;
  tlPlayheadTime = 0;
```
Replace with:
```js
function tlInit(clip) {
  if (!ENABLE_TIMELINE) return;
  tlClips = [clip];
  _tlActiveClipId = clip.id;
  tlDuration = clip.duration; // kept for trim guard (per-clip guard added in Task 6)
  tlSegments = [tlNewSeg(0, clip.duration, 0, null, clip.id)];
  tlSelectedSegId = null;
  tlPlayheadTime = 0;
```

- [ ] **Step 2: Update the download "done" handler to build a clip object and call `tlInit`**

Find the done handler (~line 4318):
```js
} else if(msg.type==='done'){
  es.close();pf.style.width='100%';pl.textContent='Done';
  downloadedVideoPath=msg.path;
  downloadedVideoCaption=msg.title||'';
  const filename=msg.path.split(/[\\/]/).pop();
  updateTplPreviews('/api/downloads/'+encodeURIComponent(filename));
  document.getElementById('vid-card').style.display='';
  document.getElementById('vid-filename').textContent=filename;
  document.getElementById('vid-meta').textContent=`${msg.width}×${msg.height} · ${Math.round(msg.duration)}s`;
  st.textContent='Downloaded successfully';st.style.color='var(--ok)';
  setTimeout(closeDlModal,1200);
```
Replace with:
```js
} else if(msg.type==='done'){
  es.close();pf.style.width='100%';pl.textContent='Done';
  const filename=msg.path.split(/[\\/]/).pop();
  const clip = {
    id: 'clip_' + Math.random().toString(36).slice(2, 9),
    path: msg.path,
    url: '/api/downloads/' + encodeURIComponent(filename),
    caption: msg.title || '',
    duration: msg.duration,
  };
  if (window._dlMode === 'append' && tlClips.length > 0) {
    tlAddClip(clip);
  } else {
    downloadedVideoPath = msg.path; // keep for export guard compat
    downloadedVideoCaption = clip.caption;
    updateTplPreviews(clip.url);
    tlInit(clip);
  }
  tlRenderClipList();
  st.textContent='Downloaded successfully';st.style.color='var(--ok)';
  setTimeout(closeDlModal,1200);
```

- [ ] **Step 3: Add `tlAddClip` function (after `tlInit`)**

```js
function tlAddClip(clip) {
  if (!ENABLE_TIMELINE) return;
  tlClips.push(clip);
  const lastSeg = tlSegments.reduce((a, b) => a.trackStart + (a.sourceEnd - a.sourceStart) > b.trackStart + (b.sourceEnd - b.sourceStart) ? a : b, tlSegments[0]);
  const afterEnd = lastSeg ? lastSeg.trackStart + (lastSeg.sourceEnd - lastSeg.sourceStart) : 0;
  tlSegments.push(tlNewSeg(0, clip.duration, afterEnd, null, clip.id));
  tlRender();
  if (typeof saveHist === 'function') saveHist();
}
```

- [ ] **Step 4: Commit**
```bash
git add frontend/index.html
git commit -m "feat(timeline): refactor tlInit to accept clip object, add tlAddClip"
```

---

### Task 3: Sidebar clip list UI

**Files:**
- Modify: `frontend/index.html` (HTML `#vid-card` ~line 55 in styles, HTML around sidebar; JS `tlRenderClipList`)

- [ ] **Step 1: Replace the single `#vid-card` CSS with `#clip-list` styles**

Find in the `<style>` block:
```css
.vid-card{margin:0 10px;padding:10px 12px;border-radius:var(--r);border:1px solid var(--b1);background:var(--s2)}
.vid-card-lbl{font-size:9px;font-weight:700;color:var(--sub);text-transform:uppercase;letter-spacing:1.1px;margin-bottom:5px;display:flex;align-items:center;gap:5px}
.vid-card-lbl::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--ok);flex-shrink:0}
.vid-filename{font-size:11px;color:var(--tx);font-weight:600;word-break:break-all;line-height:1.4}
.vid-meta{font-size:10px;color:var(--sub);margin-top:3px}
```
Replace with:
```css
#clip-list{display:flex;flex-direction:column;gap:5px;padding:0 10px;overflow-y:auto;max-height:200px}
#clip-list::-webkit-scrollbar{width:3px}
#clip-list::-webkit-scrollbar-thumb{background:var(--mut);border-radius:2px}
.clip-card{padding:8px 10px;border-radius:var(--r);border:1px solid var(--b1);background:var(--s2);display:flex;align-items:flex-start;gap:6px}
.clip-card-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;margin-top:4px}
.clip-card-body{flex:1;min-width:0}
.clip-card-name{font-size:11px;color:var(--tx);font-weight:600;word-break:break-all;line-height:1.4}
.clip-card-meta{font-size:10px;color:var(--sub);margin-top:2px}
.clip-card-rm{flex-shrink:0;width:18px;height:18px;border:none;background:transparent;color:var(--sub);cursor:pointer;border-radius:4px;display:flex;align-items:center;justify-content:center;padding:0;transition:.1s}
.clip-card-rm:hover{background:rgba(244,63,94,0.15);color:var(--danger)}
```

- [ ] **Step 2: Replace the `#vid-card` HTML in the sidebar with `#clip-list`**

Find the vid-card HTML (search for `id="vid-card"` in the sidebar HTML):
```html
<div class="vid-card" id="vid-card" style="display:none">
  <div class="vid-card-lbl">Source video</div>
  <div class="vid-filename" id="vid-filename"></div>
  <div class="vid-meta" id="vid-meta"></div>
</div>
```
Replace with:
```html
<div id="clip-list"></div>
```

- [ ] **Step 3: Add `tlRenderClipList` function (in the JS timeline section)**

Add after `tlAddClip`:
```js
function tlRenderClipList() {
  const list = document.getElementById('clip-list');
  if (!list) return;
  if (!tlClips.length) { list.innerHTML = ''; return; }
  list.innerHTML = tlClips.map((clip, i) => {
    const colors = ['#22c55e','#6366f1','#f59e0b'];
    const dot = colors[i % colors.length];
    const name = clip.path.split(/[\\/]/).pop();
    const dur = Math.round(clip.duration);
    return `<div class="clip-card">
      <div class="clip-card-dot" style="background:${dot}"></div>
      <div class="clip-card-body">
        <div class="clip-card-name">${name}</div>
        <div class="clip-card-meta">${dur}s</div>
      </div>
      <button class="clip-card-rm" onclick="tlRemoveClip('${clip.id}')" title="Remove clip">
        <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>`;
  }).join('');
}

function tlRemoveClip(clipId) {
  const idx = tlClips.findIndex(c => c.id === clipId);
  if (idx === -1) return;
  tlClips.splice(idx, 1);
  tlSegments = tlSegments.filter(s => s.clipId !== clipId);
  tlCompact();
  if (!tlClips.length) {
    tlSegments = [];
    tlSelectedSegId = null;
    tlPlayheadTime = 0;
    _tlActiveClipId = null;
    downloadedVideoPath = null;
    const vid = document.getElementById('preview-video');
    if (vid) { vid.src = ''; }
  } else if (_tlActiveClipId === clipId) {
    _tlActiveClipId = tlClips[0].id;
    const vid = document.getElementById('preview-video');
    if (vid) vid.src = tlClips[0].url;
  }
  tlRenderClipList();
  tlRender();
  if (typeof saveHist === 'function') saveHist();
}
```

- [ ] **Step 4: Fix any remaining references to `vid-card`, `vid-filename`, `vid-meta` in JS**

Search for `vid-card` in the JS — find the line that sets `document.getElementById('vid-card').style.display=''` (in the old done handler) — this was already removed in Task 2, so verify it's gone. Also search for `vid-filename` and `vid-meta` and remove any remaining JS references to them (they no longer exist in the DOM).

- [ ] **Step 5: Commit**
```bash
git add frontend/index.html
git commit -m "feat(timeline): replace vid-card with per-clip clip list"
```

---

### Task 4: "Add clip" button in timeline toolbar

**Files:**
- Modify: `frontend/index.html` (timeline toolbar HTML ~line 687; JS `tlUpdateToolbar`)

- [ ] **Step 1: Add "Add clip" button to the timeline toolbar HTML**

Find in the toolbar (after the existing zoom buttons):
```html
    <button class="tl-btn" onclick="tlZoom(5)" title="Zoom in timeline">&#43;</button>
  </div>
```
Add before the closing `</div>`:
```html
    <div class="tl-sep"></div>
    <button class="tl-btn" id="tl-addclip-btn" onclick="tlOpenAddClip()" style="display:none">+ Add clip</button>
```

- [ ] **Step 2: Add `tlOpenAddClip` function (in the JS timeline section)**

Add after `tlZoom`:
```js
function tlOpenAddClip() {
  if (!tlClips.length) return;
  window._dlMode = 'append';
  openDlModal();
}
```

- [ ] **Step 3: Reset `_dlMode` when the download modal is closed normally**

Find `closeDlModal` function and add `window._dlMode = null;` at the start:
```js
function closeDlModal(){
  window._dlMode = null;
  // ... existing close logic
```

- [ ] **Step 4: Show/hide the "Add clip" button in `tlUpdateToolbar`**

In `tlUpdateToolbar`, add at the end:
```js
  const addClipBtn = document.getElementById('tl-addclip-btn');
  if (addClipBtn) addClipBtn.style.display = tlClips.length ? '' : 'none';
```

- [ ] **Step 5: Commit**
```bash
git add frontend/index.html
git commit -m "feat(timeline): add 'Add clip' button to toolbar"
```

---

### Task 5: Per-clip segment coloring on the timeline

**Files:**
- Modify: `frontend/index.html` (`tlRenderTrack` ~line 5020; `tlRender` ~line 4985)

- [ ] **Step 1: Update `tlRenderTrack` to color each segment by its `clipId`**

Find `tlRenderTrack`:
```js
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
      <div class="tl-handle tl-handle-l" onmousedown="tlHandleMousedown(event,'${seg.id}','l')"></div>
      <span style="pointer-events:none;padding-left:4px;opacity:.85;overflow:hidden;flex:1">${tlFmt(seg.sourceStart)}-${tlFmt(seg.sourceEnd)}</span>
      <div class="tl-handle tl-handle-r" onmousedown="tlHandleMousedown(event,'${seg.id}','r')"></div>
    </div>`;
  }).join('');
}
```
Replace with:
```js
function tlRenderTrack(trackId, clips) {
  const row = document.getElementById(trackId);
  if (!row) return;
  const totalWidth = Math.max(tlTotalDuration() * tlPixelsPerSec + 60, 600);
  row.style.width = totalWidth + 'px';
  row.innerHTML = clips.map(seg => {
    const x = tlSecsToX(seg.trackStart);
    const w = Math.max(4, tlSecsToX(seg.sourceEnd - seg.sourceStart));
    const sel = seg.id === tlSelectedSegId;
    const color = tlClipColor(seg.clipId);
    return `<div class="tl-clip${sel ? ' sel' : ''}" data-seg="${seg.id}"
      style="left:${x}px;width:${w}px;background:${color};border:1.5px solid ${sel ? '#fff' : color}"
      onmousedown="tlClipMousedown(event,'${seg.id}')">
      <div class="tl-handle tl-handle-l" onmousedown="tlHandleMousedown(event,'${seg.id}','l')"></div>
      <span style="pointer-events:none;padding-left:4px;opacity:.85;overflow:hidden;flex:1">${tlFmt(seg.sourceStart)}-${tlFmt(seg.sourceEnd)}</span>
      <div class="tl-handle tl-handle-r" onmousedown="tlHandleMousedown(event,'${seg.id}','r')"></div>
    </div>`;
  }).join('');
}
```

- [ ] **Step 2: Remove the `color` argument from `tlRenderTrack` call in `tlRender`**

Find in `tlRender`:
```js
  tlRenderTrack('tl-track-video', tlSegments, 'rgba(34,197,94,0.3)');
```
Replace with:
```js
  tlRenderTrack('tl-track-video', tlSegments);
```

- [ ] **Step 3: Also update the ruler to use `tlTotalDuration()` instead of `tlDuration`**

In `tlRenderRuler`:
```js
  const totalWidth = Math.max(tlDuration * tlPixelsPerSec + 60, inner.offsetWidth || 600);
  // ...
  const step = tlDuration > 60 ? 10 : 5;
  for (let t = 0; t <= tlDuration + step; t += step) {
```
Replace all three `tlDuration` uses with `tlTotalDuration()`:
```js
  const totalWidth = Math.max(tlTotalDuration() * tlPixelsPerSec + 60, inner.offsetWidth || 600);
  // ...
  const step = tlTotalDuration() > 60 ? 10 : 5;
  for (let t = 0; t <= tlTotalDuration() + step; t += step) {
```

- [ ] **Step 4: Commit**
```bash
git add frontend/index.html
git commit -m "feat(timeline): color segments by clip index"
```

---

### Task 6: Playback src-swap — cross-clip boundary logic

**Files:**
- Modify: `frontend/index.html` (`tlTimelineToVideoTime` ~line 5072; `tlSeek` ~line 5095; playback RAF loop ~line 5140; trim mousemove handler ~line 5293)

- [ ] **Step 1: Add `tlEnsureClipLoaded` function**

Add before `tlSeek`:
```js
function tlEnsureClipLoaded(clipId, onReady) {
  const clip = tlClipById(clipId);
  if (!clip) return;
  const vid = document.getElementById('preview-video');
  if (!vid) return;
  if (_tlActiveClipId === clipId) {
    if (onReady) onReady(vid);
    return;
  }
  _tlActiveClipId = clipId;
  vid.src = clip.url;
  if (onReady) {
    vid.addEventListener('canplay', () => onReady(vid), { once: true });
  }
  vid.load();
}
```

- [ ] **Step 2: Update `tlTimelineToVideoTime` to return `{clipId, videoTime}`**

Find:
```js
function tlTimelineToVideoTime(timelineSecs) {
  // Map a timeline position (seconds) → source video time
  for (const seg of tlSegments) {
    const dur = seg.sourceEnd - seg.sourceStart;
    if (timelineSecs >= seg.trackStart && timelineSecs < seg.trackStart + dur) {
      return seg.sourceStart + (timelineSecs - seg.trackStart);
    }
  }
  // Past all segments — clamp to end of last segment
  const last = tlSegments[tlSegments.length - 1];
  return last ? last.sourceEnd : 0;
}
```
Replace with:
```js
function tlTimelineToVideoTime(timelineSecs) {
  const sorted = [...tlSegments].sort((a, b) => a.trackStart - b.trackStart);
  for (const seg of sorted) {
    const dur = seg.sourceEnd - seg.sourceStart;
    if (timelineSecs >= seg.trackStart && timelineSecs < seg.trackStart + dur) {
      return { clipId: seg.clipId, videoTime: seg.sourceStart + (timelineSecs - seg.trackStart) };
    }
  }
  const last = sorted[sorted.length - 1];
  return last ? { clipId: last.clipId, videoTime: last.sourceEnd } : { clipId: null, videoTime: 0 };
}
```

- [ ] **Step 3: Update `tlSeek` to use new return type and swap src**

Find:
```js
function tlSeek(timelineSecs) {
  const total = tlTotalDuration();
  tlPlayheadTime = Math.max(0, Math.min(total, timelineSecs));
  if (_tlVideoEl) _tlVideoEl.currentTime = tlTimelineToVideoTime(tlPlayheadTime);
  tlRender();
}
```
Replace with:
```js
function tlSeek(timelineSecs) {
  const total = tlTotalDuration();
  tlPlayheadTime = Math.max(0, Math.min(total, timelineSecs));
  const { clipId, videoTime } = tlTimelineToVideoTime(tlPlayheadTime);
  if (clipId) {
    tlEnsureClipLoaded(clipId, vid => { vid.currentTime = videoTime; });
  }
  tlRender();
}
```

- [ ] **Step 4: Update `tlSplit` to use new return type**

Find in `tlSplit`:
```js
  const splitVideoTime = tlTimelineToVideoTime(tlPlayheadTime);
  if (splitVideoTime <= seg.sourceStart + 0.05 || splitVideoTime >= seg.sourceEnd - 0.05) return;
  const left  = tlNewSeg(seg.sourceStart, splitVideoTime, seg.trackStart, Object.assign({}, seg.color));
  const rightTrackStart = seg.trackStart + (splitVideoTime - seg.sourceStart);
  const right = tlNewSeg(splitVideoTime, seg.sourceEnd, rightTrackStart, Object.assign({}, seg.color));
```
Replace with:
```js
  const { videoTime: splitVideoTime } = tlTimelineToVideoTime(tlPlayheadTime);
  if (splitVideoTime <= seg.sourceStart + 0.05 || splitVideoTime >= seg.sourceEnd - 0.05) return;
  const left  = tlNewSeg(seg.sourceStart, splitVideoTime, seg.trackStart, Object.assign({}, seg.color), seg.clipId);
  const rightTrackStart = seg.trackStart + (splitVideoTime - seg.sourceStart);
  const right = tlNewSeg(splitVideoTime, seg.sourceEnd, rightTrackStart, Object.assign({}, seg.color), seg.clipId);
```

- [ ] **Step 5: Update the playback RAF loop to handle cross-clip boundaries**

Find the RAF frame function inside `tlTogglePlay`:
```js
    const frame = () => {
      if (!_tlPlaying) return;
      const vt = _tlVideoEl.currentTime;
      // Find which segment the video is currently inside
      const activeSeg = tlSegments.find(s => vt >= s.sourceStart && vt < s.sourceEnd);
      if (activeSeg) {
        tlPlayheadTime = activeSeg.trackStart + (vt - activeSeg.sourceStart);
      } else {
        // Video has passed the end of a segment — find the next one
        const sorted = [...tlSegments].sort((a, b) => a.sourceStart - b.sourceStart);
        const nextSeg = sorted.find(s => s.sourceStart > vt);
        if (nextSeg) {
          _tlVideoEl.currentTime = nextSeg.sourceStart;
          tlPlayheadTime = nextSeg.trackStart;
        } else {
          // Past the last segment — stop playback
          _tlVideoEl.pause();
          _tlPlaying = false;
          const btn = document.getElementById('tl-play-btn');
```
Replace the frame function body with:
```js
    const frame = () => {
      if (!_tlPlaying) return;
      const vid = document.getElementById('preview-video');
      if (!vid) return;
      const vt = vid.currentTime;
      // Only match segments belonging to the active clip
      const clipSegs = tlSegments.filter(s => s.clipId === _tlActiveClipId);
      const activeSeg = clipSegs.find(s => vt >= s.sourceStart && vt < s.sourceEnd);
      if (activeSeg) {
        tlPlayheadTime = activeSeg.trackStart + (vt - activeSeg.sourceStart);
      } else {
        // Find the next segment by trackStart order (may be a different clip)
        const sorted = [...tlSegments].sort((a, b) => a.trackStart - b.trackStart);
        const nextSeg = sorted.find(s => s.trackStart > tlPlayheadTime);
        if (nextSeg) {
          tlEnsureClipLoaded(nextSeg.clipId, v => {
            v.currentTime = nextSeg.sourceStart;
            v.play().catch(() => {});
          });
          tlPlayheadTime = nextSeg.trackStart;
        } else {
          // Past the last segment — stop playback
          vid.pause();
          _tlPlaying = false;
          const btn = document.getElementById('tl-play-btn');
```

- [ ] **Step 6: Fix the trim mousemove handler — replace `tlDuration` with per-clip duration**

Find in the mousemove handler:
```js
      seg.sourceEnd = Math.max(window._tlTrimState.origStart + 0.1, Math.min(tlDuration, window._tlTrimState.origEnd + dt));
```
Replace with:
```js
      seg.sourceEnd = Math.max(window._tlTrimState.origStart + 0.1, Math.min(tlClipDuration(seg.clipId), window._tlTrimState.origEnd + dt));
```

- [ ] **Step 7: Update `_tlVideoEl` references in `tlTogglePlay`**

`tlTogglePlay` references `_tlVideoEl` directly. Replace the two `_tlVideoEl` usages inside `tlTogglePlay` (the `.pause()` and `.play()` calls) with `document.getElementById('preview-video')`:
```js
// Before:
  if (_tlPlaying) {
    _tlVideoEl.pause();
// After:
  if (_tlPlaying) {
    const vid = document.getElementById('preview-video');
    if (vid) vid.pause();
```
And:
```js
// Before:
    _tlVideoEl.play().catch(() => {});
// After:
    const vid2 = document.getElementById('preview-video');
    if (vid2) vid2.play().catch(() => {});
```

- [ ] **Step 8: Commit**
```bash
git add frontend/index.html
git commit -m "feat(timeline): src-swap playback across clip boundaries"
```

---

### Task 7: Export payload — group segments by clipId and send `clips` array

**Files:**
- Modify: `frontend/index.html` (export fetch body ~line 4545; `openExpModal` guard ~line 4342)

- [ ] **Step 1: Update the export guard in `openExpModal`**

Find:
```js
function openExpModal(){
  if(!downloadedVideoPath){alert('Download a video first.');return;}
```
Replace with:
```js
function openExpModal(){
  if(!tlClips.length){alert('Download a video first.');return;}
```

- [ ] **Step 2: Update the export `#exp-video-info` text**

Find:
```js
  const filename=downloadedVideoPath.split(/[\\/]/).pop();
  document.getElementById('exp-video-info').textContent='Video: '+filename;
```
Replace with:
```js
  const clipNames = tlClips.map(c => c.path.split(/[\\/]/).pop()).join(', ');
  document.getElementById('exp-video-info').textContent = tlClips.length === 1 ? 'Video: ' + clipNames : tlClips.length + ' clips: ' + clipNames;
```

- [ ] **Step 3: Update the export fetch body to send `clips` instead of `video_path`+`segments`**

Find (around line 4545):
```js
    body:JSON.stringify({video_path:downloadedVideoPath,template:tpl,title,emoji_source:activeEmoTab==='mypack'?'emojipack':activeEmoTab,segments:typeof ENABLE_TIMELINE!=='undefined'&&ENABLE_TIMELINE?tlSegments:null})})
```
Replace with:
```js
    body:JSON.stringify({
      clips: tlClips.map(clip => ({
        video_path: clip.path,
        segments: tlSegments.filter(s => s.clipId === clip.id)
      })),
      template:tpl,
      title,
      emoji_source:activeEmoTab==='mypack'?'emojipack':activeEmoTab
    })})
```

- [ ] **Step 4: Commit**
```bash
git add frontend/index.html
git commit -m "feat(export): send clips array instead of single video_path"
```

---

### Task 8: Backend `exporter.py` — multi-clip support

**Files:**
- Modify: `exporter.py` (`build_segment_inputs` ~line 54; `export_video` ~line 374)

- [ ] **Step 1: Add `input_offset` param to `build_segment_inputs`**

Find:
```python
def build_segment_inputs(video_path: str, segments: list) -> tuple[list, list, list, str, str, int]:
```
Replace with:
```python
def build_segment_inputs(video_path: str, segments: list, input_offset: int = 0) -> tuple[list, list, list, str, str, int]:
```

- [ ] **Step 2: Replace hardcoded stream indices `0` with `input_offset` in the single-segment branch**

Find (inside single-segment branch, ~line 90):
```python
        if color_suffix:
            vl = lbl('sv')
            al = lbl('sa')
            filter_parts = [
                f"[0:v]setpts=PTS-STARTPTS{color_suffix}[{vl}]",
                f"[0:a]asetpts=PTS-STARTPTS[{al}]",
            ]
            return main_pre_args, [], filter_parts, vl, al, 1
        # No color grading — use raw streams directly; no filter needed
        return main_pre_args, [], [], '0:v', '0:a', 1
```
Replace with:
```python
        if color_suffix:
            vl = lbl('sv')
            al = lbl('sa')
            filter_parts = [
                f"[{input_offset}:v]setpts=PTS-STARTPTS{color_suffix}[{vl}]",
                f"[{input_offset}:a]asetpts=PTS-STARTPTS[{al}]",
            ]
            return main_pre_args, [], filter_parts, vl, al, 1
        return main_pre_args, [], [], f'{input_offset}:v', f'{input_offset}:a', 1
```

- [ ] **Step 3: Replace hardcoded stream indices in the multi-segment branch**

Find (in the multi-segment for loop, ~line 104):
```python
    for i, seg in enumerate(segs):
        ss = float(seg.get('sourceStart', 0))
        se = float(seg.get('sourceEnd',   0))
        c  = seg.get('color', {})
        pre_args = ["-ss", str(ss), "-to", str(se)]
        if i == 0:
            main_pre_args = pre_args
        else:
            extra_vid_inputs.append((pre_args, video_path))

        vl = lbl('sv')
        al = lbl('sa')
        color_suffix = _color_filter_suffix(c)
        filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS{color_suffix}[{vl}]")
        filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[{al}]")
```
Replace with:
```python
    for i, seg in enumerate(segs):
        ss = float(seg.get('sourceStart', 0))
        se = float(seg.get('sourceEnd',   0))
        c  = seg.get('color', {})
        pre_args = ["-ss", str(ss), "-to", str(se)]
        if i == 0:
            main_pre_args = pre_args
        else:
            extra_vid_inputs.append((pre_args, video_path))

        stream_i = input_offset + i
        vl = lbl('sv')
        al = lbl('sa')
        color_suffix = _color_filter_suffix(c)
        filter_parts.append(f"[{stream_i}:v]setpts=PTS-STARTPTS{color_suffix}[{vl}]")
        filter_parts.append(f"[{stream_i}:a]asetpts=PTS-STARTPTS[{al}]")
```

- [ ] **Step 4: Add `clips` parameter to `export_video` with backward-compat wrapping**

Find:
```python
def export_video(video_path: str, template: dict, title: str = "",
                 on_progress=None, emoji_source: str = "twemoji",
                 segments: list = None) -> str:
    """Build and run the FFmpeg command. Returns output file path."""
    job_id = uuid.uuid4().hex[:8]
```
Replace with:
```python
def export_video(video_path: str = None, template: dict = None, title: str = "",
                 on_progress=None, emoji_source: str = "twemoji",
                 segments: list = None, clips: list = None) -> str:
    """Build and run the FFmpeg command. Returns output file path."""
    # Normalize to clips format
    if clips is None:
        clips = [{"video_path": video_path, "segments": segments or []}]
    job_id = uuid.uuid4().hex[:8]
```

- [ ] **Step 5: Replace the single `build_segment_inputs` call in `export_video` with a multi-clip loop**

Find (~line 437):
```python
    seg_pre_args, extra_vid_inputs, seg_parts, seg_vlabel, seg_alabel, n_vid = \
        build_segment_inputs(video_path, segments or [])
```
Replace with:
```python
    all_seg_pre_args = []
    all_extra_vid_inputs = []
    all_seg_parts = []
    clip_vlabels = []
    clip_alabels = []
    n_vid = 0

    for clip_entry in clips:
        cp = clip_entry["video_path"]
        cs = clip_entry.get("segments") or []
        pre, extra, parts, vl, al, nv = build_segment_inputs(cp, cs, input_offset=n_vid)
        if n_vid == 0:
            all_seg_pre_args = pre
            # first video path stored for cmd building
            _first_video_path = cp
        else:
            # subsequent clips: first segment of each clip is a new -i entry
            all_extra_vid_inputs.append((pre, cp))
        all_extra_vid_inputs.extend(extra)
        all_seg_parts.extend(parts)
        clip_vlabels.append(vl)
        clip_alabels.append(al)
        n_vid += nv

    # If multiple clips, add a top-level concat across clip outputs
    if len(clips) > 1:
        _cn = [0]
        def _clbl(p='cc'):
            _cn[0] += 1
            return f"{p}{_cn[0]}"
        vc_out = _clbl('cv')
        ac_out = _clbl('ca')
        all_seg_parts.append(''.join(f'[{l}]' for l in clip_vlabels) + f'concat=n={len(clips)}:v=1:a=0[{vc_out}]')
        all_seg_parts.append(''.join(f'[{l}]' for l in clip_alabels) + f'concat=n={len(clips)}:v=0:a=1[{ac_out}]')
        seg_vlabel, seg_alabel = vc_out, ac_out
    else:
        seg_vlabel, seg_alabel = clip_vlabels[0], clip_alabels[0]

    seg_pre_args = all_seg_pre_args
    extra_vid_inputs = all_extra_vid_inputs
    seg_parts = all_seg_parts
    video_path = _first_video_path
```

- [ ] **Step 6: Fix the FFmpeg cmd build line to use `video_path` (now set to `_first_video_path`)**

The line ~line 471:
```python
    cmd = ["ffmpeg", "-y"] + seg_pre_args + ["-i", video_path]
```
This now uses `video_path = _first_video_path` from Step 5, so it's correct as-is. Verify no other uses of the old `video_path` param remain in the function body.

Also update the filter_complex assembly to use `seg_parts` (already the variable name, verify it's used):
```python
    filter_parts, final_video = build_filter_graph(
        layers, cw, ch, text_pngs, image_inputs, mask_inputs,
        src_video_label=seg_vlabel
    )
```
Find the full filter_complex list construction and verify `seg_parts` is included. It should be assembled like:
```python
    all_filter = seg_parts + filter_parts + audio_filter_parts
```
Check that `seg_parts` (renamed from `seg_parts` which was `seg_parts` originally) is used. If the original code uses a variable named differently, match it.

- [ ] **Step 7: Commit**
```bash
git add exporter.py
git commit -m "feat(exporter): support multi-clip concatenation via clips param"
```

---

### Task 9: Update `app.py` export route to pass `clips`

**Files:**
- Modify: `app.py` (`start_export` ~line 142)

- [ ] **Step 1: Accept `clips` from request body and pass to `export_video`**

Find:
```python
@app.post("/api/export")
def start_export():
    body = request.json or {}
    video_path   = body.get("video_path", "")
    template     = body.get("template", {})
    title        = body.get("title", "")
    emoji_source = body.get("emoji_source", "twemoji")
    segments     = body.get("segments", None)
    if not video_path or not os.path.exists(video_path):
        return jsonify({"error": "video_path not found"}), 400

    job_id = uuid.uuid4().hex[:8]
    q: queue.Queue = queue.Queue()
    _jobs[job_id] = q

    def run():
        try:
            def on_progress(line):
                q.put({"type": "progress", "line": line})
            out = export_video(video_path, template, title, on_progress,
                               emoji_source=emoji_source, segments=segments)
```
Replace with:
```python
@app.post("/api/export")
def start_export():
    body = request.json or {}
    clips        = body.get("clips", None)
    video_path   = body.get("video_path", "")
    template     = body.get("template", {})
    title        = body.get("title", "")
    emoji_source = body.get("emoji_source", "twemoji")
    segments     = body.get("segments", None)

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
            out = export_video(video_path, template, title, on_progress,
                               emoji_source=emoji_source, segments=segments,
                               clips=clips)
```

- [ ] **Step 2: Commit**
```bash
git add app.py
git commit -m "feat(api): export route accepts clips array for multi-source export"
```

---

### Task 10: Tests for multi-clip export backend

**Files:**
- Modify: `tests/test_exporter.py`

- [ ] **Step 1: Add a test for `build_segment_inputs` with `input_offset`**

Open `tests/test_exporter.py` and add:
```python
def test_build_segment_inputs_with_offset():
    """input_offset shifts all stream indices so clips can be concatenated."""
    from exporter import build_segment_inputs
    segs = [{"sourceStart": 0, "sourceEnd": 10, "color": {}}]
    pre, extra, parts, vl, al, n = build_segment_inputs("clip.mp4", segs, input_offset=3)
    # With no color grading, raw stream labels use the offset
    assert vl == "3:v"
    assert al == "3:a"
    assert n == 1
    assert extra == []
    assert parts == []


def test_build_segment_inputs_offset_with_color():
    from exporter import build_segment_inputs
    segs = [{"sourceStart": 0, "sourceEnd": 5, "color": {"brightness": 10}}]
    pre, extra, parts, vl, al, n = build_segment_inputs("clip.mp4", segs, input_offset=2)
    assert n == 1
    # filter should reference stream 2
    assert "[2:v]" in parts[0]
    assert "[2:a]" in parts[1]
```

- [ ] **Step 2: Run the tests**
```
pytest tests/test_exporter.py::test_build_segment_inputs_with_offset tests/test_exporter.py::test_build_segment_inputs_offset_with_color -v
```
Expected: PASS

- [ ] **Step 3: Add a test for `export_video` with two clips using actual video files**

```python
def test_export_video_multi_clip(tmp_path, monkeypatch):
    """export_video with clips= calls ffmpeg with both source files."""
    from exporter import export_video
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        class R: returncode = 0; stdout = b''; stderr = b''
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)

    # Provide two fake clips (files don't need to exist for cmd-build test)
    clips = [
        {"video_path": "uploads/a.mp4", "segments": [{"sourceStart": 0, "sourceEnd": 5, "color": {}}]},
        {"video_path": "uploads/b.mp4", "segments": [{"sourceStart": 0, "sourceEnd": 3, "color": {}}]},
    ]
    template = {"canvas": {"width": 1080, "height": 1920}, "layers": []}
    try:
        export_video(template=template, title="test", clips=clips)
    except Exception:
        pass  # ffmpeg not available in test env; we only check the cmd

    assert any(calls), "ffmpeg was not called"
    cmd = calls[0]
    assert "uploads/a.mp4" in cmd
    assert "uploads/b.mp4" in cmd
    # concat filter should appear for 2 clips
    fc_idx = cmd.index("-filter_complex") if "-filter_complex" in cmd else -1
    assert fc_idx != -1
    assert "concat=n=2" in cmd[fc_idx + 1]
```

- [ ] **Step 4: Run the full test**
```
pytest tests/test_exporter.py -v
```
Expected: all pass (or skip if ffmpeg unavailable)

- [ ] **Step 5: Commit**
```bash
git add tests/test_exporter.py
git commit -m "test(exporter): multi-clip input_offset and clips param"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| `tlClips` array replaces single globals | Task 1, 2 |
| `clipId` on each segment | Task 1 |
| `_tlActiveClipId` tracking | Task 1, 6 |
| Sidebar clip list with remove | Task 3 |
| "Add clip" button in toolbar | Task 4 |
| `_dlMode` append flag | Task 2, 4 |
| Clip colors by index | Task 5 |
| Src-swap on clip boundary (seek + playback) | Task 6 |
| `tlTimelineToVideoTime` returns `{clipId, videoTime}` | Task 6 |
| Per-clip trim boundary guard | Task 6 |
| Export payload sends `clips` array | Task 7 |
| Export guard uses `tlClips.length` | Task 7 |
| `build_segment_inputs` `input_offset` | Task 8 |
| `export_video` `clips` param + backward compat | Task 8 |
| `app.py` accepts `clips` | Task 9 |
| Backend tests | Task 10 |

**Type consistency check:**
- `tlNewSeg(sourceStart, sourceEnd, trackStart, color, clipId)` — used consistently in Tasks 1, 2, 6 (split).
- `tlTimelineToVideoTime` returns `{clipId, videoTime}` — destructured correctly in Tasks 6 (seek, split).
- `tlEnsureClipLoaded(clipId, onReady?)` — called in Tasks 6 (seek, playback loop).
- `tlClipColor(clipId)` used in Task 5 `tlRenderTrack`.
- `tlClipDuration(clipId)` used in Task 6 trim guard.

**No placeholders found.**
