# Editor: Live Preview, Twemoji Picker, Linear-Style UI

**Date:** 2026-05-28  
**Status:** Approved

---

## Scope

Three coordinated changes to `frontend/index.html`:

1. Live video preview in the Fabric.js canvas
2. Twemoji-based emoji picker that adds emoji as canvas image objects
3. Linear-style UI redesign (CSS + HTML structure only; JS logic preserved)

---

## 1. Live Video Preview

### Problem
The canvas "video" layer is a Fabric.js `Group` containing a `Rect` (blue placeholder) and a `Text` label. Users see `[VIDEO]` instead of their actual footage, making it impossible to judge text placement and styling in context.

### Solution
When a video is downloaded (`downloadedVideoPath` / `downloadedVideoURL` are set):

- Create a hidden `<video id="preview-video">` element in the DOM (autoplay, muted, loop, playsinline).
- Set its `src` to `downloadedVideoURL`.
- Replace the placeholder group with a `fabric.Image` wrapping that video element, sized and positioned to match the template's video layer spec.
- Start a `requestAnimationFrame` loop that calls `cv.renderAll()` while the canvas is active, so frames update live.
- When format changes or a template is applied, re-initialize the video fabric.Image to fit the new dimensions.

### Constraints
- The `<video>` element must be in the DOM (not detached) for `fabric.Image` to read its frames via `drawImage`.
- The RAF loop should stop when the canvas is destroyed/reinitialised to avoid leaks.
- Existing canvas logic (history, snapping, export JSON) must remain unchanged — the video layer is just a `fabric.Image` with `_type: 'video'`, same as before.

---

## 2. Twemoji Emoji Picker

### Problem
The current picker renders emoji as Unicode characters, which display as Windows-style emoji on Windows. The user wants iOS-style emoji (Twemoji).

### Solution

**Picker UI:**
- Replace `<span class="ec">` elements with `<img>` tags loading from the jsDelivr Twemoji CDN:  
  `https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/72x72/{codepoint}.png`
- Codepoint = hex of the emoji's Unicode codepoint(s), joined by `-` for multi-codepoint sequences (e.g. `1f600` for 😀).
- The picker gets category tabs: Smileys, People, Nature, Objects, Symbols, Flags.
- Search filters by emoji name keyword (store a name alongside each emoji entry).
- Picker width increases to ~280px to fit a 7-column grid of 36px images.

**Inserting emoji:**
- Clicking an emoji adds a `fabric.Image` to the canvas (loaded from the Twemoji CDN URL), centered in the canvas, 80×80px, with `_type: 'emoji'`.
- This gives true iOS emoji appearance in the canvas and in the final export (the Python backend will render the Twemoji image rather than a system glyph).
- The old "insert into text cursor" flow is removed — emojis become standalone positionable elements.

**Emoji data:**
- Define a JS object `EMOJI_DATA` mapping category → array of `{char, name, cp}` objects.
- Start with ~120 high-use emoji across 5 categories; this covers 95% of content-creator use cases.
- `cp` is the codepoint string used to build the CDN URL.

---

## 3. Linear-Style UI Redesign

### Design language
- **Palette:** near-black backgrounds, invisible-almost borders, restrained single accent color.
- **Typography:** Inter, tighter tracking, stronger weight contrast between labels and values.
- **Density:** slightly more padding in panels; remove clutter (duplicate undo buttons in toolbar, redundant separators).
- **No decorative gradients** on panels, cards, or buttons. Gradient only on the logo mark.

### CSS variable changes

| Variable | Old | New |
|---|---|---|
| `--bg` | `#0d0d1a` | `#111113` |
| `--s1` | `#111120` | `#161618` |
| `--s2` | `#0e0e1c` | `#1c1c1f` |
| `--s3` | `#16162a` | `#222226` |
| `--b1` | `#1c1c32` | `rgba(255,255,255,0.07)` |
| `--b2` | `#262644` | `rgba(255,255,255,0.11)` |
| `--b3` | `#32325a` | `rgba(255,255,255,0.16)` |
| `--acc` | `#7c5cf6` | `#5865f2` |
| `--acc2` | `#e879f9` | `#818cf8` |
| `--accdim` | `rgba(124,92,246,.14)` | `rgba(88,101,242,.12)` |
| `--tx` | `#f0f0fa` | `#e8e8ed` |
| `--sub` | `#7070a0` | `#6e6e80` |
| `--mut` | `#2a2a48` | `rgba(255,255,255,0.06)` |

### Component changes

**Phone mockup:**
- Border: `1px solid rgba(255,255,255,0.12)` (hairline, no thick border-radius chrome)
- Border-radius: `20px` for 9:16, `12px` for 1:1
- Remove the `.notch` element entirely
- Remove the outer glow box-shadow; keep only a subtle drop-shadow

**Sidebar:**
- Logo area: smaller, just wordmark + icon, no heavy styling
- "Download Video" button: flat, border only, no `accdim` background fill by default
- Project card: more padding, subdued label

**Top bar:**
- Format switcher: flatter, pill shape, no border on active; just background swap
- Icon buttons: slightly larger hit target, no border
- "Save Template" primary button: flat solid accent, no glow shadow

**Left panel:**
- Tab underline stays; remove uppercase tracking from labels (just sentence case)
- Element grid buttons: remove individual icon background gradients; use a single neutral `--s2` bg with accent border on hover
- Template cards: cleaner — no `border-radius` on thumb, remove `transform: translateY(-1px)` hover lift (too bouncy); just border-color change on hover

**Right panel:**
- Section titles: smaller, lighter weight
- Sliders: thinner track, accent thumb
- Swatch grid: slightly larger swatches (24px)

**Canvas toolbar:**
- Remove the duplicate undo/redo buttons (already in topbar)
- Keep: zoom controls, Fit, Grid, Snap

**Modals:**
- Border-radius: `10px` (less rounded = more serious)
- No heavy box-shadow tinting; just `rgba(0,0,0,0.6)` overlay

---

## What is NOT changing

- All Fabric.js canvas logic (snapping, history, zoom, alignment, layers)
- The export/download flow and Flask API integration
- The template data structure and `canvasToTemplate()` serialization
- The right-panel property editing logic

---

## Files changed

- `frontend/index.html` — all changes are in this single file (CSS + HTML + JS additions for RAF loop and Twemoji picker)

---

## Open questions resolved

- **Emoji in exported video:** The Python `text_renderer.py` currently renders system glyphs. After this change, emoji are canvas `fabric.Image` objects exported as `{type: 'image', src: '<twemoji-url>'}` layers. The backend will need to fetch and composite these images. This is handled in the export JSON — no changes to `text_renderer.py` are needed for the frontend work, but a follow-up task should update the backend renderer.
