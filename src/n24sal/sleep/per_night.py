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
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

NIGHT_START_HOUR = 20


def _assign_night_by_midpoint(midpoint: pd.Timestamp) -> date:
    """Return the morning date of the 20h→20h night window containing ``midpoint``."""
    morning = midpoint.date()
    if midpoint.hour >= NIGHT_START_HOUR:
        morning = morning + timedelta(days=1)
    return morning


def main_sleep_per_night(
    sleep_intervals: pd.DataFrame,
    *,
    timezone: str,
    sleep_id_col: str = "sleep_id",
    stage_name_col: str = "stage_name",
    awake_label: str = "AWAKE",
) -> pd.DataFrame:
    """Compute the main sleep period and TST per night.

    Parameters
    ----------
    sleep_intervals
        DataFrame with columns ``stage_start`` (tz-aware), ``stage_end``
        (tz-aware), ``stage_name`` (string), ``sleep_id`` (string).
    timezone
        IANA timezone for the local 20h→20h night window.
    sleep_id_col, stage_name_col, awake_label
        Column / label overrides if the input doesn't match defaults.

    Returns
    -------
    pandas.DataFrame
        Indexed by ``night`` (the morning date of the night J-1 → J). Columns :
        ``main_onset`` (tz-aware Timestamp), ``main_offset`` (tz-aware
        Timestamp), ``main_duration_h`` (float), ``n_sessions`` (int),
        ``tst_h`` (float).

    Empty DataFrame (with the right columns) if input has no non-AWAKE stages.
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

    sessions = non_awake.groupby(sleep_id_col).agg(
        onset=("_local_start", "min"),
        offset=("_local_end", "max"),
    )
    sessions["duration_h"] = (
        sessions["offset"] - sessions["onset"]
    ).dt.total_seconds() / 3600.0
    sessions["midpoint"] = sessions["onset"] + (sessions["offset"] - sessions["onset"]) / 2
    sessions["night"] = sessions["midpoint"].apply(_assign_night_by_midpoint)

    # Per-night: longest session, count, total sleep time
    longest_idx = sessions.groupby("night")["duration_h"].idxmax()
    main = sessions.loc[longest_idx].set_index("night")[["onset", "offset", "duration_h"]]
    main.columns = ["main_onset", "main_offset", "main_duration_h"]

    stats = sessions.groupby("night").agg(
        n_sessions=("duration_h", "size"),
        tst_h=("duration_h", "sum"),
    )

    result = main.join(stats)
    result.index.name = "night"
    return result.sort_index()
