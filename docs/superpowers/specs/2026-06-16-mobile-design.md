# Cutly Mobile — Design Spec
**Date:** 2026-06-16

## Overview

Add a mobile-optimized version of Cutly at `/mobile`. The mobile experience is intentionally simplified: users can download a video, choose a template, and export — no template editing. A share code system allows template configurations created on desktop to be imported on mobile.

---

## Architecture

- **New file:** `frontend/mobile.html` — self-contained mobile UI, no framework
- **New Flask route:** `GET /mobile` → serves `frontend/mobile.html`
- **Backend reuse:** All existing APIs are reused as-is (`/api/templates`, `/api/download`, `/api/export`, `/api/jobs/<id>`)
- **No new API endpoints** — template share codes are encoded/decoded entirely client-side using `btoa`/`atob`
- **Only files modified:** `app.py` (one new route), `frontend/index.html` (share button per template card)

---

## Mobile UI Flow

Single vertical page, 3 sequential steps. Each step unlocks after the previous one completes.

### Step 1 — Video
- Text input: paste a YouTube or direct video URL
- OR file picker button: choose a video from device storage
- "Download" button triggers the existing `/api/download` flow
- Progress bar driven by SSE stream (same as desktop)
- Inline error message shown for invalid URLs or failed downloads

### Step 2 — Template
- Unlocks after Step 1 completes
- Scrollable vertical card grid showing all available templates
- Each card: template name + color preview swatch (no canvas preview needed)
- "Paste Code" button at top of grid — opens a modal with a text input to paste a share code
- Imported template appears at top of the grid labeled "Imported"
- Tap a card to select it (highlighted green border)

### Step 3 — Export
- Unlocks after a template is selected
- Single large "Export" button
- Progress bar driven by SSE stream
- On completion: "Download Video" button triggers file download
- Static tip shown below: "On iPhone: open the Files app, tap the video, then Share → Save Video to save to Photos"
- Retry button shown if export fails

---

## Template Share Codes

### Desktop (sender)
- A "Share" button is added to each template card in the existing desktop sidebar
- On click: reads the template's JSON (already in memory), encodes it with `btoa(JSON.stringify(template))`, prepends a prefix `CutlyV1:`, and copies the full string to clipboard
- No server involvement — purely client-side

### Mobile (receiver)
- "Paste Code" button opens a small modal
- User pastes the code string
- Client strips the `CutlyV1:` prefix, runs `JSON.parse(atob(code))`
- On success: template is added to the top of the grid as "Imported" and auto-selected
- On failure (invalid base64 or JSON parse error): shows "Invalid code — please check and try again" inline in the modal

### Code format
```
CutlyV1:<base64-encoded JSON of template definition>
```
No server storage, no expiry, works offline after page load.

---

## Error Handling

| Scenario | Handling |
|---|---|
| Invalid video URL | Inline error under input, block Step 2 |
| Download fails | Error message + retry button in Step 1 |
| Invalid share code | Inline error inside paste modal |
| Export fails | Error message + retry button in Step 3 |
| SSE connection drops during export | Show "Still processing…" with a polling fallback |
| iOS Camera Roll limitation | Static tip always shown after export (not just on failure) |

---

## iOS Download Note

Safari on iOS cannot save files directly to the Camera Roll via a web download. The video will land in the **Files app**. The mobile UI will always display the tip:
> "On iPhone: open the Files app, tap the video, tap Share → Save Video to add it to your Photos."

Android downloads go directly to the device gallery — no extra steps needed.

---

## Files Changed

| File | Change |
|---|---|
| `frontend/mobile.html` | **New** — full mobile UI |
| `app.py` | Add `GET /mobile` route (3 lines) |
| `frontend/index.html` | Add Share button to each template card in the sidebar |

No changes to backend exporters, downloaders, or existing template logic.
