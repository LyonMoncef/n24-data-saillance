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

**Manual overrides** : real-world data has edge cases the auto-detection
can't solve (legitimate 15-22h catch-up sleeps after high sleep debt that
the longest-rule mistakes for outliers ; Samsung's over-merging of distinct
biological sleeps into one sleep_id ; etc.). The optional ``overrides``
parameter accepts a :class:`SleepOverridesFile` with per-``sleep_id``
annotations :

- ``set_main`` : force this session as the main sleep of the night (overrides
  the longest rule, and reassigns the night to the override's ``date`` if
  different from the midpoint-derived one)
- ``mark_as_nap`` : exclude from main-sleep selection but keep in TST
- ``exclude`` : drop entirely
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from n24sal.io.sleep_overrides import SleepOverridesFile

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
    overrides: SleepOverridesFile | None = None,
    sleep_id_col: str = "sleep_id",
    stage_name_col: str = "stage_name",
    awake_label: str = "AWAKE",
) -> pd.DataFrame:
    """Compute the main sleep period and TST per night, with optional manual overrides.

    Parameters
    ----------
    sleep_intervals
        DataFrame with columns ``stage_start`` (tz-aware), ``stage_end``
        (tz-aware), ``stage_name`` (string), ``sleep_id`` (string).
    timezone
        IANA timezone for the local 20h→20h night window.
    overrides
        Optional manual per-session annotations. When provided, ``exclude``
        sessions are dropped, ``mark_as_nap`` sessions cannot be picked as
        main (but still contribute to TST), and ``set_main`` sessions are
        forced as main (the night is reassigned to the override's ``date``).
    sleep_id_col, stage_name_col, awake_label
        Column / label overrides if the input doesn't match defaults.

    Returns
    -------
    pandas.DataFrame
        Indexed by ``night`` (the morning date of the night J-1 → J). Columns :
        ``main_onset`` (tz-aware Timestamp), ``main_offset`` (tz-aware
        Timestamp), ``main_duration_h`` (float), ``n_sessions`` (int),
        ``tst_h`` (float).
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
    sessions["auto_night"] = sessions["midpoint"].apply(_assign_night_by_midpoint)

    # Default : no override, no nap-tag, use midpoint-derived night
    sessions["override_action"] = None
    sessions["night"] = sessions["auto_night"]

    if overrides is not None and overrides.overrides:
        ov_by_id = overrides.by_sleep_id()
        for sid, ov in ov_by_id.items():
            if sid not in sessions.index:
                continue
            sessions.at[sid, "override_action"] = ov.action
            if ov.action == "set_main":
                # Reassign the night to the user-specified date
                sessions.at[sid, "night"] = ov.date

        # Drop excludes
        sessions = sessions[sessions["override_action"] != "exclude"]
        if sessions.empty:
            return pd.DataFrame(columns=empty_cols)

    # Per-night: pick main (set_main override > longest non-nap), compute stats
    rows = []
    for night, group in sessions.groupby("night"):
        forced_main = group[group["override_action"] == "set_main"]
        if not forced_main.empty:
            main_row = forced_main.iloc[0]
        else:
            eligible = group[group["override_action"] != "mark_as_nap"]
            if eligible.empty:
                # All sessions tagged as naps — no main, but TST still computable
                main_row = None
            else:
                main_row = eligible.loc[eligible["duration_h"].idxmax()]
        rows.append(
            {
                "night": night,
                "main_onset": main_row["onset"] if main_row is not None else pd.NaT,
                "main_offset": main_row["offset"] if main_row is not None else pd.NaT,
                "main_duration_h": main_row["duration_h"] if main_row is not None else float("nan"),
                "n_sessions": len(group),
                "tst_h": float(group["duration_h"].sum()),
            }
        )

    result = pd.DataFrame(rows).set_index("night").sort_index()
    result.index.name = "night"
    return result
