"""Coverage heatmap: epochs present per hour-of-day across recording dates."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from n24sal.viz.theme import TEAL


def coverage_heatmap(
    activity: pd.DataFrame,
    *,
    timezone: str = "Europe/Paris",
    title: str = "Coverage heatmap (epochs per hour)",
    expected_per_hour: int = 60,
) -> go.Figure:
    """Heatmap of epoch density by date × hour-of-day.

    Cells brighter = more epochs ; dark cells = gaps. Useful first look at
    coverage and missing-data patterns.
    """
    if not pd.api.types.is_datetime64_any_dtype(activity["timestamp"]):
        raise ValueError("activity['timestamp'] must be datetime dtype")

    df = activity.copy()
    df["ts_local"] = df["timestamp"].dt.tz_convert(timezone)
    df["date"] = df["ts_local"].dt.date
    df["hour"] = df["ts_local"].dt.hour
    counts = (
        df.groupby(["date", "hour"]).size().unstack(fill_value=0).reindex(columns=range(24), fill_value=0)
    )

    fig = go.Figure(
        data=go.Heatmap(
            z=counts.values,
            x=list(range(24)),
            y=[str(d) for d in counts.index],
            colorscale=[[0.0, "#232e32"], [1.0, TEAL]],
            zmin=0,
            zmax=expected_per_hour,
            colorbar=dict(title=f"epochs/h<br>(max {expected_per_hour})", thickness=10),
            hovertemplate="date=%{y}<br>hour=%{x}<br>epochs=%{z}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        xaxis=dict(title=f"hour ({timezone})", tick0=0, dtick=6),
        yaxis=dict(title="date", autorange="reversed"),
        height=max(300, len(counts) * 3),
    )
    return fig
