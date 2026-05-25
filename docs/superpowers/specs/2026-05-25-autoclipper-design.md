# autoclipper — Design Spec
**Date:** 2026-05-25  
**Status:** Approved

---

## Overview

autoclipper is a local web app that downloads videos from any URL (Twitter/X, YouTube, TikTok, Instagram, etc.) via yt-dlp, lets users visually design reusable clip templates in a canvas-based editor, then exports the video in TikTok-ready format (9:16 or 1:1) using FFmpeg.

**Key principles:**
- Zero build toolchain — single HTML file for the frontend, Python for the backend
- Templates are portable JSON files that fully describe a layout
- The editor is a live WYSIWYG preview; what you see is what FFmpeg renders

---

## Architecture

```
┌──────────────────────────────────────────┐
│  Browser (single HTML page)              │
│  ┌────────────┐  ┌──────────────────┐   │
│  │ Template   │  │ Fabric.js Canvas  │   │
│  │ Editor UI  │  │ (270×480 preview) │   │
│  └────────────┘  └──────────────────┘   │
└────────────────────┬─────────────────────┘
                     │ HTTP / SSE
┌────────────────────▼─────────────────────┐
│  Flask backend (app.py)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Downloader│ │ Exporter │ │Templates │ │
│  │ (yt-dlp) │ │ (FFmpeg) │ │  (JSON)  │ │
│  └──────────┘ └──────────┘ └──────────┘ │
└──────────────────────────────────────────┘
         │              │
     downloads/      exports/
```

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python 3.11 + Flask | Simple, no async needed, yt-dlp is Python-native |
| Video download | yt-dlp | Supports 1000+ sites |
| Video processing | FFmpeg (subprocess) | Industry standard, handles all compositing |
| Image/emoji compositing | Pillow | Pre-renders emoji/images to PNG for FFmpeg overlay |
| Frontend canvas | Fabric.js 5.x | Built-in drag, resize, rotate, IText editing |
| Frontend fonts | Inter (Google Fonts) | Clean, high-legibility at all weights |
| Emoji rendering | Apple Color Emoji (browser) + Noto Color Emoji (export) | System emoji in editor; Noto for cross-platform FFmpeg export |
| Progress streaming | Server-Sent Events (SSE) | Simple one-way push, no WebSocket overhead |
| Template storage | JSON files in `templates/` | Portable, human-readable, git-friendly |

---

## Canvas Coordinate System

The editor canvas is a **scaled preview** of the actual output:

| Format | Output resolution | Editor preview | Scale factor |
|---|---|---|---|
| 9:16 | 1080 × 1920 px | 270 × 480 px | 0.25× (÷4) |
| 1:1 | 1080 × 1080 px | 360 × 360 px | 0.333× (÷3) |

When the user saves a template, all coordinates are **multiplied by the inverse scale factor** before writing to JSON, so the JSON always stores full-resolution (1080p) coordinates. When the editor loads a template, it divides back down for display.

---

## Template JSON Format

```json
{
  "name": "Blur Stack",
  "format": "9:16",
  "canvas": { "width": 1080, "height": 1920 },
  "layers": [
    {
      "id": "blur-bg",
      "type": "blur_video",
      "blur": 20,
      "opacity": 0.92
    },
    {
      "id": "main-video",
      "type": "video",
      "x": 0,
      "y": 656,
      "width": 1080,
      "height": 608,
      "fit": "contain",
      "border_radius": 0,
      "opacity": 1.0
    },
    {
      "id": "title",
      "type": "text",
      "x": 40,
      "y": 80,
      "width": 1000,
      "text": "{title}",
      "font_family": "Inter",
      "font_weight": "900",
      "font_size": 72,
      "fill": "#ffffff",
      "stroke": "#000000",
      "stroke_width": 6,
      "text_align": "center",
      "paint_first": "stroke"
    },
    {
      "id": "watermark",
      "type": "image",
      "x": 860,
      "y": 1820,
      "width": 180,
      "src": "assets/watermark.png",
      "opacity": 0.8
    }
  ]
}
```

### Layer types

| Type | Description |
|---|---|
| `blur_video` | Duplicates the source video, scales to fill canvas, applies Gaussian blur. Always goes to the bottom of the stack. |
| `video` | The main video content. Positioned and sized per template. `fit` controls aspect ratio handling: `contain` (letterbox), `cover` (crop to fill), `fill` (stretch). |
| `text` | Static or variable text. `{title}` is a variable the user fills in at export time via a simple input field — useful for clip-specific titles without editing the template. Supports inline emoji (rendered via Noto Color Emoji at export). |
| `image` | Static image overlay (watermark, logo, sticker). Path relative to project root. |
| `shape` | Solid color rectangle. Used for title bars, overlays, vignette blocks. |

---

## FFmpeg Export Pipeline

Each template layer maps to an FFmpeg filter chain. The backend builds a single `-filter_complex` string.

### Blur background layer
```
[0:v] scale=1920:1080, boxblur=lx=20:ly=20,
      scale=1080:1920:force_original_aspect_ratio=increase,
      crop=1080:1920, setsar=1 [blur_bg]
```

### Main video layer (contain)
```
[0:v] scale=1080:608:force_original_aspect_ratio=decrease,
      pad=1080:608:(ow-iw)/2:(oh-ih)/2:color=black [scaled_vid]
[blur_bg][scaled_vid] overlay=x=0:y=656 [base]
```

### Text layer
Text containing only ASCII/Latin characters is rendered directly via FFmpeg's `drawtext` filter:
```
[base] drawtext=fontfile=/fonts/Inter-Black.ttf:
       text='Your title here':x=40:y=80:fontsize=72:
       fontcolor=white:bordercolor=black:borderw=6 [with_text]
```

Text containing emoji is pre-composited: Pillow renders the full text string (with emoji via Noto Color Emoji) to a transparent PNG at the correct resolution, then FFmpeg overlays it:
```python
# server-side
img = render_text_to_png(layer, canvas_width, canvas_height)
img.save(tmp_path)
```
```
[with_prev][text_img] overlay=x=0:y=0 [with_text]
```

### Image layer
```
[with_text][1:v] overlay=x=860:y=1820:alpha=1 [with_logo]
```

### Audio
```
[0:a] aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo [audio]
```

### Final output
```
ffmpeg -i input.mp4 [-i watermark.png] ...
  -filter_complex "..."
  -map "[final]" -map "[audio]"
  -c:v libx264 -preset fast -crf 23
  -c:a aac -b:a 128k
  -movflags +faststart
  output.mp4
```

---

## Download Flow

1. User pastes URL → `POST /api/download { url }`
2. Backend calls `yt-dlp --format "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" --merge-output-format mp4 --output downloads/{id}.mp4 {url}`
3. Progress streamed via SSE: `GET /api/download/{id}/progress`
4. On completion, returns `{ path, thumbnail, duration, width, height }`
5. Frontend updates video info bar and marks template as ready to export

---

## Export Flow

1. User clicks "Export with Template"
2. Frontend sends `POST /api/export { video_path, template, title, output_format }`
3. Backend:
   a. Scales template coordinates from editor preview → full resolution
   b. Pre-renders any text layers containing emoji to PNG via Pillow
   c. Builds FFmpeg `-filter_complex` string from layers (bottom to top)
   d. Runs FFmpeg subprocess, streams progress via SSE
4. On completion, returns `{ output_path }` → browser triggers download

---

## Frontend Structure

Single file: `frontend/index.html`

### Panels
- **Top bar** — logo, format toggle (9:16 / 1:1), template name input, Download/Preview/Save/Export buttons
- **URL bar** — URL input, Download button, SSE progress bar
- **Left panel** — tabbed: *Add* (element buttons + layer stack) | *Templates* (built-in + saved template library)
- **Canvas area** — Fabric.js canvas in phone frame, snap guides, grid overlay, zoom/undo toolbar
- **Right panel** — dynamic properties for selected layer: transform, alignment, type-specific controls, iOS emoji picker for text layers

### Canvas interaction
- **Drag** — move any element
- **Corner handles** — resize
- **Double-click text** — enters IText inline editing mode; emoji inserted at cursor via emoji picker
- **Snap** — elements snap to canvas edges, canvas center lines, and other elements' edges/centers; snap guides drawn as dashed lines; phone border glows pink when snapping to its edges
- **Align toolbar** — 6 buttons: align left/center-H/right/top/center-V/bottom, all relative to the canvas

### Template save/load
- **Save** — `GET /api/templates` to list, `POST /api/templates` to save; stored as `templates/{name}.json`
- **Load** — `GET /api/templates/{name}` returns JSON; editor parses and populates Fabric canvas
- Built-in templates are bundled in `templates/builtin/`

---

## File Layout

```
autoclipper/
├── app.py                  # Flask app, all API routes
├── exporter.py             # FFmpeg filter graph builder
├── downloader.py           # yt-dlp wrapper
├── text_renderer.py        # Pillow emoji/text → PNG
├── frontend/
│   └── index.html          # Single-page editor (Fabric.js)
├── templates/
│   ├── builtin/
│   │   ├── blur-stack.json
│   │   ├── text-header.json
│   │   ├── footer-fade.json
│   │   ├── minimal.json
│   │   ├── side-blur.json
│   │   └── podcast.json
│   └── (user templates saved here)
├── assets/
│   └── (watermark images, fonts)
├── fonts/
│   ├── Inter-Black.ttf
│   ├── Inter-Bold.ttf
│   └── NotoColorEmoji.ttf
├── downloads/              # yt-dlp output (gitignored)
├── exports/                # FFmpeg output (gitignored)
└── requirements.txt        # flask, yt-dlp, pillow
```

---

## API Routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves `frontend/index.html` |
| `POST` | `/api/download` | Start yt-dlp download, returns `{ id }` |
| `GET` | `/api/download/<id>/progress` | SSE stream of download progress |
| `GET` | `/api/templates` | List all templates (builtin + user) |
| `GET` | `/api/templates/<name>` | Get template JSON |
| `POST` | `/api/templates` | Save template JSON |
| `POST` | `/api/export` | Start export, returns `{ id }` |
| `GET` | `/api/export/<id>/progress` | SSE stream of export progress |
| `GET` | `/api/exports/<filename>` | Download exported file |

---

## iOS Emoji Strategy

The user specifically wants iOS emoji appearance.

**In the editor (browser):** Text elements use `font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", Inter, sans-serif`. On macOS/iOS the Apple emoji font is used automatically. On Windows, Segoe UI Emoji is used (similar appearance).

**In the export (FFmpeg):** FFmpeg's `drawtext` filter does not support color emoji. Instead, `text_renderer.py` uses Pillow with the **Noto Color Emoji** font (bundled in `fonts/`) to render the full text block (including emoji) to a transparent RGBA PNG at the full output resolution. FFmpeg then overlays this PNG.

**Fallback:** If a text layer contains no emoji characters (detected via Unicode ranges), it uses FFmpeg `drawtext` directly for better performance.

---

## Error Handling

- Invalid URL → yt-dlp returns non-zero exit code → `{ error: "Could not download: ..." }` shown in UI
- Unsupported site → same
- FFmpeg failure → stderr captured, shown in export log panel
- Missing font → fallback to system font, warning logged
- All temp files cleaned up on export completion or failure

---

## Dependencies

```
# requirements.txt
flask>=3.0
flask-cors>=4.0
yt-dlp>=2024.1
pillow>=10.0
```

System dependencies (documented in README):
- FFmpeg ≥ 6.0 (must be in PATH)
- Python 3.11+
