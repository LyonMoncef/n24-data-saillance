#!/usr/bin/env python3
"""Joint phase + duration model — debt-coupled.

Hypothesis tested
-----------------
The user hypothesised that on a constrained regime (ATCF) the sleep-debt
mechanism explodes the **TST** on weekends (rebound), while in weekdays the
duration is **clamped by alarm** ; on the phase side, the onset is largely
asservi to the social schedule, so the debt mostly acts on duration.

Model
-----

Phase (model E from ``fit.py``, unchanged) ::

    φ(n) = α·n + β + A·sin(2π·n/P + ψ) + κ·D(n)

Duration (the new addition) ::

    TST(n) = β_T + λ·D(n−1) − μ·C(n) + ε

where ``C(n) = 1`` for week-night (Mon/Tue/Wed/Thu/Fri mornings, where an
alarm typically clamps the night) and ``0`` for week-end (Sat/Sun mornings).
λ > 0 is expected (rebound : more accumulated debt → longer TST).
μ > 0 is expected (constraint pulls TST down on weekdays).

The two equations are fit **separately** : ``D`` is treated as known
(computed from observed TST via the leaky integrator with γ, T★). This
factorisation keeps each coefficient interpretable and avoids the
identifiability problems of a true joint NLS.

Three duration variants are compared :
  T0  (baseline)  : TST(n) = β_T
  T1  (debt)      : TST(n) = β_T + λ·D(n−1)
  T2  (debt+work) : TST(n) = β_T + λ·D(n−1) − μ·C(n)

AIC/BIC chooses among them.

Outputs (in ``data/personal/<subject>/oscillator_explore/``) :
  - ``joint_<label>.html``      : 2 panels per window (phase + duration)
  - ``joint_summary.json``      : phase + duration params for every window

Usage::

    .venv/bin/python tools/oscillator_explore/joint_model.py \\
        --subject-id S001 \\
        --periods "atcf=2025-04-06:2025-07-29,recent=2026-04-01:2026-05-07,winter25=2025-11-26:2025-12-26"
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date as date_
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fit import (  # noqa: E402
    aic_bic, fit_debt_oscillator, fit_linear, fit_oscillator,
    fft_top_peaks, load_phase_series, oscillator_model, parse_periods,
    r2_of,
)

TEAL = "#0e9eb0"
AMBER = "#d37c04"
CYAN = "#3be5e7"
MAGENTA = "#c5198d"
DARK = "#2a2a2a"


# ============================================================================
# Duration model
# ============================================================================

def weekday_indicator(nights_index) -> np.ndarray:
    """1 if morning ∈ {Mon, Tue, Wed, Thu, Fri} (weekday alarm), 0 if Sat/Sun.

    Convention : a night is keyed by its morning date. The morning of a
    weekday is when an alarm typically clamps the TST. ``C(n) = 1`` for those.
    """
    out = np.zeros(len(nights_index), dtype=float)
    for i, d in enumerate(nights_index):
        wd = d.weekday() if hasattr(d, "weekday") else pd.Timestamp(d).weekday()
        out[i] = 1.0 if wd <= 4 else 0.0  # Mon–Fri
    return out


def fit_tst_baseline(tst: np.ndarray) -> tuple[dict, np.ndarray]:
    """T0 : TST(n) = β_T (constant). β_T = mean(TST)."""
    beta = float(np.mean(tst))
    pred = np.full_like(tst, beta, dtype=float)
    return {"beta_T": beta}, tst - pred


def fit_tst_debt(tst: np.ndarray, D_prev: np.ndarray) -> tuple[dict, np.ndarray]:
    """T1 : TST(n) = β_T + λ · D(n−1). OLS, 2 params."""
    X = np.column_stack([np.ones_like(tst), D_prev])
    coef, *_ = np.linalg.lstsq(X, tst, rcond=None)
    beta, lam = coef
    pred = X @ coef
    return {"beta_T": float(beta), "lambda": float(lam)}, tst - pred


def fit_tst_debt_work(
    tst: np.ndarray, D_prev: np.ndarray, C: np.ndarray,
) -> tuple[dict, np.ndarray]:
    """T2 : TST(n) = β_T + λ · D(n−1) − μ · C(n). OLS, 3 params (sign on μ is free)."""
    X = np.column_stack([np.ones_like(tst), D_prev, C])
    coef, *_ = np.linalg.lstsq(X, tst, rcond=None)
    beta, lam, neg_mu = coef
    pred = X @ coef
    # Convention : μ ≥ 0 means weekdays reduce TST. We store −neg_mu as μ.
    return (
        {"beta_T": float(beta), "lambda": float(lam), "mu": float(-neg_mu)},
        tst - pred,
    )


# ============================================================================
# Window fit
# ============================================================================

@dataclass
class JointFit:
    period_label: str
    start: str
    end: str
    n_nights_used: int
    n_nights_window: int
    t_star_h: float
    gamma_debt: float
    # Phase (model E)
    tau_debt_h: float
    amplitude_debt_h: float
    period_debt_days: float
    phase_debt_rad: float
    kappa_debt: float
    r2_phase_E: float
    aic_phase_E: float
    bic_phase_E: float
    # Duration variants
    beta_T0_h: float
    r2_T0: float
    aic_T0: float
    bic_T0: float
    beta_T1_h: float
    lambda_T1: float
    r2_T1: float
    aic_T1: float
    bic_T1: float
    beta_T2_h: float
    lambda_T2: float
    mu_T2_h: float
    r2_T2: float
    aic_T2: float
    bic_T2: float
    best_tst_aic: str
    best_tst_bic: str


def _empty_fit(label, start, end, n_used, n_window, t_star, gamma):
    nan = float("nan")
    return JointFit(
        period_label=label, start=start.isoformat(), end=end.isoformat(),
        n_nights_used=n_used, n_nights_window=n_window,
        t_star_h=t_star, gamma_debt=gamma,
        tau_debt_h=nan, amplitude_debt_h=nan, period_debt_days=nan,
        phase_debt_rad=nan, kappa_debt=nan, r2_phase_E=nan, aic_phase_E=nan, bic_phase_E=nan,
        beta_T0_h=nan, r2_T0=nan, aic_T0=nan, bic_T0=nan,
        beta_T1_h=nan, lambda_T1=nan, r2_T1=nan, aic_T1=nan, bic_T1=nan,
        beta_T2_h=nan, lambda_T2=nan, mu_T2_h=nan, r2_T2=nan, aic_T2=nan, bic_T2=nan,
        best_tst_aic="?", best_tst_bic="?",
    )


def fit_joint_window(
    sleep_path: Path, timezone: str, label: str,
    start: date_, end: date_,
    t_star_h: float, gamma_debt: float,
) -> tuple[JointFit, pd.DataFrame]:
    series = load_phase_series(
        sleep_path, timezone, start, end,
        t_star_h=t_star_h, gamma_debt=gamma_debt,
    )
    n_window = (end - start).days + 1
    if len(series) < 5 or "debt_before_h" not in series.columns:
        return _empty_fit(label, start, end, len(series), n_window, t_star_h, gamma_debt), series

    n = series["n"].to_numpy()
    phi = series["phi_h"].to_numpy()
    tst = series["tst_h"].to_numpy()
    D_before = series["debt_before_h"].to_numpy()  # debt at bedtime of night n
    C = weekday_indicator(series.index)

    # ──────────────────────────────────────────────────────────────
    # Phase fit (model E) — same machinery as fit.py
    # ──────────────────────────────────────────────────────────────
    alpha0, beta0, r2_lin, resid_lin = fit_linear(n, phi)
    top_P, top_A = fft_top_peaks(resid_lin, n, k=3)
    P_seed = top_P[0] if top_P else 7.0
    A_seed = top_A[0] if top_A else 1.0
    deb = fit_debt_oscillator(n, phi, D_before, alpha0, beta0, P_seed, A_seed)
    if deb is None:
        tau_e = A_e = P_e = psi_e = kappa_e = float("nan")
        r2_e = aic_e = bic_e = float("nan")
    else:
        p_e, resid_e = deb
        tau_e = 24.0 + p_e["alpha"]; A_e = p_e["A"]
        P_e = p_e["P"]; psi_e = p_e["psi"]; kappa_e = p_e["kappa"]
        r2_e = r2_of(phi, resid_e)
        aic_e, bic_e = aic_bic(len(phi), float(np.sum(resid_e ** 2)), 6)

    # ──────────────────────────────────────────────────────────────
    # Duration fits (T0, T1, T2) — OLS
    # ──────────────────────────────────────────────────────────────
    p_T0, resid_T0 = fit_tst_baseline(tst)
    p_T1, resid_T1 = fit_tst_debt(tst, D_before)
    p_T2, resid_T2 = fit_tst_debt_work(tst, D_before, C)
    n_data = len(tst)
    aic_T0, bic_T0 = aic_bic(n_data, float(np.sum(resid_T0 ** 2)), 1)
    aic_T1, bic_T1 = aic_bic(n_data, float(np.sum(resid_T1 ** 2)), 2)
    aic_T2, bic_T2 = aic_bic(n_data, float(np.sum(resid_T2 ** 2)), 3)

    def _r2(resid):
        ss_res = float(np.sum(resid ** 2))
        ss_tot = float(np.sum((tst - tst.mean()) ** 2))
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    r2_T0 = _r2(resid_T0)
    r2_T1 = _r2(resid_T1)
    r2_T2 = _r2(resid_T2)

    cand_aic = {"T0": aic_T0, "T1": aic_T1, "T2": aic_T2}
    cand_bic = {"T0": bic_T0, "T1": bic_T1, "T2": bic_T2}
    cand_aic = {k: v for k, v in cand_aic.items() if np.isfinite(v)}
    cand_bic = {k: v for k, v in cand_bic.items() if np.isfinite(v)}
    best_aic = min(cand_aic, key=cand_aic.get) if cand_aic else "?"
    best_bic = min(cand_bic, key=cand_bic.get) if cand_bic else "?"

    return (
        JointFit(
            period_label=label, start=start.isoformat(), end=end.isoformat(),
            n_nights_used=len(series), n_nights_window=n_window,
            t_star_h=t_star_h, gamma_debt=gamma_debt,
            tau_debt_h=tau_e, amplitude_debt_h=A_e, period_debt_days=P_e,
            phase_debt_rad=psi_e, kappa_debt=kappa_e,
            r2_phase_E=r2_e, aic_phase_E=aic_e, bic_phase_E=bic_e,
            beta_T0_h=p_T0["beta_T"], r2_T0=r2_T0, aic_T0=aic_T0, bic_T0=bic_T0,
            beta_T1_h=p_T1["beta_T"], lambda_T1=p_T1["lambda"],
            r2_T1=r2_T1, aic_T1=aic_T1, bic_T1=bic_T1,
            beta_T2_h=p_T2["beta_T"], lambda_T2=p_T2["lambda"], mu_T2_h=p_T2["mu"],
            r2_T2=r2_T2, aic_T2=aic_T2, bic_T2=bic_T2,
            best_tst_aic=best_aic, best_tst_bic=best_bic,
        ),
        series,
    )


# ============================================================================
# Visualisation
# ============================================================================

def plot_joint(label: str, series: pd.DataFrame, fit: JointFit, out_path: Path) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    n = series["n"].to_numpy()
    phi = series["phi_h"].to_numpy()
    tst = series["tst_h"].to_numpy()
    D = series["debt_before_h"].to_numpy()
    C = weekday_indicator(series.index)
    dates = list(series.index)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.14,
        subplot_titles=(
            f"<b>Phase</b>  φ(n) — model E fit  ·  τ={fit.tau_debt_h:.3f}h  "
            f"κ={fit.kappa_debt:+.3f}h/h  R²={fit.r2_phase_E:.2f}",
            f"<b>Duration</b>  TST(n)  ·  best AIC = <b>{fit.best_tst_aic}</b>  "
            f"·  best BIC = <b>{fit.best_tst_bic}</b>",
        ),
    )

    # ── Panel 1 : phase + model E ───────────────────────────────
    fig.add_trace(
        go.Scatter(x=n, y=phi, mode="markers",
                   marker=dict(color=TEAL, size=7),
                   name="onset φ(n)", showlegend=True),
        row=1, col=1,
    )
    if np.isfinite(fit.r2_phase_E):
        alpha_e = fit.tau_debt_h - 24.0
        sin_at_n = fit.amplitude_debt_h * np.sin(2 * np.pi * n / fit.period_debt_days + fit.phase_debt_rad)
        beta_e = phi.mean() - alpha_e * n.mean() - sin_at_n.mean() - fit.kappa_debt * D.mean()
        y_e = alpha_e * n + beta_e + sin_at_n + fit.kappa_debt * D
        order = np.argsort(n)
        fig.add_trace(
            go.Scatter(x=n[order], y=y_e[order], mode="lines+markers",
                       line=dict(color=DARK, width=2),
                       marker=dict(size=4, color=DARK),
                       name=f"model E  R²={fit.r2_phase_E:.2f}"),
            row=1, col=1,
        )
    fig.update_xaxes(title_text="day index n", row=1, col=1)
    fig.update_yaxes(title_text="φ(n)  (h)", row=1, col=1)

    # ── Panel 2 : TST + 3 fit variants ──────────────────────────
    # Color bars by weekday/weekend for visual context
    bar_colors = [TEAL if c == 0 else AMBER for c in C]  # weekend=teal, weekday=amber
    fig.add_trace(
        go.Bar(
            x=dates, y=tst,
            marker=dict(color=bar_colors, opacity=0.55),
            name="TST  (amber=weekday, teal=weekend)",
            showlegend=True,
            hovertemplate="%{x|%a %d %b}  TST=%{y:.2f}h<extra></extra>",
        ),
        row=2, col=1,
    )
    # T★ reference
    fig.add_hline(y=fit.t_star_h, line=dict(color="black", dash="dot", width=1),
                  annotation_text=f"T★ = {fit.t_star_h:.2f}h",
                  annotation_position="top right",
                  row=2, col=1)

    # Predictions for each TST variant
    if np.isfinite(fit.r2_T0):
        pred_T0 = np.full_like(tst, fit.beta_T0_h)
        fig.add_trace(
            go.Scatter(x=dates, y=pred_T0, mode="lines",
                       line=dict(color="#888888", dash="dot", width=1.5),
                       name=f"T0 const  β={fit.beta_T0_h:.2f}h  R²={fit.r2_T0:.2f}"),
            row=2, col=1,
        )
    if np.isfinite(fit.r2_T1):
        pred_T1 = fit.beta_T1_h + fit.lambda_T1 * D
        fig.add_trace(
            go.Scatter(x=dates, y=pred_T1, mode="lines",
                       line=dict(color=CYAN, width=2),
                       name=f"T1 β+λD  β={fit.beta_T1_h:.2f}h  λ={fit.lambda_T1:+.3f}  R²={fit.r2_T1:.2f}"),
            row=2, col=1,
        )
    if np.isfinite(fit.r2_T2):
        pred_T2 = fit.beta_T2_h + fit.lambda_T2 * D - fit.mu_T2_h * C
        fig.add_trace(
            go.Scatter(x=dates, y=pred_T2, mode="lines",
                       line=dict(color=MAGENTA, width=2.5),
                       name=f"T2 β+λD−μC  β={fit.beta_T2_h:.2f}h  λ={fit.lambda_T2:+.3f}  μ={fit.mu_T2_h:+.2f}h  R²={fit.r2_T2:.2f}"),
            row=2, col=1,
        )

    fig.update_xaxes(title_text="date", row=2, col=1)
    fig.update_yaxes(title_text="TST  (h)", rangemode="tozero", row=2, col=1)

    fig.update_layout(
        title=dict(
            text=f"<b>Joint phase + TST model — {label}</b>"
                 f"<br><sub>{fit.start} → {fit.end}  ·  {fit.n_nights_used}/{fit.n_nights_window} nights  "
                 f"·  T★={fit.t_star_h:.2f}h  γ={fit.gamma_debt:.2f}</sub>",
            x=0.02, xanchor="left",
        ),
        template="plotly_white",
        width=1200, height=820,
        legend=dict(orientation="h", y=-0.05, yanchor="top", x=0.5, xanchor="center",
                    font=dict(size=10)),
        margin=dict(t=120, l=70, r=30, b=120),
        barmode="overlay",
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn")


# ============================================================================
# CLI
# ============================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--subject-id", default="S001")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--timezone", default="Europe/Paris")
    ap.add_argument("--periods", required=True,
                    help="Comma-separated 'label=YYYY-MM-DD:YYYY-MM-DD' specs")
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--t-star", type=float, default=8.99,
                    help="Ideal sleep duration T★ in hours (default 8.99)")
    ap.add_argument("--gamma-debt", type=float, default=0.85,
                    help="Leaky decay γ for debt accumulator (default 0.85)")
    args = ap.parse_args(argv)

    data_dir = args.data_dir or (ROOT / "data" / "personal" / args.subject_id)
    sleep_path = data_dir / "sleep_intervals.parquet"
    if not sleep_path.exists():
        print(f"ERROR: {sleep_path} not found", file=sys.stderr)
        return 1
    out_dir = args.out_dir or (data_dir / "oscillator_explore")
    out_dir.mkdir(parents=True, exist_ok=True)

    periods = parse_periods(args.periods)
    summary = []
    print(f"T★ = {args.t_star:.2f}h  ·  γ = {args.gamma_debt:.2f}\n")
    header = (
        f"{'label':<10} {'nights':<10} "
        f"{'κ':>7} {'R²_φE':>6}  |  "
        f"{'β_T2':>5} {'λ':>6} {'μ':>5}  |  "
        f"{'R²_T0':>5} {'R²_T1':>5} {'R²_T2':>5}  |  "
        f"{'best_AIC':>9} {'best_BIC':>9}"
    )
    print(header); print("-" * len(header))

    for label, a, b in periods:
        fit, series = fit_joint_window(
            sleep_path, args.timezone, label, a, b,
            t_star_h=args.t_star, gamma_debt=args.gamma_debt,
        )
        out_html = out_dir / f"joint_{label}.html"
        plot_joint(label, series, fit, out_html)
        summary.append(asdict(fit))
        nights = f"{fit.n_nights_used}/{fit.n_nights_window}"
        print(
            f"{label:<10} {nights:<10} "
            f"{fit.kappa_debt:>+7.3f} {fit.r2_phase_E:>6.2f}  |  "
            f"{fit.beta_T2_h:>5.2f} {fit.lambda_T2:>+6.3f} {fit.mu_T2_h:>+5.2f}  |  "
            f"{fit.r2_T0:>5.2f} {fit.r2_T1:>5.2f} {fit.r2_T2:>5.2f}  |  "
            f"{fit.best_tst_aic:>9} {fit.best_tst_bic:>9}"
        )

    out_json = out_dir / "joint_summary.json"
    out_json.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary  → {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
