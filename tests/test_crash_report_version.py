"""A crash is reported against the version that crashed (#284, #285)."""

import json
import sys

from arctis_sound_manager import bug_reporter


def _crash(tmp_path, monkeypatch, running: str):
    monkeypatch.setattr(bug_reporter, "CRASH_REPORT_FILE", tmp_path / "crash.json")
    monkeypatch.setattr(bug_reporter, "RUNNING_VERSION", running)
    try:
        raise AttributeError("boom")
    except AttributeError:
        bug_reporter.write_crash_report(*sys.exc_info())


def test_crash_records_the_running_version(tmp_path, monkeypatch):
    _crash(tmp_path, monkeypatch, "1.4.28")
    assert json.loads((tmp_path / "crash.json").read_text())["version"] == "1.4.28"


def test_crash_from_the_same_version_is_offered(tmp_path, monkeypatch):
    _crash(tmp_path, monkeypatch, "1.4.29")
    assert bug_reporter.read_crash_report()["traceback"]


def test_crash_from_an_older_version_is_dropped(tmp_path, monkeypatch):
    # The previous release's tray dying during the upgrade to this one.
    _crash(tmp_path, monkeypatch, "1.4.28")
    monkeypatch.setattr(bug_reporter, "RUNNING_VERSION", "1.4.29")
    assert bug_reporter.read_crash_report() is None
    assert not (tmp_path / "crash.json").exists()


def test_crash_without_a_version_is_still_offered(tmp_path, monkeypatch):
    monkeypatch.setattr(bug_reporter, "CRASH_REPORT_FILE", tmp_path / "crash.json")
    (tmp_path / "crash.json").write_text(json.dumps({"traceback": "x"}))
    assert bug_reporter.read_crash_report() == {"traceback": "x"}
