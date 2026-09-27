# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every method the GUI calls across its two app objects must exist.

scripts/gui.py drives the tray (QSystrayApp) through `q_object`, and the
tray drives the main window (QMainApp) through `self._main_app`. Those
calls run from sockets, timers and menus — paths no other test walks — so a
method called on the wrong object only shows up on a user's machine. 1.4.28
shipped `q_object.restart_on_new_code(...)`, a QMainApp method, and every
tray that received the upgrade's restart command crashed (#277-#283).

This reads the source instead of running it: each `q_object.<name>(...)`
and `self._main_app.<name>(...)` call must name a method of the class the
object actually is.
"""
from __future__ import annotations

import ast
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from arctis_sound_manager.gui import systray_app
from arctis_sound_manager.gui.main_app import QMainApp
from arctis_sound_manager.gui.systray_app import QSystrayApp
from arctis_sound_manager.scripts import gui as gui_script


def _called_methods(source: str, receiver) -> set[str]:
    """Names of `<receiver>.<name>(...)` calls, receiver matched by `receiver(node)`."""
    names = set()
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and receiver(node.func.value)):
            names.add(node.func.attr)
    return names


def _is_name(name):
    return lambda node: isinstance(node, ast.Name) and node.id == name


def _is_self_attr(attr):
    return lambda node: (isinstance(node, ast.Attribute) and node.attr == attr
                         and isinstance(node.value, ast.Name) and node.value.id == "self")


def test_gui_script_only_calls_tray_methods_that_exist():
    called = _called_methods(inspect.getsource(gui_script), _is_name("q_object"))
    assert called, "no q_object calls found: the receiver was renamed, update this test"
    missing = sorted(n for n in called if not hasattr(QSystrayApp, n))
    assert not missing, f"scripts/gui.py calls methods QSystrayApp does not have: {missing}"


def test_tray_only_calls_main_window_methods_that_exist():
    called = _called_methods(inspect.getsource(systray_app), _is_self_attr("_main_app"))
    assert called, "no self._main_app calls found: the attribute was renamed, update this test"
    missing = sorted(n for n in called if not hasattr(QMainApp, n))
    assert not missing, f"QSystrayApp calls methods QMainApp does not have: {missing}"
