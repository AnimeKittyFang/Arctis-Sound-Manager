"""app_icons: a stream's PipeWire identity → the icon of its desktop file."""

import pytest

from arctis_sound_manager.gui import app_icons


@pytest.fixture
def desktop_dir(tmp_path, monkeypatch, qapp):
    icon = tmp_path / "icon.png"
    from PySide6.QtGui import QPixmap
    pixmap = QPixmap(8, 8)
    pixmap.fill()
    pixmap.save(str(icon))

    apps = tmp_path / "share" / "applications"
    apps.mkdir(parents=True)

    def add(filename, **keys):
        body = "\n".join(f"{k}={v}" for k, v in keys.items())
        (apps / filename).write_text(f"[Desktop Entry]\nIcon={icon}\n{body}\n")

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "none"))
    monkeypatch.setattr(app_icons.Path, "home", lambda: tmp_path / "home")
    app_icons._desktop_index.cache_clear()
    app_icons.app_icon.cache_clear()
    yield add
    app_icons._desktop_index.cache_clear()
    app_icons.app_icon.cache_clear()


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_found_by_exec_binary(desktop_dir):
    desktop_dir("com.discordapp.Discord.desktop", Name="Discord", Exec="/opt/discord/Discord %U")
    assert app_icons.app_icon("", "Discord", "", "WEBRTC VoiceEngine") is not None


def test_found_through_flatpak_wrapper(desktop_dir):
    desktop_dir("x.desktop", Name="Spot", Exec="/usr/bin/flatpak run --branch=stable com.spotify.Client")
    assert app_icons.app_icon("", "", "com.spotify.Client", "") is not None


def test_proton_game_matches_its_steam_shortcut_by_name(desktop_dir):
    desktop_dir("Rocket League.desktop", Name="Rocket League",
                Exec="steam steam://rungameid/252950")
    assert app_icons.app_icon("", "wine64-preloader", "", "RocketLeague.exe") is not None


def test_host_runtime_binary_is_not_used(desktop_dir):
    # A Wine desktop file must not give every game the Wine icon.
    desktop_dir("wine.desktop", Name="Wine Program Loader", Exec="wine start %f")
    assert app_icons.app_icon("", "wine64-preloader", "", "Unknown.exe") is None


def test_steam_shortcut_does_not_claim_the_steam_binary(desktop_dir):
    desktop_dir("Game.desktop", Name="Game", Exec="steam steam://rungameid/1")
    assert "steam" not in app_icons._desktop_index()[2]


def test_icon_hint_reads_pipewire_properties():
    hint = app_icons.icon_hint({
        "application.icon_name": "firefox",
        "application.process.binary": "firefox-bin",
        "pipewire.access.portal.app_id": "org.mozilla.firefox",
    })
    assert hint == ("firefox", "firefox-bin", "org.mozilla.firefox")
