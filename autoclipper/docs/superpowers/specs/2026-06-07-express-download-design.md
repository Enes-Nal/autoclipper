# Express Download Page — Design Spec
**Date:** 2026-06-07  
**Status:** Approved

---

## Overview

A streamlined "express" workflow on the download page that lets the user go from a video URL directly to a finished exported clip — no editor required. The user provides a URL, picks a template, types a title, optionally sets a start time and duration, and clicks one button to get the final video.

---

## Form Layout

Single vertical form on the download page:

```
[ Video URL                              ]
[ Template       ▼ ] (thumbnail preview on hover)
[ Title text                             ]
[ Start time  00:00 ]  [ Duration  0:30  ]
           [ Download & Export ]
```

- **Video URL** — any yt-dlp-supported URL (YouTube, TikTok, Twitter/X, Instagram, etc.)
- **Template** — `<select>` populated from the existing `/api/templates` endpoint
- **Title** — injected into the template's title text layer (see Title Injection below)
- **Start time** — optional, defaults to `00:00`. Accepts `mm:ss` or `hh:mm:ss`
- **Duration** — optional, defaults to full video. Accepts seconds or `mm:ss`
- If the selected template has no text layers, the Title field is hidden with a note: "This template has no text layer."

---

## Backend Flow

Single endpoint handles the full pipeline:

```
POST /api/express-export
  { url, template_name, title, start_time, duration }

  → yt-dlp downloads video to downloads/
  → FFmpeg trims to [start_time, start_time + duration]
  → Template layers composited (blur, mask, overlays)
  → Title injected into the designated text layer
  → Output written to exports/
  → SSE progress stream kept open throughout
```

The existing SSE progress system (`/api/export-progress`) streams live status updates to the browser. On completion, the browser auto-triggers a file download of the finished video.

---

## Title Injection

The user's title string is substituted into the correct template text layer before FFmpeg rendering:

- Templates with a designated title layer carry `"role": "title"` on that layer in the JSON.
- If no `role: "title"` layer exists, the first text layer in the template is used as fallback.
- Only the `text` property of that layer is replaced — all other layer properties (font, size, color, position, animation) remain unchanged.
- Existing built-in templates (`blur-stack`, `text-header`, `footer-fade`, `minimal`, `side-blur`, `podcast`) should have `"role": "title"` added to their primary text layer.

---

## Progress & Completion UI

While export runs, live status appears inline below the button:

```
[ Download & Export ]  ← disabled during export
─────────────────────────────────────────────
⬇ Downloading...  62%
⚙ Compositing...
✓ Done — your clip is ready
  [ Download file ]  [ Edit in editor ]
```

- Form is fully disabled while export runs (prevents duplicate submissions).
- On completion: **Download file** triggers a browser file download; **Edit in editor** loads the exported clip into the main editor (`/`).
- On error: form re-enables, error message shown inline below the button.

---

## API Contract

### `POST /api/express-export`

**Request body:**
```json
{
  "url": "https://...",
  "template_name": "blur-stack",
  "title": "My clip title",
  "start_time": "00:30",
  "duration": "00:45"
}
```

- `start_time` and `duration` are optional strings. If omitted, full video is used.
- `title` is optional. If omitted and the template has a title layer, the layer's default text is preserved.

**Response:** SSE stream (reuses existing progress event format), final event carries `{ "status": "done", "output_path": "exports/filename.mp4" }`.

---

## Changes to Existing Files

| File | Change |
|---|---|
| `frontend/index.html` | Add express form UI to the download section |
| `app.py` | Add `POST /api/express-export` route |
| `exporter.py` | Add `inject_title(template, title)` helper; accept `start_time`/`duration` params |
| `templates/builtin/*.json` | Add `"role": "title"` to primary text layer in each built-in template |

---

## Out of Scope

- Auto-highlight detection (separate feature)
- Batch/queue of multiple URLs
- Per-layer title assignment (always uses the single designated title layer)
