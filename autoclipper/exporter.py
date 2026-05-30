import subprocess, uuid, os
from pathlib import Path
from text_renderer import render_text_layer

EXPORTS_DIR = Path(__file__).parent / "exports"
TEMP_DIR = Path(__file__).parent / "temp"
for d in (EXPORTS_DIR, TEMP_DIR):
    d.mkdir(exist_ok=True)

def build_filter_graph(layers: list, cw: int, ch: int,
                       text_pngs: dict, image_inputs: dict) -> tuple[list, str]:
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
                    f"[{raw}]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black[{scaled}]"
                )
            elif fit == "cover":
                parts.append(
                    f"[{raw}]scale={w}:{h}:force_original_aspect_ratio=increase,"
                    f"crop={w}:{h}[{scaled}]"
                )
            else:
                parts.append(f"[{raw}]scale={w}:{h}[{scaled}]")
            if current:
                out = lbl()
                parts.append(f"[{current}][{scaled}]overlay=x={x}:y={y}[{out}]")
                current = out
            else:
                current = scaled

        elif t == "text":
            if i in text_pngs:
                idx = text_pngs[i]
                out = lbl()
                parts.append(f"[{current}][{idx}:v]overlay=x=0:y=0[{out}]")
                current = out

        elif t == "image" and i in image_inputs:
            idx = image_inputs[i]
            x, y = layer.get("x", 0), layer.get("y", 0)
            out = lbl()
            parts.append(f"[{current}][{idx}:v]overlay=x={x}:y={y}[{out}]")
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

    return parts, current or "0:v"


def export_video(video_path: str, template: dict, title: str = "",
                 on_progress=None) -> str:
    """Build and run the FFmpeg command. Returns output file path."""
    job_id = uuid.uuid4().hex[:8]
    layers = [dict(l) for l in template["layers"]]
    cw = template["canvas"]["width"]
    ch = template["canvas"]["height"]

    for l in layers:
        if l["type"] == "text":
            l["text"] = l.get("text", "").replace("{title}", title)

    extra_inputs, text_pngs, image_inputs = [], {}, {}
    for i, l in enumerate(layers):
        if l["type"] == "text":
            p = str(TEMP_DIR / f"{job_id}_t{i}.png")
            render_text_layer(l, cw, ch, p)
            text_pngs[i] = len(extra_inputs) + 1
            extra_inputs.append(p)
        elif l["type"] == "image" and os.path.exists(l.get("src", "")):
            image_inputs[i] = len(extra_inputs) + 1
            extra_inputs.append(l["src"])

    filter_parts, final = build_filter_graph(layers, cw, ch, text_pngs, image_inputs)
    out_path = str(EXPORTS_DIR / f"{job_id}.mp4")

    cmd = ["ffmpeg", "-y", "-i", video_path]
    for inp in extra_inputs:
        cmd += ["-i", inp]
    if filter_parts:
        cmd += ["-filter_complex", ";".join(filter_parts), "-map", f"[{final}]"]
    else:
        cmd += ["-map", "0:v"]
    cmd += [
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        out_path,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stderr_lines = []
    for line in proc.stdout:
        if on_progress:
            on_progress(line.strip())
    stderr_lines = proc.stderr.read().splitlines()
    proc.wait()
    if proc.returncode != 0:
        # Normalize Windows unsigned exit codes (e.g. 4294967274 → -22)
        code = proc.returncode
        if code > 2**31 - 1:
            code -= 2**32
        last_err = next((l for l in reversed(stderr_lines) if l.strip()), str(proc.returncode))
        raise RuntimeError(f"FFmpeg exited {code}: {last_err}")

    for p in extra_inputs:
        if "temp" in p:
            try:
                os.remove(p)
            except OSError:
                pass

    return out_path
