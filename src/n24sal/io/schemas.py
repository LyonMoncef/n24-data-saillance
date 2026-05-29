"""Portable actigraphy schema — independent of capture device.

Two artefacts per subject:

1. **Time-series parquet** validated by :func:`validate_actigraphy_frame`.
   Required columns: ``timestamp``, ``activity``. Optional: ``light_lux``,
   ``sleep_state``.

2. **JSON metadata sidecar** modelled by :class:`SubjectMetadata` describing
   the recording context (device, epoch length, timezone, demographics,
   diagnosis).

Keeping these decoupled lets the same NPCRA pipeline run on Samsung Health
exports, Philips Actiwatch CSV, GENEActiv ``.bin`` processed series, or
CamNtech MotionWatch output without branching on the source.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, field_validator

ACTIGRAPHY_REQUIRED_COLUMNS: tuple[str, ...] = ("timestamp", "activity")
ACTIGRAPHY_OPTIONAL_COLUMNS: tuple[str, ...] = ("light_lux", "sleep_state")

DeviceKind = Literal[
    "samsung_galaxy_watch",
    "philips_actiwatch",
    "camntech_motionwatch",
    "geneactiv",
    "axivity_ax3",
    "fitbit",
    "apple_watch",
    "other",
]

SourceQuality = Literal["high", "medium", "low"]
Sex = Literal["M", "F", "O"]


class SubjectMetadata(BaseModel):
    """JSON sidecar describing a recording. One file per subject per session."""

    subject_id: str = Field(..., min_length=1, max_length=64)
    device: DeviceKind
    epoch_seconds: int = Field(..., gt=0, le=3600)
    timezone: str = Field(..., description="IANA timezone identifier, e.g. 'Europe/Paris'")
    recording_start: datetime
    recording_end: datetime
    source_quality: SourceQuality = "medium"

    age: int | None = Field(default=None, ge=0, le=120)
    sex: Sex | None = None
    diagnosis: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("recording_end")
    @classmethod
    def _end_after_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("recording_start")
        if start is not None and v <= start:
            raise ValueError("recording_end must be strictly after recording_start")
        return v


def validate_actigraphy_frame(df: pd.DataFrame) -> None:
    """Contract check on a portable actigraphy DataFrame.

    Raises :class:`ValueError` on the first violation. Silent on success.
    """

    missing = [c for c in ACTIGRAPHY_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise ValueError("'timestamp' column must be datetime dtype")

    if not pd.api.types.is_numeric_dtype(df["activity"]):
        raise ValueError("'activity' column must be numeric")

    if df["activity"].isna().all():
        raise ValueError("'activity' column is entirely NaN")

    if len(df) >= 2:
        diffs = df["timestamp"].diff().dropna()
        if (diffs <= pd.Timedelta(0)).any():
            raise ValueError("'timestamp' column must be strictly monotonically increasing")
