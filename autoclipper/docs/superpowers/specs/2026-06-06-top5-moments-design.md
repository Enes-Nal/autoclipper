# Top 5 Moments — Design Spec

**Date:** 2026-06-06  
**Status:** Approved

---

## Overview

A dedicated "Top 5 Moments" page in the autoclipper UI. The user selects 5 video clips (upload or from the existing library), assigns each a rank number and title, sets in/out trim points, picks a template, and exports a single concatenated video with the ranking overlay burned in via FFmpeg `drawtext` filters.

---

## UI — Top 5 Page

Route: `/top5` (new Flask route + `frontend/top5.html`)

### Page structure

- **Template selector** at the top — picks from Top 5 templates (JSON files in `templates/top5/`). A "New Template" button opens the existing template editor.
- **5 slot rows** (played in order, top to bottom). Each slot has:
  - **Clip picker** — drag-and-drop file upload OR select from downloaded library (modal)
  - **Rank number input** — integer, user-defined (e.g. 5, 3, 4, 1, 2 — any order)
  - **Title input** — free text
  - **Trim controls** — start time and end time in seconds, shown after a clip is loaded
- **Export button** — submits all slots to the backend
- **Progress area** — SSE stream display (same pattern as existing export jobs)

---

## Templates

Top 5 templates are JSON files stored in `templates/top5/`. They follow the same structure as existing templates (array of layers with `type`, `text`, position, font, size, color, etc.).

### Placeholder tokens

Text layers may use these tokens, which are resolved per-segment at export time:

| Token | Resolves to |
|---|---|
| `<current:rank>` | Rank number of the currently playing slot |
| `<current:title>` | Title of the currently playing slot |
| `<slot1:rank>` … `<slot5:rank>` | Rank numbers for slots 1–5 (playback order) |
| `<slot1:title>` … `<slot5:title>` | Titles for slots 1–5 (playback order) |

### Example template layer (bottom bar list row for slot 3)

```json
{
  "type": "text",
  "text": "<slot3:rank>  <slot3:title>",
  "x": 20, "y": 880,
  "font_size": 28,
  "color": "white"
}
```

### Built-in starter template

A `bottom-bar.json` template is included. It stacks all 5 rank+title rows at the bottom of the frame. The active row (matching `<current:rank>`) is styled in gold; past rows are dimmed white; future rows show a dash in place of the title (handled via placeholder resolution logic — see Exporter section).

---

## Backend / API

### New endpoint

`POST /api/top5/export`

Request body:
```json
{
  "template": "bottom-bar",
  "clips": [
    { "path": "/uploads/clip_a.mp4", "rank": 5, "title": "Clip Five Title", "start": 0.0, "end": 12.5 },
    { "path": "/uploads/clip_b.mp4", "rank": 3, "title": "Clip Three Title", "start": 2.0, "end": 18.0 },
    { "path": "/downloads/clip_c.mp4", "rank": 4, "title": "Clip Four Title", "start": 0.0, "end": 9.0 },
    { "path": "/uploads/clip_d.mp4", "rank": 1, "title": "Clip One Title", "start": 5.0, "end": 22.0 },
    { "path": "/uploads/clip_e.mp4", "rank": 2, "title": "Clip Two Title", "start": 0.0, "end": 15.0 }
  ]
}
```

- Clips are in playback order (index 0 = slot 1 = plays first).
- Handler spawns a background thread and returns `{ "job_id": "..." }` immediately.
- Progress is streamed via the existing `GET /api/jobs/<job_id>` SSE endpoint.
- Reuses existing `POST /api/upload` for file uploads; library clips are referenced by their on-disk path.

---

## Exporter — `top5_exporter.py`

New module, isolated from `exporter.py`.

### Per-segment render

For each slot `i` (0-indexed, playback order):

1. **Build placeholder map:**
   - `<current:rank>` → `clips[i].rank`
   - `<current:title>` → `clips[i].title`
   - `<slot1:rank>` … `<slot5:rank>` → rank of each slot
   - `<slot1:title>` … `<slot5:title>` → title of each slot; slots not yet played (index > i) resolve to `"—"` (dash)

2. **Load template layers** — read the selected template JSON, substitute all placeholder tokens in every text layer's `text` field.

3. **Build FFmpeg command** — trim the clip with `-ss <start> -to <end>`, add one `-vf drawtext=...` filter per text layer (reusing the existing `drawtext` filter builder from `exporter.py`).

4. **Output** to a temp file: `temp/top5_<job_id>_slot<i>.mp4`.

### Concatenation

After all 5 segment temp files are rendered, concatenate with FFmpeg `concat` demuxer into `exports/top5_<job_id>.mp4`. Temp files are deleted after successful concat.

### Progress reporting

Emit SSE progress events: `{"progress": 20}` after each segment (20% per segment), `{"progress": 100, "file": "..."}` on completion.

---

## File Layout

```
templates/
  top5/
    bottom-bar.json       ← built-in starter template
frontend/
  top5.html               ← new page
top5_exporter.py          ← new module
app.py                    ← add /top5 route + /api/top5/export endpoint
```

---

## Out of Scope

- Audio mixing / crossfades between clips
- Animated transitions between clips
- More than 5 slots
- Preview playback within the Top 5 page (export-only for now)
