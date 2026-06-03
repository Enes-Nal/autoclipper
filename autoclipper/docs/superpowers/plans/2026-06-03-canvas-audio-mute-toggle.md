# Canvas Audio Mute/Unmute Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a floating mute/unmute button over the canvas that appears on hover, letting users hear the downloaded video's audio during preview.

**Architecture:** Remove the hardcoded `muted` attribute from `#preview-video`; control mute state via a JS variable `_canvasMuted` (defaults to `true` to satisfy browser autoplay policy). A `#canvas-mute-btn` button lives inside `#phone`, hidden until hover via CSS, and calls `toggleCanvasMute()`.

**Tech Stack:** Vanilla JS, HTML/CSS — all changes in `frontend/index.html`.

---

### Task 1: Add CSS for the floating mute button

**Files:**
- Modify: `frontend/index.html` (CSS block, around line 143–145 where `.tbar-btn` is defined)

- [ ] **Step 1: Add the CSS rule**

Find the line:
```css
.tbar-btn:hover{background:var(--s3);color:var(--tx)}
```
After it, add:
```css
#canvas-mute-btn{position:absolute;bottom:8px;right:8px;z-index:10;opacity:0;pointer-events:none;transition:opacity .15s;background:rgba(0,0,0,.55);color:#fff;border-radius:var(--rs);border:none;cursor:pointer;padding:5px 7px;display:inline-flex;align-items:center}
#phone:hover #canvas-mute-btn{opacity:1;pointer-events:auto}
```

- [ ] **Step 2: Commit**

```
git add frontend/index.html
git commit -m "feat: add CSS for canvas hover mute button"
```

---

### Task 2: Add the button HTML inside `#phone`

**Files:**
- Modify: `frontend/index.html` (around line 463–466, the `#phone` div)

- [ ] **Step 1: Insert the button**

Find:
```html
        <div id="phone" style="position:relative">
          <canvas id="ec"></canvas>
          <canvas id="poly-overlay" style="position:absolute;top:0;left:0;pointer-events:none;display:none"></canvas>
        </div>
```
Replace with:
```html
        <div id="phone" style="position:relative">
          <canvas id="ec"></canvas>
          <canvas id="poly-overlay" style="position:absolute;top:0;left:0;pointer-events:none;display:none"></canvas>
          <button id="canvas-mute-btn" onclick="toggleCanvasMute()" title="Toggle audio" style="display:none"></button>
        </div>
```

- [ ] **Step 2: Commit**

```
git add frontend/index.html
git commit -m "feat: add canvas mute button HTML inside #phone"
```

---

### Task 3: Remove `muted` from `#preview-video` and add JS state + helpers

**Files:**
- Modify: `frontend/index.html` (line 642 for the `<video>` tag; around line 667 for state vars; around line 1348 for the DOMContentLoaded block; around line 2411 for `updateTplPreviews`)

- [ ] **Step 1: Remove `muted` from the video element**

Find (line ~642):
```html
<video id="preview-video" autoplay muted loop playsinline style="position:absolute;width:0;height:0;opacity:0;pointer-events:none"></video>
```
Replace with:
```html
<video id="preview-video" autoplay loop playsinline style="position:absolute;width:0;height:0;opacity:0;pointer-events:none"></video>
```

- [ ] **Step 2: Add the `_canvasMuted` state variable**

Find (line ~667):
```js
let downloadedVideoPath=null, downloadedVideoURL=null;
```
After it, add:
```js
let _canvasMuted=true;
```

- [ ] **Step 3: Add `toggleCanvasMute` and `syncCanvasMuteBtn` functions**

Find the existing `stripToggleMute` function (line ~780):
```js
function stripToggleMute(){
```
Before it, add:
```js
function syncCanvasMuteBtn(){
  const btn=document.getElementById('canvas-mute-btn');
  if(!btn)return;
  btn.style.display=downloadedVideoURL?'inline-flex':'none';
  btn.innerHTML=_canvasMuted?icoVolX(15):icoVol(15);
}
function toggleCanvasMute(){
  _canvasMuted=!_canvasMuted;
  const vidEl=document.getElementById('preview-video');
  if(vidEl)vidEl.muted=_canvasMuted;
  syncCanvasMuteBtn();
}
```

- [ ] **Step 4: Initialize muted state and show button on DOMContentLoaded**

Find the existing DOMContentLoaded listener (line ~1348):
```js
document.addEventListener('DOMContentLoaded', ()=>{
  const vidEl = document.getElementById('preview-video');
  if(vidEl){
```
Inside that `if(vidEl){` block, add after the opening brace:
```js
    vidEl.muted=true;
    syncCanvasMuteBtn();
```

- [ ] **Step 5: Reset mute state when a new video loads**

Find in `updateTplPreviews` (line ~2411):
```js
function updateTplPreviews(url){
  downloadedVideoURL=url;
  const vidEl=document.getElementById('preview-video');
  vidEl.src=url;
```
After `vidEl.src=url;`, add:
```js
  _canvasMuted=true;
  vidEl.muted=true;
  syncCanvasMuteBtn();
```

- [ ] **Step 6: Commit**

```
git add frontend/index.html
git commit -m "feat: wire canvas mute/unmute toggle — video audio on hover button"
```

---

### Task 4: Manual verification

**Files:** none

- [ ] **Step 1: Start the app**

```
python app.py
```
Open `http://localhost:5000` in the browser.

- [ ] **Step 2: Download a video and verify the button appears**

Paste a video URL in the Download modal and click Download. Once the canvas shows the video:
- Hover over the canvas — the mute button (volume-X icon) should fade in at the bottom-right.
- Move the cursor away — button should fade out.

- [ ] **Step 3: Verify unmute works**

While hovering, click the button. The icon should switch to the speaker/waves icon and video audio should be audible.

- [ ] **Step 4: Verify re-mute works**

Click the button again. Audio should stop, icon reverts to volume-X.

- [ ] **Step 5: Verify new video resets to muted**

Download a second video (or reload and download again). Confirm the button resets to the muted (volume-X) state and audio is silent until explicitly unmuted.
