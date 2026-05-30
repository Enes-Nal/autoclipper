import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path(__file__).parent / "fonts"
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FA9F"
    "\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF]",
    flags=re.UNICODE,
)

def has_emoji(text: str) -> bool:
    return bool(EMOJI_RE.search(text))

def _load_font(font_size: int) -> ImageFont.FreeTypeFont:
    for name in ("Inter-Black.ttf", "Inter-Bold.ttf"):
        p = FONTS_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), font_size)
    # Fall back to common system fonts before resorting to the bitmap default
    system_candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in system_candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, font_size)
    return ImageFont.load_default()

def render_text_layer(layer: dict, canvas_w: int, canvas_h: int, output_path: str):
    """Render a text layer (with optional emoji) to a transparent RGBA PNG.

    Respects frame width (word-wrap), frame height (clip), and text_align.
    """
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(layer.get("font_size", 72))
    fill = layer.get("fill", "#ffffff")
    stroke = layer.get("stroke", "#000000")
    stroke_w = int(layer.get("stroke_width", 0))
    text = layer.get("text", "")
    align = layer.get("text_align", "center")

    frame_x = layer.get("x", 0)
    frame_y = layer.get("y", 0)
    frame_w = layer.get("width", canvas_w)
    frame_h = layer.get("height", canvas_h)

    # Line height: bounding box of a tall character * 1.2 leading
    bbox = font.getbbox("Ay")
    line_h = int((bbox[3] - bbox[1]) * 1.2)

    # Build wrapped lines respecting frame_w
    raw_lines = text.split("\n")
    lines = []
    for raw in raw_lines:
        if not raw:          # blank line (e.g. from \n\n)
            lines.append("")
            continue
        words = raw.split(" ")
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if font.getlength(candidate) <= frame_w:
                current = candidate
            else:
                if current:
                    lines.append(current)
                # Word is wider than frame — keep it; it will overflow rather than be lost
                current = word
        if current:
            lines.append(current)

    # Draw each line, clipping at frame_h
    y_cursor = frame_y
    for line in lines:
        if y_cursor + line_h > frame_y + frame_h:
            break
        line_w = font.getlength(line)
        if align == "left":
            x_cursor = frame_x
        elif align == "right":
            x_cursor = frame_x + frame_w - line_w
        else:  # center
            x_cursor = int(frame_x + (frame_w - line_w) / 2)
        draw.text(
            (x_cursor, y_cursor), line, font=font, fill=fill,
            stroke_width=stroke_w, stroke_fill=stroke,
        )
        y_cursor += line_h

    img.save(output_path, "PNG")
