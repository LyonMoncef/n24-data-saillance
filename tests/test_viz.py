"""Smoke tests for n24sal.viz — every factory must return a plotly Figure."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import pytest

from n24sal.synthetic import generate_synthetic_actigraphy
from n24sal.viz import (
    apply_theme,
    average_24h_profile,
    coverage_heatmap,
    double_plot_actogram,
    m10_phase_drift_plot,
)
from n24sal.viz.theme import AMBER, CYAN, TEAL


def _df(n_days: int = 7, tau: float = 24.7):
    return generate_synthetic_actigraphy(n_days=n_days, tau_hours=tau, seed=0)


def test_theme_templates_registered():
    assert "datasaillance_dark" in pio.templates
    assert "datasaillance_light" in pio.templates


def test_apply_theme_sets_default():
    apply_theme("dark")
    assert pio.templates.default == "datasaillance_dark"
    apply_theme("light")
    assert pio.templates.default == "datasaillance_light"


def test_apply_theme_rejects_unknown_name():
    with pytest.raises(ValueError, match="dark.*light"):
        apply_theme("neon")


def test_brand_tokens_are_dataesaillance_palette():
    assert TEAL == "#0e9eb0"
    assert AMBER == "#d37c04"
    assert CYAN == "#3be5e7"


def test_actogram_returns_figure():
    fig = double_plot_actogram(_df(n_days=5), bin_minutes=15, timezone="UTC")
    assert isinstance(fig, go.Figure)
    assert fig.layout.title.text == "Double-plotted actogram"


def test_actogram_requires_two_days():
    with pytest.raises(ValueError, match="2 distinct days"):
        double_plot_actogram(_df(n_days=1), timezone="UTC")


def test_drift_plot_returns_figure():
    fig = m10_phase_drift_plot(_df(n_days=14), timezone="UTC")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3  # unwrapped markers + wrapped markers + fit line


def test_drift_plot_requires_three_days():
    with pytest.raises(ValueError, match="3 full days"):
        m10_phase_drift_plot(_df(n_days=2), timezone="UTC")


def test_average_profile_returns_figure():
    fig = average_24h_profile(_df(), timezone="UTC")
    assert isinstance(fig, go.Figure)


def test_coverage_heatmap_returns_figure():
    fig = coverage_heatmap(_df(), timezone="UTC")
    assert isinstance(fig, go.Figure)


def test_actogram_rejects_non_datetime_timestamp():
    df = _df()
    df["timestamp"] = df["timestamp"].astype(str)
    with pytest.raises(ValueError, match="datetime dtype"):
        double_plot_actogram(df, timezone="UTC")
