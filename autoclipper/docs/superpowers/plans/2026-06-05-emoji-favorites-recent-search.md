# Emoji Favorites, Recent, and Improved Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add favorites, recent, and improved word-aware search to the My Emojis tab in the emoji picker.

**Architecture:** All changes are in `frontend/index.html` — one CSS block and one JS block. State (favorites + recent) lives in `localStorage` under `acEmoFav` / `acEmoRecent`. `renderMyEmojiGrid()` is rewritten to render three labeled sections (Favorites → Recent → All) when not searching, and a flat ranked list when searching. A delegated click listener on the container handles both star-toggle and emoji-insert.

**Tech Stack:** Vanilla JS, CSS custom properties (already used throughout), localStorage JSON

---

### Task 1: Add state variables and helpers

**Files:**
- Modify: `frontend/index.html` — JS block, just before the existing `renderEmoGrid();renderMyEmojiGrid();` lines (~line 1786)

These helpers manage the two localStorage-backed sets. Add them before the existing `renderEmoGrid()` call.

- [ ] **Step 1: Locate the insertion point**

Find the line `renderEmoGrid();` near line 1786. The new code goes immediately above it.

- [ ] **Step 2: Insert state variables and helpers**

Add the following block immediately before `renderEmoGrid();`:

```javascript
// ── EMOJI FAVORITES & RECENT STATE ─────────────────────────────────────────
let emoFav=new Set();
let emoRecent=[];

function loadEmoState(){
  try{emoFav=new Set(JSON.parse(localStorage.getItem('acEmoFav')||'[]'));}catch(e){emoFav=new Set();}
  try{emoRecent=JSON.parse(localStorage.getItem('acEmoRecent')||'[]');}catch(e){emoRecent=[];}
}
function saveEmoFav(){localStorage.setItem('acEmoFav',JSON.stringify([...emoFav]));}
function saveEmoRecent(){localStorage.setItem('acEmoRecent',JSON.stringify(emoRecent));}
function toggleEmoFav(path){
  if(emoFav.has(path))emoFav.delete(path);else emoFav.add(path);
  saveEmoFav();
  renderMyEmojiGrid();
}
function trackEmoRecent(path){
  emoRecent=emoRecent.filter(p=>p!==path);
  emoRecent.unshift(path);
  if(emoRecent.length>20)emoRecent.length=20;
  saveEmoRecent();
}
loadEmoState();
```

- [ ] **Step 3: Verify no syntax errors**

Open browser DevTools console after reload. Confirm no errors. Run in console:
```javascript
toggleEmoFav('/emoji-pack/fire_1f525.png');
console.log([...emoFav]); // ['/emoji-pack/fire_1f525.png']
toggleEmoFav('/emoji-pack/fire_1f525.png');
console.log([...emoFav]); // []
```

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat: emoji favorites/recent state helpers"
```

---

### Task 2: CSS — wrap container, section headers, dividers, star button

**Files:**
- Modify: `frontend/index.html` — CSS block, near the existing `.myemo-grid` rule (~line 284)

- [ ] **Step 1: Find the existing `.myemo-grid` rule**

Locate this block near line 284:
```css
.myemo-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;max-height:190px;overflow-y:auto;padding:6px;flex-shrink:0}
.myemo-grid::-webkit-scrollbar{width:3px}
.myemo-grid::-webkit-scrollbar-thumb{background:var(--mut);border-radius:2px}
```

- [ ] **Step 2: Replace `.myemo-grid` rules and extend `.ec`**

Replace those three lines with:

```css
.myemo-wrap{display:flex;flex-direction:column;max-height:280px;overflow-y:auto;flex-shrink:0}
.myemo-wrap::-webkit-scrollbar{width:3px}
.myemo-wrap::-webkit-scrollbar-thumb{background:var(--mut);border-radius:2px}
.myemo-sgrid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;padding:4px 6px 6px}
.myemo-shdr{font-size:10px;font-weight:700;color:var(--sub);padding:6px 8px 2px;text-transform:uppercase;letter-spacing:.05em;flex-shrink:0}
.myemo-div{border-top:1px solid var(--b1);margin:4px 6px}
.ec-star{position:absolute;top:1px;right:1px;font-size:10px;line-height:1;background:none;border:none;padding:1px;cursor:pointer;opacity:0;transition:opacity .1s;color:var(--sub);pointer-events:auto}
.ec-star.fav{opacity:1;color:#f59e0b}
```

Then find the existing `.ec` rule (near line 229):
```css
.ec{width:36px;height:36px;cursor:pointer;padding:4px;border-radius:5px;transition:.1s;display:flex;align-items:center;justify-content:center}
```

Add `position:relative` to it:
```css
.ec{position:relative;width:36px;height:36px;cursor:pointer;padding:4px;border-radius:5px;transition:.1s;display:flex;align-items:center;justify-content:center}
```

Then add hover reveal for the star after `.ec:hover{background:var(--s3)}`:
```css
.ec:hover .ec-star{opacity:.5}
.ec:hover .ec-star.fav{opacity:1}
```

- [ ] **Step 3: Update the HTML container class**

Find in the HTML (near line 646):
```html
<div class="myemo-grid" id="myemo-grid"></div>
```

Change to:
```html
<div class="myemo-wrap" id="myemo-grid"></div>
```

- [ ] **Step 4: Verify visually**

Reload the page, open the emoji picker → My Emojis tab. The grid should still render all emojis. Section headers/dividers don't appear yet (that's Task 3).

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat: emoji picker section layout CSS"
```

---

### Task 3: Rewrite renderMyEmojiGrid with sections and star cells

**Files:**
- Modify: `frontend/index.html` — JS, the `renderMyEmojiGrid` function (~lines 1714–1730)

- [ ] **Step 1: Add the shared cell-builder helper**

Immediately before the `renderMyEmojiGrid` function, add:

```javascript
function _emoLabel(path){
  return path.split('/').pop().replace(/_[^_]+\.png$/,'').replace(/-/g,' ');
}
function _emoCell(path){
  function _he(s){return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
  const label=_emoLabel(path);
  const isFav=emoFav.has(path);
  return `<div class="ec" data-path="${_he(path)}" title="${_he(label)}">` +
    `<img src="${_he(path)}" alt="${_he(label)}" loading="lazy" width="28" height="28" style="display:block">` +
    `<button class="ec-star${isFav?' fav':''}" data-star="1" title="${isFav?'Unfavorite':'Favorite'}">${isFav?'⭐':'☆'}</button>` +
    `</div>`;
}
```

- [ ] **Step 2: Replace renderMyEmojiGrid entirely**

Replace the entire `renderMyEmojiGrid` function (lines 1714–1730) with:

```javascript
function renderMyEmojiGrid(){
  const wrap=document.getElementById('myemo-grid');
  if(!wrap)return;
  const q=(document.getElementById('myemo-search')?.value||'').trim();
  if(q){
    const results=_filterMyEmoji(q);
    wrap.innerHTML=results.length
      ?`<div class="myemo-sgrid">${results.map(_emoCell).join('')}</div>`
      :'<div style="padding:18px 8px;text-align:center;font-size:12px;color:var(--sub)">No emojis found</div>';
  } else {
    const allSorted=[...EMOJIPACK_FILES].sort((a,b)=>_emoLabel(a).localeCompare(_emoLabel(b)));
    const favPaths=[...emoFav].filter(p=>EMOJIPACK_FILES.includes(p))
      .sort((a,b)=>_emoLabel(a).localeCompare(_emoLabel(b)));
    const validRecent=emoRecent.filter(p=>EMOJIPACK_FILES.includes(p));
    let html='';
    if(favPaths.length){
      html+=`<div class="myemo-shdr">⭐ Favorites</div><div class="myemo-sgrid">${favPaths.map(_emoCell).join('')}</div><div class="myemo-div"></div>`;
    }
    if(validRecent.length){
      html+=`<div class="myemo-shdr">🕐 Recent</div><div class="myemo-sgrid">${validRecent.map(_emoCell).join('')}</div><div class="myemo-div"></div>`;
    }
    html+=`<div class="myemo-shdr">All</div><div class="myemo-sgrid">${allSorted.map(_emoCell).join('')}</div>`;
    wrap.innerHTML=html;
  }
  if(!wrap._emoPackListenerAttached){
    wrap._emoPackListenerAttached=true;
    wrap.addEventListener('click',function(e){
      if(e.target.closest('[data-star]')){
        const cell=e.target.closest('[data-path]');
        if(cell)toggleEmoFav(cell.dataset.path);
        return;
      }
      const cell=e.target.closest('[data-path]');
      if(cell)insertEmojiPackImg(cell.dataset.path);
    });
  }
}
```

- [ ] **Step 3: Verify sections render**

Reload. Open My Emojis tab. You should see the "All" section header with all emojis sorted A→Z. Favorites and Recent sections should not appear yet (nothing favorited or used).

- [ ] **Step 4: Verify star toggling**

In browser: hover over any emoji — a faint ☆ should appear top-right. Click it. The star should turn ⭐ and the emoji should jump to the Favorites section at top. Click ⭐ again — it unfavorites and the Favorites section disappears.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat: emoji grid sections with favorites and star toggle"
```

---

### Task 4: Upgrade filterMyEmoji with word-aware ranked search

**Files:**
- Modify: `frontend/index.html` — JS, the `filterMyEmoji` function (~lines 1769–1784)

- [ ] **Step 1: Add `_filterMyEmoji` helper**

Add this immediately before `filterMyEmoji`:

```javascript
function _filterMyEmoji(q){
  const words=q.toLowerCase().trim().split(/\s+/).filter(Boolean);
  if(!words.length)return[];
  const scored=[];
  for(const path of EMOJIPACK_FILES){
    const label=_emoLabel(path).toLowerCase();
    if(!words.every(w=>label.includes(w)))continue;
    scored.push({path,score:label.startsWith(words[0])?0:1});
  }
  scored.sort((a,b)=>a.score-b.score||_emoLabel(a.path).localeCompare(_emoLabel(b.path)));
  return scored.map(x=>x.path);
}
```

- [ ] **Step 2: Replace filterMyEmoji**

Replace the existing `filterMyEmoji` function with:

```javascript
function filterMyEmoji(q){renderMyEmojiGrid();}
```

(`renderMyEmojiGrid` now reads the search input value directly, so the query parameter is unused but kept for compatibility with the `oninput` handler.)

- [ ] **Step 3: Verify search**

Open My Emojis tab. Type "fire" — should show fire-related emojis. Type "face fire" — should show "face with fire" style emojis (both words present in label). Type "zzz" — should show "No emojis found". Clear the input — sections reappear.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat: word-aware ranked emoji search"
```

---

### Task 5: Track recent on insert

**Files:**
- Modify: `frontend/index.html` — JS, the `insertEmojiPackImg` function (~line 1732)

- [ ] **Step 1: Find `insertEmojiPackImg`**

Locate the function definition (near line 1732):
```javascript
function insertEmojiPackImg(path){
  // Extract unicode character...
  const filename=path.split('/').pop().replace('.png','');
```

- [ ] **Step 2: Add `trackEmoRecent` call at the top of the function**

Add one line immediately after the opening `{`:

```javascript
function insertEmojiPackImg(path){
  trackEmoRecent(path);
  // Extract unicode character from the codepoint suffix in the filename
  const filename=path.split('/').pop().replace('.png','');
```

- [ ] **Step 3: Verify recent tracking**

Insert a few emojis. Reopen the picker → My Emojis tab. The "🕐 Recent" section should appear showing the most recently used emojis, most recent first. Insert a 21st unique emoji — the oldest should drop off the list (max 20). Reload the page — recent list should persist from localStorage.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat: track recent emoji usage on insert"
```

---

### Task 6: Reset search re-renders sections

**Files:**
- Modify: `frontend/index.html` — JS, `switchEmoTab` function (~line 1708)

The tab switch already calls `filterMyEmoji('')` which now calls `renderMyEmojiGrid()`. Verify this is still wired correctly.

- [ ] **Step 1: Check switchEmoTab**

Find the block (~line 1708):
```javascript
if(isMypack){
  const s=document.getElementById('myemo-search');
  if(s){s.value='';filterMyEmoji('');}
}
```

This is correct as-is — `filterMyEmoji('')` triggers `renderMyEmojiGrid()` which reads the (now empty) input and renders sections. No change needed.

- [ ] **Step 2: Verify tab switching**

Type a search query in My Emojis. Switch to Twemoji tab and back to My Emojis. The search input should be cleared and sections should render (not the search results view).

- [ ] **Step 3: Commit (only if you had to make a change)**

If no change was needed, skip the commit. Otherwise:
```bash
git add frontend/index.html
git commit -m "fix: emoji tab switch clears search and restores sections"
```

---

### Task 7: Final end-to-end verification

- [ ] **Step 1: Full flow test**

1. Open app, open emoji picker → My Emojis tab
2. Confirm "All" section shows emojis A→Z, no Favorites/Recent sections
3. Hover emoji — ☆ appears top-right
4. Click ☆ — emoji moves to Favorites section, star becomes ⭐
5. Insert the favorited emoji by clicking its image — Recent section appears with it
6. Insert 2 more different emojis — Recent section shows 3 emojis, most recent first
7. Type "fire" in search — flat filtered list, no section headers
8. Type "fire face" — multi-word match works
9. Type "zzzzz" — "No emojis found" shown
10. Clear search — sections reappear with Favorites and Recent intact
11. Reload page — Favorites and Recent persist from localStorage

- [ ] **Step 2: Check localStorage**

In DevTools console:
```javascript
JSON.parse(localStorage.getItem('acEmoFav'))  // array of favorited paths
JSON.parse(localStorage.getItem('acEmoRecent')) // array, most recent first
```

- [ ] **Step 3: Final commit**

```bash
git add frontend/index.html
git commit -m "feat: emoji favorites, recent sections, and improved search complete"
```
