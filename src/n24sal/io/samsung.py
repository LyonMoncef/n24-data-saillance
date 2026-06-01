"""Samsung Health raw export ingest.

Reads the user-facing CSV + JSON export from the Samsung Health Android app
and produces portable parquets conforming to :mod:`n24sal.io.schemas`.

Sources consumed:

* ``com.samsung.health.movement.*.csv`` — one row per hour ; each row
  references a JSON file via the ``binning_data`` column.
* ``jsons/com.samsung.health.movement/<first-char-of-uuid>/<uuid>.binning_data.json``
  — array of 60-second epochs ``{start_time, end_time, activity_level}``. This
  is the gold-grade signal for NPCRA (continuous 1-minute accelerometer-derived
  activity level, equivalent to Actiwatch activity counts).
* ``com.samsung.health.sleep_stage.*.csv`` — event-based sleep stage intervals.
* ``com.samsung.shealth.tracker.heart_rate.*.csv`` — event-based HR samples.

CLI:

.. code-block:: shell

    python -m n24sal.io.samsung ingest <export_dir> \\
        --subject-id S001 \\
        --output data/personal/S001/
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from n24sal.io.schemas import (
    GapFillStrategy,
    SubjectMetadata,
    validate_actigraphy_frame,
)

logger = logging.getLogger(__name__)

MOVEMENT_CSV_GLOB = "com.samsung.health.movement.*.csv"
MOVEMENT_JSON_DIR = "jsons/com.samsung.health.movement"
SLEEP_STAGE_CSV_GLOB = "com.samsung.health.sleep_stage.*.csv"
HEART_RATE_CSV_GLOB = "com.samsung.shealth.tracker.heart_rate.*.csv"

SLEEP_STAGE_MAP: dict[int, str] = {
    40001: "awake",
    40002: "light",
    40003: "deep",
    40004: "rem",
}


def _find_unique(export_dir: Path, glob: str) -> Path:
    matches = sorted(export_dir.glob(glob))
    if not matches:
        raise FileNotFoundError(f"no file matching {glob!r} in {export_dir}")
    if len(matches) > 1:
        raise ValueError(f"multiple files match {glob!r} in {export_dir}: {matches}")
    return matches[0]


def _read_samsung_csv(path: Path) -> Iterator[dict[str, str]]:
    """Yield CSV rows, skipping Samsung's metadata first line."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        f.readline()  # first line: "table_name,row_count,version_code"
        reader = csv.DictReader(f)
        for row in reader:
            yield {k: v for k, v in row.items() if k is not None}


def _parse_offset_to_minutes(offset_str: str) -> int:
    """Convert ``'UTC+0100'`` / ``'UTC-0500'`` to integer minutes from UTC."""
    if not offset_str or not offset_str.startswith("UTC"):
        return 0
    sign = 1 if offset_str[3] == "+" else -1
    hh = int(offset_str[4:6])
    mm = int(offset_str[6:8])
    return sign * (hh * 60 + mm)


def _local_to_utc(local_str: str, offset_str: str) -> datetime | None:
    """Parse a naive Samsung timestamp + UTC offset column into UTC datetime."""
    if not local_str:
        return None
    try:
        local_dt = datetime.strptime(local_str.strip(), "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        try:
            local_dt = datetime.strptime(local_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    offset_min = _parse_offset_to_minutes(offset_str)
    tz = timezone(timedelta(minutes=offset_min))
    return local_dt.replace(tzinfo=tz).astimezone(timezone.utc)


def _resolve_json_path(json_dir: Path, binning_filename: str) -> Path:
    """Samsung shards binning JSONs into subdirs by first char of UUID."""
    if not binning_filename:
        raise ValueError("empty binning_data filename")
    first_char = binning_filename[0]
    return json_dir / first_char / binning_filename


def read_movement(export_dir: Path) -> pd.DataFrame:
    """Read Samsung movement CSV + linked binning JSONs into a 1-min DataFrame.

    Returns
    -------
    pandas.DataFrame
        Columns ``timestamp`` (tz-aware UTC) and ``activity`` (float ≥ 0).
        Sorted, deduplicated on timestamp.
    """
    csv_path = _find_unique(export_dir, MOVEMENT_CSV_GLOB)
    json_dir = export_dir / MOVEMENT_JSON_DIR

    epochs: list[tuple[int, float]] = []
    n_rows = 0
    n_missing = 0
    for row in _read_samsung_csv(csv_path):
        n_rows += 1
        binning_filename = row.get("binning_data", "")
        if not binning_filename:
            continue
        json_path = _resolve_json_path(json_dir, binning_filename)
        if not json_path.exists():
            n_missing += 1
            continue
        with open(json_path) as f:
            data = json.load(f)
        for entry in data:
            try:
                start_ms = int(entry["start_time"])
                level = float(entry["activity_level"])
            except (KeyError, ValueError, TypeError):
                continue
            epochs.append((start_ms, level))

    if n_missing:
        logger.warning(
            "movement: %d/%d binning JSON files referenced but not found", n_missing, n_rows
        )

    if not epochs:
        raise RuntimeError(f"no movement epochs parsed from {csv_path}")

    df = pd.DataFrame(epochs, columns=["start_ms", "activity"])
    df["timestamp"] = pd.to_datetime(df["start_ms"], unit="ms", utc=True)
    df = df.drop(columns=["start_ms"])
    df = (
        df.drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    df["activity"] = df["activity"].clip(lower=0.0)
    return df[["timestamp", "activity"]]


def read_sleep_stage(export_dir: Path) -> pd.DataFrame:
    """Read sleep_stage CSV into a per-interval DataFrame (UTC tz-aware)."""
    csv_path = _find_unique(export_dir, SLEEP_STAGE_CSV_GLOB)
    rows: list[dict] = []
    for r in _read_samsung_csv(csv_path):
        start = _local_to_utc(r.get("start_time", ""), r.get("time_offset", ""))
        end = _local_to_utc(r.get("end_time", ""), r.get("time_offset", ""))
        stage_code_str = r.get("stage", "").strip()
        if start is None or end is None or not stage_code_str:
            continue
        try:
            code = int(stage_code_str)
        except ValueError:
            continue
        rows.append(
            {
                "sleep_id": r.get("sleep_id", "").strip(),
                "stage_start": start,
                "stage_end": end,
                "stage_name": SLEEP_STAGE_MAP.get(code, f"unknown_{code}"),
                "stage_code": code,
            }
        )
    if not rows:
        raise RuntimeError(f"no sleep stages parsed from {csv_path}")
    df = pd.DataFrame(rows)
    df["stage_start"] = pd.to_datetime(df["stage_start"], utc=True)
    df["stage_end"] = pd.to_datetime(df["stage_end"], utc=True)
    return df.sort_values("stage_start").reset_index(drop=True)


def read_heart_rate(export_dir: Path) -> pd.DataFrame:
    """Read heart_rate CSV into an event-based DataFrame (UTC tz-aware)."""
    csv_path = _find_unique(export_dir, HEART_RATE_CSV_GLOB)
    rows: list[dict] = []
    for r in _read_samsung_csv(csv_path):
        start = _local_to_utc(
            r.get("com.samsung.health.heart_rate.start_time", ""),
            r.get("com.samsung.health.heart_rate.time_offset", ""),
        )
        bpm_str = r.get("com.samsung.health.heart_rate.heart_rate", "").strip()
        if start is None or not bpm_str:
            continue
        try:
            bpm = float(bpm_str)
        except ValueError:
            continue
        rows.append(
            {
                "timestamp": start,
                "bpm": bpm,
                "max_bpm": _safe_float(r.get("com.samsung.health.heart_rate.max", "")),
                "min_bpm": _safe_float(r.get("com.samsung.health.heart_rate.min", "")),
            }
        )
    if not rows:
        raise RuntimeError(f"no heart_rate samples parsed from {csv_path}")
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return (
        df.drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return float("nan")


def coverage_report(activity: pd.DataFrame, epoch_seconds: int = 60) -> dict:
    """Coverage / gap report on an activity series.

    If a ``present`` boolean column is provided (dense series), coverage is
    computed exactly from it. Otherwise (sparse legacy series), coverage is
    computed by comparing actual epoch count to expected based on span.
    """
    if activity.empty:
        return {"n_epochs_actual": 0, "coverage_pct": 0.0}

    start = activity["timestamp"].iloc[0]
    end = activity["timestamp"].iloc[-1]
    duration_s = (end - start).total_seconds()

    if "present" in activity.columns:
        present_count = int(activity["present"].sum())
        total_count = len(activity)
        return {
            "date_start": start.isoformat(),
            "date_end": end.isoformat(),
            "duration_days": round(duration_s / 86400, 2),
            "n_epochs_total_grid": total_count,
            "n_epochs_present": present_count,
            "coverage_pct": round(present_count / total_count * 100, 2) if total_count else 0.0,
            "dense": True,
        }

    expected = int(duration_s / epoch_seconds) + 1
    actual = len(activity)
    diffs = activity["timestamp"].diff().dropna()
    gap_threshold = pd.Timedelta(seconds=epoch_seconds * 2)
    gaps = diffs[diffs > gap_threshold]
    longest_gap = gaps.max() if len(gaps) else pd.Timedelta(0)
    return {
        "date_start": start.isoformat(),
        "date_end": end.isoformat(),
        "duration_days": round(duration_s / 86400, 2),
        "n_epochs_expected": expected,
        "n_epochs_actual": actual,
        "coverage_pct": round(actual / expected * 100, 2),
        "n_gaps_over_2_epochs": int(len(gaps)),
        "longest_gap_hours": round(longest_gap.total_seconds() / 3600, 2),
        "dense": False,
    }


def densify_activity(
    sparse: pd.DataFrame,
    *,
    timezone_name: str,
    epoch_seconds: int = 60,
) -> pd.DataFrame:
    """Reindex a sparse 1-min activity DataFrame onto a dense grid aligned to local days.

    The output has columns ``timestamp`` (UTC tz-aware), ``activity`` (float ≥ 0,
    zero-filled where the source had a gap) and ``present`` (bool, ``True`` where
    the value was originally recorded). Length is an integer multiple of the
    number of epochs per day (24h aligned to ``timezone_name``).
    """
    if sparse.empty:
        raise ValueError("cannot densify an empty activity DataFrame")

    epochs_per_day = 86400 // epoch_seconds
    local_ts = sparse["timestamp"].dt.tz_convert(timezone_name)
    start_local = local_ts.min().floor("D")
    end_local = local_ts.max().ceil("D")
    grid_local = pd.date_range(
        start_local, end_local, freq=f"{epoch_seconds}s", tz=timezone_name, inclusive="left"
    )
    # Truncate to whole local days
    n_full_days = len(grid_local) // epochs_per_day
    grid_local = grid_local[: n_full_days * epochs_per_day]
    grid_utc = grid_local.tz_convert("UTC")

    # Floor source timestamps to the epoch grid (defensive: real Samsung
    # data is already minute-aligned, but synthetic fixtures or other devices
    # may have sub-minute offsets that would silently make the reindex empty).
    src_index = pd.DatetimeIndex(sparse["timestamp"]).floor(f"{epoch_seconds}s")
    sparse_series = pd.Series(sparse["activity"].to_numpy(), index=src_index)
    # If flooring produced duplicate epochs, keep the mean
    if not sparse_series.index.is_unique:
        sparse_series = sparse_series.groupby(level=0).mean()
    dense_with_nan = sparse_series.reindex(grid_utc)
    present = ~dense_with_nan.isna()
    dense = dense_with_nan.fillna(0.0)

    return pd.DataFrame(
        {
            "timestamp": grid_utc,
            "activity": dense.to_numpy(),
            "present": present.to_numpy(),
        }
    )


def ingest_samsung_export(
    export_dir: Path,
    subject_id: str,
    output_dir: Path,
    *,
    timezone_name: str = "Europe/Paris",
    epoch_seconds: int = 60,
    age: int | None = None,
    sex: str | None = None,
    diagnosis: list[str] | None = None,
    include_sleep: bool = True,
    include_heart_rate: bool = True,
    densify: bool = True,
) -> dict:
    """Full Samsung Health export ingest pipeline.

    Writes ``activity.parquet`` (mandatory, dense 1-min grid by default with a
    ``present`` bool column tracking which epochs were originally recorded),
    optional ``sleep_intervals.parquet`` and ``heart_rate.parquet``, plus
    ``subject_metadata.json`` and ``coverage_report.json``. Returns the coverage
    report dict.

    Parameters
    ----------
    densify
        If True (default), the activity series is re-indexed onto a dense 1-min
        grid aligned to local days, with gaps zero-filled and a ``present``
        column added. Disable only for backward compatibility with legacy
        sparse parquets (NPCRA on sparse series gives biased tau, see issue #8).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Reading movement from %s", export_dir)
    sparse_activity = read_movement(export_dir)
    if densify:
        activity = densify_activity(
            sparse_activity, timezone_name=timezone_name, epoch_seconds=epoch_seconds
        )
        strategy: GapFillStrategy = "zero_fill"
        logger.info(
            "Densified: %d sparse → %d dense epochs (%d local days)",
            len(sparse_activity),
            len(activity),
            len(activity) // (86400 // epoch_seconds),
        )
    else:
        activity = sparse_activity
        strategy = "none"
    validate_actigraphy_frame(activity)
    activity_path = output_dir / "activity.parquet"
    activity.to_parquet(activity_path, index=False)
    logger.info("Wrote %d epochs to %s", len(activity), activity_path)

    if include_sleep:
        try:
            sleep = read_sleep_stage(export_dir)
            sleep_path = output_dir / "sleep_intervals.parquet"
            sleep.to_parquet(sleep_path, index=False)
            logger.info("Wrote %d sleep stages to %s", len(sleep), sleep_path)
        except FileNotFoundError:
            logger.warning("no sleep_stage CSV in %s; skipping", export_dir)

    if include_heart_rate:
        try:
            hr = read_heart_rate(export_dir)
            hr_path = output_dir / "heart_rate.parquet"
            hr.to_parquet(hr_path, index=False)
            logger.info("Wrote %d HR samples to %s", len(hr), hr_path)
        except FileNotFoundError:
            logger.warning("no heart_rate CSV in %s; skipping", export_dir)

    metadata = SubjectMetadata(
        subject_id=subject_id,
        device="samsung_galaxy_watch",
        epoch_seconds=epoch_seconds,
        timezone=timezone_name,
        recording_start=activity["timestamp"].iloc[0].to_pydatetime(),
        recording_end=activity["timestamp"].iloc[-1].to_pydatetime(),
        source_quality="medium",
        age=age,
        sex=sex,
        diagnosis=diagnosis or [],
        gap_fill_strategy=strategy,
    )
    meta_path = output_dir / "subject_metadata.json"
    meta_path.write_text(metadata.model_dump_json(indent=2))
    logger.info("Wrote subject metadata to %s", meta_path)

    report = coverage_report(activity, epoch_seconds=epoch_seconds)
    (output_dir / "coverage_report.json").write_text(json.dumps(report, indent=2))
    if report.get("dense"):
        logger.info(
            "Coverage: %.1f%% over %s days (%d/%d epochs present, dense grid)",
            report["coverage_pct"],
            report["duration_days"],
            report["n_epochs_present"],
            report["n_epochs_total_grid"],
        )
    else:
        logger.info(
            "Coverage: %.1f%% over %s days (%d gaps, longest %sh, sparse)",
            report["coverage_pct"],
            report["duration_days"],
            report["n_gaps_over_2_epochs"],
            report["longest_gap_hours"],
        )
    return report


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m n24sal.io.samsung",
        description="Ingest Samsung Health raw export into portable parquet.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    ingest = sub.add_parser("ingest", help="Run the ingestion pipeline")
    ingest.add_argument("export_dir", type=Path, help="Samsung Health export directory")
    ingest.add_argument("--subject-id", required=True, help="Subject identifier (e.g. S001)")
    ingest.add_argument(
        "--output", required=True, type=Path, help="Output directory for parquets + sidecar JSON"
    )
    ingest.add_argument("--timezone", default="Europe/Paris", help="IANA timezone (default Europe/Paris)")
    ingest.add_argument(
        "--epoch-seconds", type=int, default=60, help="Epoch size in seconds (default 60)"
    )
    ingest.add_argument("--age", type=int, default=None)
    ingest.add_argument("--sex", choices=["M", "F", "O"], default=None)
    ingest.add_argument(
        "--diagnosis",
        action="append",
        default=[],
        help="Repeat to record multiple diagnoses (e.g. --diagnosis N24SWD)",
    )
    ingest.add_argument("--no-sleep", action="store_true", help="Skip sleep_stage parsing")
    ingest.add_argument("--no-heart-rate", action="store_true", help="Skip heart_rate parsing")
    ingest.add_argument(
        "--no-densify",
        action="store_true",
        help="Skip densification (legacy sparse output ; biases NPCRA tau — see issue #8)",
    )
    ingest.add_argument("-v", "--verbose", action="count", default=0)

    args = parser.parse_args(argv)
    level = logging.WARNING - 10 * args.verbose
    logging.basicConfig(level=max(level, logging.DEBUG), format="%(levelname)s %(message)s")

    if args.cmd == "ingest":
        ingest_samsung_export(
            export_dir=args.export_dir,
            subject_id=args.subject_id,
            output_dir=args.output,
            timezone_name=args.timezone,
            epoch_seconds=args.epoch_seconds,
            age=args.age,
            sex=args.sex,
            diagnosis=args.diagnosis,
            include_sleep=not args.no_sleep,
            include_heart_rate=not args.no_heart_rate,
            densify=not args.no_densify,
        )
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
