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
