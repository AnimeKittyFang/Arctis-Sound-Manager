# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which sink each Channels-page card is bound to (#269).

A Nova Pro user with GameBuds X plugged in saw the Game card sit at 100 %
while the dial moved Arctis_Game: the card matched "Arctis_Game" as a
substring, and ``alsa_output.usb-SteelSeries_Arctis_GameBuds_X-00…`` contains
it. The idle GameBuds card also took the Master card from the Nova Pro.
"""
from __future__ import annotations

from types import SimpleNamespace

from arctis_sound_manager.gui.home_page import (
    GAME_SINK_NAME,
    _channel_sink,
    _channel_sinks,
    _headset_sink,
)

GAMEBUDS = "alsa_output.usb-SteelSeries_Arctis_GameBuds_X-00.analog-stereo"
NOVA_PRO = "alsa_output.usb-SteelSeries_Arctis_Nova_Pro_Wireless-00.analog-stereo"
HDMI = "alsa_output.pci-0000_08_00.1.hdmi-stereo"


def _sink(name: str, state: str = "idle", vendor: str = ""):
    props = {"device.vendor.id": vendor} if vendor else {}
    return SimpleNamespace(name=name, state=state, proplist=props)


# The order the reporter's server listed them in: the GameBuds card first.
SINKS = [
    _sink(GAMEBUDS, "suspended"),
    _sink(HDMI, "running"),
    _sink(NOVA_PRO, "running"),
    _sink(GAME_SINK_NAME, "idle"),
]


def test_game_card_ignores_a_card_named_after_it():
    assert _channel_sink(SINKS, GAME_SINK_NAME).name == GAME_SINK_NAME
    assert [s.name for s in _channel_sinks(SINKS, GAME_SINK_NAME)] == [GAME_SINK_NAME]


def test_missing_channel_sink_is_none():
    assert _channel_sink([_sink(GAMEBUDS)], GAME_SINK_NAME) is None


def test_master_is_the_running_headset_not_the_first_listed():
    assert _headset_sink(SINKS).name == NOVA_PRO


def test_master_falls_back_to_an_idle_headset():
    assert _headset_sink([_sink(HDMI, "running"), _sink(GAMEBUDS, "suspended")]).name == GAMEBUDS


def test_master_matches_on_vendor_id_without_the_brand_in_the_name():
    sink = _sink("bluez_output.AA_BB_CC.1", "running", vendor="0x1038")
    assert _headset_sink([_sink(HDMI, "running"), sink]) is sink
