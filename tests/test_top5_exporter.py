import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from top5_exporter import resolve_placeholders

SLOTS = [
    {"rank": 5, "title": "Clip Five", "path": "a.mp4", "start": 0, "end": 10},
    {"rank": 3, "title": "Clip Three", "path": "b.mp4", "start": 0, "end": 10},
    {"rank": 4, "title": "Clip Four", "path": "c.mp4", "start": 0, "end": 10},
    {"rank": 1, "title": "Clip One", "path": "d.mp4", "start": 0, "end": 10},
    {"rank": 2, "title": "Clip Two", "path": "e.mp4", "start": 0, "end": 10},
]

def test_current_tokens_resolve_to_active_slot():
    result = resolve_placeholders("<current:rank> <current:title>", SLOTS, 0)
    assert result == "5 Clip Five"

def test_current_tokens_for_second_slot():
    result = resolve_placeholders("<current:rank> <current:title>", SLOTS, 1)
    assert result == "3 Clip Three"

def test_past_slot_title_visible():
    # slot1 (idx 0) is past when current_idx=2 — title should show
    result = resolve_placeholders("<slot1:title>", SLOTS, 2)
    assert result == "Clip Five"

def test_future_slot_title_is_dash():
    # slot5 (idx 4) is future when current_idx=1
    result = resolve_placeholders("<slot5:title>", SLOTS, 1)
    assert result == "—"

def test_current_slot_title_visible():
    # slot3 (idx 2) is current when current_idx=2
    result = resolve_placeholders("<slot3:title>", SLOTS, 2)
    assert result == "Clip Four"

def test_slot_rank_always_resolves():
    result = resolve_placeholders("<slot2:rank>", SLOTS, 0)
    assert result == "3"

def test_no_placeholders_unchanged():
    result = resolve_placeholders("Hello World", SLOTS, 0)
    assert result == "Hello World"

def test_multiple_tokens_in_one_string():
    text = "<slot1:rank>  <slot1:title> | <slot2:rank>  <slot2:title>"
    result = resolve_placeholders(text, SLOTS, 3)
    assert result == "5  Clip Five | 3  Clip Three"
