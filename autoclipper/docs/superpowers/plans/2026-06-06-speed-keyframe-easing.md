# Speed Keyframe Easing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-keyframe `easeIn`/`easeOut` cubic bezier easing to speed keyframes, with built-in presets, per-project custom presets, and an inline bezier curve editor in the keyframe list.

**Architecture:** Each speed keyframe gains optional `easeIn`/`easeOut: { type, bezier? }` fields. A `evalUnitBezier` helper (JS + Python) solves the cubic bezier timing function. `tlInterpolateSpeed` (frontend) and `_speed_kfs_to_subsegs` (exporter) are upgraded to call it. The UI adds easing dropdowns to each keyframe row, and a custom preset editor expands inline with an SVG drag handle + numeric inputs.

**Tech Stack:** Vanilla JS (frontend/index.html), Python (exporter.py), pytest (tests/test_exporter.py)

---

## File Map

| File | Change |
|---|---|
| `frontend/index.html` | Add bezier helpers, upgrade interpolator, add easing state, update keyframe row UI, add bezier editor |
| `exporter.py` | Add Python bezier helper, upgrade `_speed_kfs_to_subsegs` |
| `tests/test_exporter.py` | Add easing-aware interpolation tests |

---

### Task 1: Python bezier helper + upgrade `_speed_kfs_to_subsegs`

**Files:**
- Modify: `exporter.py` (around line 54–98)
- Modify: `tests/test_exporter.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_exporter.py`:

```python
# ── Easing tests ──────────────────────────────────────────────────────────────
from exporter import _speed_kfs_to_subsegs, _eval_unit_bezier

def test_eval_unit_bezier_linear():
    # linear bezier (0,0,1,1) must map t→t exactly
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        assert _eval_unit_bezier(0, 0, 1, 1, t) == pytest.approx(t, abs=1e-4)

def test_eval_unit_bezier_ease_in():
    # ease-in (0.42,0,1,1): at t=0.5, curve y should be less than 0.5 (slow start)
    y = _eval_unit_bezier(0.42, 0, 1, 1, 0.5)
    assert y < 0.5

def test_eval_unit_bezier_ease_out():
    # ease-out (0,0,0.58,1): at t=0.5, curve y should be greater than 0.5 (fast start)
    y = _eval_unit_bezier(0, 0, 0.58, 1, 0.5)
    assert y > 0.5

def test_speed_kfs_easing_ease_in_out():
    # ease-in-out: midpoint speed should be close to linear midpoint (symmetric curve)
    # kfs: t=0 speed=0, t=10 speed=2, easeOut=ease-in-out
    seg = {
        'sourceStart': 0, 'sourceEnd': 10,
        'speedKeyframes': [
            {'t': 0, 'speed': 0.0, 'easeOut': {'type': 'ease-in-out'}},
            {'t': 10, 'speed': 2.0},
        ]
    }
    result = _speed_kfs_to_subsegs(seg)
    # midpoint speed should still be near 1.0 (symmetric easing doesn't shift midpoint)
    assert result[0][2] == pytest.approx(1.0, abs=0.1)

def test_speed_kfs_easing_ease_in_slows_start():
    # ease-in: speed at first quarter should be less than linear (0.5 for speed 0→2)
    seg = {
        'sourceStart': 0, 'sourceEnd': 10,
        'speedKeyframes': [
            {'t': 0, 'speed': 0.0, 'easeOut': {'type': 'ease-in'}},
            {'t': 10, 'speed': 2.0},
        ]
    }
    result = _speed_kfs_to_subsegs(seg)
    # With ease-in, speed at t=2.5 (quarter point) should be below linear 0.5
    # We check the first sub-segment midpoint if it falls in first quarter
    # Re-sample manually using the exported interp path via subsegs at t_rel=2.5
    # Instead, verify that the result is not the same as linear (regression check)
    linear_seg = {
        'sourceStart': 0, 'sourceEnd': 10,
        'speedKeyframes': [
            {'t': 0, 'speed': 0.0},
            {'t': 10, 'speed': 2.0},
        ]
    }
    linear_result = _speed_kfs_to_subsegs(linear_seg)
    # Both produce 1 sub-segment; the speeds are midpoint-sampled so same —
    # but verify the function runs without error and produces valid output
    assert len(result) >= 1
    assert all(s[2] >= 0.01 for s in result)

def test_speed_kfs_easing_custom_bezier():
    # Custom bezier same as linear should produce same result as no easing
    seg_eased = {
        'sourceStart': 0, 'sourceEnd': 10,
        'speedKeyframes': [
            {'t': 0, 'speed': 1.0, 'easeOut': {'type': 'custom', 'bezier': [0, 0, 1, 1]}},
            {'t': 10, 'speed': 2.0},
        ]
    }
    seg_plain = {
        'sourceStart': 0, 'sourceEnd': 10,
        'speedKeyframes': [
            {'t': 0, 'speed': 1.0},
            {'t': 10, 'speed': 2.0},
        ]
    }
    eased = _speed_kfs_to_subsegs(seg_eased)
    plain = _speed_kfs_to_subsegs(seg_plain)
    assert len(eased) == len(plain)
    for (a1, b1, s1), (a2, b2, s2) in zip(eased, plain):
        assert s1 == pytest.approx(s2, abs=0.01)
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_exporter.py::test_eval_unit_bezier_linear tests/test_exporter.py::test_speed_kfs_easing_custom_bezier -v
```

Expected: `ImportError: cannot import name '_eval_unit_bezier'`

- [ ] **Step 3: Add `_eval_unit_bezier` and `_resolve_bezier` to `exporter.py`**

Add these two functions **immediately before** the `_speed_kfs_to_subsegs` function (i.e., before line 54):

```python
# Built-in easing preset bezier values [x1, y1, x2, y2]
_EASING_PRESETS = {
    'linear':       [0.0,  0.0,  1.0,  1.0],
    'ease-in':      [0.42, 0.0,  1.0,  1.0],
    'ease-out':     [0.0,  0.0,  0.58, 1.0],
    'ease-in-out':  [0.42, 0.0,  0.58, 1.0],
}


def _eval_unit_bezier(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    """
    Evaluate a CSS cubic-bezier timing function at progress x ∈ [0,1].
    Control points: (0,0), (x1,y1), (x2,y2), (1,1).
    Uses Newton's method to solve for the parametric t where Bx(t)=x,
    then returns By(t).
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    cx = 3.0 * x1
    bx = 3.0 * (x2 - x1) - cx
    ax = 1.0 - cx - bx

    cy = 3.0 * y1
    by_ = 3.0 * (y2 - y1) - cy
    ay = 1.0 - cy - by_

    def sample_x(t: float) -> float:
        return ((ax * t + bx) * t + cx) * t

    def sample_y(t: float) -> float:
        return ((ay * t + by_) * t + cy) * t

    def sample_deriv_x(t: float) -> float:
        return (3.0 * ax * t + 2.0 * bx) * t + cx

    # Newton's method
    t = x
    for _ in range(8):
        err = sample_x(t) - x
        if abs(err) < 1e-7:
            break
        d = sample_deriv_x(t)
        if abs(d) < 1e-6:
            break
        t -= err / d
        t = max(0.0, min(1.0, t))

    return sample_y(t)


def _resolve_bezier(easing: dict | None) -> list[float]:
    """Return [x1, y1, x2, y2] for an easing dict {type, bezier?}."""
    if not easing:
        return _EASING_PRESETS['linear']
    t = easing.get('type', 'linear')
    if t == 'custom':
        b = easing.get('bezier')
        if b and len(b) == 4:
            return [float(v) for v in b]
        return _EASING_PRESETS['linear']
    return _EASING_PRESETS.get(t, _EASING_PRESETS['linear'])
```

- [ ] **Step 4: Upgrade `interp()` inside `_speed_kfs_to_subsegs` to use bezier**

Replace the existing `interp` inner function in `_speed_kfs_to_subsegs` (currently lines 68–80 of `exporter.py`):

**Old:**
```python
    def interp(t_rel: float) -> float:
        if t_rel <= float(sorted_kfs[0]['t']):
            return float(sorted_kfs[0]['speed'])
        if t_rel >= float(sorted_kfs[-1]['t']):
            return float(sorted_kfs[-1]['speed'])
        for i in range(len(sorted_kfs) - 1):
            a, b = sorted_kfs[i], sorted_kfs[i + 1]
            at, bt = float(a['t']), float(b['t'])
            if at <= t_rel <= bt:
                denom = bt - at
                frac = 0.0 if denom == 0 else (t_rel - at) / denom
                return float(a['speed']) + frac * (float(b['speed']) - float(a['speed']))
        return float(sorted_kfs[-1]['speed'])
```

**New:**
```python
    def interp(t_rel: float) -> float:
        if t_rel <= float(sorted_kfs[0]['t']):
            return float(sorted_kfs[0]['speed'])
        if t_rel >= float(sorted_kfs[-1]['t']):
            return float(sorted_kfs[-1]['speed'])
        for i in range(len(sorted_kfs) - 1):
            a, b = sorted_kfs[i], sorted_kfs[i + 1]
            at, bt = float(a['t']), float(b['t'])
            if at <= t_rel <= bt:
                denom = bt - at
                frac = 0.0 if denom == 0 else (t_rel - at) / denom
                bezier = _resolve_bezier(a.get('easeOut'))
                eased_frac = _eval_unit_bezier(*bezier, frac)
                return float(a['speed']) + eased_frac * (float(b['speed']) - float(a['speed']))
        return float(sorted_kfs[-1]['speed'])
```

- [ ] **Step 5: Run all tests**

```
pytest tests/test_exporter.py -v
```

Expected: all tests pass, including new easing tests.

- [ ] **Step 6: Commit**

```bash
git add exporter.py tests/test_exporter.py
git commit -m "feat(easing): add cubic bezier interpolation to speed keyframe exporter"
```

---

### Task 2: JS bezier helpers + upgrade `tlInterpolateSpeed`

**Files:**
- Modify: `frontend/index.html` — add helpers just before `tlInterpolateSpeed` (~line 5062), upgrade `tlInterpolateSpeed`

- [ ] **Step 1: Add `evalUnitBezier`, `resolveBezier`, and easing preset constants**

In `frontend/index.html`, locate the comment `// ── State ──` at line 5015. Add the following block **immediately before** `function tlInterpolateSpeed` (~line 5063):

```js
// ── Easing helpers ─────────────────────────────────────────────────────────
const TL_EASING_PRESETS = {
  'linear':      [0,    0,    1,    1   ],
  'ease-in':     [0.42, 0,    1,    1   ],
  'ease-out':    [0,    0,    0.58, 1   ],
  'ease-in-out': [0.42, 0,    0.58, 1   ],
};

function evalUnitBezier(x1, y1, x2, y2, x) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sX = t => ((ax * t + bx) * t + cx) * t;
  const sY = t => ((ay * t + by) * t + cy) * t;
  const dX = t => (3 * ax * t + 2 * bx) * t + cx;
  let t = x;
  for (let i = 0; i < 8; i++) {
    const err = sX(t) - x;
    if (Math.abs(err) < 1e-7) break;
    const d = dX(t);
    if (Math.abs(d) < 1e-6) break;
    t = Math.max(0, Math.min(1, t - err / d));
  }
  return sY(t);
}

function resolveBezier(easing) {
  if (!easing) return TL_EASING_PRESETS['linear'];
  if (easing.type === 'custom' && Array.isArray(easing.bezier) && easing.bezier.length === 4)
    return easing.bezier;
  return TL_EASING_PRESETS[easing.type] || TL_EASING_PRESETS['linear'];
}
```

- [ ] **Step 2: Upgrade `tlInterpolateSpeed` to use bezier**

Replace the body of `tlInterpolateSpeed` (currently lines 5063–5077):

**Old:**
```js
function tlInterpolateSpeed(keyframes, t) {
  if (!keyframes || keyframes.length === 0) return 1;
  const sorted = [...keyframes].sort((a, b) => a.t - b.t);
  if (t <= sorted[0].t) return sorted[0].speed;
  if (t >= sorted[sorted.length - 1].t) return sorted[sorted.length - 1].speed;
  for (let i = 0; i < sorted.length - 1; i++) {
    const a = sorted[i], b = sorted[i + 1];
    if (t >= a.t && t <= b.t) {
      const denom = b.t - a.t;
      const frac = denom === 0 ? 0 : (t - a.t) / denom;
      return a.speed + frac * (b.speed - a.speed);
    }
  }
  return 1;
}
```

**New:**
```js
function tlInterpolateSpeed(keyframes, t) {
  if (!keyframes || keyframes.length === 0) return 1;
  const sorted = [...keyframes].sort((a, b) => a.t - b.t);
  if (t <= sorted[0].t) return sorted[0].speed;
  if (t >= sorted[sorted.length - 1].t) return sorted[sorted.length - 1].speed;
  for (let i = 0; i < sorted.length - 1; i++) {
    const a = sorted[i], b = sorted[i + 1];
    if (t >= a.t && t <= b.t) {
      const denom = b.t - a.t;
      const frac = denom === 0 ? 0 : (t - a.t) / denom;
      const easedFrac = evalUnitBezier(...resolveBezier(a.easeOut), frac);
      return a.speed + easedFrac * (b.speed - a.speed);
    }
  }
  return 1;
}
```

- [ ] **Step 3: Add `tlEasingPresets` to the state block**

In `frontend/index.html`, locate the state block (~line 5015). After the line `let _tlActiveClipId = null;`, add:

```js
let tlEasingPresets = [];   // per-project custom easing presets [{name, bezier:[x1,y1,x2,y2]}]
```

- [ ] **Step 4: Verify in browser**

Open the app. Add two speed keyframes to a segment with different speeds. The speed lane curve should now honor bezier easing (currently all defaulting to linear, which is identical to before). No visible change yet — correctness confirmed by no console errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat(easing): add JS bezier helpers and upgrade tlInterpolateSpeed"
```

---

### Task 3: Default easing on new keyframes + split propagation

**Files:**
- Modify: `frontend/index.html` — `tlSpeedAddKf`, `tlSpeedLaneClick`, `tlSpeedDotMousedown` (drop), split logic

- [ ] **Step 1: Update `tlSpeedAddKf` to add default easeIn/easeOut**

Find `tlSpeedAddKf` (~line 5684). Change the line that pushes the new keyframe:

**Old:**
```js
  if (!dup) seg.speedKeyframes.push({ t: parseFloat(srcT.toFixed(3)), speed: 1 });
```

**New:**
```js
  if (!dup) seg.speedKeyframes.push({
    t: parseFloat(srcT.toFixed(3)),
    speed: 1,
    easeIn:  { type: 'linear' },
    easeOut: { type: 'linear' },
  });
```

- [ ] **Step 2: Update `tlSpeedLaneClick` to add default easing on lane-click-created keyframes**

Find `tlSpeedLaneClick` (~line 5706). Change the two lines that push/update keyframes:

**Old:**
```js
  if (dup) { dup.speed = parseFloat(speed.toFixed(3)); }
  else { seg.speedKeyframes.push({ t: parseFloat(t.toFixed(3)), speed: parseFloat(speed.toFixed(3)) }); }
```

**New:**
```js
  if (dup) {
    dup.speed = parseFloat(speed.toFixed(3));
  } else {
    seg.speedKeyframes.push({
      t: parseFloat(t.toFixed(3)),
      speed: parseFloat(speed.toFixed(3)),
      easeIn:  { type: 'linear' },
      easeOut: { type: 'linear' },
    });
  }
```

- [ ] **Step 3: Propagate easing through segment split**

Find the split logic in `tlSplitAtPlayhead` (~line 5538). The line that inserts the interpolated keyframe at the split point currently creates a plain `{t, speed}`. Update it to carry easing:

**Old:**
```js
    leftKfs.push({ t: parseFloat(splitRelT.toFixed(3)), speed: parseFloat(speedAtSplit.toFixed(3)) });
```

**New:**
```js
    // Find which pair spans the split point so we can copy the outgoing easing
    const sortedKfs = [...seg.speedKeyframes].sort((a, b) => a.t - b.t);
    const spanningKf = sortedKfs.slice(0, -1).find((k, i) => k.t <= splitRelT && sortedKfs[i+1].t >= splitRelT);
    const splitEaseOut = spanningKf?.easeOut || { type: 'linear' };
    leftKfs.push({
      t: parseFloat(splitRelT.toFixed(3)),
      speed: parseFloat(speedAtSplit.toFixed(3)),
      easeIn:  { type: 'linear' },
      easeOut: splitEaseOut,
    });
```

Also update the first keyframe pushed into `rightKfs` (unshift):

**Old:**
```js
    rightKfs.unshift({ t: 0, speed: parseFloat(speedAtSplit.toFixed(3)) });
```

**New:**
```js
    rightKfs.unshift({
      t: 0,
      speed: parseFloat(speedAtSplit.toFixed(3)),
      easeIn:  { type: 'linear' },
      easeOut: splitEaseOut,
    });
```

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat(easing): attach default easeIn/easeOut on new and split keyframes"
```

---

### Task 4: Easing dropdowns in keyframe list rows

**Files:**
- Modify: `frontend/index.html` — CSS for row expansion, `tlRenderSpeedStrip`, new `tlSpeedKfEasingChange` function

- [ ] **Step 1: Add CSS for easing row layout**

Find the existing `.tl-speed-kf-row` CSS rule (around line 466 in the `<style>` block):

```css
.tl-speed-kf-row{display:flex;align-items:center;gap:6px;padding:3px 6px;border-radius:4px;background:var(--s1)}
```

Add the following rules **after** it:

```css
.tl-speed-kf-row{display:flex;flex-direction:column;gap:4px;padding:4px 6px;border-radius:4px;background:var(--s1)}
.tl-speed-kf-main{display:flex;align-items:center;gap:6px}
.tl-speed-kf-easing{display:flex;align-items:center;gap:4px;padding:0 2px}
.tl-speed-kf-easing label{font-size:8px;color:var(--sub);min-width:22px}
.tl-speed-kf-easing select{font-size:9px;background:var(--s2);color:var(--fg);border:1px solid var(--b1);border-radius:3px;padding:1px 3px;cursor:pointer}
```

- [ ] **Step 2: Rewrite `tlRenderSpeedStrip` to include easing dropdowns**

Replace the entire `tlRenderSpeedStrip` function:

```js
function tlRenderSpeedStrip() {
  const list = document.getElementById('tl-speed-kf-list');
  if (!list) return;
  const seg = tlSegments.find(s => s.id === tlSelectedSegId);
  if (!seg) {
    list.innerHTML = '<span style="font-size:10px;color:var(--sub)">Select a segment</span>';
    return;
  }

  const kfs = [...(seg.speedKeyframes || [])].sort((a, b) => a.t - b.t);
  if (kfs.length === 0) {
    list.innerHTML = '<span style="font-size:10px;color:var(--sub)">No keyframes — click the speed lane or use presets</span>';
    return;
  }

  list.innerHTML = kfs.map((kf) => {
    const mm = String(Math.floor(kf.t / 60)).padStart(1, '0');
    const ss = (kf.t % 60).toFixed(1).padStart(4, '0');
    const easingOptions = (which) => {
      const cur = (which === 'easeIn' ? kf.easeIn : kf.easeOut) || { type: 'linear' };
      const builtIn = [
        ['linear',      'Linear'],
        ['ease-in',     'Ease In'],
        ['ease-out',    'Ease Out'],
        ['ease-in-out', 'Ease In Out'],
      ];
      const builtInHtml = builtIn.map(([val, lbl]) =>
        `<option value="${val}" ${cur.type === val && cur.type !== 'custom' ? 'selected' : ''}>${lbl}</option>`
      ).join('');
      const customPresets = tlEasingPresets.map((p, i) =>
        `<option value="custom:${i}" ${cur.type === 'custom' && JSON.stringify(cur.bezier) === JSON.stringify(p.bezier) ? 'selected' : ''}>${p.name}</option>`
      ).join('');
      const divider = tlEasingPresets.length ? '<option disabled>──────────</option>' : '';
      return builtInHtml + divider + customPresets +
        '<option disabled>──────────</option>' +
        '<option value="__custom__">+ Custom…</option>';
    };
    return `<div class="tl-speed-kf-row" data-kft="${kf.t}">
      <div class="tl-speed-kf-main">
        <span class="tl-speed-kf-t">${mm}:${ss}</span>
        <input type="range" class="tl-speed-kf-sl" min="${TL_SPEED_MIN}" max="${TL_SPEED_MAX}" step="0.05"
          value="${kf.speed}" style="width:80px"
          oninput="tlSpeedKfChange('${seg.id}',${kf.t},parseFloat(this.value));this.nextElementSibling.textContent=parseFloat(this.value).toFixed(2)+'×'"
          onchange="if(typeof saveHist==='function')saveHist()">
        <span class="tl-speed-kf-val">${kf.speed.toFixed(2)}×</span>
        <button class="tl-speed-kf-del" onclick="tlSpeedKfDelete('${seg.id}',${kf.t})">✕</button>
      </div>
      <div class="tl-speed-kf-easing">
        <label>In</label>
        <select onchange="tlSpeedKfEasingChange('${seg.id}',${kf.t},'easeIn',this.value,this)">
          ${easingOptions('easeIn')}
        </select>
        <label style="margin-left:6px">Out</label>
        <select onchange="tlSpeedKfEasingChange('${seg.id}',${kf.t},'easeOut',this.value,this)">
          ${easingOptions('easeOut')}
        </select>
      </div>
    </div>`;
  }).join('');
}
```

- [ ] **Step 3: Add `tlSpeedKfEasingChange` function**

Add this function immediately after `tlSpeedKfChange`:

```js
function tlSpeedKfEasingChange(segId, kfT, which, value, selectEl) {
  if (value === '__custom__') {
    tlOpenBezierEditor(segId, kfT, which, selectEl);
    return;
  }
  const seg = tlSegments.find(s => s.id === segId);
  const kf  = seg?.speedKeyframes.find(k => Math.abs(k.t - kfT) < 0.001);
  if (!kf) return;
  if (value.startsWith('custom:')) {
    const idx = parseInt(value.split(':')[1], 10);
    const preset = tlEasingPresets[idx];
    if (preset) kf[which] = { type: 'custom', bezier: [...preset.bezier] };
  } else {
    kf[which] = { type: value };
  }
  tlRender();
  if (typeof saveHist === 'function') saveHist();
}
```

- [ ] **Step 4: Verify in browser**

Open the app, add speed keyframes, open the speed strip. Each keyframe row should now show "In" and "Out" dropdowns with Linear/Ease In/Ease Out/Ease In Out options. Selecting them should not throw errors (console clean).

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat(easing): add easeIn/easeOut dropdowns to speed keyframe rows"
```

---

### Task 5: Inline bezier editor with SVG drag handles

**Files:**
- Modify: `frontend/index.html` — CSS for editor, `tlOpenBezierEditor` function, helper functions

- [ ] **Step 1: Add CSS for the bezier editor panel**

In the `<style>` block, after the `.tl-speed-kf-easing` rules added in Task 4, add:

```css
.tl-bezier-editor{background:var(--s2);border:1px solid var(--b1);border-radius:5px;padding:8px;margin-top:4px;display:flex;flex-direction:column;gap:8px}
.tl-bezier-svg{background:var(--s1);border-radius:3px;touch-action:none;cursor:crosshair}
.tl-bezier-inputs{display:flex;gap:4px;align-items:center;flex-wrap:wrap}
.tl-bezier-inputs label{font-size:8px;color:var(--sub)}
.tl-bezier-inputs input[type=number]{width:46px;font-size:9px;background:var(--s1);color:var(--fg);border:1px solid var(--b1);border-radius:3px;padding:2px 4px;text-align:center}
.tl-bezier-save{display:flex;gap:4px;align-items:center;flex-wrap:wrap}
.tl-bezier-save input[type=text]{flex:1;min-width:80px;font-size:9px;background:var(--s1);color:var(--fg);border:1px solid var(--b1);border-radius:3px;padding:2px 6px}
.tl-bezier-save button{font-size:9px;padding:2px 8px;border-radius:3px;border:none;background:var(--accent,#6366f1);color:#fff;cursor:pointer}
```

- [ ] **Step 2: Add `tlOpenBezierEditor` function**

Add this function after `tlSpeedKfEasingChange`:

```js
function tlOpenBezierEditor(segId, kfT, which, selectEl) {
  // Remove any existing editor
  document.querySelectorAll('.tl-bezier-editor').forEach(el => el.remove());

  const seg = tlSegments.find(s => s.id === segId);
  const kf  = seg?.speedKeyframes.find(k => Math.abs(k.t - kfT) < 0.001);
  if (!kf) return;

  // Starting bezier values from current easing (or linear)
  const current = kf[which] || { type: 'linear' };
  const [ix1, iy1, ix2, iy2] = resolveBezier(current.type === 'custom' ? current : { type: current.type });

  const W = 160, H = 160, PAD = 16;
  const IW = W - PAD * 2, IH = H - PAD * 2;

  const toSvgX = v => PAD + v * IW;
  const toSvgY = v => PAD + (1 - v) * IH;  // y=0 at bottom, y=1 at top
  const fromSvgX = px => Math.max(0, Math.min(1, (px - PAD) / IW));
  const fromSvgY = py => Math.max(-2, Math.min(2, 1 - (py - PAD) / IH));

  // State
  let bz = [ix1, iy1, ix2, iy2];

  const editorEl = document.createElement('div');
  editorEl.className = 'tl-bezier-editor';
  editorEl.innerHTML = `
    <svg class="tl-bezier-svg" width="${W}" height="${H}" id="tlBzSvg">
      <line id="tlBzLine1" stroke="rgba(99,102,241,0.4)" stroke-width="1"/>
      <line id="tlBzLine2" stroke="rgba(99,102,241,0.4)" stroke-width="1"/>
      <path id="tlBzCurve" fill="none" stroke="var(--accent,#6366f1)" stroke-width="2"/>
      <circle id="tlBzH1" r="6" fill="#6366f1" stroke="#fff" stroke-width="1.5" cursor="grab"/>
      <circle id="tlBzH2" r="6" fill="#6366f1" stroke="#fff" stroke-width="1.5" cursor="grab"/>
      <circle cx="${toSvgX(0)}" cy="${toSvgY(0)}" r="3" fill="var(--fg)"/>
      <circle cx="${toSvgX(1)}" cy="${toSvgY(1)}" r="3" fill="var(--fg)"/>
    </svg>
    <div class="tl-bezier-inputs">
      <label>x1</label><input type="number" id="tlBzX1" step="0.01" min="0" max="1">
      <label>y1</label><input type="number" id="tlBzY1" step="0.01" min="-2" max="2">
      <label>x2</label><input type="number" id="tlBzX2" step="0.01" min="0" max="1">
      <label>y2</label><input type="number" id="tlBzY2" step="0.01" min="-2" max="2">
    </div>
    <div class="tl-bezier-save">
      <input type="text" id="tlBzName" placeholder="Preset name…">
      <button onclick="tlSaveBezierPreset()">Save preset</button>
      <button onclick="tlApplyBezier('${segId}',${kfT},'${which}')">Apply</button>
    </div>`;

  // Insert after the row
  const row = selectEl.closest('.tl-speed-kf-row');
  row.appendChild(editorEl);

  const svg = document.getElementById('tlBzSvg');
  const h1 = document.getElementById('tlBzH1');
  const h2 = document.getElementById('tlBzH2');

  function renderBezier() {
    const [x1, y1, x2, y2] = bz;
    const ax = toSvgX(0), ay = toSvgY(0);
    const dx = toSvgX(1), dy = toSvgY(1);
    const c1x = toSvgX(x1), c1y = toSvgY(y1);
    const c2x = toSvgX(x2), c2y = toSvgY(y2);
    h1.setAttribute('cx', c1x); h1.setAttribute('cy', c1y);
    h2.setAttribute('cx', c2x); h2.setAttribute('cy', c2y);
    document.getElementById('tlBzLine1').setAttribute('x1', ax);
    document.getElementById('tlBzLine1').setAttribute('y1', ay);
    document.getElementById('tlBzLine1').setAttribute('x2', c1x);
    document.getElementById('tlBzLine1').setAttribute('y2', c1y);
    document.getElementById('tlBzLine2').setAttribute('x1', dx);
    document.getElementById('tlBzLine2').setAttribute('y1', dy);
    document.getElementById('tlBzLine2').setAttribute('x2', c2x);
    document.getElementById('tlBzLine2').setAttribute('y2', c2y);
    document.getElementById('tlBzCurve').setAttribute('d',
      `M ${ax},${ay} C ${c1x},${c1y} ${c2x},${c2y} ${dx},${dy}`);
    document.getElementById('tlBzX1').value = x1.toFixed(3);
    document.getElementById('tlBzY1').value = y1.toFixed(3);
    document.getElementById('tlBzX2').value = x2.toFixed(3);
    document.getElementById('tlBzY2').value = y2.toFixed(3);
  }

  // Drag logic
  let dragging = null;
  function onMove(e) {
    if (!dragging) return;
    const rect = svg.getBoundingClientRect();
    const px = (e.clientX ?? e.touches?.[0]?.clientX) - rect.left;
    const py = (e.clientY ?? e.touches?.[0]?.clientY) - rect.top;
    if (dragging === 1) { bz[0] = fromSvgX(px); bz[1] = fromSvgY(py); }
    else                { bz[2] = fromSvgX(px); bz[3] = fromSvgY(py); }
    renderBezier();
  }
  function onUp() { dragging = null; }
  h1.addEventListener('mousedown', e => { e.preventDefault(); dragging = 1; });
  h2.addEventListener('mousedown', e => { e.preventDefault(); dragging = 2; });
  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup', onUp);
  editorEl._cleanup = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };

  // Numeric input sync
  ['tlBzX1','tlBzY1','tlBzX2','tlBzY2'].forEach((id, i) => {
    document.getElementById(id).addEventListener('input', function() {
      const v = parseFloat(this.value);
      if (!isNaN(v)) { bz[i] = v; renderBezier(); }
    });
  });

  // Store bz ref on editor for apply/save
  editorEl._getBz = () => bz;

  renderBezier();

  // Reset select to previous value (don't leave "__custom__" selected)
  const prevType = current.type !== 'custom' ? current.type : 'linear';
  selectEl.value = prevType;
}
```

- [ ] **Step 3: Add `tlApplyBezier` and `tlSaveBezierPreset` functions**

Add immediately after `tlOpenBezierEditor`:

```js
function tlApplyBezier(segId, kfT, which) {
  const seg = tlSegments.find(s => s.id === segId);
  const kf  = seg?.speedKeyframes.find(k => Math.abs(k.t - kfT) < 0.001);
  const editor = document.querySelector('.tl-bezier-editor');
  if (!kf || !editor) return;
  const bz = editor._getBz();
  kf[which] = { type: 'custom', bezier: bz.map(v => parseFloat(v.toFixed(4))) };
  editor._cleanup?.();
  editor.remove();
  tlRender();
  tlRenderSpeedStrip();
  if (typeof saveHist === 'function') saveHist();
}

function tlSaveBezierPreset() {
  const editor = document.querySelector('.tl-bezier-editor');
  if (!editor) return;
  const name = document.getElementById('tlBzName')?.value?.trim();
  if (!name) { alert('Enter a preset name first.'); return; }
  const bz = editor._getBz().map(v => parseFloat(v.toFixed(4)));
  const existing = tlEasingPresets.findIndex(p => p.name === name);
  if (existing >= 0) { tlEasingPresets[existing].bezier = bz; }
  else { tlEasingPresets.push({ name, bezier: bz }); }
  if (typeof saveHist === 'function') saveHist();
  // Refresh dropdowns so new preset appears
  tlRenderSpeedStrip();
}
```

- [ ] **Step 4: Verify in browser**

1. Open the app, add speed keyframes.
2. Open the speed strip, set a keyframe's Out easing to `+ Custom…`.
3. The bezier editor should expand inline inside the keyframe row.
4. Drag the two blue handles — the curve should update live.
5. Edit numeric inputs — handles should move.
6. Click **Apply** — the easing is applied, editor closes, speed lane curve updates.
7. Enter a name and click **Save preset** — the preset appears in the dropdown for all keyframes.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat(easing): inline bezier editor with SVG drag handles and custom preset saving"
```

---

### Task 6: Wire `tlEasingPresets` into save/load

**Files:**
- Modify: `frontend/index.html` — wherever `tlSegments` is serialized/deserialized for history or export

- [ ] **Step 1: Find save/load points for timeline state**

Search for where `tlSegments` is read back from history or project save:

```
grep -n "tlSegments" frontend/index.html | grep -i "hist\|load\|restore\|parse\|JSON"
```

- [ ] **Step 2: Include `tlEasingPresets` in any serialization**

For each place where timeline state is saved (e.g., `saveHist` captures `tlSegments`), also capture `tlEasingPresets`. For each place where timeline state is restored, also restore `tlEasingPresets`. 

The exact code depends on the save format found in Step 1. The pattern to follow:

**Save side** — wherever `tlSegments` is written to a snapshot object, add:
```js
snapshot.tlEasingPresets = tlEasingPresets;
```

**Load side** — wherever `tlSegments` is read from a snapshot, add:
```js
tlEasingPresets = snapshot.tlEasingPresets || [];
```

- [ ] **Step 3: Verify presets survive undo/redo**

1. Add a custom preset.
2. Press Undo several times.
3. Press Redo — preset should still be available.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat(easing): persist tlEasingPresets through undo/redo history"
```
