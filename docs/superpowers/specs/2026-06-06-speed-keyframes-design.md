# Speed Keyframes Design

**Date:** 2026-06-06  
**Status:** Approved

## Overview

Add per-segment variable speed control to the timeline. Users place keyframes at specific timestamps within a segment; speed interpolates linearly between them. Preview uses native `playbackRate`; export approximates the curve with sub-clip concatenation in FFmpeg.

---

## Data Model

Each segment gains a `speedKeyframes` array. `tlNewSeg()` initializes it to `[]`.

```js
{
  id,
  sourceStart,   // seconds into source video
  sourceEnd,
  trackStart,    // position on timeline track
  color,         // existing color grading
  speedKeyframes: [{ t, speed }, ...]
  // t: seconds relative to sourceStart
  // speed: multiplier (0.1 – 8.0)
}
```

**Invariants:**
- `[]` means constant 1× — backwards compatible with existing exports
- A single keyframe means constant speed for the whole segment
- Two or more keyframes: speed interpolates linearly between consecutive pairs
- `t` values are clamped to `[0, sourceEnd - sourceStart]`
- `t` values are kept sorted ascending

**Helper:** `tlInterpolateSpeed(keyframes, t)` — returns interpolated speed at source-relative time `t`. Returns 1.0 if keyframes is empty.

---

## UI — Timeline Speed Lane

A speed lane row renders directly below the clip track whenever the timeline is open.

**Layout:**
- Height: ~64px
- Y axis: 0.1× (bottom) to 8× (top); 1× marked with a faint green baseline rule; 0.5× and 2× marked with dashed rules
- X axis: mirrors the clip track ruler (same pixels-per-second scale)

**Interaction:**
- Click empty lane space → add keyframe at that timestamp, speed 1×, select it
- Drag dot left/right → move timestamp (clamped to segment bounds)
- Drag dot up/down → change speed value
- Right-click dot → delete keyframe
- Segments with no keyframes render a flat line at 1×

**Curve rendering:** SVG `<polyline>` connecting all keyframe dots, with a filled gradient area beneath. Redraws on every `tlRender()` call.

---

## UI — Segment Panel (Speed Keyframes Section)

Appears above the existing Color section when a segment is selected.

**Contents:**
- Section label: "Speed Keyframes"
- "+ Add" button: inserts keyframe at current playhead position (source-relative), speed 1×
- Preset row: `0.25×` `0.5×` `1×` `2×` `4×` buttons — each replaces all keyframes with a single constant-speed keyframe
- Keyframe list rows (one per keyframe, sorted by `t`):
  - Timestamp label (MM:SS.T format)
  - Range slider (0.1–8, step 0.05)
  - Text input (shows value with `×` suffix, accepts numeric entry)
  - Delete (✕) button
- Editing slider or text input updates `speedKeyframes` and re-renders the lane curve in real time

---

## UI — Segment Badge

The clip strip shows a speed badge when any keyframe speed ≠ 1×:
- All keyframes same value → shows that value (e.g. `0.5×`)
- Mixed values → shows `~` to indicate variable speed
- Badge color: amber (`#f59e0b`) for slow (<1×), red (`#ef4444`) for fast (>1×), green for exactly 1×

---

## Preview Behavior

During `requestAnimationFrame` playback loop:

1. Determine current segment and source-relative time `srcT`
2. Call `tlInterpolateSpeed(seg.speedKeyframes, srcT)` → `rate`
3. Set `videoEl.playbackRate = rate`
4. Advance playhead on the timeline ruler at real wall-clock time
5. Speed lane shows a vertical cursor tracking the playhead across the curve

When playback stops or segment changes, reset `videoEl.playbackRate = 1`.

---

## Export — FFmpeg

For each segment with non-trivial keyframes:

1. Collect keyframe breakpoints plus `sourceStart` and `sourceEnd` as interval boundaries
2. For each interval `[a, b]`: compute average speed = `tlInterpolateSpeed(keyframes, (a+b)/2)`
3. Emit one `-ss a -to b -i video` input per interval with filter: `[i:v]setpts=PTS*(1/speed)[sv_i]` and `[i:a]asetpts=PTS*(1/speed)[sa_i]`
4. All interval sub-clips for a segment are concatenated before joining with other segments

**Intervals:** Split at each keyframe `t` boundary. Minimum interval length: 0.05s (skip shorter gaps).

**Constant-speed segments (no keyframes or all 1×):** Use the existing fast path unchanged — no extra inputs, no filter overhead.

**Audio:** Raw speed change via `asetpts=PTS*(1/speed)` — pitch shifts with speed, no `atempo` correction.

---

## Out of Scope (Phase 2)

- Smooth easing between keyframes (Bezier curves)
- Frame interpolation for very slow speeds (<0.25×)
- Audio pitch correction (`atempo`)
