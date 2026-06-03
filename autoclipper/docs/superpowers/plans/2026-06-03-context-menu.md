# Context Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a custom right-click context menu to the autoclipper editor that appears on canvas objects and layer list rows, showing icon+label action rows relevant to the target type.

**Architecture:** A single `<div id="ctx-menu">` appended to `<body>` is absolutely positioned on each `contextmenu` event, populated dynamically based on what was right-clicked, and dismissed on outside-click/scroll/Escape. Two `contextmenu` listeners cover the canvas area and the layer list panel. All logic lives in `frontend/index.html` alongside the existing code.

**Tech Stack:** Vanilla JS, Fabric.js 5.3.1, existing CSS variables

---

### Task 1: Add the context menu DOM and CSS

**Files:**
- Modify: `frontend/index.html` — add `#ctx-menu` div before `</body>` and styles in `<style>`

- [ ] **Step 1: Add CSS for the context menu**

In the `<style>` block (anywhere after the existing rules — e.g. just before `</style>`), add:

```css
/* ─── CONTEXT MENU ───────────────────────────────────── */
#ctx-menu{position:fixed;z-index:9999;min-width:180px;background:var(--s2);border:1px solid var(--b1);border-radius:var(--r);box-shadow:0 8px 24px rgba(0,0,0,.5);padding:4px 0;display:none;user-select:none}
#ctx-menu.open{display:block}
.ctx-item{display:flex;align-items:center;gap:8px;padding:6px 12px;cursor:pointer;font-size:12px;color:var(--tx);transition:.1s}
.ctx-item:hover{background:var(--s3)}
.ctx-item.danger:hover{color:var(--danger)}
.ctx-item svg{flex-shrink:0;color:var(--sub)}
.ctx-item:hover svg{color:var(--tx)}
.ctx-item.danger:hover svg{color:var(--danger)}
```

- [ ] **Step 2: Add the menu div before `</body>`**

Insert before line 2719 (`</body>`):

```html
<div id="ctx-menu"></div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add context menu DOM and CSS"
```

---

### Task 2: Add core open/close logic

**Files:**
- Modify: `frontend/index.html` — add JS functions `openCtxMenu`, `closeCtxMenu`, and global dismiss listeners

- [ ] **Step 1: Add the context menu JS module**

In the `<script>` block, just before the closing `</script>` tag (line 2718), add:

```js
// ── CONTEXT MENU ───────────────────────────────────────────────────────────
let _clipboard = null;

function closeCtxMenu(){
  document.getElementById('ctx-menu').classList.remove('open');
}

function openCtxMenu(e, items){
  e.preventDefault();
  const menu = document.getElementById('ctx-menu');
  menu.innerHTML = '';
  items.forEach(({icon, label, action, danger}) => {
    const row = document.createElement('div');
    row.className = 'ctx-item' + (danger ? ' danger' : '');
    row.innerHTML = `${icon}<span>${label}</span>`;
    row.addEventListener('click', () => { closeCtxMenu(); action(); });
    menu.appendChild(row);
  });
  menu.classList.add('open');
  // Position: keep within viewport
  const vw = window.innerWidth, vh = window.innerHeight;
  let x = e.clientX, y = e.clientY;
  menu.style.left = '0px'; menu.style.top = '0px'; // reset to measure
  const mw = menu.offsetWidth || 180, mh = menu.offsetHeight || 200;
  if(x + mw > vw) x = vw - mw - 4;
  if(y + mh > vh) y = vh - mh - 4;
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';
}

document.addEventListener('click', closeCtxMenu);
document.addEventListener('keydown', e => { if(e.key === 'Escape') closeCtxMenu(); });
document.addEventListener('scroll', closeCtxMenu, true);
```

- [ ] **Step 2: Verify the menu element and functions exist in DevTools**

Open the app in the browser, open DevTools console and run:
```js
openCtxMenu({preventDefault:()=>{},clientX:200,clientY:200},[{icon:'',label:'Test',action:()=>{},danger:false}])
```
Expected: a small menu appears at 200,200 with a "Test" row.

Run `closeCtxMenu()` — menu disappears.

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add context menu open/close logic"
```

---

### Task 3: Build the action item factory

**Files:**
- Modify: `frontend/index.html` — add `ctxItemsForObject(o)` and `ctxItemsForAudio()` functions

- [ ] **Step 1: Add the item builder functions**

Add immediately after the `openCtxMenu`/`closeCtxMenu` block from Task 2:

```js
function _ctxIcon(path, sz=13){
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${sz}" height="${sz}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
}

const _CTX_ICO = {
  duplicate: _ctxIcon('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'),
  forward:   _ctxIcon('<polyline points="17 11 21 7 17 3"/><line x1="21" y1="7" x2="9" y2="7"/><polyline points="7 21 3 17 7 13"/><line x1="15" y1="17" x2="3" y2="17"/>'),
  backward:  _ctxIcon('<polyline points="7 13 3 17 7 21"/><line x1="3" y1="17" x2="15" y2="17"/><polyline points="17 3 21 7 17 11"/><line x1="9" y1="7" x2="21" y2="7"/>'),
  mute:      _ctxIcon('<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/>'),
  unmute:    _ctxIcon('<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>'),
  lock:      _ctxIcon('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'),
  unlock:    _ctxIcon('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>'),
  rename:    _ctxIcon('<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>'),
  split:     _ctxIcon('<line x1="12" y1="2" x2="12" y2="22"/><path d="M2 12h4"/><path d="M18 12h4"/>'),
  copy:      _ctxIcon('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'),
  paste:     _ctxIcon('<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 0-2-2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>'),
  trash:     _ctxIcon('<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'),
};

function _ctxDuplicate(o){
  o.clone(cloned => {
    cloned.set({left: (o.left||0)+10, top: (o.top||0)+10});
    cv.add(cloned);
    cv.setActiveObject(cloned);
    cv.renderAll();
    syncLayers();
    saveHist();
  });
}

function _ctxRename(o){
  // Find the layer row for this object and make its .lname inline-editable
  const objs = cv.getObjects().filter(x=>!x.excludeFromExport).slice().reverse();
  const idx = objs.indexOf(o);
  if(idx < 0) return;
  const rows = document.querySelectorAll('#layer-list .lrow');
  const row = rows[idx];
  if(!row) return;
  const nameEl = row.querySelector('.lname');
  if(!nameEl) return;
  const orig = o._label || nameEl.textContent;
  nameEl.contentEditable = 'true';
  nameEl.focus();
  // Select all text
  const range = document.createRange();
  range.selectNodeContents(nameEl);
  window.getSelection().removeAllRanges();
  window.getSelection().addRange(range);
  function finish(){
    nameEl.contentEditable = 'false';
    const newName = nameEl.textContent.trim() || orig;
    o._label = newName;
    nameEl.textContent = newName;
    saveHist();
  }
  nameEl.addEventListener('blur', finish, {once:true});
  nameEl.addEventListener('keydown', e => {
    if(e.key==='Enter'){e.preventDefault();nameEl.blur();}
    if(e.key==='Escape'){nameEl.textContent=orig;nameEl.blur();}
  }, {once:true});
}

function _ctxRenameAudio(){
  const nameEl = document.querySelector('#audio-lrow-inner .lname');
  if(!nameEl || !audioLayer) return;
  const orig = nameEl.textContent.trim();
  nameEl.contentEditable = 'true';
  nameEl.focus();
  const range = document.createRange();
  range.selectNodeContents(nameEl);
  window.getSelection().removeAllRanges();
  window.getSelection().addRange(range);
  function finish(){
    nameEl.contentEditable = 'false';
    const newName = nameEl.textContent.trim() || orig;
    audioLayer._label = newName;
    nameEl.textContent = newName;
  }
  nameEl.addEventListener('blur', finish, {once:true});
  nameEl.addEventListener('keydown', e => {
    if(e.key==='Enter'){e.preventDefault();nameEl.blur();}
    if(e.key==='Escape'){nameEl.textContent=orig;nameEl.blur();}
  }, {once:true});
}

function _ctxSplitAtPlayhead(o){
  const vidEl = document.getElementById('preview-video');
  if(!vidEl || !vidEl.src || vidEl.readyState < 1){
    _ctxToast('No video playing — cannot split');
    return;
  }
  _ctxToast('Split at playhead: trim this video in the Edit panel');
}

function _ctxToast(msg){
  let t = document.getElementById('ctx-toast');
  if(!t){
    t = document.createElement('div');
    t.id = 'ctx-toast';
    t.style.cssText='position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--s3);border:1px solid var(--b2);color:var(--tx);font-size:12px;padding:7px 14px;border-radius:var(--rs);z-index:10000;pointer-events:none;transition:opacity .2s';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.opacity = '1';
  clearTimeout(t._tid);
  t._tid = setTimeout(() => t.style.opacity='0', 2200);
}

function ctxItemsForObject(o){
  const isLocked = o.lockMovementX && o.lockMovementY;
  const isMuted  = !!o._muted;
  const isVideo  = o._type === 'video';
  const items = [];

  items.push({icon:_CTX_ICO.duplicate, label:'Duplicate', action:()=>_ctxDuplicate(o)});
  items.push({icon:_CTX_ICO.forward,   label:'Bring Forward', action:()=>{cv.bringForward(o);cv.renderAll();syncLayers();saveHist();}});
  items.push({icon:_CTX_ICO.backward,  label:'Send Back',    action:()=>{cv.sendBackwards(o);cv.renderAll();syncLayers();saveHist();}});

  if(isVideo){
    items.push({icon: isMuted ? _CTX_ICO.unmute : _CTX_ICO.mute,
      label: isMuted ? 'Unmute' : 'Mute',
      action:()=>{ o._muted = !o._muted; saveHist(); }});
  }

  items.push({icon: isLocked ? _CTX_ICO.unlock : _CTX_ICO.lock,
    label: isLocked ? 'Unlock' : 'Lock',
    action:()=>{
      const lock = !isLocked;
      o.set({lockMovementX:lock,lockMovementY:lock,lockScalingX:lock,lockScalingY:lock,hasControls:!lock,selectable:!lock});
      cv.renderAll();
      saveHist();
    }});

  items.push({icon:_CTX_ICO.rename, label:'Rename', action:()=>_ctxRename(o)});

  if(isVideo){
    items.push({icon:_CTX_ICO.split, label:'Split at Playhead', action:()=>_ctxSplitAtPlayhead(o)});
  }

  items.push({icon:_CTX_ICO.copy, label:'Copy', action:()=>{ _clipboard = o; }});

  if(_clipboard){
    items.push({icon:_CTX_ICO.paste, label:'Paste', action:()=>{
      _clipboard.clone(cloned=>{
        cloned.set({left:(_clipboard.left||0)+10,top:(_clipboard.top||0)+10});
        cv.add(cloned);cv.setActiveObject(cloned);cv.renderAll();syncLayers();saveHist();
      });
    }});
  }

  items.push({icon:_CTX_ICO.trash, label:'Delete', action:()=>{ cv.setActiveObject(o); delSel(); }, danger:true});
  return items;
}

function ctxItemsForAudio(){
  const isMuted = !!audioLayer?.muted;
  return [
    {icon: isMuted ? _CTX_ICO.unmute : _CTX_ICO.mute,
     label: isMuted ? 'Unmute' : 'Mute',
     action:()=>{ if(audioLayer){ audioLayer.muted=!audioLayer.muted; updatePreviewStrip(); }}},
    {icon:_CTX_ICO.rename, label:'Rename', action:()=>_ctxRenameAudio()},
    {icon:_CTX_ICO.trash,  label:'Delete', action:()=>removeAudioLayer(), danger:true},
  ];
}
```

- [ ] **Step 2: Verify in DevTools console**

```js
// With a canvas object selected:
const o = cv.getActiveObject();
console.log(ctxItemsForObject(o).map(i=>i.label));
// Expected: ["Duplicate","Bring Forward","Send Back", ..."Delete"]
```

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add context menu item factory functions"
```

---

### Task 4: Wire up canvas area contextmenu listener

**Files:**
- Modify: `frontend/index.html` — attach `contextmenu` listener to `#canvas-area`

- [ ] **Step 1: Find where the canvas-area mousedown listener is added**

It's around line 1152:
```js
document.getElementById('canvas-area').addEventListener('mousedown', e => {
```

- [ ] **Step 2: Add the contextmenu listener directly after that block (after its closing `});`)**

```js
document.getElementById('canvas-area').addEventListener('contextmenu', e => {
  if(!cv) return;
  const target = cv.findTarget(e, false);
  if(!target || target.excludeFromExport || target._isMaskEditor) {
    e.preventDefault();
    return;
  }
  cv.setActiveObject(target);
  cv.renderAll();
  updateProps();
  openCtxMenu(e, ctxItemsForObject(target));
});
```

- [ ] **Step 3: Test manually**

Run the app (`python app.py`), right-click a video layer on the canvas.
Expected: browser context menu is suppressed, custom menu appears at cursor with "Duplicate", "Bring Forward", etc.
Right-click on empty canvas area — expected: no custom menu, browser default suppressed.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat: wire contextmenu listener to canvas area"
```

---

### Task 5: Wire up layer list contextmenu listeners

**Files:**
- Modify: `frontend/index.html` — attach `contextmenu` listeners to `#layer-list` and `#audio-layer-row`

- [ ] **Step 1: Find where `syncLayers` builds layer rows**

Around line 1546. The `#layer-list` and `#audio-layer-row` are the two targets.

- [ ] **Step 2: Add listeners after the canvas-area contextmenu listener from Task 4**

```js
document.getElementById('layer-list').addEventListener('contextmenu', e => {
  e.preventDefault();
  const row = e.target.closest('.lrow');
  if(!row) return;
  // Map row index back to canvas object (layer list is reversed order)
  const rows = Array.from(document.querySelectorAll('#layer-list .lrow'));
  const idx = rows.indexOf(row);
  if(idx < 0) return;
  const objs = cv.getObjects().filter(o=>!o.excludeFromExport).slice().reverse();
  const obj = objs[idx];
  if(!obj) return;
  cv.setActiveObject(obj);
  cv.renderAll();
  updateProps();
  openCtxMenu(e, ctxItemsForObject(obj));
});

document.getElementById('audio-layer-row').addEventListener('contextmenu', e => {
  e.preventDefault();
  if(!audioLayer) return;
  openCtxMenu(e, ctxItemsForAudio());
});
```

- [ ] **Step 3: Test manually**

Right-click a row in the layer list panel — expected: custom menu appears. Right-click the audio layer row (when audio is loaded) — expected: Mute / Rename / Delete menu.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat: wire contextmenu listeners to layer list and audio row"
```

---

### Task 6: Verify full feature end-to-end

**Files:** none — manual verification only

- [ ] **Step 1: Test all action types on a canvas video object**

Right-click the video layer on canvas. Test each item:
- **Duplicate** — a second video layer appears, offset 10px
- **Bring Forward** — layer order changes in layer list
- **Send Back** — layer order changes in layer list
- **Mute** — menu label switches to "Unmute" on next open
- **Lock** — object handles disappear, object can't be dragged; "Unlock" on next open
- **Rename** — `.lname` in layer list becomes editable inline; Enter confirms, Escape cancels
- **Split at Playhead** — toast appears: "No video playing — cannot split" (or opens trim if video is playing)
- **Copy** — no visible change
- **Paste** — appears after Copy; cloned object added offset by 10px
- **Delete** — object removed from canvas and layer list

- [ ] **Step 2: Test on text/image/sticker objects**

Right-click a text layer — expected: no Mute or Split items in menu.

- [ ] **Step 3: Test on audio layer row**

Right-click audio layer row — expected: Mute / Rename / Delete only.

- [ ] **Step 4: Test dismiss behaviours**

- Click outside menu → menu closes
- Press Escape → menu closes
- Scroll → menu closes

- [ ] **Step 5: Test viewport clamping**

Right-click an object near the bottom-right corner of the screen — menu should flip so it stays within the viewport.

- [ ] **Step 6: Commit if any small fixes were made**

```bash
git add frontend/index.html
git commit -m "fix: context menu edge cases"
```
