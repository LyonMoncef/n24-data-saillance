"""Average 24-hour activity profile with IQR band."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from n24sal.viz.theme import TEAL


def average_24h_profile(
    activity: pd.DataFrame,
    *,
    epochs_per_day: int = 1440,
    timezone: str = "Europe/Paris",
    title: str = "Average 24h activity profile",
) -> go.Figure:
    """Mean activity by minute-of-day across all days, with IQR band."""
    if not pd.api.types.is_datetime64_any_dtype(activity["timestamp"]):
        raise ValueError("activity['timestamp'] must be datetime dtype")

    df = activity.copy()
    df["ts_local"] = df["timestamp"].dt.tz_convert(timezone)
    minutes_per_epoch = 24 * 60 // epochs_per_day
    df["minute_of_day"] = df["ts_local"].dt.hour * 60 + df["ts_local"].dt.minute
    df["bin"] = df["minute_of_day"] // minutes_per_epoch

    grouped = (
        df.groupby("bin")["activity"]
        .agg(
            mean="mean",
            q25=lambda x: x.quantile(0.25),
            q75=lambda x: x.quantile(0.75),
        )
        .reindex(range(epochs_per_day), fill_value=0.0)
    )

    hours = np.arange(epochs_per_day) * minutes_per_epoch / 60.0

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hours, y=grouped["q75"], mode="lines", line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours, y=grouped["q25"], mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor="rgba(14, 158, 176, 0.2)",
            name="IQR 25–75%",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours, y=grouped["mean"], mode="lines",
            line=dict(color=TEAL, width=2), name="mean",
        )
    )
    fig.update_layout(
        title=title,
        xaxis=dict(title=f"hour ({timezone})", tick0=0, dtick=3, range=[0, 24]),
        yaxis_title="activity (mean ± IQR)",
    )
    return fig
