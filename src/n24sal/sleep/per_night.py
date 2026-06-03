"""Per-night sleep aggregation — identifies the main sleep period per night.

A **night** is the local-time window 20h (J-1) → 20h (J), keyed by morning
date J. A **session** is a contiguous sleep period sharing the same
``sleep_id``, spanning one or more non-AWAKE stages. For each night :

- ``main_*`` columns describe the **longest session** whose midpoint falls in
  that night's window (the chronobiological "main sleep period")
- ``tst_h`` is the total sleep time = sum of all session durations attributed
  to the night (main + naps)
- ``n_sessions`` is the count of distinct sessions in the night

Why midpoint assignment ? A session starting at 16:58 and ending at 03:11 next
morning is chronobiologically a "night sleep" — but a start-time rule
(``hour >= 20``) would mis-assign it to the previous night. The midpoint rule
puts it correctly in the night where most of the sleep occurs.

Why ``sleep_id`` grouping ? Samsung Health (and Health Connect generally)
attaches a stable session ID to all stages of a single uninterrupted sleep.
Grouping by ``sleep_id`` is the canonical way to recover sessions ; it avoids
heuristics about "small AWAKE gaps within main sleep".

**User-defined night boundaries** : real-world data has cases the auto-rule
can't solve — legitimate early-evening catch-up sleeps that span the 20h
boundary, polyphasic nights where Samsung's session split doesn't match the
biological reality. The optional ``night_boundaries`` parameter accepts a
:class:`SleepNightsFile` ; for each user-defined night the auto-detection is
**replaced** :

- ``main_onset`` = user's ``start``
- ``main_offset`` = user's ``end``
- ``main_duration_h`` = wall time ``end − start``
- ``tst_h`` = sum of non-AWAKE stage durations clipped to the window
- ``n_sessions`` = count of distinct ``sleep_id`` overlapping the window

Dates without an override fall back to auto-detection on the remaining
sessions (sessions consumed by a user-defined night are not re-counted).
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from n24sal.io.sleep_nights import SleepNightsFile

NIGHT_START_HOUR = 20


def _assign_night_by_midpoint(midpoint: pd.Timestamp) -> date:
    """Return the morning date of the 20h→20h night window containing ``midpoint``."""
    morning = midpoint.date()
    if midpoint.hour >= NIGHT_START_HOUR:
        morning = morning + timedelta(days=1)
    return morning


def _user_defined_row(
    nb,
    non_awake: pd.DataFrame,
    sleep_id_col: str,
    timezone: str,
) -> dict:
    """Compute a per-night row for one user-defined boundary."""
    start_local = pd.Timestamp(nb.start).tz_convert(timezone)
    end_local = pd.Timestamp(nb.end).tz_convert(timezone)
    # Find stages overlapping [start, end] (any overlap counts)
    mask = (non_awake["_local_start"] < end_local) & (non_awake["_local_end"] > start_local)
    in_window = non_awake[mask]
    if in_window.empty:
        tst_h = 0.0
        n_sessions = 0
    else:
        # Clip stage durations to window for TST
        clipped_start = in_window["_local_start"].clip(lower=start_local)
        clipped_end = in_window["_local_end"].clip(upper=end_local)
        tst_h = float(((clipped_end - clipped_start).dt.total_seconds()).sum() / 3600.0)
        n_sessions = int(in_window[sleep_id_col].nunique())
    return {
        "night": nb.date,
        "main_onset": start_local,
        "main_offset": end_local,
        "main_duration_h": (end_local - start_local).total_seconds() / 3600.0,
        "n_sessions": n_sessions,
        "tst_h": tst_h,
    }


def main_sleep_per_night(
    sleep_intervals: pd.DataFrame,
    *,
    timezone: str,
    night_boundaries: SleepNightsFile | None = None,
    sleep_id_col: str = "sleep_id",
    stage_name_col: str = "stage_name",
    awake_label: str = "AWAKE",
) -> pd.DataFrame:
    """Compute the main sleep period and TST per night, optionally honoring user-defined boundaries.

    Parameters
    ----------
    sleep_intervals
        DataFrame with columns ``stage_start`` (tz-aware), ``stage_end``
        (tz-aware), ``stage_name`` (string), ``sleep_id`` (string).
    timezone
        IANA timezone for the local 20h→20h night window.
    night_boundaries
        Optional :class:`SleepNightsFile`. For each user-defined night, the
        auto-detection is replaced (see module docstring).
    sleep_id_col, stage_name_col, awake_label
        Column / label overrides if the input doesn't match defaults.

    Returns
    -------
    pandas.DataFrame
        Indexed by ``night`` (the morning date of the night J-1 → J). Columns :
        ``main_onset``, ``main_offset``, ``main_duration_h`` (float),
        ``n_sessions`` (int), ``tst_h`` (float).
    """
    empty_cols = ["main_onset", "main_offset", "main_duration_h", "n_sessions", "tst_h"]
    if sleep_intervals.empty:
        return pd.DataFrame(columns=empty_cols)

    df = sleep_intervals.copy()
    df["_local_start"] = df["stage_start"].dt.tz_convert(timezone)
    df["_local_end"] = df["stage_end"].dt.tz_convert(timezone)

    awake_upper = awake_label.upper()
    awake_mask = df[stage_name_col].astype(str).str.upper() == awake_upper
    non_awake = df[~awake_mask]
    if non_awake.empty:
        return pd.DataFrame(columns=empty_cols)

    user_rows: list[dict] = []
    consumed_sleep_ids: set[str] = set()
    if night_boundaries is not None and night_boundaries.nights:
        for nb in night_boundaries.nights:
            row = _user_defined_row(nb, non_awake, sleep_id_col, timezone)
            user_rows.append(row)
            # Record which sleep_ids fell into this user-defined window so we
            # don't double-count them in the auto-detection below.
            start_local = pd.Timestamp(nb.start).tz_convert(timezone)
            end_local = pd.Timestamp(nb.end).tz_convert(timezone)
            mask = (non_awake["_local_start"] < end_local) & (non_awake["_local_end"] > start_local)
            consumed_sleep_ids.update(non_awake.loc[mask, sleep_id_col].unique().tolist())

    # Build sessions from REMAINING stages (not consumed by any user-defined night)
    remaining_non_awake = non_awake[~non_awake[sleep_id_col].isin(consumed_sleep_ids)]

    auto_rows: list[dict] = []
    if not remaining_non_awake.empty:
        sessions = remaining_non_awake.groupby(sleep_id_col).agg(
            onset=("_local_start", "min"),
            offset=("_local_end", "max"),
        )
        sessions["duration_h"] = (
            sessions["offset"] - sessions["onset"]
        ).dt.total_seconds() / 3600.0
        sessions["midpoint"] = sessions["onset"] + (sessions["offset"] - sessions["onset"]) / 2
        sessions["night"] = sessions["midpoint"].apply(_assign_night_by_midpoint)

        for night, group in sessions.groupby("night"):
            main = group.loc[group["duration_h"].idxmax()]
            auto_rows.append(
                {
                    "night": night,
                    "main_onset": main["onset"],
                    "main_offset": main["offset"],
                    "main_duration_h": main["duration_h"],
                    "n_sessions": len(group),
                    "tst_h": float(group["duration_h"].sum()),
                }
            )

    # Combine user-defined + auto, dropping any auto row whose night already has a user override
    user_dates = {r["night"] for r in user_rows}
    combined = user_rows + [r for r in auto_rows if r["night"] not in user_dates]
    if not combined:
        return pd.DataFrame(columns=empty_cols)
    result = pd.DataFrame(combined).set_index("night").sort_index()
    result.index.name = "night"
    return result
