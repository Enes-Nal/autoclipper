# PasteIt — Premiere Pro Clipboard Paste Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Premiere Pro CEP extension (Windows) that pastes clipboard images directly onto the active timeline at the playhead position, triggered by a panel button or Ctrl+V when the panel is focused.

**Architecture:** Two-layer CEP extension — an HTML/JS panel (embedded Chromium + Node.js) reads the clipboard via a hidden PowerShell subprocess and writes the PNG to disk, then calls ExtendScript via `csInterface.evalScript()` to import the file into Premiere and insert it at the playhead on the active sequence.

**Tech Stack:** CEP 11 (HTML/CSS/JS + Node.js 14), ExtendScript (`.jsx`), PowerShell (built-in Windows, used for clipboard image capture), Adobe CSInterface.js bridge library.

> **Note on global keyboard shortcut:** CEP panels cannot register commands in Premiere's keyboard shortcut editor without the C++ SDK. The shortcut is implemented as Ctrl+V captured when the panel is focused — fast and reliable without extra setup.

---

## File Map

| File | Responsibility |
|---|---|
| `CSXS/manifest.xml` | CEP extension registration, panel geometry, host app targeting |
| `index.html` | Panel UI — dark Premiere theme, paste button, status line |
| `js/CSInterface.js` | Adobe's official CEP↔Premiere bridge (downloaded) |
| `js/main.js` | Clipboard read (PowerShell), file write, evalScript call, UI logic |
| `jsx/host.jsx` | ExtendScript: import PNG into project, insert on sequence at playhead |
| `icons/icon.png` | 32×32 panel icon |
| `install.ps1` | Dev install: enables CEP debug registry key, symlinks extension folder |

---

### Task 1: Project scaffold & CEP manifest

**Files:**
- Create: `CSXS/manifest.xml`
- Create: `icons/icon.png`

- [ ] **Step 1: Create directory structure**

```powershell
New-Item -ItemType Directory -Force -Path "D:\Code\pasteit\CSXS"
New-Item -ItemType Directory -Force -Path "D:\Code\pasteit\js"
New-Item -ItemType Directory -Force -Path "D:\Code\pasteit\jsx"
New-Item -ItemType Directory -Force -Path "D:\Code\pasteit\icons"
```

- [ ] **Step 2: Create `CSXS/manifest.xml`**

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<ExtensionManifest Version="7.0"
  ExtensionBundleId="com.pasteit.premiere"
  ExtensionBundleVersion="1.0.0"
  ExtensionBundleName="PasteIt">

  <ExtensionList>
    <Extension Id="com.pasteit.premiere" Version="1.0.0"/>
  </ExtensionList>

  <ExecutionEnvironment>
    <HostList>
      <Host Name="PPRO" Version="22"/>
    </HostList>
    <LocaleList>
      <Locale Code="All"/>
    </LocaleList>
    <RequiredRuntimeList>
      <RequiredRuntime Name="CSXS" Version="11.0"/>
    </RequiredRuntimeList>
  </ExecutionEnvironment>

  <DispatchInfoList>
    <Extension Id="com.pasteit.premiere">
      <DispatchInfo>
        <Resources>
          <MainPath>./index.html</MainPath>
          <ScriptPath>./jsx/host.jsx</ScriptPath>
          <CEFCommandLine>
            <Parameter>--allow-file-access-from-files</Parameter>
            <Parameter>--enable-nodejs</Parameter>
          </CEFCommandLine>
        </Resources>
        <Lifecycle>
          <AutoVisible>true</AutoVisible>
        </Lifecycle>
        <UI>
          <Type>Panel</Type>
          <Menu>PasteIt</Menu>
          <Geometry>
            <Size>
              <Height>130</Height>
              <Width>300</Width>
            </Size>
            <MinSize>
              <Height>100</Height>
              <Width>200</Width>
            </MinSize>
          </Geometry>
          <Icons>
            <Icon Type="Normal">./icons/icon.png</Icon>
          </Icons>
        </UI>
      </DispatchInfo>
    </Extension>
  </DispatchInfoList>
</ExtensionManifest>
```

- [ ] **Step 3: Generate the panel icon**

Run this PowerShell to create a 32×32 PNG icon:

```powershell
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap(32, 32)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$bg = [System.Drawing.Color]::FromArgb(255, 50, 50, 50)
$g.Clear($bg)
$pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 200, 200, 200), 2)
$g.DrawRectangle($pen, 6, 4, 20, 24)
$g.DrawRectangle($pen, 11, 2, 10, 5)
$g.DrawLine($pen, 10, 14, 22, 14)
$g.DrawLine($pen, 10, 18, 22, 18)
$g.DrawLine($pen, 10, 22, 18, 22)
$pen.Dispose(); $g.Dispose()
$bmp.Save("D:\Code\pasteit\icons\icon.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "Icon created."
```

Expected output: `Icon created.`

- [ ] **Step 4: Commit**

```bash
git add CSXS/manifest.xml icons/icon.png
git commit -m "feat: add CEP manifest and panel icon"
```

---

### Task 2: ExtendScript host

**Files:**
- Create: `jsx/host.jsx`

Runs inside Premiere Pro's engine. Given a file path, imports the PNG into the project and inserts it on the first video track at the playhead, with a 5-second duration.

- [ ] **Step 1: Create `jsx/host.jsx`**

```javascript
// jsx/host.jsx

function importAndPlace(filePath) {
  if (!app.project) return "ERROR:no_project";

  var seq = app.project.activeSequence;
  if (!seq) return "ERROR:no_sequence";

  if (seq.videoTracks.numTracks === 0) return "ERROR:no_video_track";

  // Record count before import to locate new item by position fallback
  var countBefore = app.project.rootItem.children.numItems;

  // importFiles(paths, suppressUI, targetBin, importAsNumberedStills)
  var ok = app.project.importFiles([filePath], true, app.project.rootItem, false);
  if (!ok) return "ERROR:import_failed";

  // Locate the imported item by path, fall back to last item if count grew
  var projectItems = app.project.rootItem.children;
  var importedItem = null;

  for (var i = 0; i < projectItems.numItems; i++) {
    try {
      if (projectItems[i].getMediaPath() === filePath) {
        importedItem = projectItems[i];
        break;
      }
    } catch (e) {}
  }

  if (!importedItem && projectItems.numItems > countBefore) {
    importedItem = projectItems[projectItems.numItems - 1];
  }

  if (!importedItem) return "ERROR:item_not_found";

  var playheadTime = seq.getPlayerPosition();
  var insertedClip = seq.videoTracks[0].insertClip(importedItem, playheadTime);

  // Set duration to 5 seconds from the clip's actual start position
  if (insertedClip) {
    var endTime = new Time();
    endTime.seconds = insertedClip.start.seconds + 5.0;
    insertedClip.end = endTime;
  }

  return "OK";
}
```

- [ ] **Step 2: Commit**

```bash
git add jsx/host.jsx
git commit -m "feat: add ExtendScript importAndPlace function"
```

---

### Task 3: CSInterface.js

**Files:**
- Create: `js/CSInterface.js`

Adobe's official bridge library. Download directly from Adobe's CEP Resources GitHub.

- [ ] **Step 1: Download CSInterface.js**

```powershell
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/Adobe-CEP/CEP-Resources/master/CEP_11.x/CSInterface.js" `
  -OutFile "D:\Code\pasteit\js\CSInterface.js"
$size = (Get-Item "D:\Code\pasteit\js\CSInterface.js").Length
Write-Output "Downloaded: $size bytes"
```

Expected output: `Downloaded: <size> bytes` (file is ~40 KB; if 0 bytes, the URL may have moved — check https://github.com/Adobe-CEP/CEP-Resources)

- [ ] **Step 2: Commit**

```bash
git add js/CSInterface.js
git commit -m "feat: add Adobe CSInterface bridge library"
```

---

### Task 4: Panel HTML & CSS

**Files:**
- Create: `index.html`

Dark panel matching Premiere's UI: `#1e1e1e` background, full-width paste button, status line, hint text.

- [ ] **Step 1: Create `index.html`**

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>PasteIt</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: #1e1e1e;
      color: #f0f0f0;
      font-family: "Adobe Clean", Arial, sans-serif;
      font-size: 12px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      padding: 16px;
      gap: 10px;
      overflow: hidden;
      user-select: none;
    }

    #pasteBtn {
      width: 100%;
      padding: 10px 0;
      background: #3d3d3d;
      color: #f0f0f0;
      border: 1px solid #555;
      border-radius: 3px;
      font-size: 13px;
      cursor: pointer;
      letter-spacing: 0.3px;
      transition: background 0.1s;
    }

    #pasteBtn:hover  { background: #4d4d4d; }
    #pasteBtn:active { background: #2a2a2a; }
    #pasteBtn:disabled { opacity: 0.5; cursor: default; }

    #status {
      font-size: 11px;
      min-height: 16px;
      color: #aaa;
      text-align: center;
      width: 100%;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    #status.error   { color: #e06c6c; }
    #status.success { color: #88c070; }

    #hint {
      font-size: 10px;
      color: #555;
      text-align: center;
    }
  </style>
</head>
<body>
  <button id="pasteBtn">Paste Image from Clipboard</button>
  <div id="status"></div>
  <div id="hint">Ctrl+V also works when this panel is focused</div>

  <script src="js/CSInterface.js"></script>
  <script src="js/main.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "feat: add panel HTML and CSS"
```

---

### Task 5: Main JavaScript — clipboard, file I/O, bridge

**Files:**
- Create: `js/main.js`

Core logic: reads clipboard image via PowerShell subprocess, writes PNG to `PastedImages/` inside the project folder, calls `importAndPlace` in ExtendScript, updates status line.

- [ ] **Step 1: Create `js/main.js`**

```javascript
// js/main.js
/* global CSInterface */

const csInterface = new CSInterface();
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

// -- UI helpers --

let statusTimer;

function showStatus(message, type) {
  const el = document.getElementById('status');
  el.textContent = message;
  el.className = type || '';
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => {
    el.textContent = '';
    el.className = '';
  }, 3000);
}

function setButtonEnabled(enabled) {
  document.getElementById('pasteBtn').disabled = !enabled;
}

// -- Clipboard → disk via PowerShell --

function writeClipboardImageToFile(destPath) {
  const scriptPath = path.join(os.tmpdir(), 'pasteit_clip.ps1');
  const escaped = destPath.replace(/\\/g, '\\\\');
  const script = [
    'Add-Type -AssemblyName System.Windows.Forms',
    'Add-Type -AssemblyName System.Drawing',
    '$img = [System.Windows.Forms.Clipboard]::GetImage()',
    'if ($null -eq $img) { Write-Output "no_image"; exit 1 }',
    '$img.Save("' + escaped + '", [System.Drawing.Imaging.ImageFormat]::Png)',
    'Write-Output "ok"'
  ].join('\n');

  fs.writeFileSync(scriptPath, script, 'utf8');

  try {
    const output = execSync(
      'powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + scriptPath + '"',
      { encoding: 'utf8', timeout: 6000 }
    ).trim();
    return output === 'ok';
  } catch (e) {
    return false;
  }
}

// -- Get saved project path from ExtendScript --

function getProjectPath() {
  return new Promise((resolve, reject) => {
    csInterface.evalScript('app.project.path', (result) => {
      if (!result || result === 'EvalScript Err' || result.trim() === '') {
        reject(new Error('no_project_path'));
      } else {
        resolve(result.trim());
      }
    });
  });
}

// -- Main paste flow --

async function pasteImageToTimeline() {
  setButtonEnabled(false);
  showStatus('Reading clipboard…');

  let projectPath;
  try {
    projectPath = await getProjectPath();
  } catch (e) {
    showStatus('Save your project first', 'error');
    setButtonEnabled(true);
    return;
  }

  const pasteDir = path.join(path.dirname(projectPath), 'PastedImages');
  fs.mkdirSync(pasteDir, { recursive: true });

  const filename = 'paste-' + Date.now() + '.png';
  const filePath = path.join(pasteDir, filename);

  const clipOk = writeClipboardImageToFile(filePath);
  if (!clipOk) {
    showStatus('No image in clipboard', 'error');
    setButtonEnabled(true);
    return;
  }

  const escapedPath = filePath.replace(/\\/g, '\\\\');
  csInterface.evalScript('importAndPlace("' + escapedPath + '")', (result) => {
    setButtonEnabled(true);
    if (result === 'OK') {
      showStatus('Pasted: ' + filename, 'success');
    } else if (result === 'ERROR:no_project') {
      showStatus('Open a project first', 'error');
      try { fs.unlinkSync(filePath); } catch (e) {}
    } else if (result === 'ERROR:no_sequence') {
      showStatus('Open a sequence first', 'error');
      try { fs.unlinkSync(filePath); } catch (e) {}
    } else {
      showStatus('Paste failed (' + result + ')', 'error');
      try { fs.unlinkSync(filePath); } catch (e) {}
    }
  });
}

// -- Wire up button and Ctrl+V --

document.getElementById('pasteBtn').addEventListener('click', pasteImageToTimeline);

document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'v') {
    e.preventDefault();
    pasteImageToTimeline();
  }
});
```

- [ ] **Step 2: Commit**

```bash
git add js/main.js
git commit -m "feat: add clipboard read, file write, and ExtendScript bridge"
```

---

### Task 6: Development setup — debug mode & local install

**Files:**
- Create: `install.ps1`

CEP requires a Windows registry key to load unsigned extensions in development. This script sets the key and symlinks the project folder into Premiere's extensions directory.

- [ ] **Step 1: Create `install.ps1`**

```powershell
# install.ps1
# Run once (no admin needed for per-user install)
# Usage: .\install.ps1          — install
#        .\install.ps1 -Uninstall — remove

param([switch]$Uninstall)

$extensionId  = "com.pasteit.premiere"
$extensionDir = "$env:APPDATA\Adobe\CEP\extensions\$extensionId"
$sourceDir    = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Uninstall) {
  if (Test-Path $extensionDir) { Remove-Item $extensionDir -Recurse -Force }
  Write-Output "Uninstalled. Restart Premiere Pro."
  exit 0
}

# Enable PlayerDebugMode for CEP 9–11
foreach ($v in @("CSXS.9", "CSXS.10", "CSXS.11")) {
  $key = "HKCU:\Software\Adobe\$v"
  if (!(Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
  Set-ItemProperty -Path $key -Name "PlayerDebugMode" -Value "1" -Type String
}
Write-Output "CEP debug mode enabled."

# Create extensions parent dir if needed
$parent = "$env:APPDATA\Adobe\CEP\extensions"
if (!(Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }

# Remove any existing link/dir
if (Test-Path $extensionDir) { Remove-Item $extensionDir -Recurse -Force }

# Junction works without admin on Windows
New-Item -ItemType Junction -Path $extensionDir -Target $sourceDir | Out-Null

Write-Output "Linked: $extensionDir"
Write-Output "  -> $sourceDir"
Write-Output ""
Write-Output "Restart Premiere Pro, then: Window > Extensions > PasteIt"
```

- [ ] **Step 2: Run the install script**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& "D:\Code\pasteit\install.ps1"
```

Expected output:
```
CEP debug mode enabled.
Linked: C:\Users\<you>\AppData\Roaming\Adobe\CEP\extensions\com.pasteit.premiere
  -> D:\Code\pasteit

Restart Premiere Pro, then: Window > Extensions > PasteIt
```

- [ ] **Step 3: Commit**

```bash
git add install.ps1
git commit -m "feat: add dev install script with CEP debug mode and junction"
```

---

### Task 7: Smoke test

Manual integration test. Requires Premiere Pro running with the extension loaded.

- [ ] **Step 1: Load the extension in Premiere Pro**

1. Run `install.ps1` (Task 6 Step 2) if not already done
2. Start (or restart) Premiere Pro
3. Go to `Window > Extensions > PasteIt`
4. **Expected:** Small dark panel appears with "Paste Image from Clipboard" button and hint text below

- [ ] **Step 2: Test — no image in clipboard**

1. Ensure clipboard has no image (e.g. copy some text instead)
2. Click "Paste Image from Clipboard"
3. **Expected:** Status shows *"No image in clipboard"* in red → clears after 3 seconds

- [ ] **Step 3: Test — no open sequence**

1. Copy an image (Win+Shift+S → drag a region)
2. Ensure no sequence is open in Premiere's timeline
3. Click "Paste Image from Clipboard"
4. **Expected:** Status shows *"Open a sequence first"* in red

- [ ] **Step 4: Test — happy path**

1. Create or open a sequence in Premiere
2. Right-click any image in a browser → "Copy image"
3. Move the playhead to a visible position in the timeline
4. Click "Paste Image from Clipboard" in the PasteIt panel
5. **Expected:**
   - Status shows *"Pasted: paste-XXXXXXX.png"* in green
   - A 5-second clip appears on Video 1 at the playhead position
   - The clip shows in the Project panel
   - File exists at `<project folder>/PastedImages/paste-XXXXXXX.png`

- [ ] **Step 5: Test — Ctrl+V shortcut**

1. Click anywhere inside the PasteIt panel to focus it
2. Copy a different image
3. Press `Ctrl+V`
4. **Expected:** Same result as Step 4 — new clip appears at playhead

- [ ] **Step 6: Test — unsaved project**

1. `File > New > Project` but don't save it
2. Copy an image
3. Click "Paste Image from Clipboard"
4. **Expected:** Status shows *"Save your project first"* in red

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: PasteIt CEP plugin v1.0 complete"
```
