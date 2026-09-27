# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""`asm-gui --restart` must restart the tray, window or no window.

The single-instance socket hands the package scriptlet's "restart" to the
tray object. 1.4.28 shipped with only the window (QMainApp) knowing how to
restart, so every tray that received it died on an AttributeError — seven
crash reports in two days (#277-#283). Pinned here: the tray delegates to
the window when there is one, and restarts on its own when there is not.
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from arctis_sound_manager import runtime_staleness
from arctis_sound_manager.gui.systray_app import QSystrayApp


def test_tray_without_window_restarts_directly(monkeypatch):
    restarts = []
    monkeypatch.setattr(runtime_staleness, "restart_gui", lambda: restarts.append(True))
    tray = SimpleNamespace(logger=MagicMock())

    QSystrayApp.restart_on_new_code(tray, "asked to by the package upgrade")

    assert restarts == [True]


def test_tray_with_window_lets_the_window_restart(monkeypatch):
    restarts = []
    monkeypatch.setattr(runtime_staleness, "restart_gui", lambda: restarts.append(True))
    main_app = MagicMock()
    tray = SimpleNamespace(logger=MagicMock(), _main_app=main_app)

    QSystrayApp.restart_on_new_code(tray, "asked to by the package upgrade")

    main_app.restart_on_new_code.assert_called_once_with("asked to by the package upgrade")
    assert restarts == []


def test_tray_notices_an_upgrade_without_a_window(monkeypatch):
    """The staleness poll is the tray's: a tray whose window was never opened
    used to run the previous version's code until the next reboot."""
    monkeypatch.setattr(runtime_staleness, "upgraded_under_us", lambda: "9.9.9")
    tray = MagicMock()

    QSystrayApp._check_upgraded_under_us(tray)

    tray.restart_on_new_code.assert_called_once_with("upgraded to 9.9.9")


def test_tray_stays_put_when_nothing_was_upgraded(monkeypatch):
    monkeypatch.setattr(runtime_staleness, "upgraded_under_us", lambda: None)
    tray = MagicMock()

    QSystrayApp._check_upgraded_under_us(tray)

    tray.restart_on_new_code.assert_not_called()
