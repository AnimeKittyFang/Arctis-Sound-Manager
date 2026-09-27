# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""ASM's channel sink names must be compared exactly, never as substrings.

"Arctis_Game" is inside "alsa_output.usb-SteelSeries_Arctis_GameBuds_X-00…",
so `"Arctis_Game" in sink.name` quietly binds the Game channel to a real
card whenever GameBuds X are plugged in (#269). This scans the source for
`<channel name> in <something>` and fails on any hit.
"""
from __future__ import annotations

import ast
from pathlib import Path

from arctis_sound_manager import constants

SRC = Path(__file__).resolve().parents[1] / "src" / "arctis_sound_manager"

CHANNEL_NAMES = {
    constants.PULSE_GAME_NODE_NAME,
    constants.PULSE_CHAT_NODE_NAME,
    constants.PULSE_MEDIA_NODE_NAME,
    constants.PULSE_AUX_NODE_NAME,
}
# Every identifier the code base binds to one of the names above.
CHANNEL_IDENTIFIERS = {
    "PULSE_GAME_NODE_NAME", "PULSE_CHAT_NODE_NAME",
    "PULSE_MEDIA_NODE_NAME", "PULSE_AUX_NODE_NAME",
    "GAME_SINK_NAME", "CHAT_SINK_NAME", "MEDIA_SINK_NAME", "AUX_SINK_NAME",
}


def _is_channel_name(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant):
        return node.value in CHANNEL_NAMES
    if isinstance(node, ast.Name):
        return node.id in CHANNEL_IDENTIFIERS
    if isinstance(node, ast.Attribute):
        return node.attr in CHANNEL_IDENTIFIERS
    return False


def _is_string_haystack(node: ast.expr) -> bool:
    """`x.name`, `name`, `sink_name`… — a string, not a collection of names."""
    if isinstance(node, ast.Attribute):
        return node.attr == "name" or node.attr.endswith("_name")
    if isinstance(node, ast.Name):
        return node.id == "name" or node.id.endswith("_name")
    return False


def test_channel_names_are_never_matched_as_substrings():
    offenders = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            left = node.left
            for op, right in zip(node.ops, node.comparators):
                if (isinstance(op, (ast.In, ast.NotIn))
                        and _is_channel_name(left)
                        and _is_string_haystack(right)):
                    offenders.append(f"{path.relative_to(SRC)}:{node.lineno}")
                left = right
    assert not offenders, (
        "channel sink names compared as substrings (use ==): " + ", ".join(offenders)
    )


def test_the_scan_catches_the_pattern_it_exists_for():
    tree = ast.parse('GAME_SINK_NAME in s.name or "Arctis_Chat" in sink_name')
    hits = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Compare) and _is_channel_name(n.left)
        and _is_string_haystack(n.comparators[0])
    ]
    assert len(hits) == 2
