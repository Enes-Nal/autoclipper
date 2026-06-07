import subprocess, uuid, os, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from text_renderer import render_text_layer

EXPORTS_DIR = Path(__file__).parent / "exports"
TEMP_DIR = Path(__file__).parent / "temp"
for d in (EXPORTS_DIR, TEMP_DIR):
    d.mkdir(exist_ok=True)

def render_mask_png(shape: str, w: int, h: int, radius: int,
                    points: list, path: str) -> None:
    """
    Render a white-on-black mask PNG at w×h pixels.
    shape: "rect" | "rounded_rect" | "circle" | "polygon"
    radius: corner radius in pixels (rounded_rect only)
    points: normalised [[x,y],...] vertices (polygon only, 0-1 relative to w/h)
    path: output file path
    """
    from PIL import Image, ImageDraw
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    if shape == "rect":
        draw.rectangle([0, 0, w - 1, h - 1], fill=255)
    elif shape == "rounded_rect":
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=max(0, radius), fill=255)
    elif shape == "circle":
        draw.ellipse([0, 0, w - 1, h - 1], fill=255)
    elif shape == "polygon" and points:
        pts = [(int(p[0] * w), int(p[1] * h)) for p in points]
        draw.polygon(pts, fill=255)
    img.save(path)


def _color_filter_suffix(c: dict) -> str:
    """Return eq/hue filter suffix string (e.g. ',eq=brightness=0.1,hue=h=10') or ''."""
    brightness = float(c.get('brightness', 0))
    contrast   = float(c.get('contrast',   0))
    saturation = float(c.get('saturation', 0))
    hue        = float(c.get('hue',        0))
    eq_parts = []
    if brightness != 0:
        eq_parts.append(f"brightness={brightness/100:.3f}")
    if contrast != 0:
        eq_parts.append(f"contrast={1.0 + contrast/100:.3f}")
    if saturation != 0:
        eq_parts.append(f"saturation={1.0 + saturation/100:.3f}")
    suffix = (',eq=' + ':'.join(eq_parts)) if eq_parts else ''
    if hue != 0:
        suffix += f",hue=h={hue}"
    return suffix


def _speed_kfs_to_subsegs(seg: dict) -> list[tuple[float, float, float]]:
    """
    Convert a segment's speedKeyframes into constant-speed intervals.
    Returns [(start, end, speed)] where start/end are absolute source times.
    """
    kfs = seg.get('speedKeyframes', []) or []
    ss  = float(seg.get('sourceStart', 0))
    se  = float(seg.get('sourceEnd',   0))

    if not kfs:
        return [(ss, se, 1.0)]

    sorted_kfs = sorted(kfs, key=lambda k: float(k['t']))

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

    # Breakpoints: segment start, each keyframe (absolute), segment end
    abs_breakpoints = sorted(set(
        [ss] + [ss + float(k['t']) for k in sorted_kfs] + [se]
    ))
    abs_breakpoints = [max(ss, min(se, p)) for p in abs_breakpoints]
    abs_breakpoints = sorted(set(abs_breakpoints))

    result = []
    for i in range(len(abs_breakpoints) - 1):
        a, b = abs_breakpoints[i], abs_breakpoints[i + 1]
        if b - a < 0.01:  # skip sub-10ms intervals
            continue
        mid_rel = ((a + b) / 2) - ss
        speed = interp(mid_rel)
        result.append((a, b, round(speed, 4)))

    return result if result else [(ss, se, 1.0)]


def build_segment_inputs(video_path: str, segments: list, input_offset: int = 0) -> tuple[list, list, list, str, str, int]:
    """
    Use input-level -ss/-to seeking instead of trim filters so FFmpeg can seek
    directly to the segment start rather than decoding the whole video.
    Segments with speedKeyframes are expanded into constant-speed sub-clips.

    Returns:
        main_pre_args   – seek args to insert before the main -i video_path
                          (empty when no segments)
        extra_vid_inputs – list of (pre_args, path) for segments 1..N-1
                          (empty for single/no segment)
        filter_parts    – filter_complex fragments (color grading + concat)
        video_label     – stream label to use as src_video_label downstream
        audio_label     – stream label to use as src_audio_label downstream
        n_video_inputs  – total video -i entries added (always ≥1)
    """
    if not segments:
        return [], [], [], f'{input_offset}:v', f'{input_offset}:a', 1

    segs = sorted(segments, key=lambda s: s.get('trackStart', 0))

    n = [0]
    def lbl(prefix='s'):
        n[0] += 1
        return f"{prefix}{n[0]}"

    # Expand each segment into constant-speed sub-segments
    all_subsegs = []  # list of {sourceStart, sourceEnd, speed, color}
    for seg in segs:
        c = seg.get('color', {}) or {}
        for (a, b, speed) in _speed_kfs_to_subsegs(seg):
            all_subsegs.append({'sourceStart': a, 'sourceEnd': b, 'speed': speed, 'color': c})

    n_inputs = len(all_subsegs)

    # Single sub-segment fast path (no speed change or color)
    if n_inputs == 1:
        sub = all_subsegs[0]
        ss = sub['sourceStart']
        se = sub['sourceEnd']
        speed = sub['speed']
        c = sub['color']
        main_pre_args = ["-ss", str(ss), "-to", str(se)]
        color_suffix = _color_filter_suffix(c)
        speed_is_normal = abs(speed - 1.0) <= 0.001
        if speed_is_normal and not color_suffix:
            return main_pre_args, [], [], f'{input_offset}:v', f'{input_offset}:a', 1
        vl = lbl('sv')
        al = lbl('sa')
        if speed_is_normal:
            filter_parts = [
                f"[{input_offset}:v]setpts=PTS-STARTPTS{color_suffix}[{vl}]",
                f"[{input_offset}:a]asetpts=PTS-STARTPTS[{al}]",
            ]
        else:
            filter_parts = [
                f"[{input_offset}:v]setpts=PTS*(1/{speed:.6f}){color_suffix}[{vl}]",
                f"[{input_offset}:a]asetpts=PTS*(1/{speed:.6f})[{al}]",
            ]
        return main_pre_args, [], filter_parts, vl, al, 1

    # Multiple sub-segments: each gets its own -i entry with input-level seek
    filter_parts = []
    vlabels = []
    alabels = []
    extra_vid_inputs = []
    main_pre_args = []

    for i, sub in enumerate(all_subsegs):
        ss    = sub['sourceStart']
        se    = sub['sourceEnd']
        speed = sub['speed']
        c     = sub['color']
        pre_args = ["-ss", str(ss), "-to", str(se)]
        if i == 0:
            main_pre_args = pre_args
        else:
            extra_vid_inputs.append((pre_args, video_path))

        stream_i = input_offset + i
        vl = lbl('sv')
        al = lbl('sa')
        color_suffix = _color_filter_suffix(c)
        speed_is_normal = abs(speed - 1.0) <= 0.001
        if speed_is_normal:
            filter_parts.append(f"[{stream_i}:v]setpts=PTS-STARTPTS{color_suffix}[{vl}]")
            filter_parts.append(f"[{stream_i}:a]asetpts=PTS-STARTPTS[{al}]")
        else:
            filter_parts.append(f"[{stream_i}:v]setpts=PTS*(1/{speed:.6f}){color_suffix}[{vl}]")
            filter_parts.append(f"[{stream_i}:a]asetpts=PTS*(1/{speed:.6f})[{al}]")
        vlabels.append(vl)
        alabels.append(al)

    vout = lbl('vc')
    filter_parts.append(''.join(f'[{l}]' for l in vlabels) + f'concat=n={n_inputs}:v=1:a=0[{vout}]')
    aout = lbl('ac')
    filter_parts.append(''.join(f'[{l}]' for l in alabels) + f'concat=n={n_inputs}:v=0:a=1[{aout}]')
    return main_pre_args, extra_vid_inputs, filter_parts, vout, aout, n_inputs


def build_filter_graph(layers: list, cw: int, ch: int,
                       text_pngs: dict, image_inputs: dict,
                       mask_inputs: dict = None,
                       src_video_label: str = '0:v') -> tuple[list, str]:
    if mask_inputs is None:
        mask_inputs = {}
    """
    Pure function: build FFmpeg filter_complex parts from template layers.
    text_pngs: {layer_index: input_stream_index}
    image_inputs: {layer_index: input_stream_index}
    Returns (filter_parts_list, final_label).
    """
    parts = []
    current = None
    n = [0]

    def lbl():
        n[0] += 1
        return f"v{n[0]}"

    # [0:v] can only be consumed once in filter_complex; pre-split if needed
    raw_uses = sum(1 for l in layers if l["type"] in ("blur_video", "video"))
    if raw_uses >= 2:
        split_labels = [f"sv{i}" for i in range(raw_uses)]
        parts.append(f"[{src_video_label}]split={raw_uses}{''.join(f'[{lb}]' for lb in split_labels)}")
        _raw_iter = iter(split_labels)
    else:
        _raw_iter = iter([src_video_label] if raw_uses == 1 else [])

    def next_raw():
        return next(_raw_iter)

    for i, layer in enumerate(layers):
        t = layer["type"]

        if t == "blur_video":
            blur = layer.get("blur", 20)
            raw = next_raw()
            out = lbl()
            parts.append(
                f"[{raw}]scale={cw}:{ch}:force_original_aspect_ratio=increase,"
                f"crop={cw}:{ch},boxblur=luma_radius={blur}:luma_power=1,setsar=1[{out}]"
            )
            current = out

        elif t == "video":
            x, y = layer.get("x", 0), layer.get("y", 0)
            w, h = layer.get("width", cw), layer.get("height", int(ch * 0.32))
            fit = layer.get("fit", "contain")
            raw = next_raw()
            scaled = lbl()
            if fit == "contain":
                parts.append(
                    f"[{raw}]scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black[{scaled}]"
                )
            elif fit == "cover":
                # Always scale/crop to full canvas so the center of the source
                # is visible regardless of how small the layer frame is.
                parts.append(
                    f"[{raw}]scale={cw}:{ch}:force_original_aspect_ratio=increase,"
                    f"crop={cw}:{ch}[{scaled}]"
                )
                x, y = 0, 0  # cover fills the canvas from top-left
            else:
                parts.append(f"[{raw}]scale={w}:{h}[{scaled}]")
            # Apply mask if present
            composited = scaled
            if i in mask_inputs:
                mask_idx = mask_inputs[i]
                mask_scaled = lbl()
                scaled_rgba = lbl()
                masked = lbl()
                parts.append(f"[{mask_idx}:v]scale={w}:{h}[{mask_scaled}]")
                # alphamerge requires the base input to have an alpha channel
                parts.append(f"[{scaled}]format=rgba[{scaled_rgba}]")
                parts.append(f"[{scaled_rgba}][{mask_scaled}]alphamerge[{masked}]")
                composited = masked

            if current:
                out = lbl()
                parts.append(f"[{current}][{composited}]overlay=x={int(x)}:y={int(y)}[{out}]")
                current = out
            else:
                # Video is the first layer — x/y must still be applied.
                # Use a color source + overlay so negative offsets (partial
                # off-screen positioning) are handled correctly; pad filters
                # reject negative offsets with EINVAL.
                if x == 0 and y == 0:
                    current = composited
                else:
                    ix, iy = int(x), int(y)
                    bg = lbl()
                    positioned = lbl()
                    parts.append(
                        f"color=c=black:s={int(cw)}x{int(ch)}:r=60[{bg}]"
                    )
                    parts.append(
                        f"[{bg}][{composited}]overlay=x={ix}:y={iy}:shortest=1[{positioned}]"
                    )
                    current = positioned

        elif t == "text":
            if i in text_pngs:
                idx = text_pngs[i]
                out = lbl()
                parts.append(f"[{current}][{idx}:v]overlay=x=0:y=0[{out}]")
                current = out

        elif t in ("image", "emoji") and i in image_inputs:
            idx = image_inputs[i]
            x, y = layer.get("x", 0), layer.get("y", 0)
            out = lbl()
            parts.append(f"[{current}][{idx}:v]overlay=x={int(x)}:y={int(y)}[{out}]")
            current = out

        elif t == "shape":
            x, y = layer.get("x", 0), layer.get("y", 0)
            w, h2 = layer.get("width", cw), layer.get("height", 60)
            fc = layer.get("fill", "#000000").lstrip("#")
            op = layer.get("opacity", 1.0)
            out = lbl()
            parts.append(
                f"[{current}]drawbox=x={x}:y={y}:w={w}:h={h2}:"
                f"color=0x{fc}@{op}:t=fill[{out}]"
            )
            current = out

    # Enforce canvas bounds: pad up to canvas size if too small (e.g. no full-canvas
    # base layer), then crop to exact canvas size if content overflows.
    if current:
        out = lbl()
        parts.append(
            f"[{current}]pad='max(iw,{cw})':'max(ih,{ch})':0:0:color=black,"
            f"crop={cw}:{ch}:0:0[{out}]"
        )
        current = out

    return parts, current or "0:v"


def build_audio_cmd_parts(
    layers: list,
    audio_layer,
    next_input_idx: int,
    src_audio_label: str = '0:a',
):
    """
    Build FFmpeg audio filter parts for video layer volume/mute, SFX layers,
    and an optional audio layer (music track).

    Returns:
        music_inputs  – list of music file paths (0 or 1 items) for -i args
        sfx_inputs    – list of SFX file paths for -i args (no trim/seek)
        filter_parts  – filter_complex fragment strings (no semicolons)
        audio_label   – the label/stream to use for -map audio output
    """
    music_inputs = []
    sfx_inputs = []
    filter_parts = []
    n = [0]

    def albl():
        n[0] += 1
        return f"a{n[0]}"

    # ── Step 1: Video audio volume/mute ──────────────────────────────────────
    video_vol = 1.0
    video_muted = False
    for l in layers:
        if l.get("type") == "video":
            video_vol = float(l.get("volume", 1.0))
            video_muted = bool(l.get("muted", False))
            break

    effective_vol = 0.0 if video_muted else video_vol
    if effective_vol != 1.0:
        out = albl()
        filter_parts.append(f"[{src_audio_label}]volume={effective_vol}[{out}]")
        vid_audio_label = out
    else:
        vid_audio_label = src_audio_label

    # ── Step 2: SFX layers ───────────────────────────────────────────────────
    active_sfx = [
        l for l in layers
        if l.get("type") == "sfx"
        and not l.get("muted", False)
        and l.get("src")
    ]
    sfx_labels = []
    for i, sfx in enumerate(active_sfx):
        idx = next_input_idx + i
        sfx_inputs.append(sfx["src"])
        delay_ms = max(0, int(float(sfx.get("start_time", 0)) * 1000))
        vol = float(sfx.get("volume", 1.0))
        lbl = albl()
        filter_parts.append(
            f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume={vol}[{lbl}]"
        )
        sfx_labels.append(lbl)

    # ── Step 3: Music layer ──────────────────────────────────────────────────
    music_label = None
    if audio_layer is not None:
        src = audio_layer.get("src") or ""
        if not src:
            raise ValueError("audio_layer must have a non-empty 'src'")
        music_vol = float(audio_layer.get("volume", 1.0))
        loop = bool(audio_layer.get("loop", False))

        music_idx = next_input_idx + len(sfx_inputs)
        music_inputs.append(src)

        raw_music = f"{music_idx}:a"
        cur_label = raw_music

        if loop:
            looped = albl()
            filter_parts.append(
                f"[{raw_music}]aloop=loop=-1:size=2147483647[{looped}]"
            )
            cur_label = looped

        if music_vol != 1.0:
            volout = albl()
            filter_parts.append(f"[{cur_label}]volume={music_vol}[{volout}]")
            cur_label = volout

        music_label = cur_label

    # ── Step 4: Mix all streams ──────────────────────────────────────────────
    all_labels = [vid_audio_label] + sfx_labels + ([music_label] if music_label else [])
    if len(all_labels) == 1:
        return music_inputs, sfx_inputs, filter_parts, all_labels[0]

    mixed = albl()
    inputs_str = "".join(f"[{l}]" for l in all_labels)
    filter_parts.append(
        f"{inputs_str}amix=inputs={len(all_labels)}"
        f":duration=first:dropout_transition=0:normalize=0[{mixed}]"
    )
    return music_inputs, sfx_inputs, filter_parts, mixed


def export_video(video_path: str = None, template: dict = None, title: str = "",
                 on_progress=None, emoji_source: str = "twemoji",
                 segments: list = None, clips: list = None) -> str:
    """Build and run the FFmpeg command. Returns output file path."""
    # Normalize to clips format for multi-source support
    if clips is None:
        clips = [{"video_path": video_path, "segments": segments or []}]
    if not clips:
        raise ValueError("clips must not be empty")
    job_id = uuid.uuid4().hex[:8]
    all_layers = [dict(l) for l in template["layers"]]
    cw = template["canvas"]["width"]
    ch = template["canvas"]["height"]

    for l in all_layers:
        if l["type"] == "text":
            l["text"] = l.get("text", "").replace("{title}", title)

    # Separate audio layer (not a canvas/video layer)
    audio_layer = next((l for l in all_layers if l["type"] == "audio"), None)
    layers = [l for l in all_layers if l["type"] != "audio"]

    # Collect text/mask render jobs so they can run in parallel
    text_jobs = []   # (layer_index, path, render_layer)
    mask_jobs = []   # (layer_index, path, lw, lh, radius, points, shape)
    image_entries = []  # (layer_index, src)

    for i, l in enumerate(layers):
        if l["type"] == "text":
            p = str(TEMP_DIR / f"{job_id}_t{i}.png")
            render_layer = dict(l)
            render_layer["auto_height"] = l.get("_autoHeight", True)
            render_layer["vertical_align"] = l.get("_verticalAlign", "top")
            render_layer["emoji_offset"] = l.get("_emojiOffset", 0)
            text_jobs.append((i, p, render_layer))
        elif l["type"] in ("image", "emoji") and os.path.exists(l.get("src", "")):
            image_entries.append((i, l["src"]))

    for i, l in enumerate(layers):
        shape = l.get("mask", {}).get("shape", "none")
        if shape != "none":
            p = str(TEMP_DIR / f"{job_id}_mask{i}.png")
            lw, lh = l.get("width", cw), l.get("height", ch)
            radius = l.get("mask", {}).get("radius", 20)
            points = l.get("mask", {}).get("points", [])
            mask_jobs.append((i, p, lw, lh, radius, points, shape))

    def _render_text(args):
        _, p, render_layer = args
        render_text_layer(render_layer, cw, ch, p, emoji_source=emoji_source)

    def _render_mask(args):
        _, p, lw, lh, radius, points, shape = args
        render_mask_png(shape, lw, lh, radius, points, p)

    all_render_jobs = [("text", j) for j in text_jobs] + [("mask", j) for j in mask_jobs]
    if all_render_jobs:
        with ThreadPoolExecutor(max_workers=min(len(all_render_jobs), os.cpu_count() or 4)) as ex:
            futs = {
                ex.submit(_render_text if kind == "text" else _render_mask, j): (kind, j)
                for kind, j in all_render_jobs
            }
            for fut in as_completed(futs):
                fut.result()  # re-raise any exception

    # ── Segment seek: use input-level -ss/-to for fast native seeking ────────────
    # build_segment_inputs returns pre-seek args for each video -i, plus any
    # filter_complex fragments for color grading / multi-segment concat.
    # Build FFmpeg input args and filter fragments across all clips
    all_seg_pre_args = []
    all_extra_vid_inputs = []
    all_seg_parts = []
    clip_vlabels = []
    clip_alabels = []
    n_vid = 0
    _first_video_path = clips[0]["video_path"]

    for clip_entry in clips:
        cp = clip_entry["video_path"]
        cs = clip_entry.get("segments") or []
        pre, extra, parts, vl, al, nv = build_segment_inputs(cp, cs, input_offset=n_vid)
        if n_vid == 0:
            all_seg_pre_args = pre
        else:
            # First segment of each clip after the first is a new top-level -i
            all_extra_vid_inputs.append((pre, cp))
        all_extra_vid_inputs.extend(extra)
        all_seg_parts.extend(parts)
        clip_vlabels.append(vl)
        clip_alabels.append(al)
        n_vid += nv

    # If multiple clips, concatenate their outputs
    if len(clips) > 1:
        _cn = [0]
        def _clbl(p='cc'):
            _cn[0] += 1
            return f"{p}{_cn[0]}"
        vc_out = _clbl('cv')
        ac_out = _clbl('ca')
        all_seg_parts.append(
            ''.join(f'[{l}]' for l in clip_vlabels) + f'concat=n={len(clips)}:v=1:a=0[{vc_out}]'
        )
        all_seg_parts.append(
            ''.join(f'[{l}]' for l in clip_alabels) + f'concat=n={len(clips)}:v=0:a=1[{ac_out}]'
        )
        seg_vlabel, seg_alabel = vc_out, ac_out
    else:
        seg_vlabel, seg_alabel = clip_vlabels[0], clip_alabels[0]

    seg_pre_args = all_seg_pre_args
    extra_vid_inputs = all_extra_vid_inputs
    seg_parts = all_seg_parts
    video_path = _first_video_path

    # Assign input indices in layer order.
    # Video inputs occupy indices 0..n_vid-1; extra_inputs start at n_vid.
    extra_inputs, text_pngs, image_inputs = [], {}, {}
    for layer_idx, p, _ in text_jobs:
        text_pngs[layer_idx] = len(extra_inputs) + n_vid
        extra_inputs.append(p)
    for layer_idx, src in image_entries:
        image_inputs[layer_idx] = len(extra_inputs) + n_vid
        extra_inputs.append(src)

    mask_inputs = {}
    for layer_idx, p, *_ in mask_jobs:
        mask_inputs[layer_idx] = len(extra_inputs) + n_vid
        extra_inputs.append(p)

    filter_parts, final_video = build_filter_graph(
        layers, cw, ch, text_pngs, image_inputs, mask_inputs,
        src_video_label=seg_vlabel
    )

    # next free input index = n_vid (video inputs) + len(extra_inputs)
    music_extra, sfx_extra, audio_filter_parts, audio_label = build_audio_cmd_parts(
        layers, audio_layer, next_input_idx=n_vid + len(extra_inputs),
        src_audio_label=seg_alabel
    )

    safe = re.sub(r'[^\w\s\-]', '', title, flags=re.UNICODE).strip()
    safe = re.sub(r'[\s]+', '_', safe)[:80] if safe else job_id
    out_path = str(EXPORTS_DIR / f"{safe}_{job_id}.mp4")

    # Main video input with optional seek args
    cmd = ["ffmpeg", "-y"] + seg_pre_args + ["-i", video_path]
    # Additional video inputs for multi-segment (same file, different seek points)
    for pre_args, path in extra_vid_inputs:
        cmd += pre_args + ["-i", path]
    for inp in extra_inputs:
        cmd += ["-i", inp]

    # SFX inputs (no trim/seek)
    for p in sfx_extra:
        cmd += ["-i", p]

    # Music input: apply seek/trim at input level when not looping
    if audio_layer and music_extra:
        trim_start = float(audio_layer.get("trim_start", 0.0))
        trim_end = audio_layer.get("trim_end")
        loop = bool(audio_layer.get("loop", False))
        if not loop and (trim_start > 0 or trim_end is not None):
            if trim_start > 0:
                cmd += ["-ss", str(trim_start)]
            if trim_end is not None:
                cmd += ["-to", str(trim_end)]
        cmd += ["-i", music_extra[0]]

    all_filter_parts = seg_parts + filter_parts + audio_filter_parts
    if all_filter_parts:
        cmd += ["-filter_complex", ";".join(all_filter_parts)]
    if filter_parts or seg_parts or n_vid > 1:
        cmd += ["-map", f"[{final_video}]"]
    else:
        cmd += ["-map", "0:v"]

    if audio_label == "0:a":
        cmd += ["-map", "0:a?"]
    else:
        cmd += ["-map", f"[{audio_label}]"]

    cmd += [
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        out_path,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    stderr_lines = []
    for line in proc.stderr:
        line = line.rstrip()
        stderr_lines.append(line)
        if on_progress:
            on_progress(line)
    proc.wait()
    if proc.returncode != 0:
        code = proc.returncode
        if code > 2**31 - 1:
            code -= 2**32
        last_err = "\n".join(stderr_lines[-30:]) or str(proc.returncode)
        raise RuntimeError(f"FFmpeg exited {code}:\n{last_err}")

    for p in extra_inputs:
        if "temp" in p:
            try:
                os.remove(p)
            except OSError:
                pass

    return out_path
