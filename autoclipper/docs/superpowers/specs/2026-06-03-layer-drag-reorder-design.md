# Layer Drag-and-Drop Reordering

**Date:** 2026-06-03  
**Status:** Approved

## Overview

Add drag-and-drop reordering to the layers sidebar so users can change the stacking order of canvas layers by dragging rows up or down.

## Scope

- Canvas layers only (video, text, image, shape objects rendered by Fabric.js)
- Audio layer row stays fixed at the bottom — it is not a canvas object and is not reorderable
- No new libraries; pure HTML5 drag-and-drop API

## Behaviour

1. Each `.lrow` in `#layer-list` gets `draggable="true"`
2. On `dragstart`: record the index of the dragged object in the reversed display list; set row opacity to 0.4
3. On `dragover` (over any row): prevent default to allow drop; show a green insertion line above or below the hovered row depending on cursor Y position
4. On `drop`: compute the target canvas index from display position, call `cv.moveTo(obj, targetIndex)`, then `syncLayers()` + `saveHist()`
5. On `dragend`: remove the insertion indicator and restore opacity regardless of drop outcome

## Visual Feedback

- Dragged row: `opacity: 0.4`, cursor `grabbing`
- Insertion indicator: a 2px green (`var(--acc)`) horizontal line injected between rows
- No animation on drop — the list re-renders immediately via `syncLayers()`

## Index Mapping

The layer list displays objects in **reverse** canvas order (index 0 = bottom of stack = last row). When the user drops row at display position `d` (0 = top of list), the target canvas index is:

```
canvasIndex = (totalObjects - 1) - d
```

`cv.moveTo(obj, canvasIndex)` repositions the object in Fabric's internal array.

## Files Changed

- `frontend/index.html` — CSS for insertion indicator + drag event wiring in `syncLayers()`

## Out of Scope

- Drag to reorder audio layer
- Multi-select drag
- Drag between panels
