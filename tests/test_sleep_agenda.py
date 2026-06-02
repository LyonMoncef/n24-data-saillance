"""Tests for tools/sleep_agenda/agenda_render.py — fixture-driven smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "sleep_agenda"))

import agenda_render  # type: ignore  # noqa: E402


def _fixture_sleep(tmp_path: Path) -> Path:
    rows = []
    base = pd.Timestamp("2026-03-15 21:00:00", tz="Europe/Paris")
    for night in range(3):
        start_local = base + pd.Timedelta(days=night, hours=2)  # bedtime ~23h
        rows.append(
            {
                "sleep_id": f"s{night}",
                "stage_start": start_local.tz_convert("UTC"),
                "stage_end": (start_local + pd.Timedelta(hours=3)).tz_convert("UTC"),
                "stage_name": "light",
                "stage_code": 40002,
            }
        )
        rows.append(
            {
                "sleep_id": f"s{night}",
                "stage_start": (start_local + pd.Timedelta(hours=3)).tz_convert("UTC"),
                "stage_end": (start_local + pd.Timedelta(hours=6)).tz_convert("UTC"),
                "stage_name": "deep",
                "stage_code": 40003,
            }
        )
    df = pd.DataFrame(rows)
    p = tmp_path / "sleep_intervals.parquet"
    df.to_parquet(p, index=False)
    return p


def _fixture_activity(tmp_path: Path) -> Path:
    grid = pd.date_range("2026-03-15", periods=3 * 1440, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": grid,
            "activity": [10.0] * len(grid),
            "present": [True] * (2 * 1440) + [False] * 1440,  # 2/3 days present
        }
    )
    p = tmp_path / "activity.parquet"
    df.to_parquet(p, index=False)
    return p


def test_load_nights_from_parquet(tmp_path):
    sleep = _fixture_sleep(tmp_path)
    activity = _fixture_activity(tmp_path)
    nights = agenda_render.load_nights_from_parquet(sleep, activity, "Europe/Paris")
    assert len(nights) >= 3
    for n in nights:
        assert {"date", "stages", "coverage_pct"} <= set(n.keys())
        assert all(s[0] in {"LIGHT", "DEEP", "REM", "AWAKE"} for s in n["stages"])


def test_load_nights_handles_missing_activity(tmp_path):
    sleep = _fixture_sleep(tmp_path)
    nights = agenda_render.load_nights_from_parquet(sleep, None, "Europe/Paris")
    assert all(n["coverage_pct"] == 100.0 for n in nights)


def test_render_html_medical_theme(tmp_path):
    sleep = _fixture_sleep(tmp_path)
    activity = _fixture_activity(tmp_path)
    nights = agenda_render.load_nights_from_parquet(sleep, activity, "Europe/Paris")
    html = agenda_render.render_html(
        nights, subject_id="STEST", timezone_name="Europe/Paris",
        theme="medical", interactive=True,
    )
    assert "<table class=\"agenda\">" in html
    assert "STEST" in html
    assert "#f0b878" in html  # medical sleep color
    assert "sel-panel" in html  # JS selection
    assert "<script>" in html


def test_render_html_datasaillance_theme(tmp_path):
    sleep = _fixture_sleep(tmp_path)
    activity = _fixture_activity(tmp_path)
    nights = agenda_render.load_nights_from_parquet(sleep, activity, "Europe/Paris")
    html = agenda_render.render_html(
        nights, subject_id="STEST", timezone_name="Europe/Paris",
        theme="datasaillance", interactive=True,
    )
    assert "#191e22" in html  # DataSaillance dark bg
    assert "#0e9eb0" in html  # teal


def test_render_html_non_interactive_strips_js(tmp_path):
    sleep = _fixture_sleep(tmp_path)
    nights = agenda_render.load_nights_from_parquet(sleep, None, "Europe/Paris")
    html = agenda_render.render_html(
        nights, subject_id="STEST", timezone_name="Europe/Paris",
        theme="medical", interactive=False,
    )
    # The CSS still defines #sel-panel styles (shared theme) but the panel HTML
    # div and the <script> block must NOT be present.
    assert '<div id="sel-panel">' not in html
    assert "<script>" not in html
    assert "save-btn" not in html  # JS-only id


def test_render_html_includes_session_attributes(tmp_path):
    """Each rendered .sleep block must carry data-sleep-id + data-night + data-start-ms attrs."""
    sleep = _fixture_sleep(tmp_path)
    nights = agenda_render.load_nights_from_parquet(sleep, None, "Europe/Paris")
    html = agenda_render.render_html(
        nights, subject_id="STEST", timezone_name="Europe/Paris",
        theme="datasaillance", interactive=True,
    )
    assert "data-sleep-id=" in html
    assert "data-night=" in html
    assert "data-start-ms=" in html
    # Session-index CSS class applied
    assert "sess-0" in html  # at least one session


def test_render_html_session_modal_present_in_interactive(tmp_path):
    sleep = _fixture_sleep(tmp_path)
    nights = agenda_render.load_nights_from_parquet(sleep, None, "Europe/Paris")
    html = agenda_render.render_html(
        nights, subject_id="STEST", timezone_name="Europe/Paris",
        theme="medical", interactive=True,
    )
    assert '<div id="session-modal">' in html
    assert '<div id="session-snippet-modal">' in html
    assert 'data-action="set_main"' in html
    assert 'data-action="mark_as_nap"' in html
    assert 'data-action="exclude"' in html


def test_load_nights_includes_sleep_id_in_stages(tmp_path):
    """Backwards-incompat change : stages now 4-tuples (stage_name, s_ms, e_ms, sleep_id)."""
    sleep = _fixture_sleep(tmp_path)
    nights = agenda_render.load_nights_from_parquet(sleep, None, "Europe/Paris")
    assert nights, "expected non-empty nights"
    for n in nights:
        for stage in n["stages"]:
            assert len(stage) == 4
            assert isinstance(stage[3], str)  # sleep_id


def test_theme_css_rejects_unknown():
    with pytest.raises(ValueError, match="unknown theme"):
        agenda_render.theme_css("neon")


def test_cli_end_to_end(tmp_path):
    sleep = _fixture_sleep(tmp_path)
    _fixture_activity(tmp_path)
    out = tmp_path / "out.html"
    rc = agenda_render.main(
        [
            "--subject-id", "STEST",
            "--data-dir", str(tmp_path),
            "--theme", "datasaillance",
            "--out", str(out),
        ]
    )
    assert rc == 0
    assert out.exists()
    html = out.read_text()
    assert "STEST" in html
