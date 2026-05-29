# Clipping-Inspired Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle `frontend/index.html` to match the Clipping dashboard aesthetic (pure black bg, green accents, card panels) with itshover-style CSS-animated SVG icons in the sidebar, toolbar, and right panel.

**Architecture:** Single file edit — all changes are in `frontend/index.html`. CSS custom properties are updated first (Task 1) so every downstream component picks up the new palette automatically. Animated icons are pure CSS keyframes + inline SVG, no library required.

**Tech Stack:** Vanilla HTML/CSS/JS, Fabric.js (existing, unchanged), inline SVG icons with CSS `@keyframes` animations triggered by `:hover`.

---

### Task 1: Update CSS custom properties (color tokens)

**Files:**
- Modify: `frontend/index.html` — `:root` block, lines 12–18

- [ ] **Step 1: Replace the `:root` block**

Find this exact block in `frontend/index.html`:
```css
:root{
  --bg:#111113;--s1:#161618;--s2:#1c1c1f;--s3:#222226;
  --b1:rgba(255,255,255,0.07);--b2:rgba(255,255,255,0.11);--b3:rgba(255,255,255,0.16);
  --acc:#e8e8ed;--acc2:#9999a8;--accdim:rgba(232,232,237,.07);
  --tx:#e8e8ed;--sub:#6e6e80;--mut:rgba(255,255,255,0.06);
  --danger:#f43f5e;--ok:#22c55e;
  --r:8px;--rs:6px;
}
```

Replace with:
```css
:root{
  --bg:#09090b;--s1:#0d0d0f;--s2:#111113;--s3:#161618;
  --b1:rgba(255,255,255,0.07);--b2:rgba(255,255,255,0.11);--b3:rgba(255,255,255,0.16);
  --acc:#22c55e;--acc2:#16a34a;--accdim:rgba(34,197,94,.08);
  --tx:#f0f0f5;--sub:#52526a;--mut:rgba(255,255,255,0.06);
  --danger:#f43f5e;--ok:#22c55e;
  --r:10px;--rs:7px;
}
```

- [ ] **Step 2: Fix btn-primary hover** (currently hardcodes white `#fff`, must stay readable with green bg)

Find:
```css
.btn-primary:hover{background:#fff}
```
Replace with:
```css
.btn-primary:hover{background:#16a34a}
```

- [ ] **Step 3: Open `frontend/index.html` in browser and verify**

The page should now have a noticeably darker background (#09090b), all accent elements (active format pill, layer selection borders, focused inputs, Save Template button) should appear green. If any element is obviously broken (white text invisible, etc.), stop and fix before continuing.

- [ ] **Step 4: Commit**
```bash
git add frontend/index.html
git commit -m "style: update color tokens to Clipping palette (black bg, green accent)"
```

---

### Task 2: Restyle sidebar

**Files:**
- Modify: `frontend/index.html` — sidebar CSS (lines 35–45) and sidebar HTML (lines 185–201)

- [ ] **Step 1: Replace sidebar CSS**

Find:
```css
/* ─── SIDEBAR ─────────────────────────────────────────── */
.sb-logo{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid var(--b1)}
.sb-logo-icon{width:32px;height:32px;border-radius:8px;overflow:hidden;flex-shrink:0}
.sb-logo-text{font-size:15px;font-weight:900;letter-spacing:-.4px}
.new-proj-btn{margin:10px 12px;padding:9px 10px;border-radius:var(--r);border:1px solid var(--acc);background:var(--accdim);color:var(--acc);cursor:pointer;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;gap:7px;transition:.12s}
.new-proj-btn:hover{background:var(--acc);color:var(--bg)}
.vid-card{margin:0 12px;padding:10px 12px;border-radius:var(--rs);border:1px solid var(--b1);background:var(--s2)}
.vid-card-lbl{font-size:9px;font-weight:700;color:var(--sub);text-transform:uppercase;letter-spacing:1.1px;margin-bottom:5px;display:flex;align-items:center;gap:5px}
.vid-card-lbl::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--ok);flex-shrink:0}
.vid-filename{font-size:11px;color:var(--tx);font-weight:600;word-break:break-all;line-height:1.4}
.vid-meta{font-size:10px;color:var(--sub);margin-top:3px}
```

Replace with:
```css
/* ─── SIDEBAR ─────────────────────────────────────────── */
.sb-logo{display:flex;align-items:center;gap:10px;padding:16px;border-bottom:1px solid var(--b1)}
.sb-logo-icon{width:30px;height:30px;border-radius:8px;overflow:hidden;flex-shrink:0;background:#f0f0f5;display:flex;align-items:center;justify-content:center}
.sb-logo-text{font-size:14px;font-weight:900;letter-spacing:-.4px;color:var(--tx)}
.sb-nav{display:flex;flex-direction:column;gap:2px;padding:10px 10px}
.sb-nav-item{display:flex;align-items:center;gap:9px;padding:8px 10px;border-radius:8px;font-size:12px;font-weight:600;color:var(--sub);cursor:pointer;transition:.15s;user-select:none;position:relative}
.sb-nav-item:hover{background:rgba(255,255,255,0.05);color:var(--tx)}
.sb-nav-item.active{background:rgba(34,197,94,0.09);color:var(--acc)}
.sb-nav-icon{width:16px;height:16px;flex-shrink:0;display:flex;align-items:center;justify-content:center}
.new-proj-btn{margin:4px 10px 10px;padding:9px 10px;border-radius:var(--r);border:1px solid var(--acc);background:var(--accdim);color:var(--acc);cursor:pointer;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;gap:7px;transition:.12s}
.new-proj-btn:hover{background:var(--acc);color:var(--bg)}
.vid-card{margin:0 10px;padding:10px 12px;border-radius:var(--r);border:1px solid var(--b1);background:var(--s2)}
.vid-card-lbl{font-size:9px;font-weight:700;color:var(--sub);text-transform:uppercase;letter-spacing:1.1px;margin-bottom:5px;display:flex;align-items:center;gap:5px}
.vid-card-lbl::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--ok);flex-shrink:0}
.vid-filename{font-size:11px;color:var(--tx);font-weight:600;word-break:break-all;line-height:1.4}
.vid-meta{font-size:10px;color:var(--sub);margin-top:3px}
```

- [ ] **Step 2: Replace sidebar HTML**

Find the entire sidebar `<div id="sidebar">` block (lines 185–201):
```html
<!-- ── SIDEBAR ──────────────────────────────────────── -->
<div id="sidebar">
  <div class="sb-logo">
    <div class="sb-logo-icon">
      <img src="logo.png" width="32" height="32" style="object-fit:contain;display:block;">
    </div>
    <div class="sb-logo-text">Cutly</div>
  </div>
  <button class="new-proj-btn" onclick="openDlModal()">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"/></svg>
    Download Video
  </button>
  <div class="vid-card" id="vid-card" style="display:none">
    <div class="vid-card-lbl">Ready to export</div>
    <div class="vid-filename" id="vid-filename">—</div>
    <div class="vid-meta" id="vid-meta"></div>
  </div>
</div>
```

Replace with:
```html
<!-- ── SIDEBAR ──────────────────────────────────────── -->
<div id="sidebar">
  <div class="sb-logo">
    <div class="sb-logo-icon">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="#09090b" width="18" height="18"><path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"/></svg>
    </div>
    <div class="sb-logo-text">Cutly</div>
  </div>
  <div class="sb-nav">
    <div class="sb-nav-item active" title="Editor">
      <span class="sb-nav-icon hover-icon" id="nav-icon-editor">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path class="edit-pen" stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Z"/></svg>
      </span>
      Editor
    </div>
    <div class="sb-nav-item" title="Templates" onclick="switchTab('tpl')">
      <span class="sb-nav-icon hover-icon" id="nav-icon-tpl">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><rect class="tpl-rect" x="3" y="3" width="7" height="7" rx="1"/><rect class="tpl-rect" x="14" y="3" width="7" height="7" rx="1"/><rect class="tpl-rect" x="3" y="14" width="7" height="7" rx="1"/><rect class="tpl-rect" x="14" y="14" width="7" height="7" rx="1"/></svg>
      </span>
      Templates
    </div>
  </div>
  <button class="new-proj-btn" onclick="openDlModal()">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"/></svg>
    Download Video
  </button>
  <div class="vid-card" id="vid-card" style="display:none">
    <div class="vid-card-lbl">Ready to export</div>
    <div class="vid-filename" id="vid-filename">—</div>
    <div class="vid-meta" id="vid-meta"></div>
  </div>
</div>
```

- [ ] **Step 3: Verify in browser**

Sidebar should show the Clipping-style nav items with rounded active green highlight. The logo icon is now an SVG on a white square background.

- [ ] **Step 4: Commit**
```bash
git add frontend/index.html
git commit -m "style: restyle sidebar with Clipping nav items and new logo treatment"
```

---

### Task 3: Restyle topbar (format pills + primary button)

**Files:**
- Modify: `frontend/index.html` — topbar CSS (lines 47–62)

- [ ] **Step 1: Update format group CSS to pill style**

Find:
```css
.fmt-grp{display:flex;gap:3px;background:var(--bg);border:1px solid var(--b1);border-radius:var(--rs);padding:3px}
.fmt-btn{padding:3px 11px;border:none;border-radius:4px;font-size:11px;font-weight:700;cursor:pointer;background:transparent;color:var(--sub);transition:.12s;letter-spacing:.3px}
.fmt-btn.on{background:var(--acc);color:var(--bg)}
```

Replace with:
```css
.fmt-grp{display:flex;gap:2px;background:var(--s2);border:1px solid var(--b1);border-radius:20px;padding:3px}
.fmt-btn{padding:4px 12px;border:none;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;background:transparent;color:var(--sub);transition:.15s;letter-spacing:.3px}
.fmt-btn.on{background:var(--acc);color:#09090b}
.fmt-btn:not(.on):hover{color:var(--tx)}
```

- [ ] **Step 2: Update icon-btn hover to use green tint**

Find:
```css
.icon-btn:hover{background:var(--s3);color:var(--tx)}
```
Replace with:
```css
.icon-btn:hover{background:rgba(34,197,94,0.07);color:var(--tx)}
```

- [ ] **Step 3: Verify in browser**

Format switcher (1:1 / 9:16) should now have a pill/rounded-rectangle shape. Active pill has green background with dark text. Hovering inactive toolbar icon buttons shows a faint green tint.

- [ ] **Step 4: Commit**
```bash
git add frontend/index.html
git commit -m "style: pill-style format switcher and green icon-btn hover"
```

---

### Task 4: Restyle left panel (tabs, element grid, layer rows)

**Files:**
- Modify: `frontend/index.html` — left panel CSS (lines 64–111)

- [ ] **Step 1: Update left panel tab and element grid CSS**

Find:
```css
.lp-tab{flex:1;padding:9px 0;text-align:center;font-size:11px;font-weight:700;cursor:pointer;color:var(--sub);border-bottom:2px solid transparent;transition:.12s;text-transform:uppercase;letter-spacing:.4px}
.lp-tab.on{color:var(--tx);border-bottom-color:var(--acc)}
```
Replace with:
```css
.lp-tab{flex:1;padding:9px 0;text-align:center;font-size:11px;font-weight:700;cursor:pointer;color:var(--sub);border-bottom:2px solid transparent;transition:.12s;text-transform:uppercase;letter-spacing:.4px}
.lp-tab.on{color:var(--acc);border-bottom-color:var(--acc)}
```

- [ ] **Step 2: Update element button card look**

Find:
```css
.el-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;padding:9px 6px;border-radius:var(--rs);border:1px solid var(--b1);background:var(--s2);cursor:pointer;transition:.14s;font-size:10px;color:var(--sub);font-weight:600;text-align:center}
.el-btn:hover{border-color:var(--b2);color:var(--tx);background:var(--s3)}
.el-ico{width:30px;height:30px;border-radius:7px;display:flex;align-items:center;justify-content:center}
.ei-v,.ei-b,.ei-t,.ei-i,.ei-s{background:var(--s3);color:var(--sub)}
```
Replace with:
```css
.el-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;padding:10px 6px;border-radius:10px;border:1px solid var(--b1);background:var(--s2);cursor:pointer;transition:.15s;font-size:10px;color:var(--sub);font-weight:600;text-align:center}
.el-btn:hover{border-color:rgba(34,197,94,0.3);color:var(--tx);background:var(--s3);box-shadow:0 0 0 1px rgba(34,197,94,0.08)}
.el-ico{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center}
.ei-v,.ei-b,.ei-t,.ei-i,.ei-s{background:var(--s3);color:var(--sub)}
.el-btn:hover .ei-v,.el-btn:hover .ei-b,.el-btn:hover .ei-t,.el-btn:hover .ei-i,.el-btn:hover .ei-s{color:var(--acc)}
```

- [ ] **Step 3: Update active layer row to use green left border accent**

Find:
```css
.lrow.on{background:var(--s3);border-color:var(--acc);color:var(--tx)}
```
Replace with:
```css
.lrow.on{background:var(--s3);border-color:rgba(34,197,94,0.4);color:var(--tx);border-left-color:var(--acc)}
```

- [ ] **Step 4: Verify in browser**

Active left panel tab label should be green. Element grid buttons should show a faint green border glow on hover. Active layer row has a green-tinted border.

- [ ] **Step 5: Commit**
```bash
git add frontend/index.html
git commit -m "style: green-accent left panel tabs, card element grid, layer row border"
```

---

### Task 5: Restyle right panel (section cards, inputs, toggles)

**Files:**
- Modify: `frontend/index.html` — right panel CSS (lines 124–178)

- [ ] **Step 1: Update `.psec` to card style**

Find:
```css
.psec{padding:11px 14px;border-bottom:1px solid var(--b1)}
.psec-title{font-size:9px;font-weight:700;color:var(--sub);text-transform:uppercase;letter-spacing:1.2px;margin-bottom:9px}
```
Replace with:
```css
.psec{padding:11px 12px;margin:6px 8px;border-radius:10px;border:1px solid var(--b1);background:var(--s2)}
.psec-title{font-size:9px;font-weight:700;color:var(--sub);text-transform:uppercase;letter-spacing:1.2px;margin-bottom:9px;display:flex;align-items:center;gap:6px}
.psec-title-icon{width:14px;height:14px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
```

- [ ] **Step 2: Update toggle button active state to green**

Find:
```css
.togbtn.on{background:var(--acc);color:var(--bg)}
```
Replace with:
```css
.togbtn.on{background:var(--acc);color:#09090b}
```

- [ ] **Step 3: Update alignment button hover to green border**

Find:
```css
.abtn:hover{border-color:var(--acc);color:var(--tx);background:var(--s3)}
```
Replace with:
```css
.abtn:hover{border-color:var(--acc);color:var(--acc);background:var(--s3)}
```

- [ ] **Step 4: Update `.no-sel` empty state and modal styles**

Find:
```css
.modal-box{background:var(--s1);border:1px solid var(--b2);border-radius:14px;padding:28px;width:480px;box-shadow:0 24px 64px rgba(0,0,0,.8)}
```
Replace with:
```css
.modal-box{background:var(--s1);border:1px solid var(--b1);border-radius:16px;padding:28px;width:480px;box-shadow:0 24px 80px rgba(0,0,0,.9)}
```

- [ ] **Step 5: Remove the bottom-border gap between psec cards by adding spacing to #right**

Find:
```css
#right{width:280px;flex-shrink:0;background:var(--s1);border-left:1px solid var(--b1);overflow-y:auto;overflow-x:hidden}
```
Replace with:
```css
#right{width:280px;flex-shrink:0;background:var(--s1);border-left:1px solid var(--b1);overflow-y:auto;overflow-x:hidden;padding:4px 0 12px}
```

- [ ] **Step 6: Verify in browser**

Select a text/video element on the canvas. Right panel should show sections as distinct cards with rounded corners and spacing between them, rather than flat separator lines.

- [ ] **Step 7: Commit**
```bash
git add frontend/index.html
git commit -m "style: right panel sections as cards, green toggle/align highlights"
```

---

### Task 6: Add CSS keyframe animations for hover icons

**Files:**
- Modify: `frontend/index.html` — add after the closing `}` of `.prog-fill` rule (before `</style>`)

- [ ] **Step 1: Add hover icon animation CSS block**

Find the very end of the `<style>` block — the last CSS rule before `</style>` is:
```css
.prog-fill{height:100%;background:var(--acc);width:0;transition:width .3s;border-radius:2px}
```

After that rule (still inside `<style>`, before `</style>`), add:
```css

/* ─── ANIMATED ICONS (itshover-style) ───────────────── */
.hover-icon{display:inline-flex;align-items:center;justify-content:center}

/* Editor / pen icon — pen tip dips down then returns */
@keyframes pen-write{0%{transform:translate(0,0) rotate(0deg)}30%{transform:translate(1px,1px) rotate(-8deg)}60%{transform:translate(-1px,-1px) rotate(4deg)}100%{transform:translate(0,0) rotate(0deg)}}
.sb-nav-item:hover #nav-icon-editor .edit-pen{animation:pen-write .5s ease-in-out}

/* Templates / grid icon — tiles scatter and snap back */
@keyframes grid-scatter{0%{transform:scale(1)}40%{transform:scale(1.15)}70%{transform:scale(0.95)}100%{transform:scale(1)}}
.sb-nav-item:hover #nav-icon-tpl .tpl-rect{animation:grid-scatter .4s ease-in-out}
.sb-nav-item:hover #nav-icon-tpl .tpl-rect:nth-child(2){animation-delay:.06s}
.sb-nav-item:hover #nav-icon-tpl .tpl-rect:nth-child(3){animation-delay:.03s}
.sb-nav-item:hover #nav-icon-tpl .tpl-rect:nth-child(4){animation-delay:.09s}

/* Undo / redo — sweep arc */
@keyframes undo-sweep{0%{stroke-dashoffset:0}50%{stroke-dashoffset:20}100%{stroke-dashoffset:0}}
.icon-btn:hover .undo-path{stroke-dasharray:40;animation:undo-sweep .45s ease-in-out}
.icon-btn:hover .redo-path{stroke-dasharray:40;animation:undo-sweep .45s ease-in-out reverse}

/* Gear — rotate */
@keyframes gear-spin{from{transform:rotate(0deg);transform-box:fill-box;transform-origin:center}to{transform:rotate(360deg);transform-box:fill-box;transform-origin:center}}
.psec-title:hover .gear-path,.icon-btn:hover .gear-path{animation:gear-spin .7s ease-in-out}

/* Download arrow — drop and rise */
@keyframes dl-drop{0%{transform:translateY(0)}40%{transform:translateY(3px)}100%{transform:translateY(0)}}
.new-proj-btn:hover .dl-arrow,.icon-btn:hover .dl-arrow,.btn:hover .dl-arrow{animation:dl-drop .4s ease-in-out}

/* Export arrow — rise */
@keyframes ex-rise{0%{transform:translateY(0)}40%{transform:translateY(-3px)}100%{transform:translateY(0)}}
.btn:hover .ex-arrow{animation:ex-rise .4s ease-in-out}

/* Save / bookmark — pulse */
@keyframes bm-pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.15)}}
.btn:hover .save-path{animation:bm-pulse .35s ease-in-out}

/* Palette / color — spin */
@keyframes pal-spin{0%{transform:rotate(0deg);transform-box:fill-box;transform-origin:center}100%{transform:rotate(20deg);transform-box:fill-box;transform-origin:center}}
.psec-title:hover .pal-path{animation:pal-spin .3s ease-out forwards}

/* Text cursor — blink */
@keyframes cur-blink{0%,100%{opacity:1}50%{opacity:0}}
.psec-title:hover .cur-path{animation:cur-blink .6s ease-in-out 2}

/* Film / video frames — slide */
@keyframes film-slide{0%{transform:translateX(0)}50%{transform:translateX(-2px)}100%{transform:translateX(0)}}
.psec-title:hover .film-path{animation:film-slide .4s ease-in-out}

/* Move / transform — nudge */
@keyframes move-nudge{0%{transform:translate(0,0)}25%{transform:translate(-1px,-1px)}75%{transform:translate(1px,1px)}100%{transform:translate(0,0)}}
.psec-title:hover .move-path{animation:move-nudge .4s ease-in-out}

/* Canvas grid toggle — pulse */
@keyframes grid-pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.tbar-btn:hover .grid-path{animation:grid-pulse .4s ease-in-out}
```

- [ ] **Step 2: Verify no CSS syntax errors**

Open `frontend/index.html` in browser. Check browser DevTools console — there should be no CSS parse errors. The page should look identical to after Task 5.

- [ ] **Step 3: Commit**
```bash
git add frontend/index.html
git commit -m "style: add itshover-style CSS keyframe animations for icon hover effects"
```

---

### Task 7: Add animated SVG icon classes to toolbar buttons

**Files:**
- Modify: `frontend/index.html` — topbar HTML (lines 218–244)

- [ ] **Step 1: Add animation class to undo button SVG path**

Find the undo button:
```html
    <button class="icon-btn" onclick="doUndo()" title="Undo">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="17" height="17"><path stroke-linecap="round" stroke-linejoin="round" d="M9 15 3 9m0 0 6-6M3 9h12a6 6 0 0 1 0 12h-3"/></svg>
    </button>
```
Replace with:
```html
    <button class="icon-btn" onclick="doUndo()" title="Undo">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="17" height="17"><path class="undo-path" stroke-linecap="round" stroke-linejoin="round" d="M9 15 3 9m0 0 6-6M3 9h12a6 6 0 0 1 0 12h-3"/></svg>
    </button>
```

- [ ] **Step 2: Add animation class to redo button SVG path**

Find the redo button:
```html
    <button class="icon-btn" onclick="doRedo()" title="Redo">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="17" height="17"><path stroke-linecap="round" stroke-linejoin="round" d="m15 15 6-6m0 0-6-6m6 6H9a6 6 0 0 0 0 12h3"/></svg>
    </button>
```
Replace with:
```html
    <button class="icon-btn" onclick="doRedo()" title="Redo">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="17" height="17"><path class="redo-path" stroke-linecap="round" stroke-linejoin="round" d="m15 15 6-6m0 0-6-6m6 6H9a6 6 0 0 0 0 12h3"/></svg>
    </button>
```

- [ ] **Step 3: Add animation classes to Download, Export, Save Template buttons**

Find the Download button in topbar right:
```html
      <button class="btn btn-ghost" onclick="openDlModal()">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"/></svg>
        Download
      </button>
```
Replace with:
```html
      <button class="btn btn-ghost" onclick="openDlModal()">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14"><path class="dl-arrow" stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"/></svg>
        Download
      </button>
```

Find the Export button:
```html
      <button class="btn btn-ghost" id="export-btn" onclick="openExpModal()">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"/></svg>
        Export
      </button>
```
Replace with:
```html
      <button class="btn btn-ghost" id="export-btn" onclick="openExpModal()">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14"><path class="ex-arrow" stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"/></svg>
        Export
      </button>
```

Find the Save Template button:
```html
      <button class="btn btn-primary" onclick="saveTemplate()">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0Z"/></svg>
        Save Template
      </button>
```
Replace with:
```html
      <button class="btn btn-primary" onclick="saveTemplate()">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14"><path class="save-path" stroke-linecap="round" stroke-linejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0Z"/></svg>
        Save Template
      </button>
```

- [ ] **Step 4: Add animation class to sidebar Download Video button arrow**

Find the sidebar new-proj-btn:
```html
  <button class="new-proj-btn" onclick="openDlModal()">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"/></svg>
    Download Video
  </button>
```
Replace with:
```html
  <button class="new-proj-btn" onclick="openDlModal()">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="14" height="14"><path class="dl-arrow" stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"/></svg>
    Download Video
  </button>
```

- [ ] **Step 5: Add animation class to canvas toolbar grid button**

Find:
```html
          <button class="tbar-btn" onclick="toggleGrid()">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="13" height="13"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"/></svg>
            Grid
          </button>
```
Replace with:
```html
          <button class="tbar-btn" onclick="toggleGrid()">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="13" height="13"><path class="grid-path" stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"/></svg>
            Grid
          </button>
```

- [ ] **Step 6: Verify animations work in browser**

Hover over each modified button. You should see:
- Undo: arc sweeps
- Redo: arc sweeps reverse
- Download (topbar + sidebar): arrow drops then returns
- Export: arrow rises then returns
- Save Template: bookmark pulses
- Canvas Grid: icon pulses opacity

- [ ] **Step 7: Commit**
```bash
git add frontend/index.html
git commit -m "style: add animation classes to toolbar, topbar, and sidebar button SVG paths"
```

---

### Task 8: Add animated icons to right panel section titles

**Files:**
- Modify: `frontend/index.html` — right panel HTML (built dynamically by JS)

This panel's sections are rendered by JavaScript. Search for where `.psec` and `.psec-title` are produced.

- [ ] **Step 1: Find where right panel sections are built**

Search the JS in `frontend/index.html` for `psec-title`. Each section title is set via `innerHTML` or `textContent`. Note every location.

Run in DevTools console to confirm structure:
```js
document.querySelectorAll('.psec-title').forEach(el => console.log(el.textContent.trim()))
```

- [ ] **Step 2: Add icon prefix to each `.psec-title` in the JS that renders the panel**

Find all places in the `<script>` block where a `.psec-title` innerHTML is set. They will look like one of:
```js
// Pattern A — direct innerHTML
el.innerHTML = '<div class="psec-title">Transform</div>...'
// Pattern B — innerText
titleEl.textContent = 'Transform'
```

For **Pattern A** (inline HTML strings), add icon SVGs as a prefix inside the title div. Apply these mappings:

| Section name contains | Icon SVG to prepend inside `.psec-title` |
|---|---|
| `Transform` / `Position` / `Size` | `<svg class="psec-title-icon move-path" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="12" height="12"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"/></svg>` |
| `Style` / `Appearance` / `Color` | `<svg class="psec-title-icon pal-path" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="12" height="12"><path stroke-linecap="round" stroke-linejoin="round" d="M4.098 19.902a3.75 3.75 0 0 0 5.304 0l6.401-6.402M6.75 21A3.75 3.75 0 0 1 3 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125v4.072M6.75 21a3.75 3.75 0 0 0 3.75-3.75V8.197M6.75 21h13.125c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125h-4.072M10.5 8.197l2.88-2.88c.438-.439 1.15-.439 1.59 0l3.712 3.713c.44.44.44 1.152 0 1.59l-2.879 2.88M6.75 17.25h.008v.008H6.75v-.008Z"/></svg>` |
| `Text` / `Font` | `<svg class="psec-title-icon cur-path" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="12" height="12"><path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z"/></svg>` |
| `Video` / `Clip` / `Media` | `<svg class="psec-title-icon film-path" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="12" height="12"><path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"/></svg>` |
| `Settings` / `Config` / `Options` | `<svg class="psec-title-icon gear-path" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="12" height="12"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/></svg>` |

- [ ] **Step 3: Verify icons appear in right panel section titles**

Add a text element to the canvas. Right panel should show section titles each with a small icon on the left. Hovering the title row triggers the matching animation (gear spins, palette rotates, cursor blinks, etc.).

- [ ] **Step 4: Commit**
```bash
git add frontend/index.html
git commit -m "style: animated icons in right panel section titles"
```

---

### Task 9: Polish canvas area and final touch-ups

**Files:**
- Modify: `frontend/index.html` — canvas area CSS and miscellaneous cleanup

- [ ] **Step 1: Update canvas dot grid to darker dots**

Find:
```css
.cvs-dots{position:absolute;inset:0;pointer-events:none;background-image:radial-gradient(circle,var(--s3) 1px,transparent 1px);background-size:22px 22px;opacity:.4}
```
Replace with:
```css
.cvs-dots{position:absolute;inset:0;pointer-events:none;background-image:radial-gradient(circle,rgba(255,255,255,0.08) 1px,transparent 1px);background-size:22px 22px}
```

- [ ] **Step 2: Update canvas toolbar pill to card style**

Find:
```css
.cvs-toolbar{display:flex;align-items:center;gap:8px;background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);padding:6px 12px;font-size:11px;color:var(--sub)}
```
Replace with:
```css
.cvs-toolbar{display:flex;align-items:center;gap:8px;background:var(--s1);border:1px solid var(--b1);border-radius:12px;padding:6px 14px;font-size:11px;color:var(--sub);box-shadow:0 4px 20px rgba(0,0,0,0.4)}
```

- [ ] **Step 3: Update snap button active color to green**

Find:
```html
          <button class="tbar-btn" id="snap-btn" style="color:var(--acc)" onclick="toggleSnap()">
```
This inline style `color:var(--acc)` already uses the accent so it will be green automatically from Task 1. Verify it renders green, no code change needed.

- [ ] **Step 4: Update modal backdrop to be slightly more opaque for contrast against new darker bg**

Find:
```css
#dl-modal,#exp-modal{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:400;display:none;align-items:center;justify-content:center}
```
Replace with:
```css
#dl-modal,#exp-modal{position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:400;display:none;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
```

- [ ] **Step 5: Full visual review in browser**

Open the app and check every area:
- [ ] Sidebar: pure black bg, green active nav item, white logo box
- [ ] Topbar: pill format switcher with green active, undo/redo animate on hover
- [ ] Left panel: element grid cards glow green on hover, active tab label is green
- [ ] Canvas: darker dot grid, rounded pill canvas toolbar
- [ ] Right panel: section cards with spacing, icons in section titles
- [ ] Modals: blurred backdrop, rounded box

- [ ] **Step 6: Commit**
```bash
git add frontend/index.html
git commit -m "style: canvas dot grid, toolbar pill, modal blur backdrop polish"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Color system — Task 1
- ✅ Sidebar (logo, nav, animated icons) — Tasks 2, 7
- ✅ Topbar (pill format switcher, green hover, animated icons) — Tasks 3, 7
- ✅ Left panel (element grid cards, layer rows, tab accent) — Task 4
- ✅ Right panel (section cards, animated icons) — Tasks 5, 8
- ✅ CSS keyframe animations — Task 6
- ✅ Canvas area (dot grid, toolbar pill) — Task 9
- ✅ Modals — Task 9

**No placeholders:** All tasks contain exact CSS/HTML strings to find and replace. No "TBD" or "add appropriate handling."

**Consistency:** All animation CSS class names (`undo-path`, `redo-path`, `dl-arrow`, `ex-arrow`, `save-path`, `gear-path`, `pal-path`, `cur-path`, `film-path`, `move-path`, `grid-path`, `edit-pen`, `tpl-rect`) are defined in Task 6 keyframes and applied in Tasks 7–8. No naming mismatches.
