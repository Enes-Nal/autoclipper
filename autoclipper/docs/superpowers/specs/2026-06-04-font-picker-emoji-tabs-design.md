# Design: Google Font Picker + Dual-Tab Emoji Picker

**Date:** 2026-06-04  
**Status:** Approved

---

## Overview

Two independent features added to `frontend/index.html`:

1. **Google Font Picker** — text layers can use any of ~150 top Google Fonts via a searchable dropdown in the right-panel text properties section.
2. **Dual-Tab Emoji Picker** — the emoji popup gains two top-level tabs: "My Emojis" (local EmojiPack PNGs) and "Twemoji" (existing Twitter emoji set with category tabs and search).

---

## Feature 1: Google Font Picker

### Font Loading

- Replace the single `Inter` `<link>` with one Google Fonts CSS2 URL requesting ~150 fonts:
  ```
  https://fonts.googleapis.com/css2?family=Inter:wght@400..900&family=Roboto:wght@400..900&...&display=swap
  ```
- Fonts are loaded lazily by the browser — no download until used on canvas or in the preview.
- A hardcoded `GOOGLE_FONTS` array in JS lists all available font names.

### UI — Searchable Dropdown

- Added to the text properties panel (`buildTextProps`), between the font-size row and the weight toggle row.
- A custom dropdown styled to match the existing `.pin` / `.psec` design language:
  - Trigger button shows current font name, rendered in that font.
  - On click, opens a panel with a search `<input>` and a scrollable list.
  - Each list item renders the font name in its own typeface.
  - Selecting a font calls `sp('fontFamily', fontName)` and closes the dropdown.
- Dismissed by clicking outside (existing pattern).

### Serialization

- `fontFamily` is already saved/loaded in template JSON — no schema change.
- Default for new text layers stays `Inter`.
- When loading a template with a Google Font `fontFamily`, the font is already in the `<link>` so it renders correctly.

---

## Feature 2: Dual-Tab Emoji Picker

### Picker Structure

The `#emo-popup` dropdown gets two top-level tab buttons:

| Tab | Label | Content |
|-----|-------|---------|
| 0 | My Emojis | Grid of all 768 EmojiPack PNGs |
| 1 | Twemoji | Existing category tabs + search + grid (unchanged) |

The existing `.emo-cats` category row and `#emo-search` / `#emo-grid` move inside a Twemoji-tab content div. A new "My Emojis" content div shows the local pack grid.

### EmojiPack Mapping

- A static `EMOJIPACK_MAP` JS object maps codepoint string → relative file path, generated from the 768 filenames in `EmojiPack/`.
- Filename format: `<name>_<codepoint>.png` where codepoint matches Twemoji's `convert.toCodePoint()` output (hyphen-separated hex values).
- Hardcoded inline in `index.html` — no runtime directory listing or fetch needed.
- Duplicate filenames (e.g., `anxious-face-with-sweat_1f630 (1).png`) are skipped; the canonical file wins.

### My Emojis Tab Behavior

- Renders a grid of all 768 EmojiPack images as `<img>` tags with `src="../EmojiPack/<filename>"`.
- No search in this tab (768 images are visually browsable; can be added later).
- Clicking an image inserts it as a `fabric.Image` layer using the local path — same logic as current emoji image insertion but with `../EmojiPack/<file>` as src.
- The inserted layer gets `_type:'emoji'` and `_label` set to the emoji name (derived from filename prefix).

### Twemoji Tab Behavior

- Identical to current behavior: category tabs (smileys, gestures, symbols), search box, grid of Twemoji CDN images.
- No changes to `EMOJI_DATA`, `renderEmoGrid`, `filterEmoji`, `switchEmoCat`.
- `twemoji` CDN script tag stays.

### Canvas `_renderChar` Override

- **Unchanged.** Inline emoji characters typed in text boxes continue to render via Twemoji CDN.
- EmojiPack emojis always insert as standalone image layers, never as inline text characters.

### Serialization

- EmojiPack emoji layers serialize as `type:'emoji'` with `src:'../EmojiPack/<file>'` — same as current emoji image layers. No schema change.

---

## Files Changed

- `frontend/index.html` — all changes in one file:
  - `<head>`: replace font link, remove twemoji script tag (keep if still needed for `_renderChar`)
  - CSS: font dropdown styles, emoji tab styles
  - HTML: `#emo-popup` restructured with two tabs
  - JS: `GOOGLE_FONTS` array, `EMOJIPACK_MAP` object, font picker open/close/select logic, emoji tab switch logic

---

## Out of Scope

- Font preview thumbnails in the template grid
- EmojiPack search
- Skin tone variants
- Custom emoji upload UI (EmojiPack is a static folder)
