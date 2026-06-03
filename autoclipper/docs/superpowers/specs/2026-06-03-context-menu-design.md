# Context Menu Design

**Date:** 2026-06-03  
**Status:** Approved

## Overview

A custom right-click context menu for the autoclipper editor. Triggered on canvas objects and layer list rows, showing icon+label action rows relevant to the target type. Single shared DOM element, no dependencies.

## Structure & DOM

A single `<div id="ctx-menu">` appended at the bottom of `<body>`, hidden by default (`display:none`). Repositioned to cursor coordinates on each `contextmenu` event, populated dynamically, then shown. One shared `closeCtxMenu()` call dismisses it (click-outside, scroll, or Escape).

**Styling:**
- Width: ~180px
- Background: `var(--s2)`
- Border: `1px solid var(--b1)`
- Border-radius: `var(--r)`
- Drop shadow matching existing panel style
- Each row: `display:flex; align-items:center; gap:8px`, 14px icon left, 12px label
- Row hover: `var(--s3)` background
- Delete action hover: `var(--danger)` color

## Trigger Points & Target Detection

Two `contextmenu` listeners:

1. **`#canvas-area`** — uses `cv.findTarget(e)` to find the Fabric object under cursor. If found, selects it and opens menu. If nothing found, suppresses browser default and does nothing.

2. **`#layer-list` and `#audio-layer-row`** — finds closest layer row element, maps to corresponding Fabric object or audio layer, selects it and opens menu.

### Action matrix (omit non-applicable rows, no grayed-out items)

| Target type | Actions shown |
|---|---|
| Video layer | Duplicate, Bring Forward, Send Back, Mute, Lock/Unlock, Rename, Split at Playhead, Copy, Paste, Delete |
| Text / Image / Sticker | Duplicate, Bring Forward, Send Back, Lock/Unlock, Rename, Copy, Paste, Delete |
| Audio layer | Mute, Rename, Delete |

## Actions Implementation

| Action | Implementation |
|---|---|
| Duplicate | `object.clone()`, offset +10px x/y, add to canvas |
| Bring Forward | `cv.bringForward(o)` |
| Send Back | `cv.sendBackwards(o)` |
| Mute | Toggle `o._muted` (video) or `audioLayer.muted`; update layer list UI |
| Lock/Unlock | Toggle `o.lockMovementX/Y`, `o.lockScalingX/Y`, `o.hasControls` |
| Rename | Floating `<input>` inline over the layer list row label |
| Split at Playhead | Call existing trim logic at current playhead position; toast if no playhead |
| Copy | Store reference in module-level `_clipboard` variable |
| Paste | Clone `_clipboard`, offset, add to canvas |
| Delete | Call existing `delSel()` |

Menu closes immediately after any action fires.

## Error Handling

- If `cv.findTarget` returns nothing on canvas right-click: suppress `contextmenu` default, show no menu.
- If Paste is triggered with empty `_clipboard`: show no menu item (omit Paste when `_clipboard` is null).
- Split at Playhead with no playhead position: show a brief toast ("No playhead position set").
