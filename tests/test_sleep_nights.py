"""Tests for n24sal.io.sleep_nights."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from n24sal.io.sleep_nights import (
    NightBoundary,
    SleepNightsFile,
    dump_sleep_nights,
    load_sleep_nights,
)

PARIS_PLUS_2 = timezone(timedelta(hours=2))


def test_night_boundary_valid_minimal():
    nb = NightBoundary(
        date=date(2026, 5, 27),
        start=datetime(2026, 5, 26, 18, 14, tzinfo=PARIS_PLUS_2),
        end=datetime(2026, 5, 27, 3, 38, tzinfo=PARIS_PLUS_2),
    )
    assert nb.notes is None


def test_night_boundary_rejects_naive_start():
    with pytest.raises(ValueError, match="tz-aware"):
        NightBoundary(
            date=date(2026, 5, 27),
            start=datetime(2026, 5, 26, 18, 14),  # naive
            end=datetime(2026, 5, 27, 3, 38, tzinfo=PARIS_PLUS_2),
        )


def test_night_boundary_rejects_end_before_start():
    with pytest.raises(ValueError, match="strictly after"):
        NightBoundary(
            date=date(2026, 5, 27),
            start=datetime(2026, 5, 27, 6, tzinfo=PARIS_PLUS_2),
            end=datetime(2026, 5, 27, 3, tzinfo=PARIS_PLUS_2),
        )


def test_night_boundary_rejects_implausibly_long_window():
    with pytest.raises(ValueError, match="implausibly long"):
        NightBoundary(
            date=date(2026, 5, 27),
            start=datetime(2026, 5, 25, 12, tzinfo=PARIS_PLUS_2),
            end=datetime(2026, 5, 27, 23, tzinfo=PARIS_PLUS_2),  # 59h
        )


def test_sleep_nights_file_rejects_duplicate_dates():
    with pytest.raises(ValueError, match="duplicate night boundary"):
        SleepNightsFile(
            subject_id="S001",
            nights=[
                NightBoundary(
                    date=date(2026, 5, 27),
                    start=datetime(2026, 5, 26, 22, tzinfo=PARIS_PLUS_2),
                    end=datetime(2026, 5, 27, 6, tzinfo=PARIS_PLUS_2),
                ),
                NightBoundary(
                    date=date(2026, 5, 27),
                    start=datetime(2026, 5, 26, 18, tzinfo=PARIS_PLUS_2),
                    end=datetime(2026, 5, 27, 4, tzinfo=PARIS_PLUS_2),
                ),
            ],
        )


def test_sleep_nights_file_by_date_index():
    f = SleepNightsFile(
        subject_id="S001",
        nights=[
            NightBoundary(
                date=date(2026, 5, 27),
                start=datetime(2026, 5, 26, 18, tzinfo=PARIS_PLUS_2),
                end=datetime(2026, 5, 27, 3, 38, tzinfo=PARIS_PLUS_2),
            ),
        ],
    )
    idx = f.by_date()
    assert date(2026, 5, 27) in idx
    assert idx[date(2026, 5, 27)].start.hour == 18


def test_load_sleep_nights_full_form(tmp_path):
    p = tmp_path / "sleep_nights.yaml"
    p.write_text(
        """\
subject_id: S001
timezone: Europe/Paris
nights:
  - date: 2026-05-27
    start: 2026-05-26T18:14:00+02:00
    end: 2026-05-27T03:38:00+02:00
    notes: "Catch-up précoce dimanche"
""",
        encoding="utf-8",
    )
    f = load_sleep_nights(p)
    assert f.subject_id == "S001"
    assert len(f.nights) == 1
    assert f.nights[0].notes.startswith("Catch-up")


def test_load_sleep_nights_list_form_infers_subject(tmp_path):
    subj_dir = tmp_path / "S001"
    subj_dir.mkdir()
    p = subj_dir / "sleep_nights.yaml"
    p.write_text(
        """\
- date: 2026-05-27
  start: 2026-05-26T18:14:00+02:00
  end: 2026-05-27T03:38:00+02:00
""",
        encoding="utf-8",
    )
    f = load_sleep_nights(p)
    assert f.subject_id == "S001"


def test_dump_sleep_nights_roundtrip(tmp_path):
    original = SleepNightsFile(
        subject_id="S002",
        nights=[
            NightBoundary(
                date=date(2026, 5, 27),
                start=datetime(2026, 5, 26, 18, 14, tzinfo=PARIS_PLUS_2),
                end=datetime(2026, 5, 27, 3, 38, tzinfo=PARIS_PLUS_2),
                notes="x",
            ),
        ],
    )
    p = tmp_path / "out.yaml"
    dump_sleep_nights(original, p)
    reloaded = load_sleep_nights(p)
    assert reloaded.subject_id == "S002"
    assert reloaded.nights[0].notes == "x"
