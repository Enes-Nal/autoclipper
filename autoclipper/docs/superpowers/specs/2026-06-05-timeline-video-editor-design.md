# Timeline & Video Editing Design

**Date:** 2026-06-05
**Feature:** CapCut-style collapsible timeline with split, trim, color grading, and multi-track editing

---

## Overview

Add a collapsible bottom timeline panel to the Cutly editor that lets users:
- Split video clips at the playhead position
- Trim clip in/out points by dragging handles
- Reorder/reposition clips on the track
- Delete individual segments
- Apply per-clip color grading (brightness, contrast, saturation, hue)
- See all tracks in one place: video, text, audio, SFX

This is a frontend-only feature for the editing session — the final cut/color data is passed to the exporter at export time, extending the existing FFmpeg pipeline.

---

## Layout

**Collapsible bottom panel** (Option B from design session):
- Hidden by default; toggled by a "▲ Timeline" button in the canvas toolbar or the bottom bar
- When expanded: occupies ~160px of height at the bottom of `#main`
- Canvas area shrinks to accommodate (flex layout)
- State (open/closed) stored in `localStorage`

---

## Timeline Panel Structure

### Toolbar (top of panel)
- **Split** button — cuts selected video segment at playhead
- **Color** button — toggles the color adjustment strip
- **Delete** button — removes selected segment
- Playback controls: ⏮ (go to start), ▶/⏸ (play/pause), ⏭ (go to end)
- Current time / total duration display (e.g. `0:04 / 0:30`)
- **▼ Hide** button to collapse panel

### Time Ruler
- Horizontal ruler showing timestamps (0s, 5s, 10s, …) scaled to zoom level
- Playhead needle (white vertical line + circle head) draggable to scrub

### Track Rows (4 rows)
Each row has a fixed-width label column (90px) and a scrollable clip area:

| Track | Color | Content |
|-------|-------|---------|
| VIDEO | Green (#22c55e) | Video clip segments |
| TEXT | Indigo (#818cf8) | Text layer time ranges |
| AUDIO | Amber (#f59e0b) | Audio track segments |
| SFX | Red (#f87171) | SFX clip markers |

**Clip segments:**
- Rendered as colored bars with left/right trim handles
- Selected segment gets a brighter border
- Clicking a segment selects it (highlights, enables Split/Delete/Color)
- Dragging left/right repositions the clip on the timeline
- Dragging the trim handles adjusts in/out time

### Color Adjustment Strip (below tracks, visible when Color active)
Sliders for the selected video segment:
- Brightness (-100 to +100, default 0)
- Contrast (-100 to +100, default 0)
- Saturation (-100 to +100, default 0)
- Hue (-180 to +180 degrees, default 0)

Values stored per-segment in the clip data structure.

---

## Data Model

Each video segment is an object:

```js
{
  id: "seg_abc123",
  sourceStart: 0,      // seconds into the original video
  sourceEnd: 10,       // seconds into the original video
  trackStart: 0,       // position on timeline (seconds from start)
  color: {
    brightness: 0,
    contrast: 0,
    saturation: 0,
    hue: 0
  }
}
```

The global editor state (`window.STATE`) gains:
```js
STATE.segments = [/* array of segment objects, ordered by trackStart */]
STATE.playheadTime = 0   // current playhead position in seconds
STATE.timelineOpen = false
```

On project load, a single segment covering the full video duration is created automatically.

---

## Operations

### Split
1. User clicks "Split" (or keyboard shortcut `S`)
2. The currently selected segment is split at `STATE.playheadTime`
3. Two new segments replace the original, covering `[sourceStart → playhead]` and `[playhead → sourceEnd]`
4. Color values are copied to both halves
5. Undo/redo stack records the operation

### Trim
1. User drags a trim handle on a segment
2. `sourceStart` (left handle) or `sourceEnd` (right handle) is updated
3. Adjacent segments' `trackStart` values are adjusted if needed to avoid overlap
4. Canvas preview scrubs to show the new edge frame

### Delete Segment
1. Selected segment is removed from `STATE.segments`
2. Subsequent segments shift left to fill the gap (trackStart recalculated)

### Reorder / Move
1. User drags a segment horizontally
2. `trackStart` updates in real-time; other segments shift to avoid overlap (magnetic snap)

### Color Grading
1. User selects a segment and clicks "Color"
2. Color strip appears; sliders update `segment.color.*`
3. Canvas preview applies CSS `filter:` to the preview video element for live feedback
4. At export time, FFmpeg `eq` filter is applied: `eq=brightness=X:contrast=Y:saturation=Z`
5. Hue uses `hue=h=Zdeg`

---

## Export Integration

The exporter receives the `segments` array. For each segment it:
1. Trims the source video with `-ss` / `-to` flags
2. Applies the `eq` + `hue` FFmpeg filters for color
3. Concatenates all segments in track order using FFmpeg `concat` filter

This extends `exporter.py`'s existing `build_filter_graph` function.

---

## Reversibility / Feature Flag

The timeline is implemented as a **self-contained module** (`timeline.js` or inline `<script id="timeline-module">`). A single boolean `ENABLE_TIMELINE = true` at the top of the script gates the entire feature. Setting it to `false` hides the panel and skips all timeline logic — the rest of the app is unaffected.

The HTML additions are wrapped in a `<!-- TIMELINE START --> ... <!-- TIMELINE END -->` comment block for easy identification and removal.

---

## Out of Scope

- Multi-camera / B-roll tracks
- Transitions between segments (dissolve, wipe)
- Speed ramping
- Keyframe animation
- Subtitle auto-generation
