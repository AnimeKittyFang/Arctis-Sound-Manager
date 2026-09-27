# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later

"""Searchable "pick one" window: a filter field over a list, OK / Cancel.

The Equalizer page's "Search preset" window, generalised so the Channels page
cards can open the very same window for their EQ favorites and for their
output device.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLineEdit, QListWidget, QListWidgetItem,
    QVBoxLayout, QWidget,
)

import arctis_sound_manager.gui.theme as _theme
from arctis_sound_manager.i18n import I18n

_KEY_ROLE = Qt.ItemDataRole.UserRole


class SearchPickDialog(QDialog):
    """Pick one of *entries* — (key, label) pairs — with *current* preselected.

    The chosen key lands in ``selected_key`` when the window is accepted.
    """

    def __init__(self, title: str, entries: list[tuple[str, str]],
                 parent: QWidget | None = None, current: str | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(340, 480)
        self.selected_key: str | None = None
        self._entries = list(entries)
        self._current = current

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText(I18n.translate("ui", "search_dots"))
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {_theme.c('BG_BUTTON')};
                border: 1px solid {_theme.c('BORDER')};
                border-radius: 6px;
                color: {_theme.c('TEXT_PRIMARY')};
                padding: 6px 10px;
                font-size: 11pt;
            }}
            QLineEdit:focus {{ border-color: {_theme.c('ACCENT')}; }}
        """)
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: {_theme.c('BG_CARD')};
                border: 1px solid {_theme.c('BORDER')};
                border-radius: 6px;
                color: {_theme.c('TEXT_PRIMARY')};
            }}
            QListWidget::item:selected {{ background: {_theme.c('ACCENT')}; color: #fff; }}
            QListWidget::item:hover    {{ background: {_theme.c('BG_BUTTON_HOVER')}; }}
        """)
        self._list.itemDoubleClicked.connect(self.accept)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._filter("")

    def _color_for(self, key: str) -> str | None:
        """Subclass hook: a text colour for *key*, or None for the default."""
        return None

    def _on_context_menu(self, pos) -> None:
        """Subclass hook: right-click on the list."""

    def _filter(self, text: str):
        self._list.clear()
        q = text.lower()
        for key, label in self._entries:
            if q in label.lower():
                item = QListWidgetItem(label)
                item.setData(_KEY_ROLE, key)
                color = self._color_for(key)
                if color:
                    item.setForeground(QColor(color))
                self._list.addItem(item)
                if key == self._current:
                    self._list.setCurrentItem(item)

    def accept(self):
        item = self._list.currentItem()
        if item:
            self.selected_key = item.data(_KEY_ROLE)
        super().accept()
