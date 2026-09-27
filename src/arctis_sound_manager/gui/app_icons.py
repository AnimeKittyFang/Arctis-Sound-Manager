"""Find the icon of the application behind an audio stream.

PipeWire rarely hands us one: ``application.icon_name`` is set by a few
programs (Firefox, some GTK apps) and by nothing Electron, Proton or Discord.
So, like KMix, the stream's identity is matched against the installed
``.desktop`` files — by desktop-file id, StartupWMClass, Exec binary and
Name — and their ``Icon=`` is loaded from the icon theme. None when nothing
matches; the caller draws its own placeholder.
"""

import os
import re
from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QIcon

# Runtimes that host many different programs: their icon would put the same
# Wine glass or Python logo on every game and script.
_HOST_BINARIES = {
    "wine", "wine64", "wine-preloader", "wine64-preloader", "wineserver",
    "python", "python3", "java", "node", "electron", "bwrap", "flatpak",
    # Every Steam game shortcut runs "steam steam://rungameid/…".
    "steam",
}


def _loose(text: str) -> str:
    """"Cyberpunk2077.exe" and "Cyberpunk 2077" compare equal: how a Proton
    game's stream finds the desktop shortcut Steam made for it."""
    text = text.lower()
    if text.endswith(".exe"):
        text = text[:-4]
    return re.sub(r"[^a-z0-9]", "", text)


def _application_dirs() -> list[Path]:
    home = Path.home()
    data_home = os.environ.get("XDG_DATA_HOME") or str(home / ".local" / "share")
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    roots = [data_home, *data_dirs.split(":"),
             str(home / ".local/share/flatpak/exports/share"),
             "/var/lib/flatpak/exports/share"]
    seen: list[Path] = []
    for root in roots:
        path = Path(root) / "applications"
        if root and path not in seen and path.is_dir():
            seen.append(path)
    return seen


def _read_desktop_entry(path: Path) -> dict[str, str]:
    """The [Desktop Entry] keys we use. Hand-parsed: configparser chokes on
    the duplicate keys and %-codes real desktop files are full of."""
    entry: dict[str, str] = {}
    in_section = False
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("["):
                    if in_section:
                        break
                    in_section = line == "[Desktop Entry]"
                    continue
                if in_section and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    if key in ("Icon", "Exec", "StartupWMClass", "Name"):
                        entry.setdefault(key, value.strip())
    except OSError:
        pass
    return entry


def _exec_binary(exec_line: str) -> str:
    """Program name from an Exec= line, looking through env/flatpak wrappers."""
    tokens = [t for t in exec_line.split() if not t.startswith("%")]
    while tokens and (tokens[0].endswith("/env") or tokens[0] == "env"
                      or "=" in tokens[0]):
        tokens.pop(0)
    if not tokens:
        return ""
    if tokens[0].rsplit("/", 1)[-1] == "flatpak":
        # flatpak run [--options] org.app.Id
        ids = [t for t in tokens[1:] if t != "run" and not t.startswith("-")]
        return ids[0] if ids else ""
    return tokens[0].rsplit("/", 1)[-1]


@lru_cache(maxsize=1)
def _desktop_index() -> tuple[dict[str, str], ...]:
    """Icon names keyed by lowercased id / WM class / binary / name, in the
    order a lookup should trust them. First desktop file wins, matching the
    XDG precedence of the directories."""
    by_id: dict[str, str] = {}
    by_wmclass: dict[str, str] = {}
    by_exec: dict[str, str] = {}
    by_name: dict[str, str] = {}
    for directory in _application_dirs():
        for path in directory.rglob("*.desktop"):
            entry = _read_desktop_entry(path)
            icon = entry.get("Icon")
            if not icon:
                continue
            stem = path.stem.lower()
            by_id.setdefault(stem, icon)
            # org.mozilla.firefox → also findable as "firefox".
            by_id.setdefault(stem.rsplit(".", 1)[-1], icon)
            if entry.get("StartupWMClass"):
                by_wmclass.setdefault(entry["StartupWMClass"].lower(), icon)
            binary = _exec_binary(entry.get("Exec", "")).lower()
            if binary and binary not in _HOST_BINARIES:
                by_exec.setdefault(binary, icon)
            if entry.get("Name") and _loose(entry["Name"]):
                by_name.setdefault(_loose(entry["Name"]), icon)
    return by_id, by_wmclass, by_exec, by_name


def _load(icon: str) -> QIcon | None:
    if os.path.isabs(icon):
        result = QIcon(icon) if os.path.exists(icon) else QIcon()
    else:
        result = QIcon.fromTheme(icon)
    return None if result.isNull() else result


@lru_cache(maxsize=256)
def app_icon(icon_name: str = "", binary: str = "", app_id: str = "",
             app_name: str = "") -> QIcon | None:
    """Icon for a stream, from its PipeWire properties; None if unknown.

    Cached per identity: the mixer asks on every poll tick.
    """
    if icon_name:
        found = _load(icon_name)
        if found is not None:
            return found

    binary = binary.rsplit("/", 1)[-1]
    if binary.lower() in _HOST_BINARIES:
        binary = ""
    candidates = [c.strip().lower() for c in (app_id, binary, app_name) if c and c.strip()]
    by_id, by_wmclass, by_exec, by_name = _desktop_index()
    for table, keys in ((by_id, candidates), (by_wmclass, candidates),
                        (by_exec, candidates), (by_name, [_loose(c) for c in candidates])):
        for key in keys:
            icon = table.get(key) if key else None
            if icon:
                found = _load(icon)
                if found is not None:
                    return found
    # Some programs ship a theme icon under their own name but no desktop file.
    for key in candidates:
        found = _load(key)
        if found is not None:
            return found
    return None


def icon_hint(proplist) -> tuple[str, str, str]:
    """The stream properties app_icon() needs, as a hashable tuple."""
    return (
        (proplist.get("application.icon_name", "") or "").strip(),
        (proplist.get("application.process.binary", "") or "").strip(),
        (proplist.get("pipewire.access.portal.app_id", "")
         or proplist.get("application.id", "") or "").strip(),
    )
