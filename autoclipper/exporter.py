import subprocess, uuid, os
from pathlib import Path
from text_renderer import render_text_layer, has_emoji

EXPORTS_DIR = Path("exports")
TEMP_DIR = Path("temp")
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

    for i, layer in enumerate(layers):
        t = layer["type"]

        if t == "blur_video":
            blur = layer.get("blur", 20)
            out = lbl()
            parts.append(
                f"[0:v]scale={cw}:{ch}:force_original_aspect_ratio=increase,"
                f"crop={cw}:{ch},boxblur=lx={blur}:ly={blur},setsar=1[{out}]"
            )
            current = out

        elif t == "video":
            x, y = layer.get("x", 0), layer.get("y", 0)
            w, h = layer.get("width", cw), layer.get("height", int(ch * 0.32))
            fit = layer.get("fit", "contain")
            scaled = lbl()
            if fit == "contain":
                parts.append(
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black[{scaled}]"
                )
            elif fit == "cover":
                parts.append(
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
                    f"crop={w}:{h}[{scaled}]"
                )
            else:
                parts.append(f"[0:v]scale={w}:{h}[{scaled}]")
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
            else:
                text = layer.get("text", "").replace("'", "\\'").replace(":", "\\:")
                x, y = layer.get("x", 0), layer.get("y", 0)
                fs = layer.get("font_size", 72)
                fc = layer.get("fill", "#ffffff").lstrip("#")
                bc = layer.get("stroke", "#000000").lstrip("#")
                bw = layer.get("stroke_width", 0)
                ff = "fonts/Inter-Black.ttf"
                out = lbl()
                dt = (f"fontfile={ff}:text='{text}':x={x}:y={y}:fontsize={fs}:"
                      f"fontcolor=0x{fc}:bordercolor=0x{bc}:borderw={bw}")
                parts.append(f"[{current}]drawtext={dt}[{out}]")
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
        if l["type"] == "text" and has_emoji(l.get("text", "")):
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
    cmd += [
        "-filter_complex", ";".join(filter_parts),
        "-map", f"[{final}]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        out_path,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        if on_progress:
            on_progress(line.strip())
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg exited {proc.returncode}")

    for p in extra_inputs:
        if "temp" in p:
            try:
                os.remove(p)
            except OSError:
                pass

    return out_path
