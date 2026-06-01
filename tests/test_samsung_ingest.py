"""Tests for n24sal.io.samsung — Samsung Health raw export ingest.

All tests run against synthetic fixtures (no personal data committed).
The fixtures mirror the layout of the real export discovered on 2026-05-29:
- BOM-prefixed CSV with a metadata header line
- Sharded JSON files at jsons/com.samsung.health.movement/<first-char>/<uuid>.binning_data.json
- Each JSON contains an array of 60-second epochs with continuous activity_level
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from n24sal.io.samsung import (
    _cli,
    _local_to_utc,
    _parse_offset_to_minutes,
    coverage_report,
    densify_activity,
    ingest_samsung_export,
    read_heart_rate,
    read_movement,
    read_sleep_stage,
)

# -------------------- Fixture helpers --------------------

MOVEMENT_FIELDS = [
    "create_sh_ver",
    "start_time",
    "custom",
    "binning_data",
    "modify_sh_ver",
    "update_time",
    "create_time",
    "time_offset",
    "deviceuuid",
    "comment",
    "pkg_name",
    "end_time",
    "datauuid",
]

SLEEP_FIELDS = [
    "create_sh_ver",
    "start_time",
    "sleep_id",
    "custom",
    "modify_sh_ver",
    "update_time",
    "create_time",
    "stage",
    "time_offset",
    "deviceuuid",
    "pkg_name",
    "end_time",
    "datauuid",
]

HR_FIELDS = [
    "source",
    "tag_id",
    "com.samsung.health.heart_rate.create_sh_ver",
    "com.samsung.health.heart_rate.heart_beat_count",
    "com.samsung.health.heart_rate.start_time",
    "com.samsung.health.heart_rate.custom",
    "com.samsung.health.heart_rate.binning_data",
    "com.samsung.health.heart_rate.modify_sh_ver",
    "com.samsung.health.heart_rate.update_time",
    "com.samsung.health.heart_rate.create_time",
    "com.samsung.health.heart_rate.client_data_id",
    "com.samsung.health.heart_rate.max",
    "com.samsung.health.heart_rate.min",
    "com.samsung.health.heart_rate.client_data_ver",
    "com.samsung.health.heart_rate.time_offset",
    "com.samsung.health.heart_rate.deviceuuid",
    "com.samsung.health.heart_rate.comment",
    "com.samsung.health.heart_rate.pkg_name",
    "com.samsung.health.heart_rate.end_time",
    "com.samsung.health.heart_rate.datauuid",
    "com.samsung.health.heart_rate.heart_rate",
]


def _write_samsung_csv(path: Path, table_name: str, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(f"{table_name},{len(rows)},1\n")
        f.write(",".join(fields) + "\n")
        for row in rows:
            f.write(",".join(str(row.get(field, "")) for field in fields) + "\n")


def _write_binning_json(
    path: Path,
    start_ms: int,
    n_epochs: int = 60,
    epoch_ms: int = 60_000,
    pattern: str = "saw",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    for i in range(n_epochs):
        s = start_ms + i * epoch_ms
        if pattern == "saw":
            level = float(i % 10)
        elif pattern == "const":
            level = 5.0
        else:
            level = 0.0
        entries.append({"start_time": s, "end_time": s + epoch_ms - 1, "activity_level": level})
    with open(path, "w") as f:
        json.dump(entries, f)


def _make_movement_export(root: Path, n_hours: int = 24) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    json_dir = root / "jsons" / "com.samsung.health.movement"
    rows = []
    start_ms = 1_700_000_000_000  # 2023-11-14 22:13:20 UTC
    for h in range(n_hours):
        uuid = f"{h:08x}-1234-1234-1234-1234567890ab"
        first = uuid[0]
        binning_filename = f"{uuid}.binning_data.json"
        _write_binning_json(json_dir / first / binning_filename, start_ms + h * 3_600_000, 60)
        rows.append({"binning_data": binning_filename, "time_offset": "UTC+0100"})
    _write_samsung_csv(
        root / "com.samsung.health.movement.20260101000000.csv",
        "com.samsung.health.movement",
        MOVEMENT_FIELDS,
        rows,
    )
    return root


def _add_sleep_fixture(root: Path) -> None:
    _write_samsung_csv(
        root / "com.samsung.health.sleep_stage.20260101000000.csv",
        "com.samsung.health.sleep_stage",
        SLEEP_FIELDS,
        [
            {
                "start_time": "2025-01-01 23:00:00.000",
                "end_time": "2025-01-02 02:00:00.000",
                "stage": "40002",
                "sleep_id": "s1",
                "time_offset": "UTC+0100",
            },
            {
                "start_time": "2025-01-02 02:00:00.000",
                "end_time": "2025-01-02 04:00:00.000",
                "stage": "40003",
                "sleep_id": "s1",
                "time_offset": "UTC+0100",
            },
            {
                "start_time": "2025-01-02 04:00:00.000",
                "end_time": "2025-01-02 06:00:00.000",
                "stage": "40004",
                "sleep_id": "s1",
                "time_offset": "UTC+0100",
            },
        ],
    )


def _add_hr_fixture(root: Path) -> None:
    _write_samsung_csv(
        root / "com.samsung.shealth.tracker.heart_rate.20260101000000.csv",
        "com.samsung.shealth.tracker.heart_rate",
        HR_FIELDS,
        [
            {
                "com.samsung.health.heart_rate.start_time": "2025-01-01 12:00:00.000",
                "com.samsung.health.heart_rate.heart_rate": "72",
                "com.samsung.health.heart_rate.max": "75",
                "com.samsung.health.heart_rate.min": "68",
                "com.samsung.health.heart_rate.time_offset": "UTC+0100",
            },
            {
                "com.samsung.health.heart_rate.start_time": "2025-01-01 12:05:00.000",
                "com.samsung.health.heart_rate.heart_rate": "80",
                "com.samsung.health.heart_rate.max": "82",
                "com.samsung.health.heart_rate.min": "78",
                "com.samsung.health.heart_rate.time_offset": "UTC+0100",
            },
        ],
    )


# -------------------- Pure helpers --------------------


def test_parse_offset_utc_plus_one():
    assert _parse_offset_to_minutes("UTC+0100") == 60


def test_parse_offset_negative():
    assert _parse_offset_to_minutes("UTC-0500") == -300


def test_parse_offset_empty():
    assert _parse_offset_to_minutes("") == 0


def test_local_to_utc_applies_offset():
    dt = _local_to_utc("2025-01-01 12:00:00.000", "UTC+0100")
    assert dt is not None
    assert dt.hour == 11
    assert dt.utcoffset().total_seconds() == 0


def test_local_to_utc_returns_none_on_empty():
    assert _local_to_utc("", "UTC+0100") is None


# -------------------- Movement parser --------------------


def test_read_movement_basic_shape(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=2)
    df = read_movement(export)
    assert len(df) == 120
    assert (df["activity"] >= 0).all()
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    assert df["timestamp"].dt.tz is not None
    assert df["timestamp"].is_monotonic_increasing


def test_read_movement_deduplicates_overlapping_epochs(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=2)
    # Duplicate the first JSON file's content into another referenced filename
    json_dir = export / "jsons" / "com.samsung.health.movement"
    src = next(json_dir.rglob("*.json"))
    dup = json_dir / "0" / "ffffffff-1234-1234-1234-1234567890ab.binning_data.json"
    dup.parent.mkdir(parents=True, exist_ok=True)
    dup.write_text(src.read_text())
    # Append a CSV row referencing the dup
    csv_path = next(export.glob("com.samsung.health.movement.*.csv"))
    content = csv_path.read_text(encoding="utf-8-sig")
    new_row = ",".join(
        [
            "",
            "",
            "",
            "ffffffff-1234-1234-1234-1234567890ab.binning_data.json",
            "",
            "",
            "",
            "UTC+0100",
            "",
            "",
            "",
            "",
            "",
        ]
    )
    csv_path.write_text(content + new_row + "\n", encoding="utf-8-sig")
    df = read_movement(export)
    assert len(df) == 120  # dedup still gives 2 hours


def test_read_movement_skips_missing_binning_files(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=3)
    json_files = sorted((export / "jsons" / "com.samsung.health.movement").rglob("*.json"))
    json_files[0].unlink()
    df = read_movement(export)
    assert len(df) == 120


def test_read_movement_raises_when_no_csv(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_movement(tmp_path)


def test_read_movement_raises_when_csv_has_no_usable_rows(tmp_path):
    export = tmp_path / "export"
    export.mkdir()
    _write_samsung_csv(
        export / "com.samsung.health.movement.20260101000000.csv",
        "com.samsung.health.movement",
        MOVEMENT_FIELDS,
        [{"binning_data": "", "time_offset": "UTC+0100"}],
    )
    with pytest.raises(RuntimeError, match="no movement epochs"):
        read_movement(export)


# -------------------- Sleep parser --------------------


def test_read_sleep_stage_returns_utc_tz_aware(tmp_path):
    export = tmp_path / "export"
    export.mkdir()
    _add_sleep_fixture(export)
    df = read_sleep_stage(export)
    assert len(df) == 3
    assert set(df["stage_name"]) == {"light", "deep", "rem"}
    assert df["stage_start"].dt.tz is not None
    # UTC+0100 23:00 → UTC 22:00
    assert df["stage_start"].iloc[0].hour == 22


# -------------------- Heart rate parser --------------------


def test_read_heart_rate_returns_utc_tz_aware(tmp_path):
    export = tmp_path / "export"
    export.mkdir()
    _add_hr_fixture(export)
    df = read_heart_rate(export)
    assert len(df) == 2
    assert (df["bpm"] > 0).all()
    assert df["timestamp"].dt.tz is not None
    # UTC+0100 12:00 → UTC 11:00
    assert df["timestamp"].iloc[0].hour == 11


# -------------------- Coverage report --------------------


def test_coverage_report_no_gaps(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=4)
    df = read_movement(export)
    report = coverage_report(df)
    assert report["n_gaps_over_2_epochs"] == 0
    assert report["coverage_pct"] >= 99


def test_coverage_report_detects_injected_gap(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=4)
    df = read_movement(export)
    # Drop epochs 60–180 to inject a 2h hole
    with_gap = pd.concat([df.iloc[:60], df.iloc[180:]]).reset_index(drop=True)
    report = coverage_report(with_gap)
    assert report["n_gaps_over_2_epochs"] >= 1
    assert report["longest_gap_hours"] >= 1.9
    assert report["coverage_pct"] < 80


def test_coverage_report_on_empty_frame():
    report = coverage_report(pd.DataFrame({"timestamp": [], "activity": []}))
    assert report["n_epochs_actual"] == 0


# -------------------- Full pipeline --------------------


def test_ingest_full_pipeline(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=4)
    _add_sleep_fixture(export)
    _add_hr_fixture(export)
    output = tmp_path / "out"
    report = ingest_samsung_export(
        export_dir=export,
        subject_id="STEST",
        output_dir=output,
        timezone_name="Europe/Paris",
        age=38,
        sex="M",
        diagnosis=["N24SWD"],
    )
    for filename in (
        "activity.parquet",
        "sleep_intervals.parquet",
        "heart_rate.parquet",
        "subject_metadata.json",
        "coverage_report.json",
    ):
        assert (output / filename).exists(), f"missing {filename}"

    activity = pd.read_parquet(output / "activity.parquet")
    # Densified by default: length is a whole multiple of 1440 (1 local day)
    assert len(activity) % 1440 == 0
    assert "present" in activity.columns
    # The original 4 hours = 240 minutes are present, the rest are zero-filled
    assert activity["present"].sum() == 4 * 60
    assert (activity.loc[~activity["present"], "activity"] == 0.0).all()

    meta = json.loads((output / "subject_metadata.json").read_text())
    assert meta["subject_id"] == "STEST"
    assert meta["device"] == "samsung_galaxy_watch"
    assert meta["diagnosis"] == ["N24SWD"]
    assert meta["age"] == 38
    assert meta["epoch_seconds"] == 60
    assert meta["timezone"] == "Europe/Paris"
    assert meta["gap_fill_strategy"] == "zero_fill"

    assert report["dense"] is True
    assert report["n_epochs_present"] == 4 * 60


def test_ingest_no_densify_preserves_sparse_legacy(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=2)
    output = tmp_path / "out"
    ingest_samsung_export(
        export_dir=export,
        subject_id="STEST",
        output_dir=output,
        densify=False,
        include_sleep=False,
        include_heart_rate=False,
    )
    activity = pd.read_parquet(output / "activity.parquet")
    assert len(activity) == 2 * 60  # exactly the 120 source epochs, no padding
    assert "present" not in activity.columns
    meta = json.loads((output / "subject_metadata.json").read_text())
    assert meta["gap_fill_strategy"] == "none"
    report = json.loads((output / "coverage_report.json").read_text())
    assert report["dense"] is False


# -------------------- Densify helper --------------------


def test_densify_produces_whole_local_days(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=4)
    sparse = read_movement(export)
    dense = densify_activity(sparse, timezone_name="Europe/Paris")
    assert len(dense) % 1440 == 0
    assert {"timestamp", "activity", "present"} <= set(dense.columns)
    assert dense["present"].sum() == 4 * 60  # original epochs preserved
    assert dense["present"].dtype == bool
    assert dense["timestamp"].is_monotonic_increasing
    assert (dense.loc[dense["present"], "activity"].to_numpy()
            == sparse["activity"].to_numpy()).all()


def test_densify_zero_fills_gaps(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=3)
    sparse = read_movement(export)
    dense = densify_activity(sparse, timezone_name="Europe/Paris")
    n_imputed = (~dense["present"]).sum()
    assert n_imputed > 0
    assert (dense.loc[~dense["present"], "activity"] == 0.0).all()


def test_densify_rejects_empty_input():
    with pytest.raises(ValueError, match="empty"):
        densify_activity(pd.DataFrame({"timestamp": [], "activity": []}), timezone_name="UTC")


def test_ingest_with_no_sleep_no_hr_succeeds(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=2)
    output = tmp_path / "out"
    ingest_samsung_export(
        export_dir=export,
        subject_id="STEST",
        output_dir=output,
        include_sleep=False,
        include_heart_rate=False,
    )
    assert (output / "activity.parquet").exists()
    assert not (output / "sleep_intervals.parquet").exists()
    assert not (output / "heart_rate.parquet").exists()


def test_ingest_handles_missing_optional_csvs_gracefully(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=2)
    output = tmp_path / "out"
    ingest_samsung_export(
        export_dir=export, subject_id="STEST", output_dir=output
    )
    assert (output / "activity.parquet").exists()
    assert not (output / "sleep_intervals.parquet").exists()
    assert not (output / "heart_rate.parquet").exists()


# -------------------- CLI --------------------


def test_cli_ingest_end_to_end(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=3)
    output = tmp_path / "out"
    rc = _cli(
        [
            "ingest",
            str(export),
            "--subject-id",
            "STEST",
            "--output",
            str(output),
            "--timezone",
            "Europe/Paris",
            "--no-sleep",
            "--no-heart-rate",
        ]
    )
    assert rc == 0
    assert (output / "activity.parquet").exists()
    meta = json.loads((output / "subject_metadata.json").read_text())
    assert meta["subject_id"] == "STEST"


def test_cli_with_diagnosis_flag(tmp_path):
    export = _make_movement_export(tmp_path / "export", n_hours=2)
    output = tmp_path / "out"
    _cli(
        [
            "ingest",
            str(export),
            "--subject-id",
            "STEST",
            "--output",
            str(output),
            "--diagnosis",
            "N24SWD",
            "--diagnosis",
            "DSPD",
            "--age",
            "38",
            "--sex",
            "M",
            "--no-sleep",
            "--no-heart-rate",
        ]
    )
    meta = json.loads((output / "subject_metadata.json").read_text())
    assert meta["diagnosis"] == ["N24SWD", "DSPD"]
    assert meta["age"] == 38
    assert meta["sex"] == "M"
