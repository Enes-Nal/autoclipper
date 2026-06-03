# Canvas Audio Mute/Unmute Toggle — Design Spec

**Date:** 2026-06-03

## Problem

The `#preview-video` element is hardcoded `muted`, so users cannot hear the downloaded video's audio while working on the canvas. There is no way to monitor audio levels or check that the right clip is loaded.

## Goal

Add a mute/unmute button that floats over the canvas, appears on hover, and lets the user hear the video's audio during preview.

## Approach

Unmute the `#preview-video` element directly — it is already playing, so we just open the audio gate. No extra elements, no sync logic.

## Design

### HTML

- Remove the `muted` attribute from `#preview-video` in markup.
- Add a `#canvas-mute-btn` button inside `#phone` (the canvas wrapper div), positioned absolute, bottom-right corner.
- Button uses the existing `icoVol` / `icoVolX` SVG icon helpers already present in the codebase.
- Button is hidden (`display:none`) when no video is loaded; shown when `downloadedVideoURL` is set.

### CSS

- `#canvas-mute-btn` is `opacity:0; pointer-events:none` by default.
- `#phone:hover #canvas-mute-btn` sets `opacity:1; pointer-events:auto` with a short transition.
- Styled consistently with `.tbar-btn` — same background, border-radius, padding.

### JavaScript

- `let _canvasMuted = true` — video starts muted on load (respects browser autoplay policy).
- On `DOMContentLoaded`: set `vidEl.muted = true` explicitly.
- `updateTplPreviews()` resets `_canvasMuted = true` and `vidEl.muted = true` whenever a new video loads, and updates the button icon.
- `toggleCanvasMute()` — flips `_canvasMuted`, sets `vidEl.muted`, swaps icon between `icoVol(15)` and `icoVolX(15)`.
- Button visibility: call a helper `syncCanvasMuteBtn()` that shows/hides `#canvas-mute-btn` based on whether `downloadedVideoURL` is truthy. Called after `updateTplPreviews` and on init.

## Non-goals

- Volume slider (mute/unmute only).
- Persisting mute state across sessions.
- Syncing mute state with the per-layer `_audioMuted` property (that controls export, not preview).

## Files Changed

- `frontend/index.html` — single file containing all HTML, CSS, and JS.
