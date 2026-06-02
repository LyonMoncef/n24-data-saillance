"""Per-session sleep override schema — user manual corrections for ambiguous nights.

For an N24 patient the raw Samsung Health sleep_id grouping is not always the
right granularity : some real catch-up sessions (15-22h) are biologically
single sleeps, others are over-merged by Samsung, and the user is the only
arbiter. This schema exposes a YAML file where the user can correct the
auto-detection by tagging individual ``sleep_id``s :

- ``set_main`` : this session is the main sleep of the night (overrides the
  longest-session rule) — also reassigns the night if the user gives a date
  different from the midpoint-derived one
- ``mark_as_nap`` : this session is excluded from main-sleep selection but
  still contributes to TST
- ``exclude`` : this session is removed entirely (data quality issue)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

OverrideAction = Literal["set_main", "mark_as_nap", "exclude"]


class SleepOverride(BaseModel):
    """One per-session annotation."""

    date: date
    sleep_id: str = Field(..., min_length=1)
    action: OverrideAction
    notes: str | None = None


class SleepOverridesFile(BaseModel):
    """Subject-level overrides file — the contract of ``sleep_sessions.yaml``."""

    subject_id: str = Field(..., min_length=1, max_length=64)
    timezone: str = "Europe/Paris"
    overrides: list[SleepOverride] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_unique_sleep_ids(self) -> SleepOverridesFile:
        seen: dict[str, SleepOverride] = {}
        for o in self.overrides:
            if o.sleep_id in seen:
                raise ValueError(
                    f"duplicate override for sleep_id {o.sleep_id!r} "
                    f"(first: action={seen[o.sleep_id].action}, second: action={o.action})"
                )
            seen[o.sleep_id] = o
        return self

    def by_sleep_id(self) -> dict[str, SleepOverride]:
        return {o.sleep_id: o for o in self.overrides}


def load_sleep_overrides(yaml_path: Path) -> SleepOverridesFile:
    """Parse + validate a ``sleep_sessions.yaml`` file.

    Accepts both the full form (dict with ``subject_id`` + ``overrides``) and a
    bare list of override dicts — same ergonomics as ``load_periods``.
    """
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError(f"{yaml_path} is empty")
    if isinstance(raw, list):
        parent = yaml_path.resolve().parent
        subject_id = parent.name if parent.name not in ("", "/") else "unknown"
        raw = {"subject_id": subject_id, "overrides": raw}
    return SleepOverridesFile.model_validate(raw)


def dump_sleep_overrides(file: SleepOverridesFile, yaml_path: Path) -> None:
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        yaml.safe_dump(file.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
