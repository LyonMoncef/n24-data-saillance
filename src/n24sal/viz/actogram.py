"""Double-plotted actogram.

The double-plot (Witting 1990) repeats each day side by side with the next, so
a 24-hour cycle wraps visually into the next column. The N24 signature is a
diagonal stripe of activity drifting across the calendar — striking visually,
trivial to compute.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from n24sal.viz.theme import AMBER, CYAN, TEAL


def double_plot_actogram(
    activity: pd.DataFrame,
    *,
    timezone: str = "Europe/Paris",
    bin_minutes: int = 10,
    title: str = "Double-plotted actogram",
) -> go.Figure:
    """Build a double-plotted actogram heatmap.

    Parameters
    ----------
    activity
        DataFrame with columns ``timestamp`` (tz-aware) and ``activity``.
    timezone
        IANA timezone for the calendar axis.
    bin_minutes
        Aggregation bin width in minutes (default 10). Lower = finer detail,
        higher = faster render. 10–15 min is a good compromise for ~year-long
        series.
    title
        Figure title.
    """
    if not pd.api.types.is_datetime64_any_dtype(activity["timestamp"]):
        raise ValueError("activity['timestamp'] must be datetime dtype")

    df = activity.copy()
    df["ts_local"] = df["timestamp"].dt.tz_convert(timezone)
    df["date"] = df["ts_local"].dt.date
    df["minute_of_day"] = df["ts_local"].dt.hour * 60 + df["ts_local"].dt.minute
    df["bin"] = df["minute_of_day"] // bin_minutes

    n_bins_per_day = 24 * 60 // bin_minutes
    pivot = df.pivot_table(
        index="date", columns="bin", values="activity", aggfunc="mean", fill_value=0.0
    )
    pivot = pivot.reindex(columns=range(n_bins_per_day), fill_value=0.0)
    dates = sorted(pivot.index)
    if len(dates) < 2:
        raise ValueError("at least 2 distinct days required for a double-plot")

    matrix = []
    row_labels = []
    for i in range(len(dates) - 1):
        today = pivot.loc[dates[i]].to_numpy()
        tomorrow = pivot.loc[dates[i + 1]].to_numpy()
        matrix.append(np.concatenate([today, tomorrow]))
        row_labels.append(str(dates[i]))
    matrix_np = np.array(matrix)

    hours = np.arange(2 * n_bins_per_day) * bin_minutes / 60.0

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix_np,
            x=hours,
            y=row_labels,
            colorscale=[[0.0, "#232e32"], [0.5, TEAL], [1.0, CYAN]],
            colorbar=dict(title="activity", thickness=10),
            hovertemplate="day=%{y}<br>hour=%{x:.1f}<br>activity=%{z:.2f}<extra></extra>",
        )
    )
    fig.add_vline(x=24, line=dict(color=AMBER, width=1, dash="dot"))
    fig.update_layout(
        title=title,
        xaxis=dict(title=f"hour ({timezone})", tick0=0, dtick=6, range=[0, 48]),
        yaxis=dict(title="date", autorange="reversed"),
        height=max(300, len(row_labels) * 4),
    )
    return fig
