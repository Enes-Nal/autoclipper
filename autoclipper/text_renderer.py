import re
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TWEMOJI_CDN = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/{}.png"
TWEMOJI_CACHE_DIR = Path(__file__).parent / "twemoji_cache"
TWEMOJI_CACHE_DIR.mkdir(exist_ok=True)

EMOJIPACK_DIR = Path(__file__).parent / "EmojiPack"

# Build index: codepoint-string -> Path, indexing both with and without fe0f
_EMOJIPACK_INDEX: dict[str, Path] = {}

def _build_emojipack_index() -> None:
    if not EMOJIPACK_DIR.exists():
        return
    for f in EMOJIPACK_DIR.glob("*.png"):
        if " " in f.name:           # skip "(1)" duplicate files
            continue
        # extract the hex codepoint segment after the last underscore
        parts = f.stem.split("_")
        for part in reversed(parts):
            if re.match(r"^[0-9a-f]+(?:-[0-9a-f]+)*$", part):
                _EMOJIPACK_INDEX[part] = f
                # also index with all fe0f variation-selectors stripped
                no_fe0f = "-".join(p for p in part.split("-") if p != "fe0f")
                if no_fe0f and no_fe0f != part:
                    _EMOJIPACK_INDEX.setdefault(no_fe0f, f)
                break

_build_emojipack_index()


def _emoji_codepoint_name(emoji_char: str) -> str:
    """Return the Twemoji filename stem for an emoji (strip VS-16, join with -)."""
    return "-".join(f"{ord(c):x}" for c in emoji_char if ord(c) != 0xFE0F)


def _get_twemoji(emoji_char: str, size: int) -> "Image.Image | None":
    """Return a square RGBA Twemoji image at *size*×*size* pixels, or None."""
    name = _emoji_codepoint_name(emoji_char)
    cache_file = TWEMOJI_CACHE_DIR / f"{name}.png"
    if not cache_file.exists():
        url = TWEMOJI_CDN.format(name)
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                cache_file.write_bytes(resp.read())
        except Exception:
            return None
    try:
        img = Image.open(str(cache_file)).convert("RGBA")
        return img.resize((size, size), Image.LANCZOS)
    except Exception:
        return None


def _get_emojipack(emoji_char: str, size: int) -> "Image.Image | None":
    """Return a square RGBA EmojiPack image, falling back to Twemoji if not found."""
    # try full sequence (with fe0f), then without fe0f
    cp_full = "-".join(f"{ord(c):x}" for c in emoji_char)
    cp_no_fe0f = "-".join(f"{ord(c):x}" for c in emoji_char if ord(c) != 0xFE0F)
    for cp in dict.fromkeys([cp_full, cp_no_fe0f]):   # deduplicated, order preserved
        path = _EMOJIPACK_INDEX.get(cp)
        if path:
            try:
                img = Image.open(str(path)).convert("RGBA")
                return img.resize((size, size), Image.LANCZOS)
            except Exception:
                pass
    # fallback to Twemoji if EmojiPack doesn't have this emoji
    return _get_twemoji(emoji_char, size)

FONTS_DIR = Path(__file__).parent / "fonts"
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FA9F"
    "\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF]",
    flags=re.UNICODE,
)

def has_emoji(text: str) -> bool:
    return bool(EMOJI_RE.search(text))

def _load_emoji_font(font_size: int) -> ImageFont.FreeTypeFont | None:
    candidates = [
        "C:/Windows/Fonts/seguiemj.ttf",   # Segoe UI Emoji (Windows)
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                pass
    return None


def _split_emoji(text: str) -> list[tuple[str, bool]]:
    """Split text into (segment, is_emoji) pairs."""
    segments = []
    last = 0
    for m in EMOJI_RE.finditer(text):
        if m.start() > last:
            segments.append((text[last:m.start()], False))
        segments.append((m.group(), True))
        last = m.end()
    if last < len(text):
        segments.append((text[last:], False))
    return segments or [(text, False)]

def _load_font(font_size: int, font_weight: str = "900") -> ImageFont.FreeTypeFont:
    w = str(font_weight)
    # Map CSS weight to Inter filename (prefer exact match, then heavier, then lighter)
    weight_map = {
        "900": ["Inter-Black.ttf", "Inter-Bold.ttf", "Inter-Regular.ttf"],
        "800": ["Inter-Black.ttf", "Inter-Bold.ttf", "Inter-Regular.ttf"],
        "700": ["Inter-Bold.ttf", "Inter-Black.ttf", "Inter-Regular.ttf"],
        "600": ["Inter-Bold.ttf", "Inter-Regular.ttf"],
        "500": ["Inter-Regular.ttf", "Inter-Bold.ttf"],
        "400": ["Inter-Regular.ttf", "Inter-Bold.ttf"],
        "normal": ["Inter-Regular.ttf", "Inter-Bold.ttf"],
        "bold": ["Inter-Bold.ttf", "Inter-Black.ttf", "Inter-Regular.ttf"],
    }
    candidates = weight_map.get(w, ["Inter-Black.ttf", "Inter-Bold.ttf", "Inter-Regular.ttf"])
    for name in candidates:
        p = FONTS_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), font_size)
    # Fall back to common system fonts before resorting to the bitmap default
    system_candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if w in ("700", "800", "900", "bold") else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in system_candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, font_size)
    return ImageFont.load_default()

def _line_width(line: str, font: ImageFont.FreeTypeFont,
                emoji_font: "ImageFont.FreeTypeFont | None",
                emoji_size: int = 0) -> float:
    total = 0.0
    for seg, is_emoji in _split_emoji(line):
        if is_emoji and emoji_size:
            total += emoji_size  # Twemoji is square
        else:
            f = (emoji_font or font) if is_emoji else font
            total += f.getlength(seg)
    return total


def _wrap_lines(text: str, font: ImageFont.FreeTypeFont,
                emoji_font, frame_w: float, emoji_size: int = 0) -> list[str]:
    """Word-wrap *text* into lines that each fit within *frame_w* pixels."""
    raw_lines = text.split("\n")
    lines: list[str] = []
    for raw in raw_lines:
        if not raw:
            lines.append("")
            continue
        words = raw.split(" ")
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if _line_width(candidate, font, emoji_font, emoji_size) <= frame_w:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def _truncate_to_fit(text: str, font: ImageFont.FreeTypeFont,
                     emoji_font, frame_w: float, emoji_size: int = 0) -> str:
    """Return *text* truncated with '…' so it fits within *frame_w* pixels."""
    if _line_width(text, font, emoji_font, emoji_size) <= frame_w:
        return text
    ellipsis = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = text[:mid] + ellipsis
        if _line_width(candidate, font, emoji_font, emoji_size) <= frame_w:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + ellipsis


def render_text_layer(layer: dict, canvas_w: int, canvas_h: int, output_path: str,
                      emoji_source: str = "twemoji"):
    """Render a text layer (with optional emoji) to a transparent RGBA PNG.

    overflow_mode controls behaviour when text exceeds the frame:
      'wrap'     – word-wrap across lines, clip at frame_h (default)
      'truncate' – single line, truncated with '…' at frame_w
      'shrink'   – reduce font size until all wrapped lines fit in frame_h
    """
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_size = layer.get("font_size", 72)
    font_weight = str(layer.get("font_weight", "900"))
    fill = layer.get("fill", "#ffffff")
    stroke = layer.get("stroke", "#000000")
    stroke_w = int(layer.get("stroke_width", 0))
    text = layer.get("text", "")
    align = layer.get("text_align", "center")
    overflow = layer.get("overflow_mode", "wrap")

    frame_x = layer.get("x", 0)
    frame_y = layer.get("y", 0)
    frame_w = layer.get("width", canvas_w)
    frame_h = layer.get("height", canvas_h)

    # ── Shrink mode: binary-search font size until all lines fit in frame_h ──
    if overflow == "shrink":
        lo, hi = max(6, font_size // 4), font_size
        best_size = lo
        while lo <= hi:
            mid = (lo + hi) // 2
            f_test = _load_font(mid, font_weight)
            e_test = _load_emoji_font(mid)
            bb_test = f_test.getbbox("Ay")
            lh_test = int((bb_test[3] - bb_test[1]) * 1.2)
            wrapped = _wrap_lines(text, f_test, e_test, frame_w, lh_test)
            if len(wrapped) * lh_test <= frame_h:
                best_size = mid
                lo = mid + 1
            else:
                hi = mid - 1
        font_size = best_size

    font = _load_font(font_size, font_weight)
    emoji_font = _load_emoji_font(font_size)

    # Line height: bounding box of a tall character × 1.2 leading
    bbox = font.getbbox("Ay")
    char_h = bbox[3] - bbox[1]
    line_h = int(char_h * 1.2)

    # ── Build line list per overflow mode ─────────────────────────────────────
    if overflow == "truncate":
        single = " ".join(text.split("\n")).strip()
        lines = [_truncate_to_fit(single, font, emoji_font, frame_w, line_h)]
    else:
        # 'wrap' and 'shrink' both use word-wrap
        lines = _wrap_lines(text, font, emoji_font, frame_w, line_h)

    # ── Compute y_start based on vertical_align (fixed frame only) ───────────
    vertical_align = layer.get("vertical_align", "top")
    auto_height = layer.get("auto_height", True)
    total_text_h = len(lines) * line_h

    if not auto_height and vertical_align != "top":
        if vertical_align == "middle":
            y_offset = max(0, (frame_h - total_text_h) // 2)
        else:  # bottom
            y_offset = max(0, frame_h - total_text_h)
    else:
        y_offset = 0

    # ── Draw each line, clipping at frame bottom ──────────────────────────────
    y_cursor = frame_y + y_offset - bbox[1]
    for line in lines:
        if y_cursor + line_h > frame_y + frame_h:
            break
        line_w = _line_width(line, font, emoji_font, emoji_size=line_h)
        if align == "left":
            x_cursor = frame_x
        elif align == "right":
            x_cursor = frame_x + frame_w - line_w
        else:
            x_cursor = int(frame_x + (frame_w - line_w) / 2)

        _get_emoji = _get_emojipack if emoji_source == "emojipack" else _get_twemoji
        for seg, is_emoji in _split_emoji(line):
            if is_emoji:
                tw = _get_emoji(seg, line_h)
                if tw:
                    # Twemoji PNG: paste at baseline-adjusted y position
                    paste_y = int(y_cursor + bbox[1])
                    img.paste(tw, (int(x_cursor), paste_y), tw)
                    x_cursor += line_h
                else:
                    # Fallback: system emoji font
                    f = emoji_font or font
                    draw.text((x_cursor, y_cursor), seg, font=f, fill=fill,
                              stroke_width=stroke_w, stroke_fill=stroke)
                    x_cursor += f.getlength(seg)
            else:
                draw.text(
                    (x_cursor, y_cursor), seg, font=font, fill=fill,
                    stroke_width=stroke_w, stroke_fill=stroke,
                )
                x_cursor += font.getlength(seg)

        y_cursor += line_h

    img.save(output_path, "PNG")
