---
title: Persistent Undo/Redo (Ctrl+Z / Ctrl+Y)
date: 2026-05-28
status: approved
---

# Persistent Undo/Redo

## Overview

Add Ctrl+Z (undo) and Ctrl+Y / Ctrl+Shift+Z (redo) keyboard shortcuts to the autoclipper canvas editor, backed by IndexedDB so the full undo history (up to 50 steps) survives page reloads and browser close.

## Current State

- `hist[]` array holds Fabric.js JSON snapshots in memory; wiped on reload
- `histIdx` tracks current position in the stack
- `histLock` prevents recursive saves during `loadFromJSON`
- `saveHist()` is called on `object:modified`, `object:added`, `object:removed`, template apply, and zoom
- `doUndo()` / `doRedo()` navigate the array and call `cv.loadFromJSON()`
- The `keydown` listener only handles Delete/Backspace; no Ctrl+Z/Y exists yet

## Data Model

**IndexedDB database:** `autoclipper`  
**Object store:** `history` (keyPath: `id`)

Each record:
```js
{ id: "abc123:7", projectId: "abc123", stepIndex: 7, snapshot: "<fabric json string>" }
```

**Project identity:** A UUID stored in `localStorage` as `acProjectId`. Generated once on first load, persisted across reloads. Applying a new template generates a fresh UUID, deletes all old project records from IndexedDB, and resets `hist=[], histIdx=-1`.

**History cap:** 50 entries per project. On every `saveHist()`, any record with `stepIndex < histIdx - 49` is deleted from IndexedDB.

## Architecture

### New: IndexedDB module (inline in index.html)

```
openDB() → Promise<IDBDatabase | null>
  - Opens/creates "autoclipper" DB with "history" store
  - Returns null if unavailable (private mode, browser flags)

dbPut(entry) → void (fire-and-forget)
dbDelete(id) → void (fire-and-forget)
dbGetProject(projectId) → Promise<entry[]> sorted by stepIndex
dbClearProject(projectId) → void (fire-and-forget)
```

A module-level `let db = null` holds the open connection. `openDB()` is called once at startup; subsequent calls use the cached handle.

### Modified: State variables

```js
let acProjectId = '';       // UUID, loaded from localStorage on boot
let dbAvailable = false;    // set true after openDB() succeeds
```

### Modified: `saveHist()`

1. Existing: push snapshot to `hist[]`, trim future entries
2. New: if `dbAvailable`, call `dbPut({ id, projectId, stepIndex, snapshot })`
3. New: if `dbAvailable`, delete entries where `stepIndex < histIdx - 49` for this project

### Modified: `doUndo()` / `doRedo()`

No changes — they operate on the in-memory `hist[]` which is fully populated at boot.

### Modified: `keydown` listener

```js
if (e.ctrlKey && e.key === 'z' && !inputFocused) { e.preventDefault(); doUndo(); }
if (e.ctrlKey && (e.key === 'y' || (e.key === 'Z' && e.shiftKey)) && !inputFocused) { e.preventDefault(); doRedo(); }
```

`inputFocused` = `['INPUT','TEXTAREA'].includes(document.activeElement.tagName)`

### New: Boot sequence (runs before canvas init)

```
1. acProjectId = localStorage.getItem('acProjectId') || generateUUID()
   localStorage.setItem('acProjectId', acProjectId)
2. db = await openDB()
3. dbAvailable = db !== null
4. if dbAvailable:
     entries = await dbGetProject(acProjectId)  // sorted by stepIndex
     hist = entries.map(e => e.snapshot)
     histIdx = hist.length - 1
5. initCanvas()   // existing Fabric.js setup
6. if histIdx >= 0:
     histLock = true
     cv.loadFromJSON(hist[histIdx], () => {
       cv.renderAll(); syncLayers(); refreshVideoLayers(); histLock = false;
     })
```

### Modified: Template apply

Before loading the new template JSON into the canvas:
1. `dbClearProject(acProjectId)` — delete old history
2. `acProjectId = generateUUID()`
3. `localStorage.setItem('acProjectId', acProjectId)`
4. `hist = []; histIdx = -1`

## Error Handling

| Scenario | Behavior |
|---|---|
| IndexedDB unavailable (private mode) | `openDB()` returns null; `dbAvailable=false`; in-memory only |
| Quota exceeded on write | Per-write try/catch; log to console; skip silently |
| Corrupt snapshot on restore | try/catch around `loadFromJSON`; clear `hist[]`; start blank |
| `histLock` during restore | Boot sequence sets `histLock=true` during restore, preventing recursive saves |
| Video objects | `refreshVideoLayers()` already called after every `loadFromJSON`; no change needed |

## Out of Scope

- Undo across multiple named projects (no project list UI yet)
- Compressing snapshots (acceptable at 50-step cap)
- Syncing history across tabs
