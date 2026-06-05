# Font Picker + Dual-Tab Emoji Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a searchable Google Fonts picker to text layers, and split the emoji popup into a "My Emojis" tab (local EmojiPack PNGs) and a "Twemoji" tab (existing behavior).

**Architecture:** All changes are in `frontend/index.html`. A floating `#fp-panel` (like the existing emoji popup) is placed at the document root and positioned via `getBoundingClientRect`. The emoji popup gains two top-level tab buttons; existing Twemoji content moves inside its tab. A static `EMOJIPACK_FILES` array holds all 759 local PNG paths. The `GOOGLE_FONTS` array lists 150 fonts loaded via one `<link>` tag.

**Tech Stack:** Fabric.js 5.3.1, vanilla JS/HTML/CSS, Google Fonts CSS2 API, Twemoji 14.0.2 (kept for Twemoji tab + `_renderChar`)

---

## Task 1: Add CSS for font picker and emoji tabs

**Files:**
- Modify: `frontend/index.html` — add CSS inside the `<style>` block, before the closing `</style>` tag

- [ ] **Step 1: Find the exact closing `</style>` tag line**

  In `frontend/index.html`, the `<style>` block closes on the line containing `@media(prefers-reduced-motion:reduce){.t-modal{transition:none!important}}` followed by other rules ending in `</style>`. The last CSS rule before `</style>` is around the `.sfx-picker-*` and `#ctx-menu` rules. Add the new CSS immediately before the closing `</style>` tag.

- [ ] **Step 2: Insert font picker + emoji tab CSS**

  Find the line:
  ```css
  @media(prefers-reduced-motion:reduce){.t-modal{transition:none!important}}
  ```
  Add **after** it (still inside `<style>`):
  ```css
  /* ─── FONT PICKER ──────────────────────────────────────── */
  .fp-wrap{position:relative;flex:1}
  .fp-trigger{width:100%;padding:5px 8px;background:var(--s2);border:1px solid var(--b1);border-radius:var(--rs);color:var(--tx);font-size:11px;text-align:left;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:4px;transition:.1s;overflow:hidden}
  .fp-trigger:hover{border-color:var(--b2)}
  .fp-trigger.open{border-color:var(--acc)}
  .fp-trigger-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
  #fp-panel{position:fixed;background:var(--s1);border:1px solid var(--b2);border-radius:var(--rs);z-index:300;box-shadow:0 8px 24px rgba(0,0,0,.6);display:none;flex-direction:column;min-width:180px}
  #fp-panel.open{display:flex}
  #fp-search{background:var(--s2);border:none;border-bottom:1px solid var(--b1);color:var(--tx);font-size:11px;padding:7px 10px;outline:none;font-family:'Inter',sans-serif;width:100%;border-radius:var(--rs) var(--rs) 0 0}
  #fp-list{max-height:200px;overflow-y:auto}
  #fp-list::-webkit-scrollbar{width:3px}
  #fp-list::-webkit-scrollbar-thumb{background:var(--mut);border-radius:2px}
  .fp-item{padding:5px 10px;font-size:12px;cursor:pointer;color:var(--tx);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .fp-item:hover{background:var(--s3)}
  .fp-item.on{color:var(--acc);background:var(--accdim)}
  /* ─── EMOJI TABS ────────────────────────────────────────── */
  .emo-tabs{display:flex;border-bottom:1px solid var(--b1);flex-shrink:0}
  .emo-tab{flex:1;padding:7px 0;font-size:11px;font-weight:700;cursor:pointer;background:transparent;border:none;color:var(--sub);border-bottom:2px solid transparent;transition:.12s;font-family:'Inter',sans-serif}
  .emo-tab.on{color:var(--acc);border-bottom-color:var(--acc)}
  .emo-tab-body{display:none;flex-direction:column;overflow:hidden}
  .emo-tab-body.on{display:flex}
  .myemo-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;max-height:220px;overflow-y:auto;padding:6px;flex-shrink:0}
  .myemo-grid::-webkit-scrollbar{width:3px}
  .myemo-grid::-webkit-scrollbar-thumb{background:var(--mut);border-radius:2px}
  ```

- [ ] **Step 3: Commit**
  ```bash
  git add frontend/index.html
  git commit -m "style: add font picker and emoji tab CSS"
  ```

---

## Task 2: Replace Google Fonts link + add GOOGLE_FONTS array

**Files:**
- Modify: `frontend/index.html` — replace line 8 (the `<link>` for Inter), add JS const

- [ ] **Step 1: Replace the font `<link>` tag**

  Find (line 8):
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  ```
  Replace with:
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Roboto:wght@400;700;900&family=Open+Sans:wght@400;700;900&family=Montserrat:wght@400;700;900&family=Lato:wght@400;700;900&family=Poppins:wght@400;700;900&family=Nunito:wght@400;700;900&family=Raleway:wght@400;700;900&family=Ubuntu:wght@400;700&family=Oswald:wght@400;700&family=Work+Sans:wght@400;700;900&family=DM+Sans:wght@400;700;900&family=Mulish:wght@400;700;900&family=Barlow:wght@400;700;900&family=Rubik:wght@400;700;900&family=Quicksand:wght@400;700&family=Space+Grotesk:wght@400;700&family=Josefin+Sans:wght@400;700&family=Cabin:wght@400;700&family=Exo+2:wght@400;700;900&family=IBM+Plex+Sans:wght@400;700&family=Urbanist:wght@400;700;900&family=Karla:wght@400;700;900&family=Jost:wght@400;700;900&family=Manrope:wght@400;700;900&family=Figtree:wght@400;700;900&family=Plus+Jakarta+Sans:wght@400;700;900&family=Outfit:wght@400;700;900&family=Sora:wght@400;700&family=Lexend:wght@400;700;900&family=Archivo:wght@400;700;900&family=Asap:wght@400;700&family=Chivo:wght@400;700;900&family=Dosis:wght@400;700;900&family=Fira+Sans:wght@400;700;900&family=Hind:wght@400;700&family=Noto+Sans:wght@400;700&family=Nunito+Sans:wght@400;700;900&family=Questrial&family=Rajdhani:wght@400;700&family=Signika:wght@400;700&family=Titillium+Web:wght@400;700;900&family=Varela+Round&family=Khand:wght@400;700&family=Overpass:wght@400;700;900&family=Source+Sans+3:wght@400;700;900&family=PT+Sans:wght@400;700&family=Merriweather:wght@400;700;900&family=Playfair+Display:wght@400;700;900&family=Lora:wght@400;700&family=Crimson+Text:wght@400;700&family=EB+Garamond:wght@400;700;900&family=Cormorant+Garamond:wght@400;700&family=Spectral:wght@400;700&family=Libre+Baskerville:wght@400;700&family=Bitter:wght@400;700;900&family=Libre+Franklin:wght@400;700;900&family=Zilla+Slab:wght@400;700&family=Rokkitt:wght@400;700;900&family=Source+Serif+4:wght@400;700;900&family=Bebas+Neue&family=Anton&family=Archivo+Black&family=Fjalla+One&family=Righteous&family=Teko:wght@400;700&family=Russo+One&family=Passion+One:wght@400;900&family=Yanone+Kaffeesatz:wght@400;700&family=Hammersmith+One&family=Alfa+Slab+One&family=Abril+Fatface&family=Gravitas+One&family=Boogaloo&family=Fugaz+One&family=Patua+One&family=Contrail+One&family=Cinzel:wght@400;700;900&family=Comfortaa:wght@400;700&family=Exo:wght@400;700;900&family=Sigmar+One&family=Yeseva+One&family=Bangers&family=Chewy&family=Carter+One&family=Fredoka+One&family=Permanent+Marker&family=Dancing+Script:wght@400;700&family=Pacifico&family=Lobster&family=Kaushan+Script&family=Sacramento&family=Great+Vibes&family=Satisfy&family=Yellowtail&family=Caveat:wght@400;700&family=Shadows+Into+Light&family=Indie+Flower&family=Gochi+Hand&family=Patrick+Hand&family=Amatic+SC:wght@400;700&family=Architects+Daughter&family=Rock+Salt&family=Reenie+Beanie&family=Courgette&family=Cookie&family=Marck+Script&family=Tangerine:wght@400;700&family=Allura&family=Parisienne&family=Space+Mono:wght@400;700&family=Inconsolata:wght@400;700&family=Fira+Code:wght@400;700&family=IBM+Plex+Mono:wght@400;700&family=Source+Code+Pro:wght@400;700&family=Share+Tech+Mono&family=Comic+Neue:wght@400;700&family=Varela&family=Economica:wght@400;700&family=Philosopher:wght@400;700&family=Electrolize&family=Jura:wght@400;700&family=Kreon:wght@400;700&family=Lusitana:wght@400;700&family=Proza+Libre:wght@400;700&family=Ruda:wght@400;700;900&family=Volkhov:wght@400;700&family=Gudea:wght@400;700&family=Oxygen:wght@400;700&family=Coda:wght@400;900&family=Cuprum:wght@400;700&family=Nanum+Gothic:wght@400;700&family=Sarabun:wght@400;700;900&display=swap" rel="stylesheet">
  ```

- [ ] **Step 2: Add `GOOGLE_FONTS` array**

  Find the `// ── EMOJI (TWEMOJI)` comment line and insert the following **before** it:
  ```javascript
  // ── GOOGLE FONTS ───────────────────────────────────────────────────────────
  const GOOGLE_FONTS=[
    'Inter','Roboto','Open Sans','Montserrat','Lato','Poppins','Nunito','Raleway',
    'Ubuntu','Oswald','Work Sans','DM Sans','Mulish','Barlow','Rubik','Quicksand',
    'Space Grotesk','Josefin Sans','Cabin','Exo 2','IBM Plex Sans','Urbanist',
    'Karla','Jost','Manrope','Figtree','Plus Jakarta Sans','Outfit','Sora','Lexend',
    'Archivo','Asap','Chivo','Dosis','Fira Sans','Hind','Noto Sans','Nunito Sans',
    'Questrial','Rajdhani','Signika','Titillium Web','Varela Round','Khand',
    'Overpass','Source Sans 3','PT Sans',
    'Merriweather','Playfair Display','Lora','Crimson Text','EB Garamond',
    'Cormorant Garamond','Spectral','Libre Baskerville','Bitter','Libre Franklin',
    'Zilla Slab','Rokkitt','Source Serif 4',
    'Bebas Neue','Anton','Archivo Black','Fjalla One','Righteous','Teko',
    'Russo One','Passion One','Yanone Kaffeesatz','Hammersmith One','Alfa Slab One',
    'Abril Fatface','Gravitas One','Boogaloo','Fugaz One','Patua One',
    'Contrail One','Cinzel','Comfortaa','Exo','Sigmar One','Yeseva One',
    'Bangers','Chewy','Carter One','Fredoka One','Permanent Marker',
    'Dancing Script','Pacifico','Lobster','Kaushan Script','Sacramento',
    'Great Vibes','Satisfy','Yellowtail','Caveat','Shadows Into Light',
    'Indie Flower','Gochi Hand','Patrick Hand','Amatic SC','Architects Daughter',
    'Rock Salt','Reenie Beanie','Courgette','Cookie','Marck Script','Tangerine',
    'Allura','Parisienne',
    'Space Mono','Inconsolata','Fira Code','IBM Plex Mono','Source Code Pro',
    'Share Tech Mono',
    'Comic Neue','Varela','Economica','Philosopher','Electrolize','Jura',
    'Kreon','Lusitana','Proza Libre','Ruda','Volkhov','Gudea','Oxygen',
    'Coda','Cuprum','Nanum Gothic','Sarabun',
  ];
  ```

- [ ] **Step 3: Open `frontend/index.html` in a browser and open DevTools → Network → filter by "fonts.googleapis" to confirm the link resolves without 400 errors**

- [ ] **Step 4: Commit**
  ```bash
  git add frontend/index.html
  git commit -m "feat: load 150 Google Fonts and add GOOGLE_FONTS array"
  ```

---

## Task 3: Add `EMOJIPACK_FILES` array

**Files:**
- Modify: `frontend/index.html` — add JS const after `GOOGLE_FONTS`

- [ ] **Step 1: Add the `EMOJIPACK_FILES` array immediately after the `GOOGLE_FONTS` array**

  Insert this block right after the closing `];` of `GOOGLE_FONTS`:
  ```javascript
  const EMOJIPACK_FILES=[
    '../EmojiPack/1st-place-medal_1f947.png',
    '../EmojiPack/accordion_1fa97.png',
    '../EmojiPack/adhesive-bandage_1fa79.png',
    '../EmojiPack/admission-tickets_1f39f-fe0f.png',
    '../EmojiPack/airplane_2708-fe0f.png',
    '../EmojiPack/alarm-clock_23f0.png',
    '../EmojiPack/alembic_2697-fe0f.png',
    '../EmojiPack/ambulance_1f691.png',
    '../EmojiPack/american-football_1f3c8.png',
    '../EmojiPack/amphora_1f3fa.png',
    '../EmojiPack/anchor_2693.png',
    '../EmojiPack/angry-face-with-horns_1f47f.png',
    '../EmojiPack/anxious-face-with-sweat_1f630.png',
    '../EmojiPack/artist-palette_1f3a8.png',
    '../EmojiPack/atm-sign_1f3e7.png',
    '../EmojiPack/automobile_1f697.png',
    '../EmojiPack/axe_1fa93.png',
    '../EmojiPack/baby-symbol_1f6bc.png',
    '../EmojiPack/baby_1f476.png',
    '../EmojiPack/back-arrow_1f519.png',
    '../EmojiPack/backhand-index-pointing-down_1f447.png',
    '../EmojiPack/backhand-index-pointing-left_1f448.png',
    '../EmojiPack/backhand-index-pointing-right_1f449.png',
    '../EmojiPack/backhand-index-pointing-up_1f446.png',
    '../EmojiPack/backpack_1f392.png',
    '../EmojiPack/badminton_1f3f8.png',
    '../EmojiPack/baggage-claim_1f6c4.png',
    '../EmojiPack/baguette-bread_1f956.png',
    '../EmojiPack/balance-scale_2696-fe0f.png',
    '../EmojiPack/balloon_1f388.png',
    '../EmojiPack/bank_1f3e6.png',
    '../EmojiPack/bar-chart_1f4ca.png',
    '../EmojiPack/barber-pole_1f488.png',
    '../EmojiPack/baseball_26be.png',
    '../EmojiPack/basket_1f9fa.png',
    '../EmojiPack/basketball_1f3c0.png',
    '../EmojiPack/bat_1f987.png',
    '../EmojiPack/bathtub_1f6c1.png',
    '../EmojiPack/battery_1f50b.png',
    '../EmojiPack/beach-with-umbrella_1f3d6-fe0f.png',
    '../EmojiPack/beaming-face-with-smiling-eyes_1f601.png',
    '../EmojiPack/bear_1f43b.png',
    '../EmojiPack/bed_1f6cf-fe0f.png',
    '../EmojiPack/bell_1f514.png',
    '../EmojiPack/bellhop-bell_1f6ce-fe0f.png',
    '../EmojiPack/bikini_1f459.png',
    '../EmojiPack/billed-cap_1f9e2.png',
    '../EmojiPack/biohazard_2623-fe0f.png',
    '../EmojiPack/black-circle_26ab.png',
    '../EmojiPack/black-flag_1f3f4.png',
    '../EmojiPack/black-heart_1f5a4.png',
    '../EmojiPack/black-large-square_2b1b.png',
    '../EmojiPack/blue-book_1f4d8.png',
    '../EmojiPack/blue-heart_1f499.png',
    '../EmojiPack/books_1f4da.png',
    '../EmojiPack/bottle-with-popping-cork_1f37e.png',
    '../EmojiPack/bouquet_1f490.png',
    '../EmojiPack/bow-and-arrow_1f3f9.png',
    '../EmojiPack/boxing-glove_1f94a.png',
    '../EmojiPack/briefcase_1f4bc.png',
    '../EmojiPack/broom_1f9f9.png',
    '../EmojiPack/brown-heart_1f90e.png',
    '../EmojiPack/bubbles_1fae7.png',
    '../EmojiPack/building-construction_1f3d7-fe0f.png',
    '../EmojiPack/butterfly_1f98b.png',
    '../EmojiPack/cactus_1f335.png',
    '../EmojiPack/calendar_1f4c5.png',
    '../EmojiPack/call-me-hand_1f919.png',
    '../EmojiPack/camping_1f3d5-fe0f.png',
    '../EmojiPack/candle_1f56f-fe0f.png',
    '../EmojiPack/candy_1f36c.png',
    '../EmojiPack/canoe_1f6f6.png',
    '../EmojiPack/card-file-box_1f5c3-fe0f.png',
    '../EmojiPack/carousel-horse_1f3a0.png',
    '../EmojiPack/carpentry-saw_1fa9a.png',
    '../EmojiPack/castle_1f3f0.png',
    '../EmojiPack/chains_26d3-fe0f.png',
    '../EmojiPack/chair_1fa91.png',
    '../EmojiPack/chart-decreasing_1f4c9.png',
    '../EmojiPack/chart-increasing-with-yen_1f4b9.png',
    '../EmojiPack/chart-increasing_1f4c8.png',
    '../EmojiPack/check-mark-button_2705.png',
    '../EmojiPack/cherry-blossom_1f338.png',
    '../EmojiPack/chicken_1f414.png',
    '../EmojiPack/children-crossing_1f6b8.png',
    '../EmojiPack/chocolate-bar_1f36b.png',
    '../EmojiPack/christmas-tree_1f384.png',
    '../EmojiPack/cinema_1f3a6.png',
    '../EmojiPack/circus-tent_1f3aa.png',
    '../EmojiPack/clapper-board_1f3ac.png',
    '../EmojiPack/clapping-hands_1f44f.png',
    '../EmojiPack/classical-building_1f3db-fe0f.png',
    '../EmojiPack/clinking-beer-mugs_1f37b.png',
    '../EmojiPack/clinking-glasses_1f942.png',
    '../EmojiPack/clipboard_1f4cb.png',
    '../EmojiPack/closed-book_1f4d5.png',
    '../EmojiPack/cloud-with-lightning-and-rain_26c8-fe0f.png',
    '../EmojiPack/cloud-with-lightning_1f329-fe0f.png',
    '../EmojiPack/cloud_2601-fe0f.png',
    '../EmojiPack/clown-face_1f921.png',
    '../EmojiPack/coat_1f9e5.png',
    '../EmojiPack/cockroach_1fab3.png',
    '../EmojiPack/coffin_26b0-fe0f.png',
    '../EmojiPack/coin_1fa99.png',
    '../EmojiPack/cold-face_1f976.png',
    '../EmojiPack/collision_1f4a5.png',
    '../EmojiPack/computer-disk_1f4bd.png',
    '../EmojiPack/confetti-ball_1f38a.png',
    '../EmojiPack/construction_1f6a7.png',
    '../EmojiPack/cookie_1f36a.png',
    '../EmojiPack/cooking_1f373.png',
    '../EmojiPack/couch-and-lamp_1f6cb-fe0f.png',
    '../EmojiPack/counterclockwise-arrows-button_1f504.png',
    '../EmojiPack/cowboy-hat-face_1f920.png',
    '../EmojiPack/crescent-moon_1f319.png',
    '../EmojiPack/crocodile_1f40a.png',
    '../EmojiPack/cross-mark-button_274e.png',
    '../EmojiPack/crossed-fingers_1f91e.png',
    '../EmojiPack/crossed-flags_1f38c.png',
    '../EmojiPack/crossed-swords_2694-fe0f.png',
    '../EmojiPack/crown_1f451.png',
    '../EmojiPack/crying-face_1f622.png',
    '../EmojiPack/crystal-ball_1f52e.png',
    '../EmojiPack/dagger_1f5e1-fe0f.png',
    '../EmojiPack/department-store_1f3ec.png',
    '../EmojiPack/desert-island_1f3dd-fe0f.png',
    '../EmojiPack/desktop-computer_1f5a5-fe0f.png',
    '../EmojiPack/diamond-with-a-dot_1f4a0.png',
    '../EmojiPack/direct-hit_1f3af.png',
    '../EmojiPack/dizzy-face_1f635.png',
    '../EmojiPack/dog-face_1f436.png',
    '../EmojiPack/dog_1f415.png',
    '../EmojiPack/dolphin_1f42c.png',
    '../EmojiPack/door_1f6aa.png',
    '../EmojiPack/dotted-line-face_1fae5.png',
    '../EmojiPack/doughnut_1f369.png',
    '../EmojiPack/down-arrow_2b07-fe0f.png',
    '../EmojiPack/down-left-arrow_2199-fe0f.png',
    '../EmojiPack/down-right-arrow_2198-fe0f.png',
    '../EmojiPack/downcast-face-with-sweat_1f613.png',
    '../EmojiPack/downwards-button_1f53d.png',
    '../EmojiPack/drooling-face_1f924.png',
    '../EmojiPack/droplet_1f4a7.png',
    '../EmojiPack/duck_1f986.png',
    '../EmojiPack/ear-of-corn_1f33d.png',
    '../EmojiPack/eggplant_1f346.png',
    '../EmojiPack/electric-plug_1f50c.png',
    '../EmojiPack/envelope-with-arrow_1f4e9.png',
    '../EmojiPack/evergreen-tree_1f332.png',
    '../EmojiPack/exploding-head_1f92f.png',
    '../EmojiPack/expressionless-face_1f611.png',
    '../EmojiPack/eyes_1f440.png',
    '../EmojiPack/face-blowing-a-kiss_1f618.png',
    '../EmojiPack/face-holding-back-tears_1f979.png',
    '../EmojiPack/face-savoring-food_1f60b.png',
    '../EmojiPack/face-screaming-in-fear_1f631.png',
    '../EmojiPack/face-vomiting_1f92e.png',
    '../EmojiPack/face-with-diagonal-mouth_1fae4.png',
    '../EmojiPack/face-with-hand-over-mouth_1f92d.png',
    '../EmojiPack/face-with-head-bandage_1f915.png',
    '../EmojiPack/face-with-monocle_1f9d0.png',
    '../EmojiPack/face-with-open-eyes-and-hand-over-mouth_1fae2.png',
    '../EmojiPack/face-with-peeking-eye_1fae3.png',
    '../EmojiPack/face-with-raised-eyebrow_1f928.png',
    '../EmojiPack/face-with-spiral-eyes_1f635-200d-1f4ab.png',
    '../EmojiPack/face-with-steam-from-nose_1f624.png',
    '../EmojiPack/face-with-tears-of-joy_1f602.png',
    '../EmojiPack/face-with-thermometer_1f912.png',
    '../EmojiPack/factory_1f3ed.png',
    '../EmojiPack/ferris-wheel_1f3a1.png',
    '../EmojiPack/ferry_26f4-fe0f.png',
    '../EmojiPack/file-folder_1f4c1.png',
    '../EmojiPack/fire-engine_1f692.png',
    '../EmojiPack/fire_1f525.png',
    '../EmojiPack/firecracker_1f9e8.png',
    '../EmojiPack/fish-cake-with-swirl_1f365.png',
    '../EmojiPack/flag-afghanistan_1f1e6-1f1eb.png',
    '../EmojiPack/flag-algeria_1f1e9-1f1ff.png',
    '../EmojiPack/flag-andorra_1f1e6-1f1e9.png',
    '../EmojiPack/flag-australia_1f1e6-1f1fa.png',
    '../EmojiPack/flag-azerbaijan_1f1e6-1f1ff.png',
    '../EmojiPack/flag-bahamas_1f1e7-1f1f8.png',
    '../EmojiPack/flag-bahrain_1f1e7-1f1ed.png',
    '../EmojiPack/flag-bangladesh_1f1e7-1f1e9.png',
    '../EmojiPack/flag-belgium_1f1e7-1f1ea.png',
    '../EmojiPack/flag-brazil_1f1e7-1f1f7.png',
    '../EmojiPack/flag-canada_1f1e8-1f1e6.png',
    '../EmojiPack/flag-chile_1f1e8-1f1f1.png',
    '../EmojiPack/flag-china_1f1e8-1f1f3.png',
    '../EmojiPack/flag-colombia_1f1e8-1f1f4.png',
    '../EmojiPack/flag-croatia_1f1ed-1f1f7.png',
    '../EmojiPack/flag-cuba_1f1e8-1f1fa.png',
    '../EmojiPack/flag-czechia_1f1e8-1f1ff.png',
    '../EmojiPack/flag-ecuador_1f1ea-1f1e8.png',
    '../EmojiPack/flag-england_1f3f4-e0067-e0062-e0065-e006e-e0067-e007f.png',
    '../EmojiPack/flag-estonia_1f1ea-1f1ea.png',
    '../EmojiPack/flag-european-union_1f1ea-1f1fa.png',
    '../EmojiPack/flag-finland_1f1eb-1f1ee.png',
    '../EmojiPack/flag-france_1f1eb-1f1f7.png',
    '../EmojiPack/flag-germany_1f1e9-1f1ea.png',
    '../EmojiPack/flag-greece_1f1ec-1f1f7.png',
    '../EmojiPack/flag-india_1f1ee-1f1f3.png',
    '../EmojiPack/flag-indonesia_1f1ee-1f1e9.png',
    '../EmojiPack/flag-ireland_1f1ee-1f1ea.png',
    '../EmojiPack/flag-israel_1f1ee-1f1f1.png',
    '../EmojiPack/flag-italy_1f1ee-1f1f9.png',
    '../EmojiPack/flag-japan_1f1ef-1f1f5.png',
    '../EmojiPack/flag-kenya_1f1f0-1f1ea.png',
    '../EmojiPack/flag-mexico_1f1f2-1f1fd.png',
    '../EmojiPack/flag-morocco_1f1f2-1f1e6.png',
    '../EmojiPack/flag-netherlands_1f1f3-1f1f1.png',
    '../EmojiPack/flag-new-zealand_1f1f3-1f1ff.png',
    '../EmojiPack/flag-nigeria_1f1f3-1f1ec.png',
    '../EmojiPack/flag-norway_1f1f3-1f1f4.png',
    '../EmojiPack/flag-pakistan_1f1f5-1f1f0.png',
    '../EmojiPack/flag-peru_1f1f5-1f1ea.png',
    '../EmojiPack/flag-philippines_1f1f5-1f1ed.png',
    '../EmojiPack/flag-poland_1f1f5-1f1f1.png',
    '../EmojiPack/flag-portugal_1f1f5-1f1f9.png',
    '../EmojiPack/flag-russia_1f1f7-1f1fa.png',
    '../EmojiPack/flag-saudi-arabia_1f1f8-1f1e6.png',
    '../EmojiPack/flag-scotland_1f3f4-e0067-e0062-e0073-e0063-e0074-e007f.png',
    '../EmojiPack/flag-singapore_1f1f8-1f1ec.png',
    '../EmojiPack/flag-south-africa_1f1ff-1f1e6.png',
    '../EmojiPack/flag-south-korea_1f1f0-1f1f7.png',
    '../EmojiPack/flag-spain_1f1ea-1f1f8.png',
    '../EmojiPack/flag-sweden_1f1f8-1f1ea.png',
    '../EmojiPack/flag-switzerland_1f1e8-1f1ed.png',
    '../EmojiPack/flag-thailand_1f1f9-1f1ed.png',
    '../EmojiPack/flag-turkey_1f1f9-1f1f7.png',
    '../EmojiPack/flag-ukraine_1f1fa-1f1e6.png',
    '../EmojiPack/flag-united-arab-emirates_1f1e6-1f1ea.png',
    '../EmojiPack/flag-united-kingdom_1f1ec-1f1e7.png',
    '../EmojiPack/flag-united-nations_1f1fa-1f1f3.png',
    '../EmojiPack/flag-united-states_1f1fa-1f1f8.png',
    '../EmojiPack/flag-wales_1f3f4-e0067-e0062-e0077-e006c-e0073-e007f.png',
    '../EmojiPack/flashlight_1f526.png',
    '../EmojiPack/flexed-biceps_1f4aa.png',
    '../EmojiPack/floppy-disk_1f4be.png',
    '../EmojiPack/flying-disc_1f94f.png',
    '../EmojiPack/flying-saucer_1f6f8.png',
    '../EmojiPack/folded-hands_1f64f.png',
    '../EmojiPack/fork-and-knife-with-plate_1f37d-fe0f.png',
    '../EmojiPack/four-leaf-clover_1f340.png',
    '../EmojiPack/fox_1f98a.png',
    '../EmojiPack/french-fries_1f35f.png',
    '../EmojiPack/frog_1f438.png',
    '../EmojiPack/full-moon-face_1f31d.png',
    '../EmojiPack/game-die_1f3b2.png',
    '../EmojiPack/gear_2699-fe0f.png',
    '../EmojiPack/gem-stone_1f48e.png',
    '../EmojiPack/globe-showing-americas_1f30e.png',
    '../EmojiPack/globe-showing-europe-africa_1f30d.png',
    '../EmojiPack/graduation-cap_1f393.png',
    '../EmojiPack/grapes_1f347.png',
    '../EmojiPack/green-book_1f4d7.png',
    '../EmojiPack/green-heart_1f49a.png',
    '../EmojiPack/grinning-face-with-smiling-eyes_1f604.png',
    '../EmojiPack/grinning-face-with-sweat_1f605.png',
    '../EmojiPack/guitar_1f3b8.png',
    '../EmojiPack/hamburger_1f354.png',
    '../EmojiPack/hammer-and-wrench_1f6e0-fe0f.png',
    '../EmojiPack/hammer_1f528.png',
    '../EmojiPack/hamster_1f439.png',
    '../EmojiPack/hand-with-index-finger-and-thumb-crossed_1faf0.png',
    '../EmojiPack/handshake_1f91d.png',
    '../EmojiPack/hatching-chick_1f423.png',
    '../EmojiPack/headphone_1f3a7.png',
    '../EmojiPack/heart-hands_1faf6.png',
    '../EmojiPack/heart-on-fire_2764-fe0f-200d-1f525.png',
    '../EmojiPack/heart-with-ribbon_1f49d.png',
    '../EmojiPack/high-heeled-shoe_1f460.png',
    '../EmojiPack/high-voltage_26a1.png',
    '../EmojiPack/hospital_1f3e5.png',
    '../EmojiPack/hot-beverage_2615.png',
    '../EmojiPack/hot-dog_1f32d.png',
    '../EmojiPack/hot-face_1f975.png',
    '../EmojiPack/hot-pepper_1f336-fe0f.png',
    '../EmojiPack/hotel_1f3e8.png',
    '../EmojiPack/hourglass-done_231b.png',
    '../EmojiPack/hourglass-not-done_23f3.png',
    '../EmojiPack/house_1f3e0.png',
    '../EmojiPack/hugging-face_1f917.png',
    '../EmojiPack/hundred-points_1f4af.png',
    '../EmojiPack/identification-card_1faaa.png',
    '../EmojiPack/index-pointing-at-the-viewer_1faf5.png',
    '../EmojiPack/index-pointing-up_261d-fe0f.png',
    '../EmojiPack/key_1f511.png',
    '../EmojiPack/kissing-face-with-closed-eyes_1f61a.png',
    '../EmojiPack/kissing-face-with-smiling-eyes_1f619.png',
    '../EmojiPack/kissing-face_1f617.png',
    '../EmojiPack/koala_1f428.png',
    '../EmojiPack/laptop_1f4bb.png',
    '../EmojiPack/leaf-fluttering-in-wind_1f343.png',
    '../EmojiPack/left-arrow_2b05-fe0f.png',
    '../EmojiPack/light-bulb_1f4a1.png',
    '../EmojiPack/link_1f517.png',
    '../EmojiPack/lion_1f981.png',
    '../EmojiPack/lobster_1f99e.png',
    '../EmojiPack/lollipop_1f36d.png',
    '../EmojiPack/loudly-crying-face_1f62d.png',
    '../EmojiPack/love-letter_1f48c.png',
    '../EmojiPack/love-you-gesture_1f91f.png',
    '../EmojiPack/low-battery_1faab.png',
    '../EmojiPack/magic-wand_1fa84.png',
    '../EmojiPack/magnet_1f9f2.png',
    '../EmojiPack/maple-leaf_1f341.png',
    '../EmojiPack/melting-face_1fae0.png',
    '../EmojiPack/mending-heart_2764-fe0f-200d-1fa79.png',
    '../EmojiPack/microphone_1f3a4.png',
    '../EmojiPack/middle-finger_1f595.png',
    '../EmojiPack/milky-way_1f30c.png',
    '../EmojiPack/mobile-phone_1f4f1.png',
    '../EmojiPack/money-bag_1f4b0.png',
    '../EmojiPack/monkey-face_1f435.png',
    '../EmojiPack/mouth_1f444.png',
    '../EmojiPack/mushroom_1f344.png',
    '../EmojiPack/nauseated-face_1f922.png',
    '../EmojiPack/nerd-face_1f913.png',
    '../EmojiPack/neutral-face_1f610.png',
    '../EmojiPack/newspaper_1f4f0.png',
    '../EmojiPack/night-with-stars_1f303.png',
    '../EmojiPack/no-entry_26d4.png',
    '../EmojiPack/octopus_1f419.png',
    '../EmojiPack/orange-heart_1f9e1.png',
    '../EmojiPack/package_1f4e6.png',
    '../EmojiPack/party-popper_1f389.png',
    '../EmojiPack/partying-face_1f973.png',
    '../EmojiPack/pile-of-poo_1f4a9.png',
    '../EmojiPack/pizza_1f355.png',
    '../EmojiPack/play-button_25b6-fe0f.png',
    '../EmojiPack/pleading-face_1f97a.png',
    '../EmojiPack/police-car-light_1f6a8.png',
    '../EmojiPack/popcorn_1f37f.png',
    '../EmojiPack/pouting-face_1f621.png',
    '../EmojiPack/purple-heart_1f49c.png',
    '../EmojiPack/puzzle-piece_1f9e9.png',
    '../EmojiPack/rabbit-face_1f430.png',
    '../EmojiPack/rainbow-flag_1f3f3-fe0f-200d-1f308.png',
    '../EmojiPack/rainbow_1f308.png',
    '../EmojiPack/recycling-symbol_267b-fe0f.png',
    '../EmojiPack/red-heart_2764-fe0f.png',
    '../EmojiPack/relieved-face_1f60c.png',
    '../EmojiPack/revolving-hearts_1f49e.png',
    '../EmojiPack/right-arrow_27a1-fe0f.png',
    '../EmojiPack/ring_1f48d.png',
    '../EmojiPack/rocket_1f680.png',
    '../EmojiPack/rolling-on-the-floor-laughing_1f923.png',
    '../EmojiPack/rose_1f339.png',
    '../EmojiPack/saluting-face_1fae1.png',
    '../EmojiPack/scissors_2702-fe0f.png',
    '../EmojiPack/shopping-cart_1f6d2.png',
    '../EmojiPack/shushing-face_1f92b.png',
    '../EmojiPack/sign-of-the-horns_1f918.png',
    '../EmojiPack/skull-and-crossbones_2620-fe0f.png',
    '../EmojiPack/skull_1f480.png',
    '../EmojiPack/sleeping-face_1f634.png',
    '../EmojiPack/sleepy-face_1f62a.png',
    '../EmojiPack/slightly-smiling-face_1f642.png',
    '../EmojiPack/smiling-cat-with-heart-eyes_1f63b.png',
    '../EmojiPack/smiling-face-with-halo_1f607.png',
    '../EmojiPack/smiling-face-with-heart-eyes_1f60d.png',
    '../EmojiPack/smiling-face-with-hearts_1f970.png',
    '../EmojiPack/smiling-face-with-horns_1f608.png',
    '../EmojiPack/smiling-face-with-smiling-eyes_1f60a.png',
    '../EmojiPack/smiling-face-with-tear_1f972.png',
    '../EmojiPack/smiling-face_263a-fe0f.png',
    '../EmojiPack/smirking-face_1f60f.png',
    '../EmojiPack/sneezing-face_1f927.png',
    '../EmojiPack/snowflake_2744-fe0f.png',
    '../EmojiPack/soccer-ball_26bd.png',
    '../EmojiPack/sparkles_2728.png',
    '../EmojiPack/sparkling-heart_1f496.png',
    '../EmojiPack/speech-balloon_1f4ac.png',
    '../EmojiPack/star-struck_1f929.png',
    '../EmojiPack/star_2b50.png',
    '../EmojiPack/stop-sign_1f6d1.png',
    '../EmojiPack/sunflower_1f33b.png',
    '../EmojiPack/sweat-droplets_1f4a6.png',
    '../EmojiPack/syringe_1f489.png',
    '../EmojiPack/taxi_1f695.png',
    '../EmojiPack/thinking-face_1f914.png',
    '../EmojiPack/tiger-face_1f42f.png',
    '../EmojiPack/trophy_1f3c6.png',
    '../EmojiPack/tulip_1f337.png',
    '../EmojiPack/umbrella-with-rain-drops_2614.png',
    '../EmojiPack/unicorn_1f984.png',
    '../EmojiPack/up-arrow_2b06-fe0f.png',
    '../EmojiPack/upside-down-face_1f643.png',
    '../EmojiPack/victory-hand_270c-fe0f.png',
    '../EmojiPack/video-game_1f3ae.png',
    '../EmojiPack/volcano_1f30b.png',
    '../EmojiPack/vulcan-salute_1f596.png',
    '../EmojiPack/warning_26a0-fe0f.png',
    '../EmojiPack/water-wave_1f30a.png',
    '../EmojiPack/watermelon_1f349.png',
    '../EmojiPack/waving-hand_1f44b.png',
    '../EmojiPack/white-heart_1f90d.png',
    '../EmojiPack/wilted-flower_1f940.png',
    '../EmojiPack/wine-glass_1f377.png',
    '../EmojiPack/winking-face-with-tongue_1f61c.png',
    '../EmojiPack/winking-face_1f609.png',
    '../EmojiPack/woozy-face_1f974.png',
    '../EmojiPack/wrapped-gift_1f381.png',
    '../EmojiPack/wrench_1f527.png',
    '../EmojiPack/yellow-heart_1f49b.png',
    '../EmojiPack/yin-yang_262f-fe0f.png',
    '../EmojiPack/zany-face_1f92a.png',
    '../EmojiPack/zipper-mouth-face_1f910.png',
  ];
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add frontend/index.html
  git commit -m "feat: add EMOJIPACK_FILES array (759 local emoji paths)"
  ```

---

## Task 4: Restructure emoji popup HTML with two tabs

**Files:**
- Modify: `frontend/index.html` — replace `#emo-popup` HTML (lines ~589–600)

- [ ] **Step 1: Replace the existing `#emo-popup` block**

  Find this entire block:
  ```html
  <!-- EMOJI POPUP -->
  <div id="emo-popup" class="t-dropdown" data-origin="top-left">
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

  Replace with:
  ```html
  <!-- EMOJI POPUP -->
  <div id="emo-popup" class="t-dropdown" data-origin="top-left">
    <div class="emo-tabs">
      <button class="emo-tab on" onclick="switchEmoTab('mypack')">My Emojis</button>
      <button class="emo-tab" onclick="switchEmoTab('twemoji')">Twemoji</button>
    </div>
    <div class="emo-tab-body on" id="emo-tab-mypack">
      <div class="myemo-grid" id="myemo-grid"></div>
    </div>
    <div class="emo-tab-body" id="emo-tab-twemoji">
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
  </div>
  ```

- [ ] **Step 2: Add font picker panel HTML**

  Immediately after the closing `</div><!-- /emo-popup -->` block (i.e., right after the `</div>` that closes `#emo-popup`), add:
  ```html
  <!-- FONT PICKER PANEL -->
  <div id="fp-panel">
    <input id="fp-search" type="text" placeholder="Search fonts…" oninput="renderFontList(this.value)" autocomplete="off">
    <div id="fp-list"></div>
  </div>
  ```

- [ ] **Step 3: Commit**
  ```bash
  git add frontend/index.html
  git commit -m "feat: restructure emoji popup with two tabs, add font picker panel HTML"
  ```

---

## Task 5: Add My Emojis tab JS + update emoji serialization

**Files:**
- Modify: `frontend/index.html` — add JS after the existing emoji section

- [ ] **Step 1: Add `switchEmoTab`, `renderMyEmojiGrid`, `insertEmojiPackImg` functions**

  Find this existing line:
  ```javascript
  renderEmoGrid();
  Object.values(EMOJI_DATA).flat().forEach(({e})=>preloadTwemojiImg(e));
  ```

  **Before** those two lines, insert:
  ```javascript
  function switchEmoTab(tab){
    document.querySelectorAll('.emo-tab').forEach((b,i)=>{
      b.classList.toggle('on',i===(tab==='mypack'?0:1));
    });
    document.getElementById('emo-tab-mypack').classList.toggle('on',tab==='mypack');
    document.getElementById('emo-tab-twemoji').classList.toggle('on',tab==='twemoji');
  }

  function renderMyEmojiGrid(){
    const grid=document.getElementById('myemo-grid');
    if(!grid)return;
    grid.innerHTML=EMOJIPACK_FILES.map(path=>{
      const filename=path.split('/').pop();
      const label=filename.replace(/_[^_]+\.png$/,'').replace(/-/g,' ');
      return `<div class="ec" onclick="insertEmojiPackImg('${path.replace(/'/g,"\\'")}',this)" title="${label}"><img src="${path}" alt="${label}" loading="lazy" width="28" height="28" style="display:block"></div>`;
    }).join('');
  }

  function insertEmojiPackImg(path){
    const _epop=document.getElementById('emo-popup');
    const _ecms=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--dropdown-close-dur'))||150;
    _epop.classList.remove('is-open');_epop.classList.add('is-closing');
    setTimeout(()=>_epop.classList.remove('is-closing'),_ecms);
    emoOpen=false;
    const filename=path.split('/').pop();
    const label=filename.replace(/_[^_]+\.png$/,'').replace(/-/g,' ');
    const currentFmt=fmt;
    fabric.Image.fromURL(path,function(img){
      if(!img||!img.width||!img.height)return;
      const {w,h}=FMT[currentFmt];
      const size=Math.round(Math.min(w,h)*0.18);
      img.set({
        left:Math.round(w/2-size/2),
        top:Math.round(h/2-size/2),
        scaleX:size/img.width,
        scaleY:size/img.height,
        _type:'emoji',
        _label:label,
        _src:path,
      });
      cv.add(img);cv.setActiveObject(img);cv.renderAll();saveHist();
    },{crossOrigin:'anonymous'});
  }
  ```

- [ ] **Step 2: Call `renderMyEmojiGrid()` on init**

  Find:
  ```javascript
  renderEmoGrid();
  Object.values(EMOJI_DATA).flat().forEach(({e})=>preloadTwemojiImg(e));
  ```

  Change to:
  ```javascript
  renderEmoGrid();
  renderMyEmojiGrid();
  Object.values(EMOJI_DATA).flat().forEach(({e})=>preloadTwemojiImg(e));
  ```

- [ ] **Step 3: Update emoji serialization to use `_src` when available**

  Find:
  ```javascript
  if(t==='emoji')return{...base,src:twemojiUrl(obj._label||''),label:obj._label||''};
  ```
  Replace with:
  ```javascript
  if(t==='emoji')return{...base,src:obj._src||twemojiUrl(obj._label||''),label:obj._label||''};
  ```

- [ ] **Step 4: Open the app, click the emoji button, verify "My Emojis" tab shows images, click an image and confirm it appears on canvas**

- [ ] **Step 5: Commit**
  ```bash
  git add frontend/index.html
  git commit -m "feat: add My Emojis tab with EmojiPack images, update emoji serialization"
  ```

---

## Task 6: Add font picker JS + wire into text properties panel

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add font picker JS functions**

  Find the `// ── CANVAS INIT` comment and insert **before** it:
  ```javascript
  // ── FONT PICKER ────────────────────────────────────────────────────────────
  let fpOpen=false;

  function toggleFontPicker(triggerEl){
    const panel=document.getElementById('fp-panel');
    if(fpOpen){closeFontPicker();return;}
    const rect=triggerEl.getBoundingClientRect();
    panel.style.top=(rect.bottom+4)+'px';
    panel.style.left=rect.left+'px';
    panel.style.width=rect.width+'px';
    panel.classList.add('open');
    triggerEl.classList.add('open');
    fpOpen=true;
    const searchEl=document.getElementById('fp-search');
    searchEl.value='';
    renderFontList('');
    searchEl.focus();
  }

  function closeFontPicker(){
    const panel=document.getElementById('fp-panel');
    panel.classList.remove('open');
    fpOpen=false;
    const trigger=document.getElementById('fp-trigger');
    if(trigger)trigger.classList.remove('open');
  }

  function renderFontList(query){
    const list=document.getElementById('fp-list');
    const obj=cv?.getActiveObject();
    const curFont=(obj?.fontFamily||'Inter').replace(/^"|"$/g,'').split(',')[0].trim();
    const q=query.toLowerCase();
    const filtered=q?GOOGLE_FONTS.filter(f=>f.toLowerCase().includes(q)):GOOGLE_FONTS;
    list.innerHTML=filtered.map(f=>
      `<div class="fp-item${f===curFont?' on':''}" style="font-family:'${f}'" onclick="selectFont('${f.replace(/'/g,"\\'")}')"><span>${f}</span></div>`
    ).join('');
  }

  function selectFont(fontName){
    sp('fontFamily',fontName);
    closeFontPicker();
    const trigger=document.getElementById('fp-trigger');
    if(trigger){
      trigger.style.fontFamily=`'${fontName}'`;
      const nameEl=trigger.querySelector('.fp-trigger-name');
      if(nameEl)nameEl.textContent=fontName;
    }
  }

  document.addEventListener('click',e=>{
    if(fpOpen&&!e.target.closest('#fp-panel')&&!e.target.closest('#fp-trigger')){
      closeFontPicker();
    }
  });
  ```

- [ ] **Step 2: Add font row to the text properties panel HTML**

  In the `updateProps` function, find this exact string inside the text properties template (around line 2324):
  ```javascript
  <div class="prow"><span class="plbl">Size</span>
  ```
  
  Insert a new `prow` **before** it (inside the same template literal, after the `psec-title` closing tag on the Text section):
  ```javascript
  <div class="prow"><span class="plbl">Font</span>
    <div class="fp-wrap">
      <button class="fp-trigger" id="fp-trigger" onclick="toggleFontPicker(this)" style="font-family:'${(obj.fontFamily||'Inter').replace(/^"|"$/g,'').split(',')[0].trim()}'">
        <span class="fp-trigger-name">${(obj.fontFamily||'Inter').replace(/^"|"$/g,'').split(',')[0].trim()}</span>
        <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><polyline points="6 9 12 15 18 9"></polyline></svg>
      </button>
    </div>
  </div>
  ```

  The exact surrounding context to find for the insertion point is:
  ```javascript
  html+=`<div class="psec"><div class="psec-title"><svg class="psec-title-icon cur-path"
  ```
  After the entire `psec-title` div closes (after `</div>Text</div>` equivalent — the title div that contains the SVG and "Text" label), add the Font row before the Size row.

  The precise `old_string` to target for the Edit tool is:
  ```
  <div class="prow"><span class="plbl">Size</span>
      <div class="slrow">
        <input type="range" class="psl" min="8" max="180" value="${fs}"
          oninput="sp('fontSize',+this.value);this.nextElementSibling.textContent=this.value+'px'">
        <span class="slv">${fs}px</span>
      </div>
    </div>
  ```
  Prepend the font row so it reads:
  ```
  <div class="prow"><span class="plbl">Font</span>
      <div class="fp-wrap">
        <button class="fp-trigger" id="fp-trigger" onclick="toggleFontPicker(this)" style="font-family:'${(obj.fontFamily||'Inter').replace(/^"|"$/g,'').split(',')[0].trim()}'">
          <span class="fp-trigger-name">${(obj.fontFamily||'Inter').replace(/^"|"$/g,'').split(',')[0].trim()}</span>
          <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </button>
      </div>
    </div>
    <div class="prow"><span class="plbl">Size</span>
      <div class="slrow">
        <input type="range" class="psl" min="8" max="180" value="${fs}"
          oninput="sp('fontSize',+this.value);this.nextElementSibling.textContent=this.value+'px'">
        <span class="slv">${fs}px</span>
      </div>
    </div>
  ```

- [ ] **Step 3: Close font picker when props panel rebuilds**

  Find:
  ```javascript
  function clearProps(){
    document.getElementById('right').innerHTML=
  ```
  After the opening brace of `clearProps()`, add `closeFontPicker();` as the first statement. The result should be:
  ```javascript
  function clearProps(){
    closeFontPicker();
    document.getElementById('right').innerHTML=...
  ```

  Also find:
  ```javascript
  function updateProps(){
    let obj=cv?.getActiveObject();
  ```
  Add `closeFontPicker();` as the first statement:
  ```javascript
  function updateProps(){
    closeFontPicker();
    let obj=cv?.getActiveObject();
  ```

- [ ] **Step 4: Update the "Add Emoji" pnote text**

  Find:
  ```
  <p class="pnote">Inserts Twemoji at cursor in this text. If no cursor position is saved, appends to end. Without a text selection, adds as a standalone image layer.</p>
  ```
  Replace with:
  ```
  <p class="pnote">Inserts emoji at cursor. Without a text selection, adds as a standalone image layer.</p>
  ```

- [ ] **Step 5: Open the app, select a text layer, verify the Font picker row appears, click it, type to filter, select a font, confirm the canvas text changes typeface**

- [ ] **Step 6: Commit**
  ```bash
  git add frontend/index.html
  git commit -m "feat: add searchable Google Font picker to text layer properties"
  ```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|---|---|
| ~150 Google Fonts loaded | Task 2 |
| `GOOGLE_FONTS` JS array | Task 2 |
| Searchable font dropdown in text props | Task 6 |
| Font name shown in its own typeface in picker | Task 6 — `style="font-family:'${f}'"` on each item |
| Trigger shows current font | Task 6 — `fp-trigger-name` |
| `sp('fontFamily', ...)` on select | Task 6 — `selectFont` |
| Serialization works | No change needed — `fontFamily` already serialized |
| Emoji popup has two tabs | Task 4 |
| "My Emojis" tab shows EmojiPack images | Task 5 |
| "Twemoji" tab = existing behavior | Task 4 — wraps existing content unchanged |
| EmojiPack click inserts as fabric.Image | Task 5 — `insertEmojiPackImg` |
| `_renderChar` override unchanged | Not touched |
| EmojiPack layers serialize with local `_src` | Task 5 — serialization update |

**Placeholder scan:** No TBDs, no "similar to above", all code is complete.

**Type consistency:** `EMOJIPACK_FILES` array used in `renderMyEmojiGrid` ✓. `GOOGLE_FONTS` used in `renderFontList` ✓. `sp('fontFamily', ...)` matches existing `sp` function signature ✓. `insertEmojiPackImg(path)` signature matches onclick call ✓. `closeFontPicker()` called in `clearProps` and `updateProps` before they reference `#fp-trigger` ✓.
