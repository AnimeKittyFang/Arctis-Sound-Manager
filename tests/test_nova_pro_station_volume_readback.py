# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later

"""The GameDAC wheel position must be known from daemon start (#268).

The wheel only reports itself (0x0725) when it moves, so until then the
Master card had no DAC wheel gauge to show. The [0x06, 0x20] audio_settings
query already sent at init answers with the same value at byte 3 (byte 2 is
audio_input), per ~/steelseries-research/decoded-119.0.0/
base_arctis_nova_pro_wireless.device and base_arctis_nova_pro.device.

The frame below is a real Nova Pro Wireless reply captured on 2026-09-27;
the wheel's next 0x0725 event read 20 one notch up, confirming both frames
share the 0-56 scale.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from arctis_sound_manager.config import (ConfigStatusResponseMapping,
                                         DeviceConfiguration, parsed_status)

DEVICES = Path(__file__).parent.parent / "src" / "arctis_sound_manager" / "devices"

# audio_input=0, volume=19, device_gain=2, ...
CAPTURED_0620 = [6, 32, 0, 19, 2, 0, 0, 20, 20, 20, 0, 0, 0, 0, 0, 0, 0, 10, 0, 1, 100, 100]


@pytest.mark.parametrize("profile", ["nova_pro_wireless.yaml", "arctis_nova_pro_wired.yaml"])
def test_audio_settings_reply_carries_the_wheel(profile):
    raw = YAML(typ="safe").load(DEVICES / profile)["device"]
    config = DeviceConfiguration({"device": raw})
    entry = next(m for m in raw["status"]["response_mapping"] if m["starts_with"] == 0x0620)

    values = ConfigStatusResponseMapping(**entry).get_status_values(CAPTURED_0620)
    assert values == {"station_volume": 19}

    event = next(m for m in raw["status"]["response_mapping"] if m["starts_with"] == 0x0725)
    from_event = ConfigStatusResponseMapping(**event).get_status_values([7, 37, 19])
    assert parsed_status(values, config) == parsed_status(from_event, config)
