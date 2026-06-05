import subprocess, uuid, os
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


def build_filter_graph(layers: list, cw: int, ch: int,
                       text_pngs: dict, image_inputs: dict,
                       mask_inputs: dict = None) -> tuple[list, str]:
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
        parts.append(f"[0:v]split={raw_uses}{''.join(f'[{lb}]' for lb in split_labels)}")
        _raw_iter = iter(split_labels)
    else:
        _raw_iter = iter(["0:v"] if raw_uses == 1 else [])

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
        filter_parts.append(f"[0:a]volume={effective_vol}[{out}]")
        vid_audio_label = out
    else:
        vid_audio_label = "0:a"

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


def export_video(video_path: str, template: dict, title: str = "",
                 on_progress=None, emoji_source: str = "twemoji") -> str:
    """Build and run the FFmpeg command. Returns output file path."""
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

    extra_inputs, text_pngs, image_inputs = [], {}, {}
    for i, l in enumerate(layers):
        if l["type"] == "text":
            p = str(TEMP_DIR / f"{job_id}_t{i}.png")
            render_layer = dict(l)
            render_layer["auto_height"] = l.get("_autoHeight", True)
            render_layer["vertical_align"] = l.get("_verticalAlign", "top")
            render_text_layer(render_layer, cw, ch, p, emoji_source=emoji_source)
            text_pngs[i] = len(extra_inputs) + 1
            extra_inputs.append(p)
        elif l["type"] in ("image", "emoji") and os.path.exists(l.get("src", "")):
            image_inputs[i] = len(extra_inputs) + 1
            extra_inputs.append(l["src"])

    # Mask pre-processing: render mask PNGs for masked video layers
    mask_inputs = {}
    for i, l in enumerate(layers):
        shape = l.get("mask", {}).get("shape", "none")
        if shape != "none":
            p = str(TEMP_DIR / f"{job_id}_mask{i}.png")
            lw, lh = l.get("width", cw), l.get("height", ch)
            radius = l.get("mask", {}).get("radius", 20)
            points = l.get("mask", {}).get("points", [])
            render_mask_png(shape, lw, lh, radius, points, p)
            mask_inputs[i] = len(extra_inputs) + 1
            extra_inputs.append(p)

    filter_parts, final_video = build_filter_graph(layers, cw, ch, text_pngs, image_inputs, mask_inputs)

    # next free input index = 1 (video) + len(extra_inputs)
    music_extra, sfx_extra, audio_filter_parts, audio_label = build_audio_cmd_parts(
        layers, audio_layer, next_input_idx=1 + len(extra_inputs)
    )

    out_path = str(EXPORTS_DIR / f"{job_id}.mp4")

    cmd = ["ffmpeg", "-y", "-i", video_path]
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

    all_filter_parts = filter_parts + audio_filter_parts
    if filter_parts and audio_filter_parts:
        # Both video and audio filters: final_video is a filter label
        cmd += ["-filter_complex", ";".join(all_filter_parts), "-map", f"[{final_video}]"]
    elif filter_parts:
        # Video filters only: final_video is a filter label
        cmd += ["-filter_complex", ";".join(filter_parts), "-map", f"[{final_video}]"]
    elif audio_filter_parts:
        # Audio filters only: final_video is a raw stream specifier, not a label
        cmd += ["-filter_complex", ";".join(audio_filter_parts), "-map", "0:v"]
    else:
        cmd += ["-map", "0:v"]

    if audio_label == "0:a":
        cmd += ["-map", "0:a?"]
    else:
        cmd += ["-map", f"[{audio_label}]"]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
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
