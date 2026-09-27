# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later

"""EQ preset picker on the Channels page cards (#256).

Each card but Master lists the channel's favorites from the Equalizer page
and applies the one picked, like the preset dropdown in GG's own mixer.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from arctis_sound_manager.gui import home_page
from arctis_sound_manager.gui.home_page import AudioCard, HomePage


@pytest.fixture
def card():
    QApplication.instance() or QApplication([])
    return AudioCard("Game", "#ff0000")


def _items(card) -> list[str]:
    return [card._preset_combo.itemText(i) for i in range(card._preset_combo.count())]


def test_picker_hidden_until_presets_given(card):
    assert card._preset_combo.isHidden()


def test_picker_lists_favorites_with_active_selected(card):
    card.set_presets(["Flat", "FPS", "Racing"], "FPS")
    assert not card._preset_combo.isHidden()
    assert _items(card) == ["Flat", "FPS", "Racing"]
    assert card._preset_combo.currentText() == "FPS"


def test_active_preset_listed_even_when_not_a_favorite(card):
    """The picker must show what is really applied, not a favorite that isn't."""
    card.set_presets(["FPS", "Racing"], "Podcast")
    assert _items(card) == ["Podcast", "FPS", "Racing"]
    assert card._preset_combo.currentText() == "Podcast"


def test_no_favorites_shows_disabled_placeholder(card):
    card.set_presets([], "")
    assert card._preset_combo.count() == 1
    assert not card._preset_combo.isEnabled()


def test_none_hides_the_picker(card):
    card.set_presets(["FPS"], "FPS")
    card.set_presets(None)
    assert card._preset_combo.isHidden()


def test_picking_calls_back_once_and_not_for_the_active_one(card):
    picked = []
    card.set_on_preset(picked.append)
    card.set_presets(["Flat", "FPS"], "Flat")
    card._on_preset_activated(0)          # already active: nothing to apply
    card._on_preset_activated(1)
    assert picked == ["FPS"]


def test_same_listing_does_not_rebuild(card):
    """A poll redrawing the same list would close a popup the user has open."""
    card.set_presets(["Flat", "FPS"], "Flat")
    cleared = []
    card._preset_combo.clear = lambda: cleared.append(True)
    card.set_presets(["Flat", "FPS"], "Flat")
    assert cleared == []


# ── HomePage wiring ────────────────────────────────────────────────────────────

class _FakeCard:
    def __init__(self):
        self.presets = "unset"
        self.busy: list[bool] = []

    def set_presets(self, names, active=""):
        self.presets = (names, active) if names is not None else None

    def set_preset_busy(self, busy):
        self.busy.append(busy)


class _FakeApplier:
    def __init__(self, running=False):
        self.running = running
        self.applied: list[tuple[str, str]] = []

    def is_running(self):
        return self.running

    def apply(self, channel, name):
        self.applied.append((channel, name))


def _page(mode: str, monkeypatch, running=False):
    monkeypatch.setattr(home_page, "current_eq_mode", lambda: mode)
    monkeypatch.setattr(home_page, "list_sonar_channel_presets",
                        lambda ch, limit=None: [f"{ch}-fav"])
    monkeypatch.setattr(home_page, "get_sonar_active_preset", lambda ch: "")
    channels = ("game", "chat", "media", "aux", "output")
    return SimpleNamespace(
        _preset_cards={ch: _FakeCard() for ch in channels},
        _preset_appliers={ch: _FakeApplier(running) for ch in channels},
    )


def test_master_has_no_picker(monkeypatch):
    page = _page("sonar", monkeypatch)
    assert "master" not in page._preset_cards
    HomePage._refresh_eq_presets(page)
    assert page._preset_cards["game"].presets == (["game-fav"], "Flat")


def test_pickers_hidden_outside_sonar_mode(monkeypatch):
    """Custom EQ is one global curve, not a per-channel preset."""
    page = _page("custom", monkeypatch)
    HomePage._refresh_eq_presets(page)
    assert all(c.presets is None for c in page._preset_cards.values())


def test_refresh_leaves_a_card_alone_while_its_preset_applies(monkeypatch):
    page = _page("sonar", monkeypatch, running=True)
    HomePage._refresh_eq_presets(page)
    assert page._preset_cards["game"].presets == "unset"


def test_choosing_applies_on_that_channel_and_locks_the_picker(monkeypatch):
    page = _page("sonar", monkeypatch)
    HomePage._on_eq_preset_chosen(page, "media", "Movie")
    assert page._preset_appliers["media"].applied == [("media", "Movie")]
    assert page._preset_cards["media"].busy == [True]
