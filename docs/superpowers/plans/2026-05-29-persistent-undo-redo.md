# Persistent Undo/Redo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Ctrl+Z / Ctrl+Y undo-redo keyboard shortcuts backed by IndexedDB so up to 50 history steps survive page reloads, keyed per project.

**Architecture:** All changes are in `frontend/index.html`. A thin IndexedDB wrapper (5 functions) is added after the state-variable block. `saveHist()` gains a fire-and-forget DB write + trim call. The synchronous init block at the bottom is replaced with an async IIFE that loads history from IndexedDB before creating canvas objects, then restores the latest snapshot automatically.

**Tech Stack:** Vanilla JS, Fabric.js 5.3.1, IndexedDB (native browser API), localStorage for project UUID.

---

## File map

| File | Change |
|---|---|
| `frontend/index.html` (line 406) | Add `db`, `dbAvailable`, `acProjectId` to state vars |
| `frontend/index.html` (after line 410) | Insert IndexedDB helper functions |
| `frontend/index.html` (line 801) | Extend `keydown` listener with Ctrl+Z / Ctrl+Y |
| `frontend/index.html` (lines 675–679) | Extend `saveHist()` to persist to DB and trim |
| `frontend/index.html` (line 1127) | Extend `applyBuiltinTpl()` to reset project history |
| `frontend/index.html` (lines 1273–1277) | Replace sync init block with async IIFE |

---

## Task 1: Add state variables and IndexedDB helpers

**Files:**
- Modify: `frontend/index.html:406` (state block)
- Modify: `frontend/index.html:410` (insert helpers after state block)

- [ ] **Step 1: Add three new state variables to the existing state block**

Find this exact line (line 406):
```js
let hist=[], histIdx=-1, histLock=false;
```
Replace it with:
```js
let hist=[], histIdx=-1, histLock=false;
let db=null, dbAvailable=false, acProjectId='';
```

- [ ] **Step 2: Insert IndexedDB helper functions after the state block**

Find this exact line (line 409):
```js
let downloadedVideoPath=null, downloadedVideoURL=null;
```
Add the following block immediately after it (before the blank line that follows):
```js

// ── PERSISTENCE ────────────────────────────────────────────────────────────
function generateUUID(){
  return crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2)+Date.now().toString(36);
}
function openDB(){
  return new Promise(resolve=>{
    if(!window.indexedDB){resolve(null);return;}
    const req=indexedDB.open('autoclipper',1);
    req.onupgradeneeded=e=>{
      const store=e.target.result.createObjectStore('history',{keyPath:'id'});
      store.createIndex('byProject','projectId',{unique:false});
    };
    req.onsuccess=e=>resolve(e.target.result);
    req.onerror=()=>resolve(null);
  });
}
function dbPut(entry){
  if(!db)return;
  try{const tx=db.transaction('history','readwrite');tx.objectStore('history').put(entry);}
  catch(e){console.warn('autoclipper: dbPut failed',e);}
}
function dbGetProject(projectId){
  return new Promise((resolve,reject)=>{
    const tx=db.transaction('history','readonly');
    const idx=tx.objectStore('history').index('byProject');
    const req=idx.getAll(projectId);
    req.onsuccess=()=>resolve(req.result.sort((a,b)=>a.stepIndex-b.stepIndex));
    req.onerror=()=>reject(req.error);
  });
}
function dbTrimProject(projectId,keepMin,keepMax){
  if(!db)return;
  try{
    const tx=db.transaction('history','readwrite');
    const idx=tx.objectStore('history').index('byProject');
    const req=idx.openCursor(IDBKeyRange.only(projectId));
    req.onsuccess=e=>{
      const cursor=e.target.result;
      if(!cursor)return;
      if(cursor.value.stepIndex<keepMin||cursor.value.stepIndex>keepMax)cursor.delete();
      cursor.continue();
    };
  }catch(e){console.warn('autoclipper: dbTrimProject failed',e);}
}
function dbClearProject(projectId){
  if(!db)return;
  dbTrimProject(projectId,Infinity,-Infinity);
}
```

- [ ] **Step 3: Verify the file still parses — open `frontend/index.html` in a browser and check the console for syntax errors. There should be none.**

- [ ] **Step 4: Commit**
```bash
git add frontend/index.html
git commit -m "feat: add IndexedDB helpers and project-identity state vars"
```

---

## Task 2: Ctrl+Z / Ctrl+Y keyboard shortcuts

**Files:**
- Modify: `frontend/index.html:801` (keydown listener)

- [ ] **Step 1: Extend the keydown listener**

Find this exact block:
```js
document.addEventListener('keydown',e=>{
  if((e.key==='Delete'||e.key==='Backspace')&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName))delSel();
});
```
Replace it with:
```js
document.addEventListener('keydown',e=>{
  const inp=['INPUT','TEXTAREA'].includes(document.activeElement.tagName);
  if((e.key==='Delete'||e.key==='Backspace')&&!inp)delSel();
  if(e.ctrlKey&&e.key==='z'&&!inp){e.preventDefault();doUndo();}
  if(e.ctrlKey&&(e.key==='y'||(e.key==='Z'&&e.shiftKey))&&!inp){e.preventDefault();doRedo();}
});
```

- [ ] **Step 2: Manually verify in the browser**

Open `frontend/index.html`. Make two changes to the canvas (e.g. move an object twice). Press Ctrl+Z — the last change should undo. Press Ctrl+Y — it should redo. Pressing Ctrl+Z in a text input (`<input>`) should NOT trigger undo.

- [ ] **Step 3: Commit**
```bash
git add frontend/index.html
git commit -m "feat: add Ctrl+Z undo and Ctrl+Y/Ctrl+Shift+Z redo keyboard shortcuts"
```

---

## Task 3: Persist snapshots in `saveHist()`

**Files:**
- Modify: `frontend/index.html:675` (`saveHist` function)

- [ ] **Step 1: Extend `saveHist()` to write to IndexedDB and trim**

Find this exact function:
```js
function saveHist(){
  if(histLock)return;
  const j=JSON.stringify(cv.toJSON(['_type','_label','_blur','_fit']));
  hist=hist.slice(0,histIdx+1);hist.push(j);histIdx=hist.length-1;
}
```
Replace it with:
```js
function saveHist(){
  if(histLock)return;
  const j=JSON.stringify(cv.toJSON(['_type','_label','_blur','_fit']));
  hist=hist.slice(0,histIdx+1);hist.push(j);histIdx=hist.length-1;
  if(dbAvailable){
    dbPut({id:`${acProjectId}:${histIdx}`,projectId:acProjectId,stepIndex:histIdx,snapshot:j});
    dbTrimProject(acProjectId,Math.max(0,histIdx-49),histIdx);
  }
}
```

- [ ] **Step 2: Manually verify persistence is being written**

Open `frontend/index.html`, make a change to the canvas (move an object). Open DevTools → Application → IndexedDB → autoclipper → history. Confirm a record appears with keys like `"<uuid>:0"`, `"<uuid>:1"`, etc.

- [ ] **Step 3: Commit**
```bash
git add frontend/index.html
git commit -m "feat: persist undo snapshots to IndexedDB on every saveHist"
```

---

## Task 4: Reset history when a template is applied

**Files:**
- Modify: `frontend/index.html:1127` (`applyBuiltinTpl` function)

- [ ] **Step 1: Add history reset to the top of `applyBuiltinTpl`**

Find this exact function opening:
```js
function applyBuiltinTpl(id){
  const tpl=BUILTIN_TEMPLATES.find(t=>t.id===id);
  // Set format first (synchronous resize, no dispose)
  if(tpl?.format && tpl.format!==fmt) setFmt(tpl.format);
  stopVideoLoop(); cv.clear(); cv.backgroundColor='#0c0c18';
```
Replace it with:
```js
function applyBuiltinTpl(id){
  const tpl=BUILTIN_TEMPLATES.find(t=>t.id===id);
  // Reset history for the new project
  histLock=true;
  dbClearProject(acProjectId);
  acProjectId=generateUUID();
  localStorage.setItem('acProjectId',acProjectId);
  hist=[];histIdx=-1;
  // Set format first (synchronous resize, no dispose)
  if(tpl?.format && tpl.format!==fmt) setFmt(tpl.format);
  stopVideoLoop(); cv.clear(); cv.backgroundColor='#0c0c18';
```

Then find the closing lines of `applyBuiltinTpl`:
```js
  (map[id]||map['blur-stack'])();
  cv.renderAll();syncLayers();
  document.getElementById('proj-name-input').value=tpl?.name||id;
  switchTab('el');
}
```
Replace with:
```js
  (map[id]||map['blur-stack'])();
  histLock=false;
  cv.renderAll();syncLayers();
  document.getElementById('proj-name-input').value=tpl?.name||id;
  switchTab('el');
}
```

- [ ] **Step 2: Verify template switching creates a fresh history**

Open `frontend/index.html`. Make 3 edits (check DevTools → IndexedDB shows 3 records). Apply a template from the sidebar. Confirm: (a) Ctrl+Z does nothing (history is empty for the new template), (b) DevTools IndexedDB shows records only for the new UUID with no old entries.

- [ ] **Step 3: Commit**
```bash
git add frontend/index.html
git commit -m "feat: reset project history UUID on template apply"
```

---

## Task 5: Async boot — load history from IndexedDB and auto-restore canvas

**Files:**
- Modify: `frontend/index.html:1273` (init block at bottom of script)

- [ ] **Step 1: Replace the synchronous init block with an async IIFE**

Find this exact block at the very bottom of the `<script>` tag:
```js
// ── INIT ───────────────────────────────────────────────────────────────────
initCanvas('9:16');
addBlur();
addVideo();
addText();
```
Replace it with:
```js
// ── INIT ───────────────────────────────────────────────────────────────────
(async()=>{
  // 1. Project identity
  acProjectId=localStorage.getItem('acProjectId')||generateUUID();
  localStorage.setItem('acProjectId',acProjectId);

  // 2. Open IndexedDB
  db=await openDB();
  dbAvailable=db!==null;

  // 3. Load persisted history
  if(dbAvailable){
    try{
      const entries=await dbGetProject(acProjectId);
      hist=entries.map(e=>e.snapshot);
      histIdx=hist.length-1;
    }catch(err){
      console.warn('autoclipper: failed to load history, starting fresh',err);
      hist=[];histIdx=-1;
    }
  }

  // 4. Initialise canvas
  initCanvas('9:16');

  // 5. Restore latest state or add default elements
  if(histIdx>=0){
    histLock=true;
    cv.loadFromJSON(hist[histIdx],()=>{
      cv.renderAll();syncLayers();refreshVideoLayers();histLock=false;
    });
  }else{
    addBlur();addVideo();addText();
  }
})();
```

- [ ] **Step 2: Verify auto-restore on reload**

Open `frontend/index.html`. Make 2–3 canvas edits (add text, move objects). Close the browser tab entirely. Reopen the file. The canvas should restore to the last state automatically. Ctrl+Z should undo through the persisted history.

- [ ] **Step 3: Verify fallback when IndexedDB is unavailable**

Open `frontend/index.html` in a Private/Incognito window (IndexedDB may be restricted). The canvas should still load with the default elements (blur, video, text) and undo/redo should work in-memory for the session.

- [ ] **Step 4: Verify the 50-step cap**

Make 55 canvas edits. Open DevTools → IndexedDB → autoclipper → history. Confirm the number of records for the current project UUID stays at or below 50.

- [ ] **Step 5: Commit**
```bash
git add frontend/index.html
git commit -m "feat: async boot restores canvas from IndexedDB history on page load"
```

---

## Self-review

**Spec coverage check:**
| Spec requirement | Task |
|---|---|
| Ctrl+Z → undo | Task 2 |
| Ctrl+Y / Ctrl+Shift+Z → redo | Task 2 |
| Skip shortcuts when input focused | Task 2 |
| IndexedDB database + history store | Task 1 |
| Per-project UUID in localStorage | Task 1 + Task 5 |
| 50-step history cap via dbTrimProject | Task 3 |
| saveHist persists to DB | Task 3 |
| Template apply → new UUID, clear old entries | Task 4 |
| histLock during template clear to suppress noise | Task 4 |
| Auto-restore latest canvas state on page open | Task 5 |
| Graceful fallback if IndexedDB unavailable | Task 5 (step 3) |
| Corrupt snapshot fallback (try/catch) | Task 5 (step 1, catch block) |
| Video objects handled via refreshVideoLayers | Task 5 (step 1) |

All spec requirements covered. No placeholders. Types and function names are consistent across all tasks (`dbTrimProject`, `dbClearProject`, `dbPut`, `dbGetProject`, `acProjectId`, `dbAvailable` used uniformly).
