#!/usr/bin/env python3
"""Project fitted oscillator curves onto the sleep agenda (Y=night × X=hours-past-20h).

Mapping
-------
The fitter computes φ(n) = onset_deviation from a 24h schedule (hours) at
day index n. The actual onset timestamp is then::

    onset_ts(n) = anchor + (24 · n + φ(n)) hours

where ``anchor`` is noon on the window's start day (the same convention used
in ``fit.py``). To project this onto the agenda's (morning_date, x_hours)
space we use the standard 20h-night convention::

    morning = ts.date() + (1 if ts.hour >= 20 else 0)
    night_start = 20:00 on (morning - 1 day)
    x_hours = (ts - night_start) in hours      (∈ [0, 24])

The fit is evaluated at **integer n only** (one prediction per biological
night). Sampling at fractional n would sweep across each row's 24h width
since ``onset_ts(n+δ) = onset_ts(n) + 24·δ·h``, which is meaningless visually
— the model predicts ONE onset per night, not a continuous within-night
trajectory. The line between consecutive predictions shows the
night-to-night drift directly ; gaps are inserted only when the predicted
rhythm skips a row entirely (> 1 day jump).

Visualisation
-------------
- Y axis : morning date, oldest at top (mirrors the existing HTML agenda).
- X axis : 0 → 24 h, ticked every 2 h, labels [20h, 22h, 00h, ..., 18h, 20h].
- Sleep sessions (main_sleep_per_night) drawn as semi-transparent teal bars.
- Fit overlays : linear (amber dash), single-sin (cyan), double-sin (magenta).
- Actual onset markers (teal dots) for direct visual residual reading.

Usage
-----
::

    .venv/bin/python tools/oscillator_explore/agenda_overlay.py \\
        --subject-id S001 \\
        --periods "atcf=2025-04-06:2025-07-29,recent=2026-04-01:2026-05-07,winter25=2025-11-26:2025-12-26"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date as date_, datetime, time as time_, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from n24sal.sleep.per_night import main_sleep_per_night  # noqa: E402

NIGHT_START_HOUR = 20

TEAL = "#0e9eb0"
AMBER = "#d37c04"
CYAN = "#3be5e7"
MAGENTA = "#c5198d"
DARK = "#2a2a2a"


def to_agenda_xy(ts_local: pd.Timestamp) -> tuple[pd.Timestamp, float]:
    """Project a tz-aware local Timestamp to (morning_date, x_hours_past_20h)."""
    morning = ts_local.date()
    if ts_local.hour >= NIGHT_START_HOUR:
        morning = morning + timedelta(days=1)
    night_start = pd.Timestamp(
        datetime.combine(morning - timedelta(days=1), time_(NIGHT_START_HOUR, 0)),
        tz=ts_local.tz,
    )
    x_h = (ts_local - night_start).total_seconds() / 3600.0
    return pd.Timestamp(morning), float(x_h)


def predict_phi(model: str, n_eval: np.ndarray, params: dict,
                n_data: np.ndarray, phi_data: np.ndarray,
                D_data: np.ndarray | None = None) -> np.ndarray:
    """Evaluate the chosen fit at n_eval — β reconstructed from the data centroid.

    For model ``"debt"``, ``D_data`` (per-night debt at bedtime, same length
    as ``n_data``) must be provided. D is linearly interpolated onto n_eval
    when n_eval has values between observed nights — coherent with the
    physiology (debt evolves continuously between sleeps).
    """
    alpha = params["alpha"]
    if model == "linear":
        beta = phi_data.mean() - alpha * n_data.mean()
        return alpha * n_eval + beta
    if model == "oscillator":
        A, P, psi = params["A"], params["P"], params["psi"]
        sin_at_data = A * np.sin(2 * np.pi * n_data / P + psi)
        beta = phi_data.mean() - alpha * n_data.mean() - sin_at_data.mean()
        return alpha * n_eval + beta + A * np.sin(2 * np.pi * n_eval / P + psi)
    if model == "double":
        A1, P1, psi1 = params["A1"], params["P1"], params["psi1"]
        A2, P2, psi2 = params["A2"], params["P2"], params["psi2"]
        sin_at_data = (A1 * np.sin(2 * np.pi * n_data / P1 + psi1)
                       + A2 * np.sin(2 * np.pi * n_data / P2 + psi2))
        beta = phi_data.mean() - alpha * n_data.mean() - sin_at_data.mean()
        return (alpha * n_eval + beta
                + A1 * np.sin(2 * np.pi * n_eval / P1 + psi1)
                + A2 * np.sin(2 * np.pi * n_eval / P2 + psi2))
    if model == "debt":
        if D_data is None:
            raise ValueError("model='debt' requires D_data argument")
        A, P, psi, kappa = params["A"], params["P"], params["psi"], params["kappa"]
        sin_at_data = A * np.sin(2 * np.pi * n_data / P + psi)
        # Recover β from the data centroid (same trick as the other models)
        beta = (phi_data.mean() - alpha * n_data.mean()
                - sin_at_data.mean() - kappa * D_data.mean())
        # Interpolate D at n_eval (continuous between observed nights)
        order = np.argsort(n_data)
        D_eval = np.interp(n_eval, n_data[order], D_data[order])
        return (alpha * n_eval + beta
                + A * np.sin(2 * np.pi * n_eval / P + psi)
                + kappa * D_eval)
    raise ValueError(f"unknown model {model!r}")


def project_curve(model: str, n_data: np.ndarray, phi_data: np.ndarray,
                  params: dict, anchor: pd.Timestamp, timezone: str,
                  D_data: np.ndarray | None = None) -> tuple[list[float], list]:
    """Sample fit at INTEGER n (one prediction per biological night) and project.

    Why integer n only : the model predicts one onset per biological day. If we
    sample n at fractional values, ``onset_ts(n + δ) = onset_ts(n) + 24·δ·h``
    sweeps through the entire 24h agenda row as δ goes from 0 to 1, producing
    a misleading horizontal sweep in the visualisation. The correct trajectory
    is one marker per integer night ; the connecting line then shows the
    night-to-night drift directly.

    Big jumps (the predicted onset skips a row, e.g. when the rhythm advances
    by close to 24h between two consecutive nights) introduce a gap so the
    trace doesn't sweep across.
    """
    n_min, n_max = int(np.floor(n_data.min())), int(np.ceil(n_data.max()))
    n_eval = np.arange(n_min, n_max + 1, dtype=float)
    phi_eval = predict_phi(model, n_eval, params, n_data, phi_data, D_data=D_data)

    ts_eval = pd.DatetimeIndex(
        [anchor + pd.Timedelta(hours=float(24 * ni + pi))
         for ni, pi in zip(n_eval, phi_eval)]
    )
    if ts_eval.tz is None:
        ts_eval = ts_eval.tz_localize(timezone)
    else:
        ts_eval = ts_eval.tz_convert(timezone)

    xs: list[float] = []
    ms: list = []
    prev_m = None
    for t in ts_eval:
        m, x = to_agenda_xy(t)
        # Insert a gap if the row jumped by more than 1 day (skipped night)
        if prev_m is not None and (m - prev_m).days > 1:
            xs.append(float("nan"))
            ms.append(None)
        xs.append(x)
        ms.append(m)
        prev_m = m
    return xs, ms


def render_window(label: str, start: date_, end: date_, sleep_path: Path,
                  summary: list[dict], timezone: str, out_path: Path) -> None:
    import plotly.graph_objects as go

    s = next((x for x in summary if x["period_label"] == label), None)
    if s is None:
        raise ValueError(f"no summary entry for label {label!r}")

    # Recompute the debt per-night on the full chronology using T★/γ from summary
    # (so the window inherits its accumulated debt). Filter outliers identically
    # to fit.py (default 2-24h) so the accumulator isn't poisoned.
    t_star_h = s.get("t_star_h")
    gamma_debt = s.get("gamma_debt", 0.85)
    df = pd.read_parquet(sleep_path)
    all_nights = main_sleep_per_night(df, timezone=timezone)
    all_nights = all_nights[(all_nights["main_duration_h"] >= 2.0)
                            & (all_nights["main_duration_h"] <= 24.0)]
    if t_star_h is not None and np.isfinite(t_star_h):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from sleep_debt import compute_debt
        all_nights = compute_debt(all_nights, t_star_h,
                                  gamma=gamma_debt, floor_at_zero=False)

    nights = all_nights[(all_nights.index >= start) & (all_nights.index <= end)].copy()
    if nights.empty:
        print(f"[{label}] no nights in window — skipped")
        return

    anchor = pd.Timestamp(datetime.combine(start, time_(12, 0)), tz=timezone)
    onsets = nights["main_onset"].dt.tz_convert(timezone)
    offsets = nights["main_offset"].dt.tz_convert(timezone)
    delta_h = (onsets - anchor).dt.total_seconds() / 3600.0
    n_data = np.array([(d - start).days for d in nights.index], dtype=float)
    phi_data = delta_h.to_numpy() - 24.0 * n_data
    D_data = nights["debt_before_h"].to_numpy() if "debt_before_h" in nights.columns else None

    fig = go.Figure()

    # --- Sleep sessions as semi-transparent rectangles -----------------------
    # Each session may span 1 or 2 agenda rows (if it crosses 20:00).
    bar_h = pd.Timedelta(hours=9)  # rectangle half-height ; 18h tall row → visible band
    for onset_ts, offset_ts in zip(onsets, offsets):
        m_o, x_o = to_agenda_xy(onset_ts)
        m_e, x_e = to_agenda_xy(offset_ts)
        if m_o == m_e:
            fig.add_shape(
                type="rect", xref="x", yref="y",
                x0=x_o, x1=x_e,
                y0=pd.Timestamp(m_o) - bar_h, y1=pd.Timestamp(m_o) + bar_h,
                fillcolor="rgba(14, 158, 176, 0.35)",
                line=dict(color="rgba(14, 158, 176, 0.7)", width=0.5),
                layer="below",
            )
        else:
            fig.add_shape(
                type="rect", xref="x", yref="y",
                x0=x_o, x1=24,
                y0=pd.Timestamp(m_o) - bar_h, y1=pd.Timestamp(m_o) + bar_h,
                fillcolor="rgba(14, 158, 176, 0.35)",
                line=dict(color="rgba(14, 158, 176, 0.7)", width=0.5),
                layer="below",
            )
            fig.add_shape(
                type="rect", xref="x", yref="y",
                x0=0, x1=x_e,
                y0=pd.Timestamp(m_e) - bar_h, y1=pd.Timestamp(m_e) + bar_h,
                fillcolor="rgba(14, 158, 176, 0.35)",
                line=dict(color="rgba(14, 158, 176, 0.7)", width=0.5),
                layer="below",
            )

    # --- Fit overlays -------------------------------------------------------
    fits = [
        (
            "linear", AMBER, "dash",
            {"alpha": s["alpha_linear_h_per_day"]},
            f"L  τ={s['tau_linear_h']:.3f}h  R²={s['r2_linear']:.2f}",
        ),
    ]
    if np.isfinite(s.get("r2_full", float("nan"))):
        fits.append((
            "oscillator", CYAN, "solid",
            {"alpha": s["alpha_full_h_per_day"], "A": s["amplitude_h"],
             "P": s["period_days"], "psi": s["phase_rad"]},
            f"O  τ={s['tau_full_h']:.3f}h  A={s['amplitude_h']:.2f}h  P={s['period_days']:.1f}d  R²={s['r2_full']:.2f}",
        ))
    if np.isfinite(s.get("r2_double", float("nan"))):
        fits.append((
            "double", MAGENTA, "solid",
            {"alpha": s["tau_double_h"] - 24.0,
             "A1": s["amplitude_double_short_h"], "P1": s["period_double_short_days"],
             "psi1": s["phase_double_short_rad"],
             "A2": s["amplitude_double_long_h"], "P2": s["period_double_long_days"],
             "psi2": s["phase_double_long_rad"]},
            f"D  τ={s['tau_double_h']:.3f}h  "
            f"P₁={s['period_double_short_days']:.1f}d/A₁={s['amplitude_double_short_h']:.2f}h  "
            f"P₂={s['period_double_long_days']:.1f}d/A₂={s['amplitude_double_long_h']:.2f}h  "
            f"R²={s['r2_double']:.2f}",
        ))
    if np.isfinite(s.get("r2_debt", float("nan"))) and D_data is not None:
        fits.append((
            "debt", DARK, "solid",
            {"alpha": s["tau_debt_h"] - 24.0,
             "A": s["amplitude_debt_h"], "P": s["period_debt_days"],
             "psi": s["phase_debt_rad"], "kappa": s["kappa_debt"]},
            f"E  τ={s['tau_debt_h']:.3f}h  A={s['amplitude_debt_h']:.2f}h  "
            f"P={s['period_debt_days']:.1f}d  κ={s['kappa_debt']:+.3f}h/h  "
            f"R²={s['r2_debt']:.2f}",
        ))

    for model_name, color, dash, params, legend_label in fits:
        xs, ms = project_curve(model_name, n_data, phi_data, params, anchor, timezone,
                               D_data=D_data if model_name == "debt" else None)
        fig.add_trace(go.Scatter(
            x=xs, y=ms,
            mode="lines",
            line=dict(color=color, width=2.2, dash=dash),
            name=legend_label,
            connectgaps=False,
            hoverinfo="skip",
        ))

    # --- Actual onset markers (overlay last so they sit on top) -------------
    actual_xs = []
    actual_ys = []
    for ts in onsets:
        m, x = to_agenda_xy(ts)
        actual_xs.append(x)
        actual_ys.append(m)
    fig.add_trace(go.Scatter(
        x=actual_xs, y=actual_ys,
        mode="markers",
        marker=dict(color=TEAL, size=6, line=dict(color="white", width=0.5)),
        name="actual onset",
        hovertemplate="<b>%{y|%Y-%m-%d}</b><br>onset x = %{x:.2f}h past 20:00<extra></extra>",
    ))

    # --- Layout -------------------------------------------------------------
    tick_x = list(range(0, 25, 2))
    tick_labels = [f"{(NIGHT_START_HOUR + i) % 24:02d}h" for i in tick_x]
    fig.update_xaxes(
        tickvals=tick_x, ticktext=tick_labels,
        range=[-0.5, 24.5],
        title="time of night  (0 = 20:00 J−1   →   24 = 20:00 J)",
        showgrid=True, gridcolor="rgba(0,0,0,0.06)",
        zeroline=False,
    )
    # Midnight reference
    fig.add_vline(x=4, line=dict(color="rgba(0,0,0,0.25)", dash="dot"),
                  annotation_text="00:00", annotation_position="top")
    fig.update_yaxes(
        autorange="reversed",
        title="night (morning date)",
        showgrid=True, gridcolor="rgba(0,0,0,0.06)",
        tickformat="%Y-%m-%d",
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Agenda projection — {label}</b><br>"
                 f"<sub>{start} → {end}  ·  {len(nights)} nights  ·  "
                 f"AIC winner = <b>{s['best_model_aic']}</b>  ·  BIC winner = <b>{s['best_model_bic']}</b></sub>",
            x=0.02, xanchor="left",
        ),
        template="plotly_white",
        width=1000,
        height=max(520, 14 * len(nights) + 220),
        legend=dict(orientation="h", y=1.04, yanchor="bottom",
                    x=0.5, xanchor="center", font=dict(size=10)),
        margin=dict(t=130, l=90, r=30, b=70),
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    print(f"[{label}] {len(nights)} nights  →  {out_path.name}")


def parse_periods(spec: str) -> list[tuple[str, date_, date_]]:
    out = []
    for i, chunk in enumerate(spec.split(",")):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" in chunk:
            label, dates = chunk.split("=", 1)
        else:
            label, dates = f"p{i+1}", chunk
        a, b = dates.split(":")
        out.append((label.strip(), date_.fromisoformat(a), date_.fromisoformat(b)))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--subject-id", default="S001")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--timezone", default="Europe/Paris")
    ap.add_argument("--periods", required=True,
                    help="Comma-separated 'label=YYYY-MM-DD:YYYY-MM-DD' specs")
    ap.add_argument("--summary", type=Path, default=None,
                    help="Path to summary.json (default: <data_dir>/oscillator_explore/summary.json)")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="Output dir (default: <data_dir>/oscillator_explore)")
    args = ap.parse_args(argv)

    data_dir = args.data_dir or (ROOT / "data" / "personal" / args.subject_id)
    sleep_path = data_dir / "sleep_intervals.parquet"
    if not sleep_path.exists():
        print(f"ERROR: {sleep_path} not found", file=sys.stderr)
        return 1
    summary_path = args.summary or (data_dir / "oscillator_explore" / "summary.json")
    if not summary_path.exists():
        print(f"ERROR: {summary_path} not found — run fit.py first", file=sys.stderr)
        return 1
    out_dir = args.out_dir or (data_dir / "oscillator_explore")
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = json.loads(summary_path.read_text())
    for label, start, end in parse_periods(args.periods):
        out = out_dir / f"{label}_agenda.html"
        render_window(label, start, end, sleep_path, summary, args.timezone, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
