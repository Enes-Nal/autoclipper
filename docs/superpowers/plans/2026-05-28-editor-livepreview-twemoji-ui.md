# Editor: Live Preview, Twemoji Picker, Linear-Style UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship live video-frame preview in the Fabric.js canvas, an iOS-style Twemoji emoji picker, and a Linear-inspired UI redesign — all in `frontend/index.html`.

**Architecture:** Single-file frontend. JS logic (canvas, history, snapping, export) is preserved as-is. CSS variables are replaced wholesale. Three JS additions: a `requestAnimationFrame` loop for live video, a `fabric.Image`-backed `addVideo()`, and a Twemoji image picker that adds emoji as canvas objects.

**Tech Stack:** Fabric.js 5.3.1 (existing), Twemoji 14.0.2 (jsDelivr CDN, new), Flask 5000 for serving.

**How to run the app during testing:**
```
python app.py
# open http://localhost:5000
```

---

## File Map

| File | Change |
|---|---|
| `frontend/index.html` | All changes (CSS variables, HTML structure, JS additions) |

No new files. No backend changes.

---

## Task 1: Add Twemoji CDN + Linear-Style CSS Overhaul

**Files:**
- Modify: `frontend/index.html` (lines 1–173, CSS + `<head>`)

- [ ] **Step 1: Add Twemoji script tag to `<head>`**

In `frontend/index.html`, find the line:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.1/fabric.min.js"></script>
```
Add the Twemoji script directly after it:
```html
<script src="https://cdn.jsdelivr.net/npm/twemoji@14.0.2/dist/twemoji.min.js" crossorigin="anonymous"></script>
```

- [ ] **Step 2: Replace CSS root variables**

Find the entire `:root{...}` block (lines 10–17):
```css
:root{
  --bg:#0d0d1a;--s1:#111120;--s2:#0e0e1c;--s3:#16162a;
  --b1:#1c1c32;--b2:#262644;--b3:#32325a;
  --acc:#7c5cf6;--acc2:#e879f9;--accdim:rgba(124,92,246,.14);
  --tx:#f0f0fa;--sub:#7070a0;--mut:#2a2a48;
  --danger:#f43f5e;--ok:#22c55e;
  --r:8px;--rs:6px;
}
```
Replace with:
```css
:root{
  --bg:#111113;--s1:#161618;--s2:#1c1c1f;--s3:#222226;
  --b1:rgba(255,255,255,0.07);--b2:rgba(255,255,255,0.11);--b3:rgba(255,255,255,0.16);
  --acc:#5865f2;--acc2:#818cf8;--accdim:rgba(88,101,242,.12);
  --tx:#e8e8ed;--sub:#6e6e80;--mut:rgba(255,255,255,0.06);
  --danger:#f43f5e;--ok:#22c55e;
  --r:8px;--rs:6px;
}
```

- [ ] **Step 3: Update phone mockup style**

Find:
```css
#phone{position:relative;border:2.5px solid #242440;border-radius:28px;overflow:hidden;background:#000;box-shadow:0 0 0 1px #080810,0 0 50px rgba(124,92,246,.1),0 24px 56px rgba(0,0,0,.7)}
```
Replace with:
```css
#phone{position:relative;border:1px solid rgba(255,255,255,0.12);border-radius:20px;overflow:hidden;background:#000;box-shadow:0 20px 60px rgba(0,0,0,.5)}
```

- [ ] **Step 4: Strip glow from buttons and interactive elements**

Find and replace the `.fmt-btn.on` rule:
```css
.fmt-btn.on{background:var(--acc);color:#fff;box-shadow:0 0 10px rgba(124,92,246,.4)}
```
→
```css
.fmt-btn.on{background:var(--acc);color:#fff}
```

Find and replace `.btn-primary`:
```css
.btn-primary{background:var(--acc);color:#fff;box-shadow:0 0 14px rgba(124,92,246,.3)}
.btn-primary:hover{background:#8b6cf6}
```
→
```css
.btn-primary{background:var(--acc);color:#fff}
.btn-primary:hover{background:#6672f5}
```

Find and replace `.el-btn:hover`:
```css
.el-btn:hover{border-color:var(--acc);color:var(--tx);background:var(--s3);transform:translateY(-1px);box-shadow:0 4px 12px rgba(124,92,246,.12)}
```
→
```css
.el-btn:hover{border-color:var(--b2);color:var(--tx);background:var(--s3)}
```

Find and replace `.tcard:hover`:
```css
.tcard:hover{border-color:var(--acc);transform:translateY(-1px);box-shadow:0 6px 16px rgba(124,92,246,.14)}
```
→
```css
.tcard:hover{border-color:var(--b2);background:var(--s3)}
```

- [ ] **Step 5: Update individual element icon styles**

Find the five `.ei-*` rules:
```css
.ei-v{background:linear-gradient(135deg,#1a3a6e,#0d1a38);color:#5b8cff}
.ei-b{background:linear-gradient(135deg,#131828,#080d16);color:#7070a0}
.ei-t{background:linear-gradient(135deg,#2e1560,#160a30);color:#a78bfa}
.ei-i{background:linear-gradient(135deg,#123220,#06180e);color:#34d399}
.ei-s{background:linear-gradient(135deg,#280d1a,#130608);color:#f87171}
```
Replace all five with a single neutral rule:
```css
.ei-v,.ei-b,.ei-t,.ei-i,.ei-s{background:var(--s3);color:var(--sub)}
```

- [ ] **Step 6: Replace emoji picker CSS**

Find the old emoji popup rules (from `#emo-popup` to `.ec:hover`):
```css
#emo-popup{position:fixed;z-index:300;background:var(--s1);border:1px solid var(--b2);border-radius:var(--r);padding:10px;width:224px;box-shadow:0 16px 48px rgba(0,0,0,.7);display:none}
#emo-popup.open{display:block}
.emo-search{width:100%;background:var(--s2);border:1px solid var(--b1);border-radius:var(--rs);color:var(--tx);font-family:'Inter',sans-serif;font-size:11px;padding:6px 9px;outline:none;margin-bottom:8px}
.emo-search:focus{border-color:var(--acc)}
.emo-grid{display:flex;flex-wrap:wrap;gap:2px;max-height:164px;overflow-y:auto}
.emo-grid::-webkit-scrollbar{width:3px}
.emo-grid::-webkit-scrollbar-thumb{background:var(--mut)}
.ec{font-size:20px;cursor:pointer;padding:4px;border-radius:5px;transition:.1s;line-height:1}
.ec:hover{background:var(--s3);transform:scale(1.1)}
```
Replace with:
```css
#emo-popup{position:fixed;z-index:300;background:var(--s1);border:1px solid var(--b2);border-radius:var(--r);width:280px;box-shadow:0 20px 60px rgba(0,0,0,.7);display:none;overflow:hidden;flex-direction:column}
#emo-popup.open{display:flex}
.emo-cats{display:flex;border-bottom:1px solid var(--b1);padding:4px;gap:2px;flex-shrink:0}
.emo-cat-btn{flex:1;padding:5px 0;border:none;border-radius:5px;cursor:pointer;background:transparent;font-size:17px;transition:.1s;opacity:.4;line-height:1}
.emo-cat-btn.on{background:var(--s3);opacity:1}
.emo-search{margin:6px;background:var(--s2);border:1px solid var(--b1);border-radius:var(--rs);color:var(--tx);font-family:'Inter',sans-serif;font-size:11px;padding:6px 9px;outline:none;flex-shrink:0;width:calc(100% - 12px)}
.emo-search:focus{border-color:var(--acc)}
.emo-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;max-height:190px;overflow-y:auto;padding:0 6px 6px;flex-shrink:0}
.emo-grid::-webkit-scrollbar{width:3px}
.emo-grid::-webkit-scrollbar-thumb{background:var(--mut);border-radius:2px}
.ec{width:36px;height:36px;cursor:pointer;padding:4px;border-radius:5px;transition:.1s;display:flex;align-items:center;justify-content:center}
.ec img{width:28px;height:28px;object-fit:contain}
.ec:hover{background:var(--s3)}
```

- [ ] **Step 7: Start the app and visually verify CSS changes**

```
python app.py
```
Open `http://localhost:5000` in a browser.

Expected:
- Background is near-black `#111113`, not purple-tinted
- Panels are dark gray, not purple
- Phone mockup has a thin hairline border (not thick `2.5px` purple border)
- Buttons have no glow/shadows
- Element icons in the Add Element grid are neutral gray (not colored gradients)

- [ ] **Step 8: Commit**

```bash
git add frontend/index.html
git commit -m "feat: linear-style CSS overhaul and twemoji CDN"
```

---

## Task 2: HTML Structure Cleanup

**Files:**
- Modify: `frontend/index.html` (HTML body only — no JS/CSS changes)

- [ ] **Step 1: Remove the notch element**

Find and delete this exact line in the `#phone` div:
```html
          <div class="notch"></div>
```

- [ ] **Step 2: Remove duplicate undo/redo from canvas toolbar**

Find these two toolbar buttons and the separator before them (inside `.cvs-toolbar`):
```html
          <div class="tsep"></div>
          <button class="tbar-btn" onclick="doUndo()">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="13" height="13"><path stroke-linecap="round" stroke-linejoin="round" d="M9 15 3 9m0 0 6-6M3 9h12a6 6 0 0 1 0 12h-3"/></svg>
          </button>
          <button class="tbar-btn" onclick="doRedo()">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="13" height="13"><path stroke-linecap="round" stroke-linejoin="round" d="m15 15 6-6m0 0-6-6m6 6H9a6 6 0 0 0 0 12h3"/></svg>
          </button>
```
Delete all four of those lines (the separator + two buttons). Undo/redo remain in the topbar.

- [ ] **Step 3: Add hidden video element to body**

Find the line:
```html
<input type="file" id="img-pick" accept="image/*" style="display:none" onchange="onImgFile(event)">
```
Add the hidden video element directly before it:
```html
<video id="preview-video" autoplay muted loop playsinline style="position:absolute;width:0;height:0;opacity:0;pointer-events:none"></video>
```

- [ ] **Step 4: Replace emoji popup HTML**

Find the entire emoji popup block:
```html
<!-- EMOJI POPUP -->
<div id="emo-popup">
  <input class="emo-search" id="emo-search" placeholder="Search emoji…" oninput="filterEmoji(this.value)">
  <div class="emo-grid" id="emo-grid"></div>
</div>
```
Replace with:
```html
<!-- EMOJI POPUP -->
<div id="emo-popup">
  <div class="emo-cats">
    <button class="emo-cat-btn on" data-cat="smileys" onclick="switchEmoCat('smileys')" title="Smileys">😀</button>
    <button class="emo-cat-btn" data-cat="people" onclick="switchEmoCat('people')" title="People">👋</button>
    <button class="emo-cat-btn" data-cat="fire" onclick="switchEmoCat('fire')" title="Trending">🔥</button>
    <button class="emo-cat-btn" data-cat="objects" onclick="switchEmoCat('objects')" title="Objects">🎮</button>
    <button class="emo-cat-btn" data-cat="symbols" onclick="switchEmoCat('symbols')" title="Symbols">❤️</button>
  </div>
  <input class="emo-search" id="emo-search" placeholder="Search emoji…" oninput="filterEmoji(this.value)">
  <div class="emo-grid" id="emo-grid"></div>
</div>
```

- [ ] **Step 5: Visually verify HTML changes**

Reload `http://localhost:5000`.

Expected:
- No pill-shaped notch at the top of the phone mockup
- Canvas toolbar shows only: `− 100% + | Fit | Grid | Snap ON` (no undo/redo icons)
- Right-clicking page source shows `<video id="preview-video">` in DOM
- Emoji popup (triggered by selecting a text layer → clicking "Insert Emoji") shows 5 category tab buttons at top

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat: remove notch, deduplicate toolbar, add video element and emoji categories"
```

---

## Task 3: Live Video Preview in Canvas

**Files:**
- Modify: `frontend/index.html` (JS section only)

These JS changes keep canvas history (`saveHist`/`loadFromJSON`) working correctly by refreshing the video layer after undo/redo.

- [ ] **Step 1: Add RAF loop helpers after the STATE block**

Find the state block comment and the line immediately after it:
```javascript
let downloadedVideoPath=null, downloadedVideoURL=null;
```
Add these two functions directly after that line:
```javascript
let _rafId=null;
function startVideoLoop(){
  if(_rafId!==null)return;
  (function tick(){cv.renderAll();_rafId=fabric.util.requestAnimFrame(tick);})();
}
function stopVideoLoop(){
  if(_rafId!==null){fabric.util.cancelAnimFrame(_rafId);_rafId=null;}
}
```

- [ ] **Step 2: Replace `addVideo()`**

Find the entire current `addVideo` function:
```javascript
function addVideo(){
  const {w,h}=FMT[fmt],is16=fmt==='9:16';
  const vh=is16?Math.round(h*.32):Math.round(h*.6);
  const r=new fabric.Rect({left:0,top:Math.round((h-vh)/2),width:w,height:vh,fill:'#1a3a6a',stroke:'rgba(91,140,255,.4)',strokeWidth:1,rx:3,ry:3});
  const t=new fabric.Text('[VIDEO]',{left:w/2,top:Math.round((h-vh)/2)+vh/2,originX:'center',originY:'center',fontSize:13,fill:'rgba(91,140,255,.7)',fontFamily:'Inter',fontWeight:'700',selectable:false,evented:false});
  const g=new fabric.Group([r,t],{_type:'video',_label:'Video Layer',_fit:'contain'});
  cv.add(g);cv.setActiveObject(g);cv.renderAll();
}
```
Replace with:
```javascript
function addVideo(){
  const {w,h}=FMT[fmt],is16=fmt==='9:16';
  const vh=is16?Math.round(h*.32):Math.round(h*.6);
  const vTop=Math.round((h-vh)/2);
  const vidEl=document.getElementById('preview-video');
  if(downloadedVideoURL&&vidEl.readyState>=1){
    const img=new fabric.Image(vidEl,{
      left:0,top:vTop,objectCaching:false,
      _type:'video',_label:'Video Layer',_fit:'contain',
    });
    const sx=w/(vidEl.videoWidth||w),sy=vh/(vidEl.videoHeight||vh);
    const s=Math.min(sx,sy);
    img.set({scaleX:s,scaleY:s});
    img.set({left:Math.round((w-img.getScaledWidth())/2),top:Math.round(vTop+(vh-img.getScaledHeight())/2)});
    cv.add(img);cv.setActiveObject(img);
    startVideoLoop();
  } else {
    const r=new fabric.Rect({left:0,top:vTop,width:w,height:vh,fill:'#1a1a1d',stroke:'rgba(255,255,255,0.08)',strokeWidth:1,rx:3,ry:3});
    const t=new fabric.Text('[VIDEO]',{left:w/2,top:vTop+vh/2,originX:'center',originY:'center',fontSize:12,fill:'rgba(255,255,255,0.2)',fontFamily:'Inter',fontWeight:'600',selectable:false,evented:false});
    const g=new fabric.Group([r,t],{_type:'video',_label:'Video Layer',_fit:'contain'});
    cv.add(g);cv.setActiveObject(g);
  }
  cv.renderAll();
}
```

- [ ] **Step 3: Replace `updateTplPreviews()`**

Find the current function:
```javascript
function updateTplPreviews(url){
  downloadedVideoURL=url;
  document.querySelectorAll('.tpl-vid').forEach(v=>{v.src=url;v.classList.add('visible');v.play().catch(()=>{});});
}
```
Replace with:
```javascript
function updateTplPreviews(url){
  downloadedVideoURL=url;
  const vidEl=document.getElementById('preview-video');
  vidEl.src=url;
  document.querySelectorAll('.tpl-vid').forEach(v=>{v.src=url;v.classList.add('visible');v.play().catch(()=>{});});
  function swapVideoLayer(){
    vidEl.play().catch(()=>{});
    if(!cv)return;
    cv.getObjects().filter(o=>o._type==='video').forEach(o=>cv.remove(o));
    addVideo();saveHist();
  }
  if(vidEl.readyState>=1)swapVideoLayer();
  else vidEl.addEventListener('loadedmetadata',swapVideoLayer,{once:true});
}
```

- [ ] **Step 4: Add `refreshVideoLayers()` and update undo/redo**

Find `doUndo`:
```javascript
function doUndo(){
  if(histIdx<=0)return;histIdx--;
  histLock=true;cv.loadFromJSON(hist[histIdx],()=>{cv.renderAll();syncLayers();histLock=false;});
}
function doRedo(){
  if(histIdx>=hist.length-1)return;histIdx++;
  histLock=true;cv.loadFromJSON(hist[histIdx],()=>{cv.renderAll();syncLayers();histLock=false;});
}
```
Replace with:
```javascript
function refreshVideoLayers(){
  if(!downloadedVideoURL)return;
  const vidEl=document.getElementById('preview-video');
  if(vidEl.readyState<1)return;
  const toReplace=cv.getObjects().filter(o=>o._type==='video');
  if(toReplace.length>0){toReplace.forEach(o=>cv.remove(o));addVideo();}
}
function doUndo(){
  if(histIdx<=0)return;histIdx--;
  histLock=true;cv.loadFromJSON(hist[histIdx],()=>{cv.renderAll();syncLayers();refreshVideoLayers();histLock=false;});
}
function doRedo(){
  if(histIdx>=hist.length-1)return;histIdx++;
  histLock=true;cv.loadFromJSON(hist[histIdx],()=>{cv.renderAll();syncLayers();refreshVideoLayers();histLock=false;});
}
```

- [ ] **Step 5: Fix border-radius in `initCanvas` and `setFmt`**

In `initCanvas`, find:
```javascript
phone.style.borderRadius=f==='9:16'?'28px':'16px';
```
Replace with:
```javascript
phone.style.borderRadius=f==='9:16'?'20px':'12px';
```

In `setFmt`, find the same line (there's one occurrence there too):
```javascript
phone.style.borderRadius=f==='9:16'?'28px':'16px';
```
Replace with:
```javascript
phone.style.borderRadius=f==='9:16'?'20px':'12px';
```

- [ ] **Step 6: Test live video preview**

Start the app (`python app.py`), open `http://localhost:5000`.

1. Click "Download Video" in the sidebar, paste any Twitter/YouTube/TikTok URL, click Download.
2. While downloading, verify the canvas still shows the `[VIDEO]` placeholder (subtle dark rect, no blue).
3. When download completes: the canvas video layer should immediately update to show live video frames from the actual footage. Text/shape layers overlay correctly on top.
4. Move or scale the video layer — it stays live.
5. Click Undo — canvas reloads, video layer is re-attached and still shows frames (not a broken placeholder).
6. Switch format (9:16 → 1:1) — phone gets `border-radius: 12px`, canvas resets.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat: live video frame preview in canvas with RAF loop and undo-safe refresh"
```

---

## Task 4: Twemoji Emoji Picker

**Files:**
- Modify: `frontend/index.html` (JS section — replace emoji block)

- [ ] **Step 1: Replace the entire emoji JS block**

Find the section starting with `// ── EMOJI` and ending before `// ── CANVAS INIT`:

```javascript
// ── EMOJI ──────────────────────────────────────────────────────────────────
const ALL_EMOJI=[
  ...
];
let emoOpen=false;
function renderEmoGrid(filter=''){
  document.getElementById('emo-grid').innerHTML=
    (filter?ALL_EMOJI.filter(e=>e.includes(filter)):ALL_EMOJI)
    .map(e=>`<span class="ec" onclick="insertEmoji('${e}')">${e}</span>`).join('');
}
function filterEmoji(v){renderEmoGrid(v);}
renderEmoGrid();

function toggleEmojiPicker(triggerEl){
  const popup=document.getElementById('emo-popup');
  if(emoOpen){popup.classList.remove('open');emoOpen=false;return;}
  const r=triggerEl.getBoundingClientRect();
  popup.style.left=r.left+'px';
  popup.style.top=(r.bottom+6)+'px';
  popup.classList.add('open');emoOpen=true;
  document.getElementById('emo-search').value='';renderEmoGrid();
}
document.addEventListener('click',e=>{
  if(emoOpen&&!e.target.closest('#emo-popup')&&!e.target.closest('.emo-btn')){
    document.getElementById('emo-popup').classList.remove('open');emoOpen=false;
  }
});
function insertEmoji(emoji){
  const obj=cv?.getActiveObject();
  if(!obj||obj._type!=='text')return;
  if(obj.isEditing){obj.insertChars(emoji);}
  else{
    const pos=(obj===lastTextObj&&lastTextPos!==null)?lastTextPos:obj.text.length;
    obj.text=obj.text.slice(0,pos)+emoji+obj.text.slice(pos);
    lastTextPos=pos+[...emoji].length; lastTextObj=obj;
  }
  cv.renderAll();
  document.getElementById('emo-popup').classList.remove('open');emoOpen=false;
}
```

Replace the entire block with:

```javascript
// ── EMOJI (TWEMOJI) ────────────────────────────────────────────────────────
const EMOJI_DATA={
  smileys:[
    {e:'😀',n:'grinning'},{e:'😂',n:'joy'},{e:'🤣',n:'rofl'},
    {e:'😭',n:'crying'},{e:'😅',n:'sweat smile'},{e:'😍',n:'heart eyes'},
    {e:'🥲',n:'smiling tear'},{e:'😎',n:'sunglasses'},{e:'🤯',n:'mind blown'},
    {e:'😤',n:'triumph'},{e:'😡',n:'angry'},{e:'🥶',n:'cold face'},
    {e:'😱',n:'scream'},{e:'🤭',n:'hand over mouth'},{e:'😏',n:'smirk'},
    {e:'🤔',n:'thinking'},{e:'😈',n:'smiling devil'},{e:'💀',n:'skull'},
    {e:'☠️',n:'skull crossbones'},{e:'👻',n:'ghost'},{e:'🤡',n:'clown'},
    {e:'🤖',n:'robot'},{e:'👾',n:'alien monster'},{e:'🫠',n:'melting'},
  ],
  people:[
    {e:'👀',n:'eyes'},{e:'👁️',n:'eye'},{e:'🫡',n:'saluting'},
    {e:'👏',n:'clapping'},{e:'💪',n:'muscle'},{e:'🤝',n:'handshake'},
    {e:'👍',n:'thumbs up'},{e:'👎',n:'thumbs down'},{e:'🙏',n:'pray'},
    {e:'🫶',n:'heart hands'},{e:'🤌',n:'pinched fingers'},{e:'✌️',n:'victory'},
    {e:'🤞',n:'crossed fingers'},{e:'🫵',n:'point at you'},{e:'☝️',n:'index up'},
    {e:'🧠',n:'brain'},{e:'💅',n:'nail polish'},{e:'🦾',n:'mechanical arm'},
  ],
  fire:[
    {e:'🔥',n:'fire'},{e:'💥',n:'explosion'},{e:'✨',n:'sparkles'},
    {e:'⚡',n:'lightning'},{e:'🌊',n:'wave'},{e:'❄️',n:'snowflake'},
    {e:'💯',n:'hundred'},{e:'🎯',n:'bullseye'},{e:'🏆',n:'trophy'},
    {e:'🥇',n:'gold medal'},{e:'👑',n:'crown'},{e:'💎',n:'diamond'},
    {e:'💰',n:'money bag'},{e:'🚀',n:'rocket'},{e:'⭐',n:'star'},
    {e:'🌟',n:'glowing star'},{e:'💫',n:'dizzy'},{e:'🌈',n:'rainbow'},
  ],
  objects:[
    {e:'🥊',n:'boxing glove'},{e:'⚽',n:'soccer'},{e:'🏀',n:'basketball'},
    {e:'🎮',n:'video game'},{e:'🕹️',n:'joystick'},{e:'🎲',n:'dice'},
    {e:'🎬',n:'clapper board'},{e:'🎤',n:'microphone'},{e:'🎧',n:'headphones'},
    {e:'🎵',n:'music note'},{e:'🎶',n:'notes'},{e:'🃏',n:'joker'},
    {e:'🎰',n:'slot machine'},{e:'📱',n:'phone'},{e:'💻',n:'laptop'},
    {e:'🎁',n:'gift'},{e:'🍕',n:'pizza'},{e:'☕',n:'coffee'},
  ],
  symbols:[
    {e:'❤️',n:'red heart'},{e:'🧡',n:'orange heart'},{e:'💛',n:'yellow heart'},
    {e:'💚',n:'green heart'},{e:'💙',n:'blue heart'},{e:'💜',n:'purple heart'},
    {e:'🖤',n:'black heart'},{e:'🤍',n:'white heart'},{e:'🩷',n:'pink heart'},
    {e:'‼️',n:'double exclamation'},{e:'⁉️',n:'exclamation question'},
    {e:'❓',n:'question'},{e:'❗',n:'exclamation'},{e:'✅',n:'check mark'},
    {e:'❌',n:'cross mark'},{e:'⚠️',n:'warning'},{e:'💤',n:'zzz'},
    {e:'🆒',n:'cool'},{e:'🔞',n:'no under 18'},{e:'🎉',n:'party popper'},
  ],
};

let emoOpen=false, emoActiveCat='smileys', emoSearchVal='';

function twemojiUrl(emoji){
  const cp=twemoji.convert.toCodePoint(emoji);
  return `https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/72x72/${cp}.png`;
}

function renderEmoGrid(){
  const grid=document.getElementById('emo-grid');
  let list;
  if(emoSearchVal){
    list=Object.values(EMOJI_DATA).flat()
      .filter(({e,n})=>n.toLowerCase().includes(emoSearchVal.toLowerCase()));
  } else {
    list=EMOJI_DATA[emoActiveCat]||[];
  }
  grid.innerHTML=list.map(({e})=>
    `<div class="ec" onclick="insertEmoji('${e}')"><img src="${twemojiUrl(e)}" alt="${e}" loading="lazy" onerror="this.parentNode.textContent='${e}'"></div>`
  ).join('');
}

function filterEmoji(v){emoSearchVal=v;renderEmoGrid();}

function switchEmoCat(cat){
  emoActiveCat=cat;emoSearchVal='';
  document.getElementById('emo-search').value='';
  document.querySelectorAll('.emo-cat-btn').forEach(b=>b.classList.remove('on'));
  document.querySelector(`.emo-cat-btn[data-cat="${cat}"]`).classList.add('on');
  renderEmoGrid();
}

function toggleEmojiPicker(triggerEl){
  const popup=document.getElementById('emo-popup');
  if(emoOpen){popup.classList.remove('open');emoOpen=false;return;}
  const r=triggerEl.getBoundingClientRect();
  popup.style.left=r.left+'px';
  popup.style.top=(r.bottom+6)+'px';
  popup.classList.add('open');emoOpen=true;
  document.getElementById('emo-search').value='';
  emoSearchVal='';renderEmoGrid();
}
document.addEventListener('click',e=>{
  if(emoOpen&&!e.target.closest('#emo-popup')&&!e.target.closest('.emo-btn')){
    document.getElementById('emo-popup').classList.remove('open');emoOpen=false;
  }
});

function insertEmoji(emoji){
  const url=twemojiUrl(emoji);
  fabric.Image.fromURL(url,function(img){
    const {w,h}=FMT[fmt];
    const size=Math.round(Math.min(w,h)*0.18);
    img.set({
      left:Math.round(w/2-size/2),
      top:Math.round(h/2-size/2),
      scaleX:size/img.width,
      scaleY:size/img.height,
      _type:'emoji',
      _label:emoji,
    });
    cv.add(img);cv.setActiveObject(img);cv.renderAll();
    syncLayers();saveHist();
  },{crossOrigin:'anonymous'});
  document.getElementById('emo-popup').classList.remove('open');emoOpen=false;
}

renderEmoGrid();
```

- [ ] **Step 2: Update emoji label in right panel**

Find the label in `updateProps`:
```javascript
    <div class="psec"><div class="psec-title">iOS Emoji</div>
      <button class="emo-btn" onclick="toggleEmojiPicker(this)">😊 Insert Emoji into Text</button>
      <p class="pnote">Double-click text on canvas to position cursor, then pick an emoji.</p>
    </div>`;
```
Replace with:
```javascript
    <div class="psec"><div class="psec-title">Emoji</div>
      <button class="emo-btn" onclick="toggleEmojiPicker(this)">😊 Add iOS Emoji to Canvas</button>
      <p class="pnote">Emoji are added as resizable image layers using Apple-style Twemoji.</p>
    </div>`;
```

- [ ] **Step 3: Test the Twemoji picker**

Reload `http://localhost:5000`.

1. Add a text layer (click "Text" in the left panel).
2. With the text layer selected, look at the right panel → "Emoji" section → click "Add iOS Emoji to Canvas".
3. The picker opens. Verify:
   - 5 category tab buttons across the top
   - Grid shows iOS-style Twemoji image tiles (not Windows system emoji)
   - Clicking a category tab switches the grid
   - Typing in the search box filters by name (e.g., "fire" shows 🔥 and related)
4. Click any emoji. It closes the picker and adds an iOS-style emoji image to the canvas as an independent, movable/resizable element.
5. Verify the emoji layer appears in the Layers panel on the left.
6. Click Undo — emoji layer is removed. Click Redo — it comes back.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat: twemoji picker with categories, adds emoji as canvas image objects"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Live video frame in canvas (Task 3 `addVideo` rewrite + RAF loop)
- [x] Template cards still show video previews (Task 3 `updateTplPreviews`)
- [x] Undo/redo restores video layer (Task 3 `refreshVideoLayers`)
- [x] Twemoji CDN loaded (Task 1 script tag)
- [x] Twemoji picker with categories and search (Task 4)
- [x] Emoji adds as canvas image, not into text (Task 4 `insertEmoji`)
- [x] Linear CSS variables (Task 1)
- [x] Phone hairline border, no notch (Task 1 CSS + Task 2 HTML)
- [x] No button glows/shadows (Task 1)
- [x] Element icon gradients removed (Task 1)
- [x] Duplicate toolbar undo/redo removed (Task 2)

**Placeholders:** None.

**Type consistency:** `_type: 'video'`, `_type: 'emoji'`, `_type: 'text'` — consistent with `canvasToTemplate()` serialization and layer panel color lookup (`LC`). Add `'emoji':'#f59e0b'` to `LC` so emoji layers show a distinctive dot in the layer list.

**Missed item — fix `LC`:**

In Task 4, after the `renderEmoGrid()` call at the bottom of the emoji block, also find the `LC` constant:
```javascript
const LC={video:'#5b8cff',blur:'#666',text:'#a78bfa',image:'#34d399',shape:'#f87171'};
```
And add `emoji` to it:
```javascript
const LC={video:'#5b8cff',blur:'#666',text:'#a78bfa',image:'#34d399',shape:'#f87171',emoji:'#f59e0b'};
```
Include this change in the Task 4 commit.
