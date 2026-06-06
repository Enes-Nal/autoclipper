# Emoji Favorites, Recent, and Improved Search

**Date:** 2026-06-05  
**Status:** Approved

## Overview

Enhance the My Emojis tab in the emoji picker with three features:
1. Favorites — user-pinned emojis floated to the top
2. Recent — last 20 used emojis shown after favorites
3. Improved search — word-aware matching across filenames

## Layout

When no search query is active, the My Emojis tab renders three sections separated by labeled dividers:

```
[ ⭐ Favorites          ]   ← section header label
[ emoji grid            ]   ← favorited emojis, star always visible
─────────────────────────
[ 🕐 Recent             ]
[ emoji grid            ]   ← last 20 used, most-recent first
─────────────────────────
[ All                   ]
[ emoji grid            ]   ← full EMOJIPACK_FILES list, A→Z
```

- Favorites and Recent emojis also appear in the All section (no deduplication).
- If a section has no entries (no favorites yet, or nothing used yet), that section and its divider are hidden.
- All section is always visible (always has entries).

## Star Interaction

Each emoji cell in the My Emojis tab has a star toggle (⭐ filled / ☆ outline):
- The star icon is positioned top-right of the cell.
- On non-favorited emojis: star is hidden by default, revealed on cell hover.
- On favorited emojis: star is always visible (filled).
- Clicking the star toggles favorite status without inserting the emoji or closing the picker.
- Clicking the emoji image (not the star) inserts the emoji and records it as recent, then closes the picker.

## Search Behavior

When a query is typed in the My Emojis search input:
- The three-section layout collapses into a single flat filtered grid.
- Matching uses word-aware logic: the query is split on whitespace, and all words must appear in the emoji label (derived from filename, underscores/hyphens→spaces).
- Results are ranked: exact prefix matches on the full label come first, then partial matches.
- If no results, show a "No emojis found" message.

Example: query "fire face" matches "face-with-fire-eyes" because both "fire" and "face" appear in the label.

## Persistence

Both lists are stored in `localStorage`:

| Key | Format | Max entries |
|-----|--------|-------------|
| `acEmoFav` | JSON array of file paths | unlimited |
| `acEmoRecent` | JSON array of file paths | 20 (oldest dropped) |

On insert (`insertEmojiPackImg`), the emoji's path is prepended to `acEmoRecent`, duplicates removed, truncated to 20, then saved.

Favorites are written on star toggle. Both are read at picker-open time (or on page load).

## Affected Code

- `renderMyEmojiGrid()` — rewrite to render three sections with dividers
- `filterMyEmoji(q)` — upgrade matching logic
- `insertEmojiPackImg(path)` — add recent tracking hook
- New helpers: `toggleEmoFav(path)`, `loadEmoState()`, `saveEmoFav()`, `saveEmoRecent()`
- CSS: star icon styles, section header/divider styles, hover states

## Out of Scope

- Twemoji tab favorites/recent (not requested)
- Drag-to-reorder favorites
- Sync across devices
