"""M10 phase drift plot with tau regression overlay."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import linregress

from n24sal.npcra.tau import _unwrap_phases_hours, m10_phases_per_day
from n24sal.viz.theme import AMBER, CYAN, TEAL


def m10_phase_drift_plot(
    activity: pd.DataFrame,
    *,
    epochs_per_hour: int = 60,
    epochs_per_day: int = 1440,
    timezone: str = "Europe/Paris",
    title: str = "M10 phase drift",
) -> go.Figure:
    """Plot daily M10 start hour (unwrapped) with linear regression overlay.

    Slope of the line is the daily drift; tau is ``24h + slope``.
    """
    if not pd.api.types.is_datetime64_any_dtype(activity["timestamp"]):
        raise ValueError("activity['timestamp'] must be datetime dtype")

    df = activity.sort_values("timestamp").copy()
    df["ts_local"] = df["timestamp"].dt.tz_convert(timezone)
    arr = df["activity"].to_numpy()

    phases = m10_phases_per_day(arr, epochs_per_hour, epochs_per_day)
    n = len(phases)
    if n < 3:
        raise ValueError(f"need at least 3 full days, got {n}")

    days = np.arange(n)
    unwrapped = _unwrap_phases_hours(phases)
    res = linregress(days, unwrapped)
    tau = 24.0 + res.slope
    r2 = res.rvalue**2

    fit_y = res.intercept + res.slope * days

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=days,
            y=unwrapped,
            mode="markers",
            name="daily M10 (unwrapped)",
            marker=dict(color=CYAN, size=5),
            hovertemplate="day %{x}<br>M10 start=%{y:.2f}h<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=days,
            y=phases,
            mode="markers",
            name="daily M10 (wrapped 0–24h)",
            marker=dict(color=TEAL, size=4, opacity=0.5),
            visible="legendonly",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=days,
            y=fit_y,
            mode="lines",
            name=f"linear fit · tau={tau:.3f}h · R²={r2:.2f}",
            line=dict(color=AMBER, width=2),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="day index (from recording start)",
        yaxis_title="M10 start hour (unwrapped)",
    )
    return fig
