# Cutly — Clipping-Inspired Restyle Design

Date: 2026-05-29

## Overview

Restyle the Cutly video editor UI to match the aesthetic of the "Clipping" dashboard (pure black background, green accents, card-based panels) and add itshover.com-style animated hover icons throughout the sidebar, toolbar, and right panel.

The app is a single vanilla HTML file (`frontend/index.html`) with embedded CSS and JavaScript — no build step, no React. All changes are in that one file.

## Color System

| Token | Current | New |
|-------|---------|-----|
| `--bg` | `#111113` | `#09090b` |
| `--s1` | `#161618` | `#0d0d0f` |
| `--s2` | `#1c1c1f` | `#111113` |
| `--s3` | `#222226` | `#161618` |
| `--acc` | `#e8e8ed` | `#22c55e` (green) |
| `--acc2` | `#9999a8` | `#16a34a` |
| `--accdim` | `rgba(232,232,237,.07)` | `rgba(34,197,94,.08)` |
| `--tx` | `#e8e8ed` | `#f0f0f5` |
| `--sub` | `#6e6e80` | `#52526a` |
| `--ok` | `#22c55e` | `#22c55e` (unchanged) |

Primary accent switches from white to green (`#22c55e`) everywhere: active nav items, active format pills, selected layer rows, focused inputs, primary buttons.

## Sidebar

- Logo area: icon gets a pure white rounded square bg with dark icon inside (matches Clipping logo style)
- Nav items: `border-radius: 8px`, active state = `background: rgba(34,197,94,0.09)` + green left text, inactive = transparent
- Each nav item gets an inline SVG icon with a CSS hover animation (itshover-style):
  - **Dashboard/Home** → grid icon, tiles scatter+return on hover
  - **Editor/Layers** → stack icon, layers slide up on hover  
  - **Templates** → layout icon, columns slide in on hover
  - **Export** → arrow-up-from-box, arrow rises on hover
  - **Settings** (bottom) → gear icon, rotates 360° on hover
- Sidebar bottom: user avatar card with green online dot, matches Clipping footer

## Topbar

- Background: `--s1`, border-bottom remains
- Filename input: unchanged behavior, styled with green focus ring
- Format switcher pills: `border-radius: 20px` pill shape, active pill = `background: #22c55e; color: #09090b`
- Toolbar icon buttons: each gets an animated SVG icon (itshover-style):
  - **Undo** → curved arrow sweeps counterclockwise on hover
  - **Redo** → curved arrow sweeps clockwise on hover  
  - **Zoom in/out** → magnifier glass pulses on hover
- Export button: green primary `background: #22c55e; color: #09090b`

## Left Panel (Elements / Layers)

- Panel background: `--s1`, unchanged
- Element grid buttons (`.el-btn`): get card look — `border-radius: 10px`, `border: 1px solid rgba(255,255,255,0.07)`, hover lifts with subtle green border glow
- Each element button icon gets an animated SVG replacing current emoji-style icons:
  - **Video** → play icon, play triangle pulses on hover
  - **Box** → square icon, border draws on hover
  - **Text** → T icon, cursor blinks on hover
  - **Image** → image icon, frame slides in on hover
  - **Shape** → shape icon, morphs on hover
- Layer rows: active row gets `border-left: 2px solid #22c55e` accent instead of full border

## Right Panel

- Section dividers (`.psec`) get `border-radius: 10px; border: 1px solid rgba(255,255,255,0.07); margin: 6px 8px` card look
- Section titles get small animated icon prefix:
  - **Transform** → move icon, nudges on hover
  - **Style** → palette icon, rotates on hover
  - **Text** → type icon, cursor blinks on hover
  - **Video** → film icon, frames scroll on hover
- Input fields: green focus ring (`border-color: #22c55e`)
- Sliders: `accent-color: #22c55e` (already set, ensure consistent)

## Animated Icons Implementation

Since the app is vanilla HTML (no React/framer-motion), all itshover-style animations are implemented as:

1. **Inline SVGs** replacing current SVG/text icons
2. **CSS keyframe animations** that play on `.icon-wrapper:hover svg [class]`
3. Pattern: each icon wrapper gets `class="hover-icon"`, child SVG paths get animation classes that activate on `parent:hover`

Example pattern:
```css
.hover-icon:hover .gear-path { animation: gear-spin 0.6s ease-in-out; }
@keyframes gear-spin { to { transform: rotate(360deg); transform-origin: center; } }
```

No external JS library required — pure CSS animations triggered by `:hover`.

## Canvas / Phone Area

- Dot grid: color shifts slightly darker to match new bg
- Phone frame: `border-color: rgba(255,255,255,0.10)` (slightly brighter for contrast on darker bg)
- Canvas toolbar pill: card-style with `border-radius: 12px`

## What Does NOT Change

- Layout structure (sidebar/topbar/left panel/canvas/right panel proportions)
- All JavaScript functionality (canvas editing, undo/redo, template loading, export, history)
- Font (Inter stays)
- Fabric.js integration
- Twemoji integration

## Files Changed

- `frontend/index.html` — only file that changes (all CSS variables, component styles, SVG icons)
