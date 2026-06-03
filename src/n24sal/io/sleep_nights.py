"""User-defined night boundaries — manual override of biological sleep periods.

For N24 patients the auto-detection of "main sleep per night" via longest
session sometimes fails to match the user's mental model — typical example :
the user goes to bed early at 18h on day D, sleeps until 03h30 on day D+1.
Samsung sees this as 1-2 sleep_ids split across the 20h→20h calendar boundary,
the longest-session rule mis-classifies it, and the chronobiology numbers go
wrong.

The user is the only authority. This module exposes a YAML file where the
user defines, per date, the explicit ``start`` (bedtime) and ``end``
(wake-up) of the biological night :

.. code-block:: yaml

    subject_id: S001
    timezone: Europe/Paris
    nights:
      - date: 2026-05-27           # canonical date = morning the night ends
        start: 2026-05-26T18:14:00+02:00
        end: 2026-05-27T03:38:00+02:00
        notes: "Early catch-up sleep"

When a date has a user-defined boundary, ``main_sleep_per_night`` ignores its
auto-detection for that date and computes :

- ``main_onset`` = ``start``
- ``main_offset`` = ``end``
- ``main_duration_h`` = wall time ``end - start``
- ``tst_h`` = sum of non-AWAKE stage durations clipped to ``[start, end]``
- ``n_sessions`` = count of distinct ``sleep_id`` overlapping the window

Dates without a user-defined boundary fall back to the auto-detection.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class NightBoundary(BaseModel):
    """One user-defined night : bedtime / wake-up / canonical date."""

    date: date
    start: datetime
    end: datetime
    notes: str | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> NightBoundary:
        # Tz-awareness first — comparing naive vs aware datetimes raises TypeError
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError(
                f"night {self.date}: start and end must be tz-aware datetimes (ISO with offset)"
            )
        if self.end <= self.start:
            raise ValueError(
                f"night {self.date}: end ({self.end}) must be strictly after start ({self.start})"
            )
        # Sanity bound: a single biological night > 30h is almost certainly a mistake
        # (the longest real catch-up sleeps documented in the literature are ~22h)
        if self.end - self.start > timedelta(hours=30):
            raise ValueError(
                f"night {self.date}: window > 30h ({(self.end - self.start).total_seconds() / 3600:.1f}h) "
                "is implausibly long — check the start/end timestamps"
            )
        return self


class SleepNightsFile(BaseModel):
    """Subject-level file — the contract of ``sleep_nights.yaml``."""

    subject_id: str = Field(..., min_length=1, max_length=64)
    timezone: str = "Europe/Paris"
    nights: list[NightBoundary] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_unique_dates(self) -> SleepNightsFile:
        seen: dict[date, NightBoundary] = {}
        for nb in self.nights:
            if nb.date in seen:
                raise ValueError(
                    f"duplicate night boundary for date {nb.date} "
                    "(only one definition allowed per canonical date)"
                )
            seen[nb.date] = nb
        return self

    def by_date(self) -> dict[date, NightBoundary]:
        return {nb.date: nb for nb in self.nights}


def load_sleep_nights(yaml_path: Path) -> SleepNightsFile:
    """Parse + validate ``sleep_nights.yaml``.

    Accepts both the full form (dict with ``subject_id`` + ``nights``) and a
    bare list of night-boundary dicts — same ergonomy as ``load_periods`` and
    ``load_sleep_overrides``.
    """
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError(f"{yaml_path} is empty")
    if isinstance(raw, list):
        parent = yaml_path.resolve().parent
        subject_id = parent.name if parent.name not in ("", "/") else "unknown"
        raw = {"subject_id": subject_id, "nights": raw}
    return SleepNightsFile.model_validate(raw)


def dump_sleep_nights(file: SleepNightsFile, yaml_path: Path) -> None:
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        yaml.safe_dump(file.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
