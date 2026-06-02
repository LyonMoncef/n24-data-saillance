"""Tests for n24sal.sleep.per_night.main_sleep_per_night."""

from __future__ import annotations

import pandas as pd
import pytest

from n24sal.sleep import main_sleep_per_night


def _df(rows: list[tuple[str, str, str, str]]) -> pd.DataFrame:
    """Build a sleep_intervals-like DataFrame from (start_local, end_local, stage, sleep_id) tuples.

    Timestamps are interpreted as Europe/Paris and stored as UTC tz-aware in the
    output (matching the contract of `sleep_intervals.parquet`).
    """
    return pd.DataFrame(
        {
            "stage_start": pd.to_datetime([r[0] for r in rows]).tz_localize("Europe/Paris").tz_convert("UTC"),
            "stage_end": pd.to_datetime([r[1] for r in rows]).tz_localize("Europe/Paris").tz_convert("UTC"),
            "stage_name": [r[2] for r in rows],
            "sleep_id": [r[3] for r in rows],
        }
    )


def test_empty_input_returns_empty_frame():
    df = pd.DataFrame(columns=["stage_start", "stage_end", "stage_name", "sleep_id"])
    res = main_sleep_per_night(df, timezone="Europe/Paris")
    assert res.empty
    assert list(res.columns) == ["main_onset", "main_offset", "main_duration_h", "n_sessions", "tst_h"]


def test_only_awake_input_returns_empty_frame():
    df = _df([("2025-04-06 23:00", "2025-04-07 00:00", "AWAKE", "S1")])
    res = main_sleep_per_night(df, timezone="Europe/Paris")
    assert res.empty


def test_single_simple_night():
    """Bedtime 23h, wake 06:30, one continuous session."""
    df = _df(
        [
            ("2025-04-06 23:00", "2025-04-07 02:00", "LIGHT", "S1"),
            ("2025-04-07 02:00", "2025-04-07 04:30", "DEEP", "S1"),
            ("2025-04-07 04:30", "2025-04-07 06:30", "REM", "S1"),
        ]
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris")
    night = pd.Timestamp("2025-04-07").date()
    assert len(res) == 1
    assert res.loc[night, "n_sessions"] == 1
    assert abs(res.loc[night, "main_duration_h"] - 7.5) < 0.01
    assert abs(res.loc[night, "tst_h"] - 7.5) < 0.01


def test_main_sleep_is_longest_session_not_first():
    """Three sessions same night : evening nap + main night sleep + daytime nap.
    Main = longest = night sleep ; TST = sum of all three."""
    df = _df(
        [
            # Evening nap before main sleep (1.5h)
            ("2025-04-06 21:15", "2025-04-06 22:45", "LIGHT", "NAP_EVE"),
            # Main night sleep (7h)
            ("2025-04-06 23:30", "2025-04-07 06:30", "DEEP", "NIGHT"),
            # Daytime nap (1h)
            ("2025-04-07 14:00", "2025-04-07 15:00", "LIGHT", "NAP_DAY"),
        ]
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris")
    night = pd.Timestamp("2025-04-07").date()
    assert res.loc[night, "n_sessions"] == 3
    assert abs(res.loc[night, "main_duration_h"] - 7.0) < 0.01
    assert abs(res.loc[night, "tst_h"] - (1.5 + 7.0 + 1.0)) < 0.01
    # Onset = main session start, NOT the earliest session start
    assert res.loc[night, "main_onset"].hour in (23, 21)  # tz-aware, depends on conversion
    # Strict check via duration: end - onset = 7h
    delta = (res.loc[night, "main_offset"] - res.loc[night, "main_onset"]).total_seconds() / 3600
    assert abs(delta - 7.0) < 0.01


def test_late_afternoon_start_session_assigned_by_midpoint():
    """A session starting at 16:58 and ending at 03:11 should be assigned to the
    night where its MIDPOINT falls — chronobiologically the next morning, not
    the previous one (a start-time-only rule would mis-assign it)."""
    df = _df(
        [
            ("2025-04-06 16:58", "2025-04-07 03:11", "LIGHT", "LONG"),
        ]
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris")
    # Midpoint ≈ 22:04 on 2025-04-06, hour >= 20 → night = 2025-04-07
    assert pd.Timestamp("2025-04-07").date() in res.index
    assert pd.Timestamp("2025-04-06").date() not in res.index


def test_awake_stages_excluded_from_session_duration():
    """AWAKE stages within a sleep_id are filtered out before duration math."""
    df = _df(
        [
            ("2025-04-06 23:00", "2025-04-07 02:00", "LIGHT", "S1"),
            ("2025-04-07 02:00", "2025-04-07 02:30", "AWAKE", "S1"),
            ("2025-04-07 02:30", "2025-04-07 06:30", "REM", "S1"),
        ]
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris")
    night = pd.Timestamp("2025-04-07").date()
    # Duration uses min(start)-max(end) of non-AWAKE: 23:00 → 06:30 = 7.5h
    # (We accept the AWAKE-bridge time as part of the session ; a stricter
    # "summed non-AWAKE only" version is out of scope here.)
    assert abs(res.loc[night, "main_duration_h"] - 7.5) < 0.01
    assert res.loc[night, "n_sessions"] == 1


def test_multiple_nights_sorted_by_index():
    df = _df(
        [
            ("2025-04-07 23:00", "2025-04-08 06:00", "DEEP", "N2"),
            ("2025-04-06 23:00", "2025-04-07 06:00", "DEEP", "N1"),
        ]
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris")
    nights = list(res.index)
    assert nights == sorted(nights)
    assert len(res) == 2


def test_custom_awake_label():
    df = _df(
        [
            ("2025-04-06 23:00", "2025-04-07 06:00", "asleep", "S1"),
            ("2025-04-07 06:00", "2025-04-07 07:00", "wake", "S1"),
        ]
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris", awake_label="wake")
    night = pd.Timestamp("2025-04-07").date()
    assert abs(res.loc[night, "main_duration_h"] - 7.0) < 0.01


# -------------------- User-defined night boundaries --------------------


from datetime import date as _date, datetime as _datetime, timedelta as _td, timezone as _tz

from n24sal.io.sleep_nights import NightBoundary, SleepNightsFile

_PARIS = _tz(_td(hours=2))  # Europe/Paris in summer (sufficient for tests)


def test_user_boundary_replaces_auto_detection_for_that_night():
    """A user defines an early-evening catch-up that spans 18h day J → 03:30 day J+1.
    Both Samsung sessions in this window are aggregated as ONE night."""
    df = _df(
        [
            # Samsung sees two sessions in that bio night (its sleep_id split on
            # a brief awake) — but the user defines it as ONE biological night.
            ("2025-04-06 18:14", "2025-04-06 22:30", "DEEP", "EVE"),
            ("2025-04-06 23:00", "2025-04-07 03:38", "REM", "MORN"),
        ]
    )
    nights_file = SleepNightsFile(
        subject_id="S001",
        nights=[
            NightBoundary(
                date=_date(2025, 4, 7),
                start=_datetime(2025, 4, 6, 18, 14, tzinfo=_PARIS),
                end=_datetime(2025, 4, 7, 3, 38, tzinfo=_PARIS),
                notes="Catch-up précoce dimanche",
            ),
        ],
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris", night_boundaries=nights_file)
    assert _date(2025, 4, 7) in res.index
    night = res.loc[_date(2025, 4, 7)]
    # main_duration = wall time between user-defined start and end
    expected_wall_h = (3 + 38 / 60) + (24 - 18 - 14 / 60)  # 9.4h
    assert abs(night["main_duration_h"] - expected_wall_h) < 0.05
    # n_sessions = 2 distinct sleep_ids overlapping the window
    assert night["n_sessions"] == 2
    # tst_h = sum of non-AWAKE durations clipped to window
    # EVE 18:14→22:30 = 4.27h, MORN 23:00→03:38 = 4.63h → ~8.9h
    assert abs(night["tst_h"] - (4 + 16 / 60 + 4 + 38 / 60)) < 0.05


def test_user_boundary_overrides_auto_for_dates_without_override():
    """Two nights : one with user boundary, one without. Both appear in result."""
    df = _df(
        [
            # Night 1 (2025-04-07): standard night sleep
            ("2025-04-06 23:00", "2025-04-07 06:30", "DEEP", "N1"),
            # Night 2 (2025-04-08): user-defined catch-up
            ("2025-04-07 18:00", "2025-04-08 02:00", "DEEP", "N2_EVE"),
        ]
    )
    nights_file = SleepNightsFile(
        subject_id="S001",
        nights=[
            NightBoundary(
                date=_date(2025, 4, 8),
                start=_datetime(2025, 4, 7, 18, 0, tzinfo=_PARIS),
                end=_datetime(2025, 4, 8, 2, 0, tzinfo=_PARIS),
            ),
        ],
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris", night_boundaries=nights_file)
    # Night 2025-04-07 = auto (N1 = 7.5h)
    assert abs(res.loc[_date(2025, 4, 7), "main_duration_h"] - 7.5) < 0.01
    # Night 2025-04-08 = user (8.0h wall, 8.0h TST since one continuous session)
    assert abs(res.loc[_date(2025, 4, 8), "main_duration_h"] - 8.0) < 0.01


def test_user_boundary_consumes_session_from_auto_assignment():
    """A session that auto-detection would put in night X is instead consumed
    by a user boundary for night Y. It must not appear in BOTH nights."""
    df = _df(
        [
            # Without override : midpoint ~22:00 → night 2025-04-08
            ("2025-04-07 18:00", "2025-04-08 02:00", "DEEP", "S1"),
        ]
    )
    nights_file = SleepNightsFile(
        subject_id="S001",
        nights=[
            NightBoundary(
                date=_date(2025, 4, 9),  # user assigns to a DIFFERENT date
                start=_datetime(2025, 4, 7, 18, 0, tzinfo=_PARIS),
                end=_datetime(2025, 4, 8, 2, 0, tzinfo=_PARIS),
            ),
        ],
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris", night_boundaries=nights_file)
    # Should appear only on the user-defined night (2025-04-09), not on auto (2025-04-08)
    assert _date(2025, 4, 9) in res.index
    assert _date(2025, 4, 8) not in res.index


def test_user_boundary_with_no_overlapping_stages_still_reports_window():
    """User defines a night where no Samsung stages exist (sensor off). The row
    is still created with the user-defined window but n_sessions=0 and tst_h=0."""
    df = _df(
        [
            # A real session on a different night
            ("2025-04-07 23:00", "2025-04-08 06:00", "DEEP", "REAL"),
        ]
    )
    nights_file = SleepNightsFile(
        subject_id="S001",
        nights=[
            NightBoundary(
                date=_date(2025, 4, 10),
                start=_datetime(2025, 4, 9, 22, 0, tzinfo=_PARIS),
                end=_datetime(2025, 4, 10, 6, 0, tzinfo=_PARIS),
                notes="Sensor was off, no data captured",
            ),
        ],
    )
    res = main_sleep_per_night(df, timezone="Europe/Paris", night_boundaries=nights_file)
    user_night = res.loc[_date(2025, 4, 10)]
    assert user_night["n_sessions"] == 0
    assert user_night["tst_h"] == 0.0
    assert abs(user_night["main_duration_h"] - 8.0) < 0.01
    # And the auto-detected night is still present
    assert _date(2025, 4, 8) in res.index
