# Audio Features — Design Spec
**Date:** 2026-05-30
**Scope:** Template mode only. Manual timeline mode is a separate future spec.

---

## Overview

Four connected audio features added to the template editor:

1. **Video layer volume/mute** — per-layer volume slider and mute toggle in the properties panel
2. **Audio layer type** — a new `audio` layer that adds a music/sound track on top of the video
3. **Audio trimmer modal** — waveform view with drag handles to select start/end region, loop/trim toggle
4. **Preview audio strip** — waveform bar below the canvas that plays audio in sync with the video preview, with a preview-only volume/mute control

---

## Feature 1 — Video Layer Volume/Mute

### UI
When a video layer is selected, the right-side properties panel shows a new **Audio** section below Position & Size:
- A mute toggle button (🔊 / 🔇) — clicking toggles between muted and unmuted
- A volume slider (0–100%)
- Current volume percentage displayed next to the slider

### Data model
The audio settings are stored on the layer object in the template JSON:

```json
{
  "type": "video",
  "volume": 0.7,
  "muted": false
}
```

`volume` defaults to `1.0`. `muted` defaults to `false`. A muted layer exports with volume `0`.

### Export
In `exporter.py`, `build_filter_graph` applies a `volume` filter to the video's audio stream before the final mix:

```
[0:a]volume=0.7[va]
```

If `muted` is `true`, volume is set to `0`.

---

## Feature 2 — Audio Layer Type

### UI
- A **+ Add Audio** button at the bottom of the layers panel (below the layer list)
- Clicking it opens a file picker — accepted formats: `.mp3`, `.wav`, `.ogg`, `.m4a`, `.aac`
- The uploaded file is saved to a `uploads/` directory on the server and its path stored in the layer
- The audio layer appears in the layers list as a row with a 🎵 icon, the filename, and an **Edit ✂️** button
- Only one audio layer is allowed per template (the button is hidden if one already exists)

### Properties panel (audio layer selected)
- Volume slider (0–100%), defaults to `1.0`
- Loop / Trim toggle — determines behaviour when audio is longer/shorter than the video
- **Edit ✂️** button — opens the Audio Trimmer modal

### Data model

```json
{
  "type": "audio",
  "src": "uploads/abc123.mp3",
  "volume": 1.0,
  "loop": false,
  "trim_start": 0.0,
  "trim_end": null
}
```

`trim_start` and `trim_end` are seconds. `trim_end: null` means use the full file duration (or loop to video length if `loop: true`).

### Backend
New Flask route: `POST /api/upload-audio` — accepts a multipart file, saves it to `uploads/`, returns `{ "path": "uploads/abc123.mp3" }`.

---

## Feature 3 — Audio Trimmer Modal

### Trigger
Clicking **Edit ✂️** on an audio layer row or in the properties panel opens the trimmer modal.

### UI
- **Playback bar** — Play/Pause button, filename, current time / total duration
- **Waveform display** — rendered using the Web Audio API (`AudioContext.decodeAudioData` → downsample to canvas bars). Full file duration shown.
- **Selection region** — a semi-transparent purple overlay with two draggable handles (left = trim_start, right = trim_end). Dragging a handle snaps to the nearest 0.1s.
- **Start / End labels** — show the current `trim_start` and `trim_end` values in `m:ss` format below the waveform
- **Playhead** — a white vertical line that moves as the audio plays
- **Loop / Trim toggle** — two buttons: "Trim ✓" (selected by default) and "Loop". Selecting Loop sets `loop: true`; selecting Trim sets `loop: false`
- **Cancel / Apply buttons** — Apply saves `trim_start`, `trim_end`, `loop` back to the layer and closes the modal

### Behaviour
- Play/Pause controls the `<audio>` element used for preview only
- Playback starts from `trim_start` when Play is pressed
- Waveform is drawn once when the modal opens (decoded via Web Audio API, drawn to a `<canvas>`)
- Drag handles update the labels in real time

---

## Feature 4 — Preview Audio Strip

### UI
A collapsible horizontal bar below the canvas (above the bottom toolbar if one exists). It contains:
- **Play/Pause button** — controls both the video preview (`<video>`) and audio preview (`<audio>`) simultaneously
- **Mini waveform** — a read-only canvas showing the full audio layer waveform, with a playhead that tracks current playback position
- **Preview volume slider** — a small range input (0–100%)
- **Preview mute toggle** — 🔊 / 🔇 icon button
- A **"preview only"** label to make clear this doesn't affect export

### Behaviour
- The strip is only visible when an audio layer exists in the template
- Play/Pause is synced: pressing play starts both `<video>` and `<audio>` from the same relative position
- The `<audio>` element's `currentTime` is kept in sync with the existing `<video>` element (already used by `refreshVideoLayers` in the canvas) via a `timeupdate` event listener on that element
- The preview volume slider controls `audio.volume` only — it is never written to the template data model
- The waveform playhead is updated on each `requestAnimationFrame` tick during playback

### What is NOT affected
- The preview volume/mute state is purely in-memory (JS variable). It is never serialised to the template JSON or sent to the export API.
- Exporting always uses `layer.volume` and `layer.muted` from the template.

---

## Export — FFmpeg Changes (`exporter.py`)

### Audio layer processing
The `export_video` function is updated to handle the `audio` layer type:

1. The audio file is passed as an additional `-i` input to FFmpeg.
2. The selected region is extracted using `-ss trim_start -to trim_end` on the audio input (omitted if `trim_start == 0` and `trim_end == null`).
3. If `loop: true`, the audio is looped to match video duration using the `aloop` filter:
   ```
   [Xa]aloop=loop=-1:size=2147483647,atrim=duration=VID_DURATION[audio_looped]
   ```
4. The video audio stream is optionally volume-adjusted. If the video layer has `volume != 1.0` or `muted == true`:
   ```
   [0:a]volume=V[va]
   ```
   Otherwise `[0:a]` is used directly as `[va]`.
5. If the source video has no audio track (`0:a?` produces nothing), only the music track is mapped — `amix` is skipped and the audio layer is mapped directly.
6. Otherwise, mix with `amix`:
   ```
   [va][audio_looped]amix=inputs=2:duration=first:dropout_transition=0[aout]
   ```
7. The final command maps `[aout]` (or the audio-only stream from step 5) as the audio output.

### Fallback
If no audio layer exists and video layer volume is unchanged (`volume == 1.0`, `muted == false`), the existing `-map 0:a?` passthrough is used unchanged — no audio filter_complex is added.

---

## File / Component Boundaries

| File | Change |
|------|--------|
| `frontend/index.html` | Add audio section to properties panel; add audio layer row + Add Audio button to layers panel; add audio trimmer modal; add preview strip below canvas |
| `exporter.py` | Handle `audio` layer type; add `volume` filter for video layers; add `amix` mixing |
| `app.py` | Add `POST /api/upload-audio` route |

---

## Out of Scope (this spec)

- Multiple audio layers
- Crossfade between audio and video audio
- Per-clip audio for multi-clip timelines (Manual mode — separate spec)
- Video masking (separate spec)
