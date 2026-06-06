import os, subprocess, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from exporter import build_filter_graph
from text_renderer import render_text_layer

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
