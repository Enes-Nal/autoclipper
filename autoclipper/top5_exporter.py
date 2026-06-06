import os, subprocess, uuid  # used by render_slot / export_top5 (added in later tasks)
from concurrent.futures import ThreadPoolExecutor, as_completed  # used by export_top5 (added in later tasks)
from pathlib import Path

from exporter import build_filter_graph  # used by render_slot (added in later tasks)
from text_renderer import render_text_layer  # used by render_slot (added in later tasks)

EXPORTS_DIR = Path(__file__).parent / "exports"
TEMP_DIR    = Path(__file__).parent / "temp"
for _d in (EXPORTS_DIR, TEMP_DIR):
    _d.mkdir(exist_ok=True)


def resolve_placeholders(text: str, slots: list[dict], current_idx: int) -> str:
    """Replace <current:rank>, <current:title>, <slotN:rank>, <slotN:title> tokens."""
    text = text.replace("<current:rank>",  str(slots[current_idx]["rank"]))
    text = text.replace("<current:title>", slots[current_idx]["title"])
    for i, slot in enumerate(slots):
        n = i + 1
        text = text.replace(f"<slot{n}:rank>",  str(slot["rank"]))
        title = slot["title"] if i <= current_idx else "—"
        text = text.replace(f"<slot{n}:title>", title)
    return text


def render_slot(slot: dict, all_slots: list[dict], slot_idx: int,
                template: dict, job_id: str, temp_dir: Path) -> str:
    """Render one slot's clip with template overlay to a temp mp4. Returns output path."""
    layers = [dict(l) for l in template["layers"]]
    cw = template["canvas"]["width"]
    ch = template["canvas"]["height"]

    # Resolve placeholders in every text layer
    for l in layers:
        if l["type"] == "text":
            l["text"] = resolve_placeholders(l.get("text", ""), all_slots, slot_idx)

    # Render text layers to PNGs in parallel
    text_jobs = []
    for i, l in enumerate(layers):
        if l["type"] == "text":
            p = str(temp_dir / f"{job_id}_s{slot_idx}_t{i}.png")
            rl = dict(l)
            rl["auto_height"]    = l.get("_autoHeight", True)
            rl["vertical_align"] = l.get("_verticalAlign", "top")
            rl["emoji_offset"]   = l.get("_emojiOffset", 0)
            text_jobs.append((i, p, rl))

    try:
        if text_jobs:
            with ThreadPoolExecutor(max_workers=min(len(text_jobs), os.cpu_count() or 4)) as ex:
                futs = [ex.submit(render_text_layer, rl, cw, ch, p) for _, p, rl in text_jobs]
                for f in as_completed(futs):
                    f.result()

        # Map text PNGs to input indices (0 = the video clip)
        extra_inputs = []
        text_pngs = {}
        for layer_idx, p, _ in text_jobs:
            text_pngs[layer_idx] = 1 + len(extra_inputs)
            extra_inputs.append(p)

        filter_parts, final_label = build_filter_graph(
            layers, cw, ch, text_pngs, {}, {}, src_video_label="0:v"
        )

        out_path = str(temp_dir / f"{job_id}_slot{slot_idx}.mp4")
        clip_path = slot["path"]
        start = float(slot.get("start", 0))
        end   = float(slot.get("end",   0))

        cmd = ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", clip_path]
        for inp in extra_inputs:
            cmd += ["-i", inp]

        if filter_parts:
            cmd += ["-filter_complex", ";".join(filter_parts), "-map", f"[{final_label}]"]
        else:
            cmd += ["-map", "0:v"]

        cmd += [
            "-map", "0:a?",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed for slot {slot_idx}:\n{result.stderr.decode()[-2000:]}")

        return out_path
    finally:
        for _, p, _ in text_jobs:
            try:
                os.remove(p)
            except OSError:
                pass


def concat_segments(temp_files: list[str], job_id: str) -> str:
    """Concatenate temp mp4 files into a single exports/ output. Returns output path."""
    list_path = str(TEMP_DIR / f"{job_id}_concat.txt")
    with open(list_path, "w") as f:
        for p in temp_files:
            # FFmpeg concat demuxer requires forward slashes even on Windows
            f.write(f"file '{p.replace(chr(92), '/')}'\n")

    out_path = str(EXPORTS_DIR / f"top5_{job_id}.mp4")
    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
         "-c", "copy", out_path],
        capture_output=True,
    )
    try:
        os.remove(list_path)
    except OSError:
        pass

    if result.returncode != 0:
        raise RuntimeError(f"Concat failed:\n{result.stderr.decode()[-2000:]}")
    return out_path


def export_top5(slots: list[dict], template: dict, job_id: str,
                on_progress=None) -> str:
    """Render each slot, concat, return output path."""
    temp_files = []
    for i, slot in enumerate(slots):
        if on_progress:
            on_progress({"type": "progress", "slot": i + 1, "total": len(slots)})
        temp_files.append(render_slot(slot, slots, i, template, job_id, TEMP_DIR))

    out = concat_segments(temp_files, job_id)

    for p in temp_files:
        try:
            os.remove(p)
        except OSError:
            pass

    return out
