// js/main.js
/* global CSInterface */

const csInterface = new CSInterface();
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

// -- UI helpers --

let statusTimer;
let isRunning = false;

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
  const escaped = destPath.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
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
  if (isRunning) return;
  isRunning = true;
  setButtonEnabled(false);
  showStatus('Reading clipboard…');

  let projectPath;
  try {
    projectPath = await getProjectPath();
  } catch (e) {
    showStatus('Save your project first', 'error');
    setButtonEnabled(true);
    isRunning = false;
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
    isRunning = false;
    return;
  }

  const escapedPath = filePath.replace(/\\/g, '\\\\');
  csInterface.evalScript('importAndPlace("' + escapedPath + '")', (result) => {
    setButtonEnabled(true);
    isRunning = false;
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
