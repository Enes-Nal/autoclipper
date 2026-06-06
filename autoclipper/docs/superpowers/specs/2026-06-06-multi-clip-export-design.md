# Multi-Clip Export — Design Spec
_Date: 2026-06-06_

## Overview

Allow the user to download multiple source videos and arrange them sequentially on the timeline, then export them as a single concatenated video. Each source video is a "clip"; existing split/trim/color-grade features apply per-segment within each clip.

---

## Data Model

### `tlClips` array (new global)

Replaces the single `downloadedVideoPath`/`downloadedVideoURL`/`downloadedVideoCaption` globals.

```js
tlClips = [
  {
    id: string,          // unique clip id, e.g. 'c1'
    path: string,        // server path, e.g. 'uploads/video1.mp4'
    url: string,         // browser-accessible URL for <video> src
    caption: string,     // title from download
    duration: number,    // source duration in seconds
  },
  ...
]
```

A hidden `<video>` element per clip is NOT created. Instead, the single `<video id="preview-video">` has its `src` swapped when the playhead crosses a clip boundary.

### `tlSegments` — extended

Each segment gains a `clipId` field:

```js
{
  id: string,
  clipId: string,      // references tlClips[i].id
  sourceStart: number,
  sourceEnd: number,
  trackStart: number,
  color: { brightness, contrast, saturation, hue }
}
```

`tlDuration` is retired. `tlTotalDuration()` already computes total from segments and remains the source of truth.

### `_tlVideoEl`

Stays pointing to `document.getElementById('preview-video')`. The element's `src` is swapped to the correct clip's `url` when needed.

---

## UI Changes

### Sidebar clip list

The single `#vid-card` becomes a scrollable `#clip-list` container. Each clip renders as a card showing filename, duration, and a trash/remove button. Removing a clip removes its segments from `tlSegments` and re-compacts the timeline.

### "Add clip" button

Added to the timeline toolbar (next to zoom controls). Only visible when `tlClips.length > 0`. Clicking it opens the existing download modal in "append" mode — on completion, the clip is appended to `tlClips` and its segments are placed after the last existing segment.

The download modal's "done" handler checks a flag (`_dlMode`) to determine whether to initialize or append.

### Clip colors

Segments are colored by clip index:
- Clip 0: green `rgba(34,197,94,0.3)` (existing)
- Clip 1: blue `rgba(99,102,241,0.3)`
- Clip 2: amber `rgba(245,158,11,0.3)`
- Clip 3+: cycle through these three

---

## Playback

### Src-swap approach

When `tlSeek` or the playback RAF loop determines the active segment has changed clips, it:
1. Pauses the preview video.
2. Sets `preview-video.src` to the new clip's `url`.
3. Seeks to the correct `sourceStart + offset`.
4. Resumes playback if in play mode.

A `_tlActiveClipId` variable tracks which clip is currently loaded in the preview element to avoid redundant src swaps.

### `tlTimelineToVideoTime` — unchanged

Returns `{clipId, videoTime}` instead of just `videoTime` (small signature change to carry clip identity).

---

## Export

### Frontend payload change

```json
{
  "clips": [
    { "video_path": "uploads/a.mp4", "segments": [ ... ] },
    { "video_path": "uploads/b.mp4", "segments": [ ... ] }
  ],
  "template": { ... },
  "title": "...",
  "emoji_source": "..."
}
```

Segments within each clip entry have the same shape as today minus `clipId` (backend doesn't need it).

The existing `"video_path"` + `"segments"` fields at the top level are removed. The export button guard changes from `if (!downloadedVideoPath)` to `if (!tlClips.length)`.

### Backend `exporter.py`

`export_video` currently accepts `video_path` + `segments`. It gains a `clips` parameter (list of `{video_path, segments}`). When `clips` is provided, `build_segment_inputs` is called once per clip and results are merged. The existing concat filter at the end joins all clip outputs.

Backward compatibility: if `clips` is absent but `video_path` is present, wrap it as `[{video_path, segments}]` internally.

---

## Error handling

- Removing the only clip clears the timeline and resets to empty state.
- If a clip's video file is missing at export time, the backend returns an error for that specific clip (existing error handling covers this).
- Segment trim handles on a clip boundary cannot cross into another clip's source (existing `tlDuration` guard replaced with per-clip duration guard).

---

## Out of scope

- Reordering clips by drag-and-drop (clips are appended in download order).
- Cross-clip segment dragging.
- Uploading local files (existing upload flow is separate and unchanged).
