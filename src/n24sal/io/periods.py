"""Period definitions for regime-aware analysis.

A "period" is a named contiguous date range over which NPCRA metrics are
computed. Multiple periods coexist in a single YAML file per subject so the
case-report manuscript can cite each regime by name.

The YAML schema is validated by :class:`PeriodsFile` (Pydantic). Load via
:func:`load_periods`.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

PERIOD_NAME_RE = re.compile(r"^[a-z0-9_]+$")


class PeriodDef(BaseModel):
    """One named contiguous date range."""

    name: str = Field(..., min_length=1, max_length=64)
    start: date
    end: date
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def _check_name_pattern(cls, v: str) -> str:
        if not PERIOD_NAME_RE.fullmatch(v):
            raise ValueError(
                f"period name {v!r} must match /^[a-z0-9_]+$/ (lowercase, digits, underscores)"
            )
        return v

    @model_validator(mode="after")
    def _check_dates(self) -> PeriodDef:
        if self.end <= self.start:
            raise ValueError(
                f"period {self.name!r}: end ({self.end}) must be strictly after start ({self.start})"
            )
        return self


class PeriodsFile(BaseModel):
    """Subject-level periods file — the contract of ``periods.yaml``."""

    subject_id: str = Field(..., min_length=1, max_length=64)
    timezone: str = "Europe/Paris"
    periods: list[PeriodDef] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_unique_names(self) -> PeriodsFile:
        names = [p.name for p in self.periods]
        if len(names) != len(set(names)):
            duplicates = sorted({n for n in names if names.count(n) > 1})
            raise ValueError(f"duplicate period names: {duplicates}")
        return self

    def get(self, name: str) -> PeriodDef:
        for p in self.periods:
            if p.name == name:
                return p
        raise KeyError(f"period {name!r} not found in {self.subject_id!r}")


def load_periods(yaml_path: Path) -> PeriodsFile:
    """Parse + validate a ``periods.yaml`` file.

    Accepts two top-level forms for ergonomics — users often paste raw snippets
    from the sleep agenda without realising they need a wrapper :

    - **Full form** : dict with ``subject_id``, ``timezone``, ``periods`` keys
    - **List-only form** : a YAML list of period dicts ; ``subject_id`` is
      inferred from the parent directory name (e.g. ``data/personal/S001/`` →
      ``S001``), ``timezone`` defaults to ``Europe/Paris``
    """
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError(f"{yaml_path} is empty")
    if isinstance(raw, list):
        parent = yaml_path.resolve().parent
        # data/personal/<subject>/periods.yaml → subject = parent name
        subject_id = parent.name if parent.name not in ("", "/") else "unknown"
        raw = {"subject_id": subject_id, "periods": raw}
    return PeriodsFile.model_validate(raw)


def dump_periods(periods: PeriodsFile, yaml_path: Path) -> None:
    """Write a ``PeriodsFile`` back to YAML (overwrites)."""
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    data = periods.model_dump(mode="json")
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
