#!/usr/bin/env python3
"""Generate a comparative figure from the oscillator_explore summary.json.

Single side-by-side plot showing the centered phase trajectory φ(n) for each
period, with overlaid linear / linear+sin / linear+weekly / combined fits.
Useful to *visually* compare regimes.

Usage::

    .venv/bin/python tools/oscillator_explore/compare.py \\
        --summary data/personal/S001/oscillator_explore/summary.json \\
        --subject-id S001
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date as date_, datetime, time as time_
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from n24sal.sleep.per_night import main_sleep_per_night  # noqa: E402
from fit import load_phase_series  # noqa: E402

TEAL, AMBER, CYAN, VIOLET, GREEN = "#0e9eb0", "#d37c04", "#3be5e7", "#7c5cff", "#1d8a4a"
DARK = "#2a2a2a"


def load_phi(sleep_path: Path, timezone: str, start: date_, end: date_,
             t_star_h: float | None = None, gamma_debt: float = 0.85) -> pd.DataFrame:
    """Return phase series + (optional) debt columns from load_phase_series."""
    return load_phase_series(
        sleep_path, timezone, start, end,
        t_star_h=t_star_h, gamma_debt=gamma_debt,
    )


def main(argv=None) -> int:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", type=Path, default=ROOT / "data/personal/S001/oscillator_explore/summary.json")
    ap.add_argument("--subject-id", default="S001")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--timezone", default="Europe/Paris")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    data_dir = args.data_dir or (ROOT / "data" / "personal" / args.subject_id)
    sleep_path = data_dir / "sleep_intervals.parquet"
    out = args.out or (data_dir / "oscillator_explore" / "comparison.html")
    summary = json.loads(args.summary.read_text())

    # T★ and γ are stored on each FitResult ; use the first window's values for
    # data reloading (they're constant across windows in the standard pipeline).
    t_star_h = next(
        (s.get("t_star_h") for s in summary if np.isfinite(s.get("t_star_h", float("nan")))),
        None,
    )
    gamma_debt = next(
        (s.get("gamma_debt") for s in summary if np.isfinite(s.get("gamma_debt", float("nan")))),
        0.85,
    )

    n_panels = len(summary)
    fig = make_subplots(
        rows=1, cols=n_panels,
        subplot_titles=[
            f"<b>{s['period_label']}</b><br><sub>{s['start']} → {s['end']}  ·  "
            f"{s['n_nights_used']}/{s['n_nights_window']} nights</sub>"
            for s in summary
        ],
        horizontal_spacing=0.06,
    )

    for col, s in enumerate(summary, start=1):
        series = load_phi(
            sleep_path, args.timezone,
            date_.fromisoformat(s["start"]), date_.fromisoformat(s["end"]),
            t_star_h=t_star_h, gamma_debt=gamma_debt,
        )
        if series.empty:
            continue
        n = series["n"].to_numpy()
        phi = series["phi_h"].to_numpy()
        # Center φ on its linear fit intercept so panels share a baseline of 0
        alpha = s["alpha_linear_h_per_day"]
        beta = phi.mean() - alpha * n.mean()
        phi_c = phi - beta  # so the linear fit is just α·n through origin
        n_smooth = np.linspace(n.min(), n.max(), 400)

        fig.add_trace(
            go.Scatter(x=n, y=phi_c, mode="markers",
                       marker=dict(color=TEAL, size=6),
                       name="onset" if col == 1 else None, showlegend=(col == 1)),
            row=1, col=col,
        )
        # linear
        fig.add_trace(
            go.Scatter(x=n_smooth, y=alpha * n_smooth, mode="lines",
                       line=dict(color=AMBER, dash="dash"),
                       name=f"linear (τ−24={alpha*24:.0f}min/day)" if col == 1 else None,
                       showlegend=(col == 1)),
            row=1, col=col,
        )
        # oscillator
        if np.isfinite(s.get("amplitude_h", float("nan"))):
            A, P, psi = s["amplitude_h"], s["period_days"], s["phase_rad"]
            alpha_f = s["alpha_full_h_per_day"]
            # re-center
            y_osc_raw = alpha_f * n_smooth + A * np.sin(2 * np.pi * n_smooth / P + psi)
            y_osc_on_data = alpha_f * n + A * np.sin(2 * np.pi * n / P + psi)
            offset = y_osc_on_data.mean() - phi_c.mean()
            fig.add_trace(
                go.Scatter(x=n_smooth, y=y_osc_raw - offset, mode="lines",
                           line=dict(color=CYAN, width=2),
                           name="linear+sin" if col == 1 else None, showlegend=(col == 1)),
                row=1, col=col,
            )
        # weekly
        if np.isfinite(s.get("weekend_offset_h", float("nan"))):
            grid = np.arange(int(n.min()), int(n.max()) + 1)
            we_dates = [series.index.min() + pd.Timedelta(days=int(g - n.min())) for g in grid]
            we = np.array([1.0 if pd.Timestamp(d).weekday() in (5, 6) else 0.0 for d in we_dates])
            alpha_w = s["tau_weekly_h"] - 24.0
            dw = s["weekend_offset_h"]
            y_w = alpha_w * grid + dw * we
            offset_w = y_w.mean() - phi_c.mean()
            fig.add_trace(
                go.Scatter(x=grid, y=y_w - offset_w, mode="lines",
                           line=dict(color=VIOLET, dash="dot"),
                           name=f"linear+weekly (ΔW)" if col == 1 else None, showlegend=(col == 1)),
                row=1, col=col,
            )
        # double sinusoid
        if np.isfinite(s.get("r2_double", float("nan"))):
            alpha_d = s["tau_double_h"] - 24.0
            A1, P1, psi1 = s["amplitude_double_short_h"], s["period_double_short_days"], s["phase_double_short_rad"]
            A2, P2, psi2 = s["amplitude_double_long_h"], s["period_double_long_days"], s["phase_double_long_rad"]
            sin_smooth = (A1 * np.sin(2 * np.pi * n_smooth / P1 + psi1)
                          + A2 * np.sin(2 * np.pi * n_smooth / P2 + psi2))
            sin_at_n = (A1 * np.sin(2 * np.pi * n / P1 + psi1)
                        + A2 * np.sin(2 * np.pi * n / P2 + psi2))
            y_d = alpha_d * n_smooth + sin_smooth
            offset_d = (alpha_d * n + sin_at_n).mean() - phi_c.mean()
            fig.add_trace(
                go.Scatter(x=n_smooth, y=y_d - offset_d, mode="lines",
                           line=dict(color="#c5198d", width=2),
                           name="linear+2sin" if col == 1 else None, showlegend=(col == 1)),
                row=1, col=col,
            )
        # debt-oscillator (model E) — needs per-night D from loaded series
        if np.isfinite(s.get("r2_debt", float("nan"))) and "debt_before_h" in series.columns:
            alpha_e = s["tau_debt_h"] - 24.0
            A_e, P_e, psi_e, kappa_e = s["amplitude_debt_h"], s["period_debt_days"], s["phase_debt_rad"], s["kappa_debt"]
            D_at_n = series["debt_before_h"].to_numpy()
            sin_at_n_e = A_e * np.sin(2 * np.pi * n / P_e + psi_e)
            y_e_at_n = alpha_e * n + sin_at_n_e + kappa_e * D_at_n
            offset_e = y_e_at_n.mean() - phi_c.mean()
            order = np.argsort(n)
            fig.add_trace(
                go.Scatter(x=n[order], y=(y_e_at_n - offset_e)[order],
                           mode="lines+markers",
                           line=dict(color=DARK, width=2),
                           marker=dict(size=4, color=DARK),
                           name="linear+sin+κD" if col == 1 else None, showlegend=(col == 1)),
                row=1, col=col,
            )

        # Annotate stats in the panel
        ann = (
            f"τ_lin = {s['tau_linear_h']:.3f}h  (R²={s['r2_linear']:.2f})<br>"
            f"τ_osc = {s['tau_full_h']:.3f}h  A={s['amplitude_h']:.1f}h  P={s['period_days']:.1f}d  (R²={s['r2_full']:.2f})<br>"
            f"τ_wk  = {s['tau_weekly_h']:.3f}h  ΔW={s['weekend_offset_h']:+.1f}h  (R²={s['r2_weekly']:.2f})<br>"
            f"τ_c   = {s['tau_combined_h']:.3f}h  (R²={s['r2_combined']:.2f})<br>"
            f"τ_dbl = {s['tau_double_h']:.3f}h  "
            f"P₁={s['period_double_short_days']:.1f}d/A₁={s['amplitude_double_short_h']:.1f}h  "
            f"P₂={s['period_double_long_days']:.1f}d/A₂={s['amplitude_double_long_h']:.1f}h  "
            f"(R²={s['r2_double']:.2f})<br>"
            f"τ_deb = {s['tau_debt_h']:.3f}h  κ={s['kappa_debt']:+.3f}h/h  "
            f"(R²={s['r2_debt']:.2f}, T★={s.get('t_star_h', float('nan')):.2f}h γ={s.get('gamma_debt', float('nan')):.2f})<br>"
            f"<b>AIC winner: {s['best_model_aic']}</b>  ·  <b>BIC winner: {s['best_model_bic']}</b>"
        )
        suffix = "" if col == 1 else str(col)
        fig.add_annotation(
            xref=f"x{suffix} domain", yref=f"y{suffix} domain",
            x=0.02, y=0.98, xanchor="left", yanchor="top",
            text=ann, showarrow=False,
            font=dict(family="monospace", size=10),
            bgcolor="rgba(255,255,255,0.85)", bordercolor="lightgray", borderwidth=1,
        )
        fig.update_xaxes(title_text="day index n", row=1, col=col)
        fig.update_yaxes(title_text="φ centered (h)" if col == 1 else None, row=1, col=col)

    fig.update_layout(
        title=dict(text="<b>Oscillator-on-drift — regime comparison</b>",
                   x=0.02, xanchor="left"),
        template="plotly_white",
        width=420 * n_panels, height=540,
        legend=dict(orientation="h", y=-0.18, yanchor="top", x=0.5, xanchor="center"),
        margin=dict(t=90, l=70, r=30, b=120),
    )
    fig.write_html(str(out), include_plotlyjs="cdn")
    print(f"Comparison figure → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
