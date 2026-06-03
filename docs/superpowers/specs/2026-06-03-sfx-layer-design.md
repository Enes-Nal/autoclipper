# Sound Effects Layer — Design Spec
**Date:** 2026-06-03
**Scope:** Template editor — SFX library, SFX strip UI, fine-grained placement, export mixing.

---

## Overview

Users can build a personal SFX library by uploading audio files, then place those sounds at precise timestamps in any clip. Placements appear as chips on a dedicated SFX strip below the canvas. Each placement is a first-class `sfx` layer in the template JSON, exported via FFmpeg's `adelay` + `amix` pipeline.

---

## Data Model

### SFX Library (`sfx_library.json`)

Stored in the project root. Persists across sessions.

```json
{
  "sounds": [
    { "id": "<uuid>", "name": "Whoosh", "path": "sfx/whoosh.mp3" }
  ]
}
```

Uploaded files are copied into an `sfx/` folder alongside the project. Names are editable by the user.

### SFX Layer (in template `layers` array)

```json
{
  "type": "sfx",
  "id": "<uuid>",
  "src": "sfx/whoosh.mp3",
  "start_time": 1.35,
  "volume": 1.0,
  "muted": false
}
```

- `start_time` — seconds from clip start, float, minimum 0.
- `volume` — 0.0–1.0, defaults to `1.0`.
- `muted` — boolean, defaults to `false`. Muted SFX layers are excluded from export.
- Layer-triggered SFX (sounds that fire when a visual layer appears) are plain SFX layers whose `start_time` matches a layer's start time — no special schema needed.

---

## UI

### SFX Library Panel

Located in the left sidebar, below the layers list. Collapsible section titled "Sound Effects".

- Rows: sound name, ▶ preview button, 🗑 delete button.
- "Upload SFX" button at top — opens file picker (`.mp3`, `.wav`, `.ogg`). File is copied to `sfx/`, entry added to `sfx_library.json`.
- Sound names are editable inline.

### SFX Strip

A 32px-tall horizontal track sitting between the canvas and the audio waveform strip (if present). Spans the full clip duration.

- **Click to place:** clicking anywhere on the strip places an SFX marker at that timestamp and opens a library picker popover.
- **Snap to layer boundaries:** if the click lands within 8px of a layer's start or end boundary, the marker snaps to that boundary.
- **Drag to reposition:** existing chips can be dragged left/right along the strip.

### SFX Marker Chip

Small colored pill on the SFX strip, labeled with the sound name. Clicking selects the layer and shows its properties in the right panel.

### Properties Panel (SFX layer selected)

- Sound name + "Change" button — opens library picker to swap the sound.
- **Timestamp field** — displays `1.350s`, fully editable by typing. Up/Down arrow keys nudge ±0.1s; Shift+Arrow nudges ±1s.
- Volume slider (0–100%).
- Mute toggle.
- Delete button — removes the SFX layer from the template.

---

## Export

`build_audio_cmd_parts` in `exporter.py` is extended to handle `sfx` layers alongside the existing `audio` (music) layer.

For each non-muted `sfx` layer:
1. Its file path is added as an extra `-i` input.
2. An `adelay={start_ms}|{start_ms}` filter delays the stream to `start_time`.
3. A `volume={volume}` filter is applied.
4. All SFX streams, the video audio stream, and the optional music track are combined in a single `amix=inputs=N:normalize=0`.

Example filter fragment (one SFX at 1.35s, volume 0.8):
```
[3:a]adelay=1350|1350,volume=0.8[sfx0]
[0:a][sfx0]amix=inputs=2:normalize=0[aout]
```

Multiple SFX layers are each delayed independently and all fed into the same final `amix`. `normalize=0` prevents FFmpeg from reducing overall volume as more streams are added.

---

## Out of Scope

- Built-in bundled SFX library (user uploads only).
- SFX preview playback in sync with the video preview (preview plays the sound in isolation via the browser Audio API when ▶ is clicked in the library panel or properties panel).
- Fade-in/fade-out per SFX (can be added later as `afade` filters).
