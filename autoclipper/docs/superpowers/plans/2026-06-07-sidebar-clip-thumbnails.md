# Sidebar Clip Thumbnails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show each downloaded clip in the sidebar with a video thumbnail and its YouTube title instead of a colored dot and filename.

**Architecture:** ffmpeg extracts a still frame after each download and saves it as `{job_id}_thumb.jpg` in the `downloads/` folder. The path is returned through the existing SSE `done` message. The frontend attaches it to the clip object and renders it in `tlRenderClipList()`.

**Tech Stack:** Python (ffmpeg subprocess), Flask (static file serving already in place), vanilla JS, CSS

---

## File Map

| File | Change |
|---|---|
| `downloader.py` | Add `extract_thumbnail()` function; call it in `download_video()` |
| `app.py` | No change needed — `done` message is built from `download_video()` return dict via `**info` spread |
| `frontend/index.html` | (1) Add `thumbnail` to clip object on SSE done; (2) update `tlRenderClipList()` card HTML; (3) update CSS |
| `tests/test_downloader.py` | Add test for `extract_thumbnail()` |

---

### Task 1: Add `extract_thumbnail()` to `downloader.py`

**Files:**
- Modify: `downloader.py`
- Test: `tests/test_downloader.py`

- [ ] **Step 1: Write the failing test**

Open `tests/test_downloader.py` and add at the bottom:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from downloader import extract_thumbnail, DOWNLOADS_DIR


def test_extract_thumbnail_returns_path_on_success(tmp_path):
    """extract_thumbnail runs ffmpeg and returns the thumbnail path."""
    fake_video = tmp_path / "abc123.mp4"
    fake_video.write_bytes(b"fake")
    expected_thumb = tmp_path / "abc123_thumb.jpg"

    with patch("downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = extract_thumbnail(str(fake_video), "abc123", base_dir=tmp_path)

    assert result == str(expected_thumb)
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "-ss" in args
    assert str(fake_video) in args
    assert str(expected_thumb) in args


def test_extract_thumbnail_returns_none_on_failure(tmp_path):
    """extract_thumbnail returns None when ffmpeg fails."""
    fake_video = tmp_path / "abc123.mp4"
    fake_video.write_bytes(b"fake")

    with patch("downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = extract_thumbnail(str(fake_video), "abc123", base_dir=tmp_path)

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_downloader.py::test_extract_thumbnail_returns_path_on_success tests/test_downloader.py::test_extract_thumbnail_returns_none_on_failure -v
```

Expected: FAIL with `ImportError: cannot import name 'extract_thumbnail'`

- [ ] **Step 3: Implement `extract_thumbnail()` in `downloader.py`**

Add this function after `probe_video()` (line 65):

```python
def extract_thumbnail(video_path: str, job_id: str, base_dir: Path | None = None) -> str | None:
    """Extract a single frame at t=1s from the video and save as {job_id}_thumb.jpg.

    Returns the thumbnail path string on success, or None on failure.
    """
    if base_dir is None:
        base_dir = DOWNLOADS_DIR
    thumb_path = Path(base_dir) / f"{job_id}_thumb.jpg"
    cmd = [
        "ffmpeg", "-y",
        "-ss", "1",
        "-i", video_path,
        "-vframes", "1",
        "-vf", "scale=320:-1",
        "-q:v", "5",
        str(thumb_path),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        return None
    return str(thumb_path)
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_downloader.py::test_extract_thumbnail_returns_path_on_success tests/test_downloader.py::test_extract_thumbnail_returns_none_on_failure -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add downloader.py tests/test_downloader.py
git commit -m "feat: add extract_thumbnail() to generate jpeg frame from downloaded video"
```

---

### Task 2: Call `extract_thumbnail()` inside `download_video()` and return thumbnail URL

**Files:**
- Modify: `downloader.py` (lines 31-55)
- Test: `tests/test_downloader.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_downloader.py`:

```python
def test_download_video_includes_thumbnail(tmp_path):
    """download_video() return dict includes a 'thumbnail' key."""
    from downloader import download_video

    fake_mp4 = tmp_path / "testjob.mp4"

    def fake_popen(cmd, **kwargs):
        fake_mp4.write_bytes(b"fake")
        m = MagicMock()
        m.stdout = iter(["[download]  100% of 1.00MiB\n"])
        m.returncode = 0
        m.wait = lambda: None
        return m

    probe_data = {
        "streams": [{"width": 1920, "height": 1080, "duration": "10.0"}]
    }

    with patch("downloader.subprocess.Popen", side_effect=fake_popen), \
         patch("downloader.get_video_title", return_value="Test Title"), \
         patch("downloader.subprocess.run") as mock_run, \
         patch("downloader.get_job_path", return_value=fake_mp4), \
         patch("downloader.DOWNLOADS_DIR", tmp_path):
        # First call to subprocess.run is ffprobe (probe_video), second is ffmpeg (thumbnail)
        probe_result = MagicMock(returncode=0, stdout='{"streams":[{"width":1920,"height":1080,"duration":"10.0"}]}')
        thumb_result = MagicMock(returncode=0)
        mock_run.side_effect = [probe_result, thumb_result]

        result = download_video("https://example.com/video", "testjob")

    assert "thumbnail" in result
    assert result["thumbnail"] is not None or result["thumbnail"] is None  # presence required
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_downloader.py::test_download_video_includes_thumbnail -v
```

Expected: FAIL — `thumbnail` key missing from result

- [ ] **Step 3: Update `download_video()` to call `extract_thumbnail()`**

In `downloader.py`, replace the last line of `download_video()`:

```python
# Before:
    return {"path": str(output), "title": title, **probe_video(str(output))}
```

```python
# After:
    info = {"path": str(output), "title": title, **probe_video(str(output))}
    thumb = extract_thumbnail(str(output), job_id)
    if thumb:
        # Convert absolute path to a URL the browser can fetch
        thumb_filename = Path(thumb).name
        info["thumbnail"] = "/api/downloads/" + thumb_filename
    else:
        info["thumbnail"] = None
    return info
```

- [ ] **Step 4: Run all downloader tests**

```
pytest tests/test_downloader.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add downloader.py tests/test_downloader.py
git commit -m "feat: include thumbnail URL in download_video() return dict"
```

---

### Task 3: Update frontend clip object and `tlRenderClipList()` CSS

**Files:**
- Modify: `frontend/index.html`

This task updates the CSS only so the new card layout has styles ready before the JS is changed.

- [ ] **Step 1: Find and replace the clip card CSS block**

In `frontend/index.html`, find the existing clip card styles (around lines 55–64). Replace the entire block:

```css
/* Before — lines ~55–64: */
#clip-list{display:flex;flex-direction:column;gap:5px;padding:0 10px;overflow-y:auto;max-height:200px}
#clip-list::-webkit-scrollbar{width:3px}
#clip-list::-webkit-scrollbar-thumb{background:var(--mut);border-radius:2px}
.clip-card{padding:8px 10px;border-radius:var(--r);border:1px solid var(--b1);background:var(--s2);display:flex;align-items:flex-start;gap:6px}
.clip-card-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;margin-top:4px}
.clip-card-body{flex:1;min-width:0}
.clip-card-name{font-size:11px;color:var(--tx);font-weight:600;word-break:break-all;line-height:1.4}
.clip-card-meta{font-size:10px;color:var(--sub);margin-top:2px}
.clip-card-rm{flex-shrink:0;width:18px;height:18px;border:none;background:transparent;color:var(--sub);cursor:pointer;border-radius:4px;display:flex;align-items:center;justify-content:center;padding:0;transition:.1s}
.clip-card-rm:hover{background:rgba(244,63,94,0.15);color:var(--danger)}
```

```css
/* After — new clip card styles: */
#clip-list{display:flex;flex-direction:column;gap:6px;padding:0 10px;overflow-y:auto;flex:1}
#clip-list::-webkit-scrollbar{width:3px}
#clip-list::-webkit-scrollbar-thumb{background:var(--mut);border-radius:2px}
.clip-card{border-radius:var(--r);border:1px solid var(--b1);background:var(--s2);overflow:hidden;display:flex;flex-direction:column}
.clip-thumb-wrap{position:relative;width:100%;aspect-ratio:16/9;background:var(--s3);flex-shrink:0}
.clip-thumb{width:100%;height:100%;object-fit:cover;display:block}
.clip-thumb-placeholder{width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:var(--sub)}
.clip-dur-badge{position:absolute;bottom:5px;right:5px;background:rgba(0,0,0,0.72);color:#fff;font-size:10px;font-weight:700;padding:1px 5px;border-radius:4px;line-height:1.5}
.clip-info{display:flex;align-items:flex-start;gap:4px;padding:6px 8px}
.clip-title{flex:1;font-size:11px;color:var(--tx);font-weight:600;line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.clip-card-rm{flex-shrink:0;width:18px;height:18px;border:none;background:transparent;color:var(--sub);cursor:pointer;border-radius:4px;display:flex;align-items:center;justify-content:center;padding:0;transition:.1s;margin-top:1px}
.clip-card-rm:hover{background:rgba(244,63,94,0.15);color:var(--danger)}
```

- [ ] **Step 2: Verify the page still loads without visual errors**

Open the app in the browser (`python app.py` then `http://localhost:5000`). The sidebar should look roughly the same (no clips downloaded yet). No console errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "style: update clip card CSS for thumbnail layout"
```

---

### Task 4: Update JS — clip object and `tlRenderClipList()`

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add `thumbnail` field to the clip object on SSE done**

Find the clip object construction in the SSE `done` handler (around line 4405):

```js
// Before:
const clip = {
  id: 'clip_' + Math.random().toString(36).slice(2, 9),
  path: msg.path,
  url: '/api/downloads/' + encodeURIComponent(filename),
  caption: msg.title || '',
  duration: msg.duration,
};
```

```js
// After:
const clip = {
  id: 'clip_' + Math.random().toString(36).slice(2, 9),
  path: msg.path,
  url: '/api/downloads/' + encodeURIComponent(filename),
  caption: msg.title || '',
  duration: msg.duration,
  thumbnail: msg.thumbnail || null,
};
```

- [ ] **Step 2: Replace `tlRenderClipList()` with the new card template**

Find `function tlRenderClipList()` (around line 5166) and replace the entire function:

```js
function tlRenderClipList() {
  const list = document.getElementById('clip-list');
  if (!list) return;
  if (!tlClips.length) { list.innerHTML = ''; return; }
  list.innerHTML = tlClips.map(clip => {
    const dur = Math.round(clip.duration);
    const thumbHtml = clip.thumbnail
      ? `<img class="clip-thumb" src="${clip.thumbnail}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
        + `<div class="clip-thumb-placeholder" style="display:none"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2"/><polygon points="10,8 16,12 10,16"/></svg></div>`
      : `<div class="clip-thumb-placeholder"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2"/><polygon points="10,8 16,12 10,16"/></svg></div>`;
    return `<div class="clip-card">
      <div class="clip-thumb-wrap">
        ${thumbHtml}
        <span class="clip-dur-badge">${dur}s</span>
      </div>
      <div class="clip-info">
        <div class="clip-title"></div>
        <button class="clip-card-rm" onclick="tlRemoveClip('${clip.id}')" title="Remove clip">
          <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    </div>`;
  }).join('');
  // Set titles safely via textContent (prevents XSS)
  Array.from(list.children).forEach((card, i) => {
    const titleEl = card.querySelector('.clip-title');
    if (titleEl) titleEl.textContent = tlClips[i].caption || tlClips[i].path.split(/[\\/]/).pop();
  });
}
```

- [ ] **Step 3: Manually test**

1. Run `python app.py`
2. Open `http://localhost:5000`
3. Download a YouTube video
4. Verify the sidebar shows:
   - A thumbnail image (frame from the video)
   - The YouTube title below it (2-line clamp)
   - A duration badge (e.g. `42s`) overlaid bottom-right of the thumbnail
   - A × remove button
5. Click × — card disappears, clip is removed

- [ ] **Step 4: Test thumbnail fallback**

In DevTools, set `clip.thumbnail = null` on a clip in `tlClips`, then call `tlRenderClipList()`. The card should show a film-strip placeholder icon instead of a broken image.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat: show thumbnail and YouTube title in sidebar clip cards"
```
