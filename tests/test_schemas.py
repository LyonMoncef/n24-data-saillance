from datetime import datetime, timezone

import pandas as pd
import pytest

from n24sal.io import SubjectMetadata, validate_actigraphy_frame


def _good_frame(n: int = 10) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=n, freq="min", tz="UTC"),
            "activity": list(range(n)),
        }
    )


def test_validate_actigraphy_frame_accepts_minimal_valid_frame():
    validate_actigraphy_frame(_good_frame())


def test_validate_actigraphy_frame_rejects_missing_column():
    df = _good_frame().drop(columns=["activity"])
    with pytest.raises(ValueError, match="missing required columns"):
        validate_actigraphy_frame(df)


def test_validate_actigraphy_frame_rejects_non_datetime_timestamp():
    df = _good_frame()
    df["timestamp"] = df["timestamp"].astype(str)
    with pytest.raises(ValueError, match="datetime dtype"):
        validate_actigraphy_frame(df)


def test_validate_actigraphy_frame_rejects_non_numeric_activity():
    df = _good_frame()
    df["activity"] = df["activity"].astype(str)
    with pytest.raises(ValueError, match="must be numeric"):
        validate_actigraphy_frame(df)


def test_validate_actigraphy_frame_rejects_non_monotonic_timestamps():
    df = _good_frame()
    df.loc[5, "timestamp"] = df.loc[0, "timestamp"]
    with pytest.raises(ValueError, match="monotonically increasing"):
        validate_actigraphy_frame(df)


def test_subject_metadata_valid_roundtrip():
    meta = SubjectMetadata(
        subject_id="S001",
        device="samsung_galaxy_watch",
        epoch_seconds=60,
        timezone="Europe/Paris",
        recording_start=datetime(2026, 5, 1, tzinfo=timezone.utc),
        recording_end=datetime(2026, 5, 22, tzinfo=timezone.utc),
        age=38,
        sex="M",
        diagnosis=["N24SWD"],
    )
    assert meta.subject_id == "S001"
    assert meta.diagnosis == ["N24SWD"]


def test_subject_metadata_rejects_inverted_recording_window():
    with pytest.raises(ValueError, match="strictly after"):
        SubjectMetadata(
            subject_id="S001",
            device="samsung_galaxy_watch",
            epoch_seconds=60,
            timezone="Europe/Paris",
            recording_start=datetime(2026, 5, 22, tzinfo=timezone.utc),
            recording_end=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )
