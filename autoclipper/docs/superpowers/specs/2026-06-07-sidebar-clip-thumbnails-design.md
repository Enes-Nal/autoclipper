# Sidebar Clip Thumbnails — Design Spec
**Date:** 2026-06-07

## Overview

Show all previously downloaded clips in the sidebar with a visual thumbnail and the YouTube video title, so the user can identify clips at a glance without relying on filenames or colored dots.

---

## Architecture

The feature has three layers:

1. **Thumbnail generation (backend)** — ffmpeg extracts a still frame after download
2. **API surface** — thumbnail served as a static file alongside the video
3. **Sidebar UI (frontend)** — clip cards redesigned to show thumbnail + title

---

## Backend: `downloader.py`

After `download_video()` successfully writes the `.mp4`, call ffmpeg to extract a single frame at t=1s (or t=0s if the video is shorter than 1s):

```
ffmpeg -ss 1 -i {output}.mp4 -vframes 1 -vf scale=320:-1 -q:v 5 {job_id}_thumb.jpg
```

- Output file: `downloads/{job_id}_thumb.jpg`
- Resolution: 320px wide, height auto-scaled (keeps file small)
- Quality: ffmpeg `-q:v 5` (~good enough for a sidebar thumbnail)
- If ffmpeg fails (e.g. very short clip), log and return `thumbnail: None` — the UI handles the missing case gracefully with a fallback placeholder.

`probe_video()` is unchanged. `download_video()` returns an updated dict:

```python
{"path": ..., "title": ..., "duration": ..., "thumbnail": "/api/downloads/{job_id}_thumb.jpg"}
```

---

## Backend: `app.py`

No new endpoint needed. The `downloads/` folder is already served statically. The SSE `done` message gains a `thumbnail` field:

```json
{"type": "done", "path": "...", "title": "...", "duration": 42.0, "thumbnail": "/api/downloads/abc123_thumb.jpg"}
```

---

## Frontend: Clip Object

When the `done` SSE event fires, include `thumbnail` in the clip:

```js
const clip = {
  id: 'clip_' + ...,
  path: msg.path,
  url: '/api/downloads/' + encodeURIComponent(filename),
  caption: msg.title || '',
  duration: msg.duration,
  thumbnail: msg.thumbnail || null,   // ← new
};
```

---

## Frontend: `tlRenderClipList()`

Replace the current dot-based card with a thumbnail card:

```
┌──────────────────────┐
│  [thumbnail image]   │  ← 16:9, full card width, 118×66px approx
│               [dur]  │  ← duration badge, bottom-right overlay
├──────────────────────┤
│  YouTube title here  │  ← 2-line clamp, 11px, var(--tx)
│                  [×] │  ← remove button, bottom-right
└──────────────────────┘
```

- If `clip.thumbnail` is null/missing, show a dark placeholder rectangle with a film-strip icon.
- Title uses `textContent` (safe, no XSS) from `clip.caption`.
- Duration badge: `${Math.round(clip.duration)}s`, overlaid bottom-right of the image.
- Remove button: same `tlRemoveClip(clip.id)` logic, repositioned.

---

## Frontend: CSS

New/updated classes:

| Class | Purpose |
|---|---|
| `.clip-card` | Updated: `flex-direction: column`, no gap |
| `.clip-thumb-wrap` | Relative container for image + badges |
| `.clip-thumb` | `width:100%; aspect-ratio:16/9; object-fit:cover; border-radius: var(--rs) var(--rs) 0 0` |
| `.clip-thumb-placeholder` | Dark rect shown when no thumbnail |
| `.clip-dur-badge` | Absolute, bottom-right of thumb, small pill |
| `.clip-info` | Flex row: title + remove button |
| `.clip-title` | 2-line clamp, 11px, `var(--tx)` |
| `.clip-card-rm` | Repositioned to bottom-right of `.clip-info` |

---

## Error Handling

- ffmpeg thumbnail failure: logged, `thumbnail` field omitted from response. UI shows placeholder.
- Image load failure (`onerror` on `<img>`): swap to placeholder via JS.

---

## Out of Scope

- Clicking a clip thumbnail to switch the active clip (separate feature)
- Regenerating thumbnails for clips already downloaded before this change
