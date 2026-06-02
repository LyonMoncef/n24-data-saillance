"""Tests for n24sal.io.periods — Pydantic validation + YAML I/O."""

from __future__ import annotations

from datetime import date

import pytest
import yaml

from n24sal.io.periods import PeriodDef, PeriodsFile, dump_periods, load_periods


def test_period_def_minimal_valid():
    p = PeriodDef(name="regime_a", start=date(2026, 3, 16), end=date(2026, 5, 6))
    assert p.name == "regime_a"
    assert p.notes is None


def test_period_def_rejects_invalid_name():
    with pytest.raises(ValueError, match="must match"):
        PeriodDef(name="Regime A!", start=date(2026, 1, 1), end=date(2026, 2, 1))
    with pytest.raises(ValueError, match="must match"):
        PeriodDef(name="UPPER", start=date(2026, 1, 1), end=date(2026, 2, 1))
    with pytest.raises(ValueError, match="must match"):
        PeriodDef(name="with-dash", start=date(2026, 1, 1), end=date(2026, 2, 1))


def test_period_def_rejects_inverted_dates():
    with pytest.raises(ValueError, match="strictly after"):
        PeriodDef(name="bad", start=date(2026, 5, 1), end=date(2026, 3, 1))
    with pytest.raises(ValueError, match="strictly after"):
        PeriodDef(name="bad", start=date(2026, 5, 1), end=date(2026, 5, 1))


def test_periods_file_rejects_duplicate_names():
    with pytest.raises(ValueError, match="duplicate period names"):
        PeriodsFile(
            subject_id="S001",
            periods=[
                PeriodDef(name="a", start=date(2026, 1, 1), end=date(2026, 2, 1)),
                PeriodDef(name="a", start=date(2026, 3, 1), end=date(2026, 4, 1)),
            ],
        )


def test_periods_file_get_by_name():
    pf = PeriodsFile(
        subject_id="S001",
        periods=[
            PeriodDef(name="alpha", start=date(2026, 1, 1), end=date(2026, 2, 1)),
            PeriodDef(name="beta", start=date(2026, 3, 1), end=date(2026, 4, 1)),
        ],
    )
    assert pf.get("alpha").start == date(2026, 1, 1)
    assert pf.get("beta").end == date(2026, 4, 1)
    with pytest.raises(KeyError):
        pf.get("missing")


def test_load_periods_yaml(tmp_path):
    p = tmp_path / "periods.yaml"
    p.write_text(
        """\
subject_id: S001
timezone: Europe/Paris
periods:
  - name: regime_a
    start: 2026-03-16
    end: 2026-05-06
    notes: "First stable regime"
  - name: regime_b
    start: 2025-11-29
    end: 2026-01-15
    notes: "Disrupted period"
""",
        encoding="utf-8",
    )
    pf = load_periods(p)
    assert pf.subject_id == "S001"
    assert pf.timezone == "Europe/Paris"
    assert len(pf.periods) == 2
    assert pf.get("regime_a").notes == "First stable regime"


def test_load_periods_rejects_empty_file(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="is empty"):
        load_periods(p)


def test_load_periods_rejects_malformed(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(
        """\
subject_id: S001
periods:
  - name: BAD-NAME
    start: 2026-01-01
    end: 2026-02-01
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must match"):
        load_periods(p)


def test_dump_periods_roundtrip(tmp_path):
    original = PeriodsFile(
        subject_id="S002",
        timezone="UTC",
        periods=[PeriodDef(name="x", start=date(2026, 1, 1), end=date(2026, 2, 1))],
    )
    p = tmp_path / "out.yaml"
    dump_periods(original, p)
    reloaded = load_periods(p)
    assert reloaded.subject_id == "S002"
    assert reloaded.timezone == "UTC"
    assert reloaded.periods[0].name == "x"
    assert reloaded.periods[0].start == date(2026, 1, 1)


def test_load_periods_minimal_file(tmp_path):
    p = tmp_path / "minimal.yaml"
    p.write_text("subject_id: S001\n", encoding="utf-8")
    pf = load_periods(p)
    assert pf.subject_id == "S001"
    assert pf.timezone == "Europe/Paris"  # default
    assert pf.periods == []
