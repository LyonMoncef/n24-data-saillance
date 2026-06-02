"""Tests for n24sal.io.sleep_overrides."""

from __future__ import annotations

from datetime import date

import pytest

from n24sal.io.sleep_overrides import (
    SleepOverride,
    SleepOverridesFile,
    dump_sleep_overrides,
    load_sleep_overrides,
)


def test_sleep_override_valid_minimal():
    o = SleepOverride(date=date(2026, 5, 1), sleep_id="abc-123", action="set_main")
    assert o.notes is None
    assert o.action == "set_main"


def test_sleep_override_rejects_invalid_action():
    with pytest.raises(ValueError):
        SleepOverride(date=date(2026, 5, 1), sleep_id="abc", action="wrong_action")


def test_sleep_overrides_file_rejects_duplicate_sleep_ids():
    with pytest.raises(ValueError, match="duplicate override"):
        SleepOverridesFile(
            subject_id="S001",
            overrides=[
                SleepOverride(date=date(2026, 1, 1), sleep_id="X", action="set_main"),
                SleepOverride(date=date(2026, 2, 1), sleep_id="X", action="exclude"),
            ],
        )


def test_sleep_overrides_by_sleep_id_index():
    f = SleepOverridesFile(
        subject_id="S001",
        overrides=[
            SleepOverride(date=date(2026, 1, 1), sleep_id="A", action="set_main"),
            SleepOverride(date=date(2026, 2, 1), sleep_id="B", action="mark_as_nap"),
        ],
    )
    idx = f.by_sleep_id()
    assert idx["A"].action == "set_main"
    assert idx["B"].action == "mark_as_nap"
    assert "missing" not in idx


def test_load_sleep_overrides_full_form(tmp_path):
    p = tmp_path / "sleep_sessions.yaml"
    p.write_text(
        """\
subject_id: S001
timezone: Europe/Paris
overrides:
  - date: 2024-06-01
    sleep_id: 927e3715-69bf-4c4c-aca9-791ca9d10453
    action: set_main
    notes: "Catch-up dimanche après semaine difficile"
  - date: 2024-12-15
    sleep_id: 0c7f322c-9fb7-48b2-b4a6-c4f384ba80f3
    action: exclude
""",
        encoding="utf-8",
    )
    f = load_sleep_overrides(p)
    assert f.subject_id == "S001"
    assert len(f.overrides) == 2
    assert f.overrides[0].notes.startswith("Catch-up")


def test_load_sleep_overrides_list_form_infers_subject(tmp_path):
    subj_dir = tmp_path / "S001"
    subj_dir.mkdir()
    p = subj_dir / "sleep_sessions.yaml"
    p.write_text(
        """\
- date: 2024-06-01
  sleep_id: A
  action: set_main
""",
        encoding="utf-8",
    )
    f = load_sleep_overrides(p)
    assert f.subject_id == "S001"
    assert len(f.overrides) == 1


def test_load_sleep_overrides_rejects_empty_file(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="is empty"):
        load_sleep_overrides(p)


def test_dump_sleep_overrides_roundtrip(tmp_path):
    original = SleepOverridesFile(
        subject_id="S002",
        timezone="UTC",
        overrides=[SleepOverride(date=date(2026, 1, 1), sleep_id="X", action="exclude")],
    )
    p = tmp_path / "out.yaml"
    dump_sleep_overrides(original, p)
    reloaded = load_sleep_overrides(p)
    assert reloaded.subject_id == "S002"
    assert reloaded.overrides[0].action == "exclude"
