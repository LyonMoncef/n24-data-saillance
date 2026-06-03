#!/usr/bin/env python3
"""Out-of-sample prediction test for the oscillator phase models.

For each window: fit the 5 phase-only models (L, O, W, C, D — model E is
**excluded** because projecting D(n) into the future requires also projecting
TST(n), which closes a recursive loop best handled by a separate joint
forecaster — left for a future iteration), pick the best by AIC, project the
chosen model ``--horizon`` nights forward, and compare to the **actually
observed** nights in the prediction window.

Outputs (in ``data/personal/<subject>/oscillator_explore/``):
    prediction_<label>.html      : agenda view + φ(n) view, fit + projection
                                   + observed validation nights overlaid
    prediction_summary.json      : best model, MAE, RMSE per window

Usage::

    .venv/bin/python tools/oscillator_explore/predict.py \\
        --subject-id S001 \\
        --windows "summer24=2024-06-01:2024-06-30,autumn24=2024-10-01:2024-11-29,post-atcf=2025-08-01:2025-10-29" \\
        --horizon 10
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date as date_, datetime, time as time_, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from n24sal.sleep.per_night import main_sleep_per_night  # noqa: E402
from fit import (  # noqa: E402
    aic_bic, fit_combined, fit_double_oscillator, fit_linear,
    fit_oscillator, fit_weekly, lomb_scargle_top_peaks,
    load_phase_series, weekend_indicator,
)
from agenda_overlay import predict_phi, to_agenda_xy  # noqa: E402

TEAL = "#0e9eb0"
AMBER = "#d37c04"
CYAN = "#3be5e7"
MAGENTA = "#c5198d"
DARK = "#2a2a2a"
GREEN = "#1d8a4a"
RED = "#c5198d"


# ============================================================================
# Fit-and-select
# ============================================================================

@dataclass
class PredictionResult:
    label: str
    fit_start: str
    fit_end: str
    pred_start: str
    pred_end: str
    n_fit: int
    n_pred: int
    horizon: int
    best_model: str
    best_model_params: dict
    # in-sample
    r2_in_sample: float
    std_in_sample_h: float
    aic_in_sample: float
    # out-of-sample
    mae_h: float
    rmse_h: float
    bias_h: float                  # mean(observed - predicted)
    per_night_residuals_h: list[float]
    per_night_dates: list[str]
    # all models' AIC for context
    aic_all: dict
    bic_all: dict


def fit_all_phase_models(n: np.ndarray, phi: np.ndarray,
                          weekend: np.ndarray) -> dict[str, dict]:
    """Fit L, O, W, C, D — returns dict[name] -> {params, aic, bic, k, r2}."""
    n_data = len(phi)
    out: dict[str, dict] = {}

    # L
    alpha0, beta0, r2_lin, resid_lin = fit_linear(n, phi)
    aic_l, bic_l = aic_bic(n_data, float(np.sum(resid_lin ** 2)), 2)
    out["L"] = {
        "params": {"alpha": alpha0, "beta": beta0},
        "aic": aic_l, "bic": bic_l, "k": 2, "r2": r2_lin,
        "predict_key": "linear",
    }

    # Seed period for O / C from Lomb-Scargle
    top_P, top_A, _ = lomb_scargle_top_peaks(resid_lin, n, k=3)
    P_seed = top_P[0] if top_P else 7.0
    A_seed = top_A[0] if top_A else max(np.std(resid_lin), 0.5)

    # O
    osc = fit_oscillator(n, phi, alpha0, beta0, P_seed, A_seed)
    if osc is not None:
        p, resid = osc
        aic, bic = aic_bic(n_data, float(np.sum(resid ** 2)), 5)
        r2 = 1.0 - float(np.sum(resid ** 2)) / float(np.sum((phi - phi.mean()) ** 2))
        out["O"] = {"params": p, "aic": aic, "bic": bic, "k": 5, "r2": r2,
                    "predict_key": "oscillator"}

    # W (no NLS — OLS via fit_weekly)
    wk = fit_weekly(n, phi, weekend)
    alpha_w, beta_w, dw, r2_w, resid_w = wk
    aic, bic = aic_bic(n_data, float(np.sum(resid_w ** 2)), 3)
    out["W"] = {
        "params": {"alpha": alpha_w, "beta": beta_w, "dw": dw},
        "aic": aic, "bic": bic, "k": 3, "r2": r2_w,
        "predict_key": "weekly",
    }

    # C
    cm = fit_combined(n, phi, weekend, alpha0, beta0, P_seed, A_seed, dw)
    if cm is not None:
        p, resid = cm
        aic, bic = aic_bic(n_data, float(np.sum(resid ** 2)), 6)
        r2 = 1.0 - float(np.sum(resid ** 2)) / float(np.sum((phi - phi.mean()) ** 2))
        out["C"] = {"params": p, "aic": aic, "bic": bic, "k": 6, "r2": r2,
                    "predict_key": "combined"}

    # D (double sinusoid)
    P1_seed = top_P[0] if len(top_P) >= 1 else 3.0
    A1_seed = top_A[0] if len(top_A) >= 1 else 0.5
    P2_seed = top_P[1] if len(top_P) >= 2 else 10.0
    A2_seed = top_A[1] if len(top_A) >= 2 else 0.5
    db = fit_double_oscillator(n, phi, alpha0, beta0,
                                P1_seed, A1_seed, P2_seed, A2_seed)
    if db is not None:
        p, resid = db
        aic, bic = aic_bic(n_data, float(np.sum(resid ** 2)), 8)
        r2 = 1.0 - float(np.sum(resid ** 2)) / float(np.sum((phi - phi.mean()) ** 2))
        out["D"] = {"params": p, "aic": aic, "bic": bic, "k": 8, "r2": r2,
                    "predict_key": "double"}

    return out


def _predict_for_name(name: str, n_eval: np.ndarray, params: dict,
                       n_data: np.ndarray, phi_data: np.ndarray,
                       weekend_eval: np.ndarray | None) -> np.ndarray:
    """Evaluate a fitted model at n_eval — reconstructing β from data centroid.

    For models L/O/D this delegates to ``agenda_overlay.predict_phi``. For W
    and C we add the weekend term explicitly (predict_phi doesn't know about
    weekend) — β is recovered from the residual on the fit data.
    """
    if name in ("L", "O", "D"):
        key = {"L": "linear", "O": "oscillator", "D": "double"}[name]
        return predict_phi(key, n_eval, params, n_data, phi_data)

    if name == "W":
        # φ(n) = α·n + β + ΔW · weekend(n)
        alpha = params["alpha"]; dw = params["dw"]
        # Re-derive β from data centroid (consistent with predict_phi's convention)
        # Need weekend on data:
        # We rebuild weekend_data from n_data + the start date — but we don't
        # have it here. Easiest: use the stored β from the fit (fit_weekly
        # returned it explicitly).
        beta = params["beta"]
        if weekend_eval is None:
            raise ValueError("model 'W' needs weekend_eval")
        return alpha * n_eval + beta + dw * weekend_eval

    if name == "C":
        alpha = params["alpha"]; A = params["A"]
        P = params["P"]; psi = params["psi"]; dw = params["dw"]
        beta = params["beta"]
        if weekend_eval is None:
            raise ValueError("model 'C' needs weekend_eval")
        return (alpha * n_eval + beta
                + A * np.sin(2 * np.pi * n_eval / P + psi)
                + dw * weekend_eval)
    raise ValueError(f"unknown model {name}")


# ============================================================================
# Predict + validate one window
# ============================================================================

def predict_window(sleep_path: Path, timezone: str, label: str,
                    fit_start: date_, fit_end: date_, horizon: int,
                    min_duration_h: float = 2.0, max_duration_h: float = 24.0,
                    ) -> tuple[PredictionResult, dict]:
    # Load fit window
    series_fit = load_phase_series(
        sleep_path, timezone, fit_start, fit_end,
        min_duration_h=min_duration_h, max_duration_h=max_duration_h,
    )
    if len(series_fit) < 8:
        raise ValueError(f"[{label}] only {len(series_fit)} nights — too few to fit")

    n_data = series_fit["n"].to_numpy()
    phi_data = series_fit["phi_h"].to_numpy()
    weekend_data = weekend_indicator(series_fit.index)

    # Fit all
    fits = fit_all_phase_models(n_data, phi_data, weekend_data)
    best = min(fits, key=lambda k: fits[k]["aic"])
    best_fit = fits[best]

    # Validation window
    pred_start = fit_end + timedelta(days=1)
    pred_end = pred_start + timedelta(days=horizon - 1)
    series_pred = load_phase_series(
        sleep_path, timezone, fit_start, pred_end,
        min_duration_h=min_duration_h, max_duration_h=max_duration_h,
    )
    # Index may contain datetime.date objects ; coerce to Timestamps for comparison
    idx_ts = pd.to_datetime([str(d) for d in series_pred.index])
    mask = (idx_ts > pd.Timestamp(fit_end)) & (idx_ts <= pd.Timestamp(pred_end))
    series_val = series_pred[mask].copy()

    if len(series_val) == 0:
        # No real nights in validation horizon
        return (PredictionResult(
            label=label, fit_start=fit_start.isoformat(), fit_end=fit_end.isoformat(),
            pred_start=pred_start.isoformat(), pred_end=pred_end.isoformat(),
            n_fit=len(series_fit), n_pred=0, horizon=horizon,
            best_model=best, best_model_params=best_fit["params"],
            r2_in_sample=best_fit["r2"],
            std_in_sample_h=float(np.std(phi_data - _predict_for_name(
                best, n_data, best_fit["params"], n_data, phi_data, weekend_data
            ))),
            aic_in_sample=best_fit["aic"],
            mae_h=float("nan"), rmse_h=float("nan"), bias_h=float("nan"),
            per_night_residuals_h=[], per_night_dates=[],
            aic_all={k: v["aic"] for k, v in fits.items()},
            bic_all={k: v["bic"] for k, v in fits.items()},
        ), {"fits": fits, "series_fit": series_fit, "series_val": series_val})

    n_val = series_val["n"].to_numpy()
    phi_val = series_val["phi_h"].to_numpy()
    weekend_val = weekend_indicator(series_val.index)

    phi_pred = _predict_for_name(best, n_val, best_fit["params"],
                                  n_data, phi_data, weekend_val)
    residuals = phi_val - phi_pred
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    bias = float(np.mean(residuals))

    # Also compute the in-sample std for the chosen model
    phi_in_pred = _predict_for_name(best, n_data, best_fit["params"],
                                     n_data, phi_data, weekend_data)
    std_in = float(np.std(phi_data - phi_in_pred, ddof=0))

    return (PredictionResult(
        label=label, fit_start=fit_start.isoformat(), fit_end=fit_end.isoformat(),
        pred_start=pred_start.isoformat(), pred_end=pred_end.isoformat(),
        n_fit=len(series_fit), n_pred=len(series_val), horizon=horizon,
        best_model=best, best_model_params=best_fit["params"],
        r2_in_sample=best_fit["r2"], std_in_sample_h=std_in,
        aic_in_sample=best_fit["aic"],
        mae_h=mae, rmse_h=rmse, bias_h=bias,
        per_night_residuals_h=[float(x) for x in residuals],
        per_night_dates=[d.date().isoformat() if hasattr(d, "date") else str(d)
                         for d in series_val.index],
        aic_all={k: v["aic"] for k, v in fits.items()},
        bic_all={k: v["bic"] for k, v in fits.items()},
    ), {"fits": fits, "series_fit": series_fit, "series_val": series_val})


# ============================================================================
# Visualisation : agenda + phi(n) view
# ============================================================================

def render_prediction(label: str, series_fit: pd.DataFrame,
                       series_val: pd.DataFrame,
                       result: PredictionResult, fits: dict,
                       timezone: str, out_path: Path) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fit_start = date_.fromisoformat(result.fit_start)
    fit_end = date_.fromisoformat(result.fit_end)
    pred_end = date_.fromisoformat(result.pred_end)
    anchor = pd.Timestamp(datetime.combine(fit_start, time_(12, 0)), tz=timezone)

    n_data = series_fit["n"].to_numpy()
    phi_data = series_fit["phi_h"].to_numpy()
    weekend_data = weekend_indicator(series_fit.index)

    # Dense n grid covering both fit and prediction periods (integer per night)
    n_min = int(np.floor(n_data.min()))
    n_max_pred = (pred_end - fit_start).days
    n_dense = np.arange(n_min, n_max_pred + 1, dtype=float)
    # Weekend indicator for the dense grid (by date)
    dense_dates = [fit_start + timedelta(days=int(i)) for i in n_dense]
    weekend_dense = weekend_indicator(dense_dates)

    best = result.best_model
    best_params = result.best_model_params
    phi_curve = _predict_for_name(best, n_dense, best_params,
                                   n_data, phi_data, weekend_dense)

    # Convert (n, phi) to (date, x_hours)
    ts_curve = pd.DatetimeIndex(
        [anchor + pd.Timedelta(hours=float(24 * ni + pi))
         for ni, pi in zip(n_dense, phi_curve)]
    )
    if ts_curve.tz is None:
        ts_curve = ts_curve.tz_localize(timezone)
    else:
        ts_curve = ts_curve.tz_convert(timezone)

    xs_fit: list[float] = []; ys_fit: list = []
    xs_pred: list[float] = []; ys_pred: list = []
    for ts, ni in zip(ts_curve, n_dense):
        m, x = to_agenda_xy(ts)
        is_pred = m > pd.Timestamp(fit_end)
        if is_pred:
            xs_pred.append(x); ys_pred.append(m)
        else:
            xs_fit.append(x); ys_fit.append(m)

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.55, 0.45],
        horizontal_spacing=0.10,
        subplot_titles=(
            f"<b>Agenda view</b>  ·  fit + projection vs observed",
            f"<b>φ(n)</b>  ·  fit ({result.n_fit} nights) → {result.horizon}-night projection",
        ),
    )

    # ── Panel 1 : agenda ────────────────────────────────────────────
    # Real observed sessions (fit period) — semi-transparent teal
    df_raw = pd.read_parquet(sleep_path_global[0])  # set below
    all_nights = main_sleep_per_night(df_raw, timezone=timezone)
    all_nights = all_nights[(all_nights["main_duration_h"] >= 2.0)
                              & (all_nights["main_duration_h"] <= 24.0)]
    onsets_fit = series_fit["main_onset"]
    onsets_fit_local = pd.to_datetime(onsets_fit, utc=True).dt.tz_convert(timezone) \
        if hasattr(onsets_fit, "dt") else onsets_fit

    # Real onset markers in fit window
    xs_obs_fit = []; ys_obs_fit = []
    for ts in onsets_fit_local:
        m, x = to_agenda_xy(ts)
        xs_obs_fit.append(x); ys_obs_fit.append(m)
    fig.add_trace(
        go.Scatter(x=xs_obs_fit, y=ys_obs_fit, mode="markers",
                   marker=dict(color=TEAL, size=7, symbol="circle"),
                   name="observed (fit)", legendgroup="fit"),
        row=1, col=1,
    )

    # Real onset markers in validation window (the ground truth we predict)
    if len(series_val) > 0:
        onsets_val = series_val["main_onset"]
        onsets_val_local = pd.to_datetime(onsets_val, utc=True).dt.tz_convert(timezone) \
            if hasattr(onsets_val, "dt") else onsets_val
        xs_obs_val = []; ys_obs_val = []
        for ts in onsets_val_local:
            m, x = to_agenda_xy(ts)
            xs_obs_val.append(x); ys_obs_val.append(m)
        fig.add_trace(
            go.Scatter(x=xs_obs_val, y=ys_obs_val, mode="markers",
                       marker=dict(color=AMBER, size=10, symbol="diamond",
                                   line=dict(color="black", width=1)),
                       name="observed (truth)", legendgroup="val"),
            row=1, col=1,
        )

    # Model curve — fit segment (solid teal-dark)
    fig.add_trace(
        go.Scatter(x=xs_fit, y=ys_fit, mode="lines+markers",
                   line=dict(color=DARK, width=2),
                   marker=dict(size=4, color=DARK),
                   name=f"model {best} (fit)", legendgroup="fit"),
        row=1, col=1,
    )
    # Model curve — projection segment (dashed cyan)
    fig.add_trace(
        go.Scatter(x=xs_pred, y=ys_pred, mode="lines+markers",
                   line=dict(color=CYAN, width=2, dash="dash"),
                   marker=dict(size=6, color=CYAN, symbol="x"),
                   name=f"model {best} (projected)", legendgroup="pred"),
        row=1, col=1,
    )

    fig.update_xaxes(title_text="hours past 20:00", range=[0, 24],
                     tickvals=list(range(0, 25, 2)),
                     ticktext=["20", "22", "00", "02", "04", "06", "08", "10",
                                "12", "14", "16", "18", "20", "22", "24"],
                     row=1, col=1)
    fig.update_yaxes(title_text="morning date", autorange="reversed", row=1, col=1)

    # ── Panel 2 : φ(n) classic view ─────────────────────────────────
    fig.add_trace(
        go.Scatter(x=n_data, y=phi_data, mode="markers",
                   marker=dict(color=TEAL, size=7),
                   name="observed φ (fit)", showlegend=False),
        row=1, col=2,
    )
    if len(series_val) > 0:
        n_val = series_val["n"].to_numpy()
        phi_val = series_val["phi_h"].to_numpy()
        fig.add_trace(
            go.Scatter(x=n_val, y=phi_val, mode="markers",
                       marker=dict(color=AMBER, size=10, symbol="diamond",
                                   line=dict(color="black", width=1)),
                       name="observed φ (truth)", showlegend=False),
            row=1, col=2,
        )

    # Smooth fit curve (dense n)
    fig.add_trace(
        go.Scatter(x=n_dense, y=phi_curve, mode="lines",
                   line=dict(color=DARK, width=2),
                   name=f"model {best}", showlegend=False),
        row=1, col=2,
    )
    # Vertical line separating fit from prediction
    n_split = (fit_end - fit_start).days + 0.5
    fig.add_vline(x=n_split, line=dict(color="gray", dash="dot", width=1),
                  annotation_text="fit | predict",
                  annotation_position="top right",
                  row=1, col=2)

    fig.update_xaxes(title_text="day index n", row=1, col=2)
    fig.update_yaxes(title_text="φ(n)  (h)", row=1, col=2)

    # ── Title with metrics ──────────────────────────────────────────
    aic_str = "  ".join(f"{k}={v:.1f}" for k, v in result.aic_all.items())
    title = (
        f"<b>Prediction test — {label}</b><br>"
        f"<sub>fit {result.fit_start} → {result.fit_end}  "
        f"({result.n_fit} nights, model <b>{best}</b>, R²={result.r2_in_sample:.2f}, "
        f"std={result.std_in_sample_h:.2f}h)  ·  "
        f"predict {result.pred_start} → {result.pred_end}  "
        f"({result.n_pred} nights, MAE={result.mae_h:.2f}h, "
        f"RMSE={result.rmse_h:.2f}h, bias={result.bias_h:+.2f}h)<br>"
        f"AIC: {aic_str}</sub>"
    )
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left"),
        template="plotly_white",
        width=1500, height=720,
        margin=dict(t=110, l=70, r=30, b=70),
        legend=dict(orientation="h", y=-0.12, yanchor="top",
                    x=0.5, xanchor="center"),
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn")


def parse_windows(spec: str) -> list[tuple[str, date_, date_]]:
    """Parse 'label1=YYYY-MM-DD:YYYY-MM-DD,label2=...' (same syntax as fit.parse_periods)."""
    out = []
    for chunk in spec.split(","):
        if "=" not in chunk:
            continue
        lbl, dates = chunk.split("=", 1)
        s, e = dates.split(":")
        out.append((lbl.strip(),
                    date_.fromisoformat(s.strip()),
                    date_.fromisoformat(e.strip())))
    return out


# Module-level handle so render_prediction can read raw sleep parquet without
# threading the path through every signature
sleep_path_global: list[Path] = [Path()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject-id", default="S001")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--timezone", default="Europe/Paris")
    ap.add_argument("--windows", required=True,
                    help='"label1=YYYY-MM-DD:YYYY-MM-DD,..." (fit windows)')
    ap.add_argument("--horizon", type=int, default=10,
                    help="number of nights to project forward (default: 10)")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    data_dir = args.data_dir or (ROOT / "data" / "personal" / args.subject_id)
    sleep_path = data_dir / "sleep_intervals.parquet"
    sleep_path_global[0] = sleep_path
    out_dir = args.out_dir or (data_dir / "oscillator_explore")
    out_dir.mkdir(parents=True, exist_ok=True)

    windows = parse_windows(args.windows)
    all_results: list[PredictionResult] = []

    for label, fit_start, fit_end in windows:
        print(f"[predict] {label}  fit {fit_start} → {fit_end}  horizon={args.horizon}…")
        try:
            result, extras = predict_window(
                sleep_path, args.timezone, label, fit_start, fit_end, args.horizon,
            )
        except ValueError as e:
            print(f"  ⚠  {e}")
            continue

        all_results.append(result)
        render_prediction(
            label, extras["series_fit"], extras["series_val"], result,
            extras["fits"], args.timezone,
            out_dir / f"prediction_{label}.html",
        )

    (out_dir / "prediction_summary.json").write_text(
        json.dumps([asdict(r) for r in all_results], indent=2)
    )

    print("\n=== Prediction summary ===")
    print(f"{'label':<12s} {'n_fit':>5s} {'best':>5s} {'R²_in':>6s} "
          f"{'std_in':>7s} {'n_pred':>6s} {'MAE':>6s} {'RMSE':>6s} {'bias':>7s}")
    for r in all_results:
        print(f"{r.label:<12s} {r.n_fit:>5d} {r.best_model:>5s} "
              f"{r.r2_in_sample:>6.2f} {r.std_in_sample_h:>6.2f}h "
              f"{r.n_pred:>6d} {r.mae_h:>5.2f}h {r.rmse_h:>5.2f}h "
              f"{r.bias_h:>+6.2f}h")
    print(f"\nFigures + summary → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
