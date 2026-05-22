# Premiere Pro Clipboard Paste Plugin — Design Spec

**Date:** 2026-05-22  
**Project:** pasteit  
**Status:** Approved

---

## Overview

A Premiere Pro CEP (Common Extensibility Platform) extension for Windows that lets users paste images directly from the clipboard onto the active timeline at the playhead position. Triggered via a panel button or a user-configured global keyboard shortcut registered in Premiere Pro's keyboard shortcut editor.

---

## Goals

- Paste any image from clipboard (screenshots, images copied from browser, etc.) onto the active Premiere Pro timeline
- Feel native: dark panel UI matching Premiere's theme, no external windows or processes
- Windows only
- Fast: paste to timeline in under 1 second

## Non-Goals

- Mac support
- Video/GIF clipboard support
- Configurable image duration (hardcoded to 5 seconds, Premiere's default)
- Auto-upload or cloud storage

---

## Architecture

Two-layer CEP architecture communicating via Adobe's `CSInterface`:

```
┌─────────────────────────────────────┐
│  CEP Panel (HTML/JS + Node.js)      │  ← Runs in embedded Chromium
│  - Floating panel UI                │
│  - Reads clipboard image            │
│  - Writes PNG to disk               │
│  - Menu command listener            │
└────────────────┬────────────────────┘
                 │ csInterface.evalScript()
┌────────────────▼────────────────────┐
│  ExtendScript (.jsx)                │  ← Runs inside Premiere Pro
│  - Imports file to project          │
│  - Places clip on active sequence   │
│  - At current playhead position     │
│  - Sets duration to 5 seconds       │
└─────────────────────────────────────┘
```

The plugin registers a **menu command** via the CEP manifest so Premiere Pro exposes it as an assignable keyboard shortcut under `Edit → Keyboard Shortcuts`. No native code, no external processes, no Python.

---

## File Structure

```
pasteit/
├── CSXS/
│   └── manifest.xml          ← Registers plugin, panel, and menu command
├── index.html                ← Panel UI (dark theme matching Premiere)
├── js/
│   ├── main.js               ← Clipboard read, file write, evalScript bridge
│   └── CSInterface.js        ← Adobe's official bridge library
├── jsx/
│   └── host.jsx              ← ExtendScript: import file + place on timeline
└── icons/
    └── icon.png              ← Panel icon (32x32)
```

---

## Data Flow

1. User presses their assigned shortcut OR clicks "Paste Image" in the panel
2. `main.js` calls `navigator.clipboard.read()` → receives image blob
3. Blob is converted to base64 PNG and written to `{projectFolder}/PastedImages/paste-{timestamp}.png` via Node.js `fs`
4. `csInterface.evalScript("importAndPlace('...')")` calls into ExtendScript
5. `host.jsx` runs `app.project.importFiles([path])` then inserts the clip at the current playhead on the active sequence

---

## Panel UI

- Small floating panel, Premiere dark theme (`#1e1e1e` background, `#f0f0f0` text)
- One primary button: **"Paste Image"** (full width)
- Status line below button: shows last paste result (e.g. *"Pasted: paste-1234.png"*) or error message
- Status clears after 3 seconds
- No settings, no preferences — YAGNI

---

## Error Handling

| Scenario | Behavior |
|---|---|
| No image in clipboard | Status line: *"No image in clipboard"*, no crash |
| No open project or active sequence | Status line: *"Open a sequence first"*, no crash |
| `PastedImages/` folder missing | Created automatically with `fs.mkdirSync(..., { recursive: true })` on first paste |

---

## Keyboard Shortcut Setup (User-Facing)

The plugin registers a menu command in `manifest.xml`. After installing, the user:

1. Opens Premiere Pro → `Edit → Keyboard Shortcuts`
2. Searches for **"Paste Image from Clipboard"**
3. Assigns their preferred key (e.g. `Ctrl+Shift+V`)

This is a one-time setup. The shortcut then works globally within Premiere Pro regardless of panel focus.

---

## Installation

CEP extensions on Windows are installed by copying the plugin folder to:

```
C:\Program Files (x86)\Common Files\Adobe\CEP\extensions\
```

Or for per-user install (no admin required):

```
%APPDATA%\Adobe\CEP\extensions\
```

A `.zxp` package (signed ZIP) will be the distributable format, installable via Adobe Extension Manager or ZXPInstaller.

---

## Out of Scope

- Auto-placement on a specific track (uses first available video track)
- Image format options (always saves as PNG)
- Undo support beyond Premiere's built-in Ctrl+Z
- Mac support
