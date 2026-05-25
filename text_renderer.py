import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path("fonts")
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
    return ImageFont.load_default()

def render_text_layer(layer: dict, canvas_w: int, canvas_h: int, output_path: str):
    """Render a text layer (with emoji) to a transparent RGBA PNG."""
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(layer.get("font_size", 72))
    fill = layer.get("fill", "#ffffff")
    stroke = layer.get("stroke", "#000000")
    stroke_w = int(layer.get("stroke_width", 0))
    text = layer.get("text", "")
    x, y = layer.get("x", 0), layer.get("y", 0)
    draw.text(
        (x, y), text, font=font, fill=fill,
        stroke_width=stroke_w, stroke_fill=stroke,
    )
    img.save(output_path, "PNG")
