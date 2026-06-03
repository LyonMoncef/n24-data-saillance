#!/usr/bin/env python3
"""Exploratory fit of the oscillator-on-drift phase model on real N24 data.

Models fitted
-------------
    L     φ(n) = α·n + β
    O₁    φ(n) = α·n + β + A·sin(2π·n/P + ψ)
    O₂    φ(n) = α·n + β + A₁·sin(2π·n/P₁ + ψ₁) + A₂·sin(2π·n/P₂ + ψ₂)
    W     φ(n) = α·n + β + ΔW · I_weekend(n)
    C     L + O₁ + W (combined)

where φ(n) is the sleep-onset deviation (hours) from a perfect 24h schedule
at day index n, α = τ − 24, P period in days, A amplitude in hours, ψ phase.

P determination
---------------
Period seeding uses **Lomb-Scargle periodogram** on the linear-residuals at
the actual night indices (handles missing nights natively — no interpolation
required, unlike FFT). Top-k peaks are reported. For O₂ we seed (P₁, P₂)
from the top-2 LS peaks ordered by period (P₁ < P₂).

Model selection
---------------
For each window we report **AIC** and **BIC** alongside R² and residual std.
AIC = n·ln(SSR/n) + 2k, BIC = n·ln(SSR/n) + k·ln(n). Lower is better.
The "winner" model is annotated in the summary.

Pipeline
--------
1. Load sleep_intervals.parquet → per-night main_onset via
   :func:`n24sal.sleep.per_night.main_sleep_per_night`.
2. Anchor : φ(n) = ((onset − anchor).total_seconds() / 3600) − 24 · n
   where n = (onset.date() − window_start).days, anchor = noon of window start.
3. Linear regression → (α₀, β₀, R²_lin, residuals_lin).
4. Lomb-Scargle on residuals_lin → top-3 (period, amplitude) peaks.
5. NLS (curve_fit) for O₁, O₂, W, C — bounded, multi-start where useful.
6. Plot : scatter φ(n) + fits, residuals comparison, LS periodogram top-3.

Usage
-----
::

    .venv/bin/python tools/oscillator_explore/fit.py \\
        --subject-id S001 --periods 2025-04-06:2025-07-29

Multiple periods : comma-separate.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import date as date_, datetime, time as time_
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import lombscargle
from scipy.stats import linregress

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from n24sal.sleep.per_night import main_sleep_per_night  # noqa: E402

# Local import: sleep_debt lives in the same directory
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sleep_debt import compute_debt  # noqa: E402


@dataclass
class FitResult:
    period_label: str
    start: str
    end: str
    n_nights_used: int
    n_nights_window: int
    tau_linear_h: float
    alpha_linear_h_per_day: float
    r2_linear: float
    residual_std_linear_h: float
    tau_full_h: float
    alpha_full_h_per_day: float
    amplitude_h: float
    period_days: float
    phase_rad: float
    r2_full: float
    residual_std_full_h: float
    delta_r2: float
    fft_dominant_period_days: float
    fft_dominant_amplitude_h: float
    # Top 3 FFT peaks (period_days, amplitude_h)
    fft_top_periods_days: list[float]
    fft_top_amplitudes_h: list[float]
    # Weekly model: φ(n) = α·n + β + ΔW · I_weekend(n)
    tau_weekly_h: float
    weekend_offset_h: float
    r2_weekly: float
    residual_std_weekly_h: float
    # Combined: φ(n) = α·n + β + A sin(2π n / P + ψ) + ΔW · I_weekend(n)
    tau_combined_h: float
    amplitude_combined_h: float
    period_combined_days: float
    weekend_offset_combined_h: float
    r2_combined: float
    residual_std_combined_h: float
    # Double sinusoid: φ(n) = α·n + β + A1·sin(2π·n/P1+ψ1) + A2·sin(2π·n/P2+ψ2)
    tau_double_h: float
    amplitude_double_short_h: float
    period_double_short_days: float
    phase_double_short_rad: float
    amplitude_double_long_h: float
    period_double_long_days: float
    phase_double_long_rad: float
    r2_double: float
    residual_std_double_h: float
    # Debt-oscillator (model E):
    #   φ(n) = α·n + β + A·sin(2π·n/P + ψ) + κ·D(n)
    # where D is the leaky debt computed on the full chronology (γ fixed,
    # T★ fixed). κ has units h/h (phase shift per hour of accumulated debt).
    t_star_h: float
    gamma_debt: float
    tau_debt_h: float
    amplitude_debt_h: float
    period_debt_days: float
    phase_debt_rad: float
    kappa_debt: float
    r2_debt: float
    residual_std_debt_h: float
    # AIC / BIC per model (lower is better)
    aic_linear: float
    bic_linear: float
    aic_oscillator: float
    bic_oscillator: float
    aic_weekly: float
    bic_weekly: float
    aic_combined: float
    bic_combined: float
    aic_double: float
    bic_double: float
    aic_debt: float
    bic_debt: float
    best_model_aic: str
    best_model_bic: str


def load_phase_series(
    sleep_intervals_path: Path,
    timezone: str,
    start: date_,
    end: date_,
    *,
    t_star_h: float | None = None,
    gamma_debt: float = 0.85,
    min_duration_h: float = 2.0,
    max_duration_h: float = 24.0,
) -> pd.DataFrame:
    """Return DataFrame indexed by night date with phase + (optional) debt columns.

    Columns :
        n              calendar-day index since ``start`` (integer, may have gaps)
        phi_h          onset deviation from 24h schedule, anchored at noon of ``start``
        main_onset     tz-aware onset Timestamp
        tst_h          total sleep time (incl. naps) — passed through from per-night
        debt_before_h  D at bedtime of the night (only if ``t_star_h`` provided)
        debt_after_h   D after the night (only if ``t_star_h`` provided)

    When ``t_star_h`` is given, the leaky debt ``D(n)`` is computed on the
    **full chronology** of the sleep record (so the window inherits the
    accumulated debt from prior history), then sliced to ``[start, end]``.
    Outliers outside ``[min_duration_h, max_duration_h]`` (on main_duration_h)
    are dropped first so the debt accumulator isn't poisoned by Samsung
    artefacts.
    """
    df = pd.read_parquet(sleep_intervals_path)
    nights = main_sleep_per_night(df, timezone=timezone)
    if nights.empty:
        return pd.DataFrame(columns=["n", "phi_h", "main_onset", "tst_h"])

    # Apply duration filter on the whole chronology before any window slicing
    nights = nights[
        (nights["main_duration_h"] >= min_duration_h)
        & (nights["main_duration_h"] <= max_duration_h)
    ]

    # Optionally compute leaky debt on the FULL filtered chronology
    if t_star_h is not None:
        nights = compute_debt(nights, t_star_h, gamma=gamma_debt, floor_at_zero=False)

    nights = nights[(nights.index >= start) & (nights.index <= end)].copy()
    if nights.empty:
        cols = ["n", "phi_h", "main_onset", "tst_h"]
        if t_star_h is not None:
            cols += ["debt_before_h", "debt_after_h"]
        return pd.DataFrame(columns=cols)

    anchor = pd.Timestamp(datetime.combine(start, time_(12, 0)), tz=timezone)
    onsets = nights["main_onset"].dt.tz_convert(timezone)
    delta_h = (onsets - anchor).dt.total_seconds() / 3600.0
    n = np.array([(d - start).days for d in nights.index], dtype=float)
    phi_h = delta_h.to_numpy() - 24.0 * n

    data = {
        "n": n, "phi_h": phi_h,
        "main_onset": onsets.to_numpy(),
        "tst_h": nights["tst_h"].to_numpy(),
    }
    if t_star_h is not None:
        data["debt_before_h"] = nights["debt_before_h"].to_numpy()
        data["debt_after_h"] = nights["debt_after_h"].to_numpy()
    return pd.DataFrame(data, index=nights.index)


def fit_linear(n: np.ndarray, phi: np.ndarray) -> tuple[float, float, float, np.ndarray]:
    """Return (alpha, beta, r_squared, residuals)."""
    res = linregress(n, phi)
    pred = res.slope * n + res.intercept
    return float(res.slope), float(res.intercept), float(res.rvalue**2), phi - pred


def fft_seed_period(residuals: np.ndarray, n: np.ndarray) -> tuple[float, float]:
    """Dominant period (days) + amplitude (h) — kept for backward compat."""
    periods, amps, _ = lomb_scargle_top_peaks(residuals, n, k=1)
    return (periods[0] if periods else float("nan"), amps[0] if amps else float("nan"))


def lomb_scargle_periodogram(
    residuals: np.ndarray, n: np.ndarray, P_min: float = 1.8, P_max: float | None = None,
    n_freqs: int = 800,
) -> tuple[np.ndarray, np.ndarray]:
    """Lomb-Scargle on (n, residuals), no interpolation. Handles missing nights.

    Returns (periods_days, amplitude_h).

    Conversion : the scipy ``lombscargle`` output is a power spectral density;
    we convert to **amplitude in hours** via the standard relation
    ``A = sqrt(4·P_LS / N_eff)``, which matches the FFT-amplitude convention
    used elsewhere in this script. This is accurate for a single sinusoid in
    Gaussian noise.
    """
    if len(residuals) < 6:
        return np.array([]), np.array([])
    if P_max is None:
        P_max = max((n.max() - n.min()) / 2.0, P_min + 1.0)
    P_max = max(P_max, P_min + 0.5)
    # log-spaced periods → uniform in frequency in log scale
    periods = np.geomspace(P_min, P_max, n_freqs)
    angular = 2.0 * np.pi / periods  # rad/day
    y = residuals - residuals.mean()
    try:
        power = lombscargle(n.astype(float), y, angular, normalize=False)
    except Exception:
        return np.array([]), np.array([])
    # scipy returns SSE-like power; convert to amplitude (h)
    n_eff = len(y)
    amp = np.sqrt(np.maximum(4.0 * power / n_eff, 0.0))
    return periods, amp


def lomb_scargle_top_peaks(
    residuals: np.ndarray, n: np.ndarray, k: int = 3,
    P_min: float = 1.8, P_max: float | None = None,
) -> tuple[list[float], list[float], np.ndarray]:
    """Top-``k`` (period_days, amplitude_h) peaks from Lomb-Scargle, plus full spectrum.

    Peak picking is **local-maximum based** in log-period space, then sorted by
    amplitude. Returns ([], [], spectrum) if too few data points.
    """
    periods, amp = lomb_scargle_periodogram(residuals, n, P_min=P_min, P_max=P_max)
    if len(periods) == 0:
        return [], [], np.array([])
    # Local maxima
    is_peak = np.zeros_like(amp, dtype=bool)
    is_peak[1:-1] = (amp[1:-1] > amp[:-2]) & (amp[1:-1] > amp[2:])
    if not is_peak.any():
        # fallback : argmax
        idx = int(np.argmax(amp))
        return [float(periods[idx])], [float(amp[idx])], np.column_stack([periods, amp])
    peak_idx = np.where(is_peak)[0]
    sorted_by_amp = peak_idx[np.argsort(amp[peak_idx])[::-1]]
    top = sorted_by_amp[:k]
    return (
        [float(periods[i]) for i in top],
        [float(amp[i]) for i in top],
        np.column_stack([periods, amp]),
    )


# Backwards-compat alias used by plotting code
def fft_top_peaks(
    residuals: np.ndarray, n: np.ndarray, k: int = 3
) -> tuple[list[float], list[float]]:
    """Backwards-compat: returns (periods, amps) using Lomb-Scargle internally."""
    p, a, _ = lomb_scargle_top_peaks(residuals, n, k=k)
    return p, a


def weekend_indicator(nights_index: pd.DatetimeIndex | list) -> np.ndarray:
    """1.0 if night.weekday() ∈ {Fri, Sat} (the "weekend onset" — Fri & Sat nights), else 0."""
    out = np.zeros(len(nights_index), dtype=float)
    for i, d in enumerate(nights_index):
        # d is the morning date ; "weekend night" = night BEFORE Sat or Sun
        # i.e. morning Sat (weekday=5) or morning Sun (weekday=6)
        wd = d.weekday() if hasattr(d, "weekday") else pd.Timestamp(d).weekday()
        out[i] = 1.0 if wd in (5, 6) else 0.0
    return out


def fit_weekly(
    n: np.ndarray, phi: np.ndarray, weekend: np.ndarray
) -> tuple[float, float, float, float, np.ndarray]:
    """OLS fit of φ(n) = α·n + β + ΔW · weekend(n).

    Returns (alpha, beta, delta_w, r_squared, residuals).
    """
    X = np.column_stack([n, np.ones_like(n), weekend])
    coef, *_ = np.linalg.lstsq(X, phi, rcond=None)
    alpha, beta, dw = coef
    pred = X @ coef
    resid = phi - pred
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((phi - phi.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(alpha), float(beta), float(dw), r2, resid


def double_oscillator_model(n, alpha, beta, A1, P1, psi1, A2, P2, psi2):
    return (alpha * n + beta
            + A1 * np.sin(2 * np.pi * n / P1 + psi1)
            + A2 * np.sin(2 * np.pi * n / P2 + psi2))


def fit_double_oscillator(
    n: np.ndarray, phi: np.ndarray,
    alpha0: float, beta0: float,
    P1_0: float, A1_0: float,
    P2_0: float, A2_0: float,
) -> tuple[dict, np.ndarray] | None:
    """NLS for the 2-sinusoid model. Enforces P1 < P2 via ordered bounds."""
    window = float(n.max() - n.min())
    if not np.isfinite(P1_0) or P1_0 <= 1.0:
        P1_0 = 3.0
    if not np.isfinite(P2_0) or P2_0 <= 1.0:
        P2_0 = 10.0
    # Ensure P1_0 < P2_0
    if P1_0 > P2_0:
        P1_0, P2_0 = P2_0, P1_0
        A1_0, A2_0 = A2_0, A1_0
    if not np.isfinite(A1_0) or A1_0 <= 0:
        A1_0 = 0.5
    if not np.isfinite(A2_0) or A2_0 <= 0:
        A2_0 = 0.5
    # Separate the two bands so the optimizer doesn't collapse P1 = P2
    P1_hi = max(min(window / 3.0, 10.0), P1_0 + 0.5)
    P2_lo = max(P1_hi, P2_0 - 0.5)
    P2_hi = max(window / 2.0, P2_lo + 1.0)
    P1_0 = float(np.clip(P1_0, 1.8, P1_hi - 0.1))
    P2_0 = float(np.clip(P2_0, P2_lo + 0.1, P2_hi - 0.1))
    p0 = [alpha0, beta0, A1_0, P1_0, 0.0, A2_0, P2_0, 0.0]
    bounds = (
        [-5.0, -100.0, 0.0, 1.8, -2 * np.pi, 0.0, P2_lo, -2 * np.pi],
        [5.0, 1000.0, 24.0, P1_hi, 2 * np.pi, 24.0, P2_hi, 2 * np.pi],
    )
    try:
        popt, _ = curve_fit(double_oscillator_model, n, phi, p0=p0, bounds=bounds, maxfev=12000)
    except (RuntimeError, ValueError):
        return None
    alpha, beta, A1, P1, psi1, A2, P2, psi2 = popt
    pred = double_oscillator_model(n, *popt)
    return (
        {"alpha": float(alpha), "beta": float(beta),
         "A1": float(A1), "P1": float(P1), "psi1": float(psi1),
         "A2": float(A2), "P2": float(P2), "psi2": float(psi2)},
        phi - pred,
    )


def aic_bic(n_data: int, ssr: float, n_params: int) -> tuple[float, float]:
    """Gaussian-residuals AIC / BIC. Returns (NaN, NaN) for degenerate inputs."""
    if n_data <= 0 or ssr <= 0 or n_params <= 0:
        return float("nan"), float("nan")
    log_ssr_n = float(np.log(ssr / n_data))
    aic = n_data * log_ssr_n + 2.0 * n_params
    bic = n_data * log_ssr_n + n_params * float(np.log(n_data))
    return aic, bic


def combined_model(n_and_weekend, alpha, beta, A, P, psi, dw):
    n, weekend = n_and_weekend
    return alpha * n + beta + A * np.sin(2 * np.pi * n / P + psi) + dw * weekend


def fit_combined(
    n: np.ndarray, phi: np.ndarray, weekend: np.ndarray,
    alpha0: float, beta0: float, P0: float, A0: float, dw0: float,
) -> tuple[dict, np.ndarray] | None:
    """NLS for φ(n) = α·n + β + A·sin(2πn/P + ψ) + ΔW·weekend(n)."""
    if not np.isfinite(P0) or P0 <= 1.0:
        P0 = 7.0
    if not np.isfinite(A0) or A0 <= 0:
        A0 = 0.5
    p0 = [alpha0, beta0, A0, P0, 0.0, dw0]
    window = float(n.max() - n.min())
    bounds = (
        [-5.0, -100.0, 0.0, 1.5, -2 * np.pi, -10.0],
        [5.0, 1000.0, 24.0, max(window / 2, 3.0), 2 * np.pi, 10.0],
    )
    try:
        popt, _ = curve_fit(combined_model, (n, weekend), phi, p0=p0, bounds=bounds, maxfev=8000)
    except (RuntimeError, ValueError):
        return None
    alpha, beta, A, P, psi, dw = popt
    pred = combined_model((n, weekend), *popt)
    return (
        {"alpha": float(alpha), "beta": float(beta), "A": float(A),
         "P": float(P), "psi": float(psi), "dw": float(dw)},
        phi - pred,
    )


def oscillator_model(n, alpha, beta, A, P, psi):
    return alpha * n + beta + A * np.sin(2.0 * np.pi * n / P + psi)


def fit_oscillator(
    n: np.ndarray,
    phi: np.ndarray,
    alpha0: float,
    beta0: float,
    P0: float,
    A0: float,
) -> tuple[dict, np.ndarray] | None:
    """NLS around oscillator_model. Returns (params_dict, residuals) or None on failure."""
    if not np.isfinite(P0) or P0 <= 1.0:
        P0 = 7.0
    if not np.isfinite(A0) or A0 <= 0:
        A0 = max(np.std(phi - (alpha0 * n + beta0)), 0.1)
    p0 = [alpha0, beta0, A0, P0, 0.0]
    window = float(n.max() - n.min())
    bounds = (
        [-5.0, -100.0, 0.0, 1.5, -2 * np.pi],
        [5.0, 1000.0, 24.0, max(window / 2, 3.0), 2 * np.pi],
    )
    try:
        popt, _ = curve_fit(oscillator_model, n, phi, p0=p0, bounds=bounds, maxfev=5000)
    except (RuntimeError, ValueError):
        return None
    alpha, beta, A, P, psi = popt
    pred = oscillator_model(n, *popt)
    resid = phi - pred
    return (
        {"alpha": float(alpha), "beta": float(beta), "A": float(A), "P": float(P), "psi": float(psi)},
        resid,
    )


def fit_debt_oscillator(
    n: np.ndarray,
    phi: np.ndarray,
    D: np.ndarray,
    alpha0: float,
    beta0: float,
    P0: float,
    A0: float,
) -> tuple[dict, np.ndarray] | None:
    """NLS for **model E** : φ(n) = α·n + β + A·sin(2π·n/P + ψ) + κ·D(n).

    ``D`` must be the per-night debt **at bedtime** (debt_before_h), same
    length as ``n`` and ``phi``. κ is unconstrained in sign — we expect κ < 0
    (more accumulated debt → earlier onset = lower φ).
    """
    if not np.isfinite(P0) or P0 <= 1.0:
        P0 = 7.0
    if not np.isfinite(A0) or A0 <= 0:
        A0 = max(np.std(phi - (alpha0 * n + beta0)), 0.1)
    window = float(n.max() - n.min())

    def model(n_, alpha, beta, A, P, psi, kappa):
        return (alpha * n_ + beta
                + A * np.sin(2.0 * np.pi * n_ / P + psi)
                + kappa * D)

    p0 = [alpha0, beta0, A0, P0, 0.0, 0.0]
    bounds = (
        [-5.0, -100.0, 0.0, 1.5, -2 * np.pi, -5.0],
        [5.0, 1000.0, 24.0, max(window / 2, 3.0), 2 * np.pi, 5.0],
    )
    try:
        popt, _ = curve_fit(model, n, phi, p0=p0, bounds=bounds, maxfev=8000)
    except (RuntimeError, ValueError):
        return None
    alpha, beta, A, P, psi, kappa = popt
    pred = model(n, *popt)
    return (
        {"alpha": float(alpha), "beta": float(beta), "A": float(A),
         "P": float(P), "psi": float(psi), "kappa": float(kappa)},
        phi - pred,
    )


def r2_of(phi: np.ndarray, resid: np.ndarray) -> float:
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((phi - phi.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def _nan_fit(label, start, end, n_used, n_window, t_star_h=float("nan"), gamma_debt=float("nan")):
    nan = float("nan")
    return FitResult(
        period_label=label, start=start.isoformat(), end=end.isoformat(),
        n_nights_used=n_used, n_nights_window=n_window,
        tau_linear_h=nan, alpha_linear_h_per_day=nan, r2_linear=nan, residual_std_linear_h=nan,
        tau_full_h=nan, alpha_full_h_per_day=nan, amplitude_h=nan, period_days=nan, phase_rad=nan,
        r2_full=nan, residual_std_full_h=nan, delta_r2=nan,
        fft_dominant_period_days=nan, fft_dominant_amplitude_h=nan,
        fft_top_periods_days=[], fft_top_amplitudes_h=[],
        tau_weekly_h=nan, weekend_offset_h=nan, r2_weekly=nan, residual_std_weekly_h=nan,
        tau_combined_h=nan, amplitude_combined_h=nan, period_combined_days=nan,
        weekend_offset_combined_h=nan, r2_combined=nan, residual_std_combined_h=nan,
        tau_double_h=nan,
        amplitude_double_short_h=nan, period_double_short_days=nan, phase_double_short_rad=nan,
        amplitude_double_long_h=nan, period_double_long_days=nan, phase_double_long_rad=nan,
        r2_double=nan, residual_std_double_h=nan,
        t_star_h=t_star_h, gamma_debt=gamma_debt,
        tau_debt_h=nan, amplitude_debt_h=nan, period_debt_days=nan,
        phase_debt_rad=nan, kappa_debt=nan, r2_debt=nan, residual_std_debt_h=nan,
        aic_linear=nan, bic_linear=nan,
        aic_oscillator=nan, bic_oscillator=nan,
        aic_weekly=nan, bic_weekly=nan,
        aic_combined=nan, bic_combined=nan,
        aic_double=nan, bic_double=nan,
        aic_debt=nan, bic_debt=nan,
        best_model_aic="?", best_model_bic="?",
    )


def fit_window(
    sleep_path: Path,
    timezone: str,
    label: str,
    start: date_,
    end: date_,
    *,
    t_star_h: float = 8.99,
    gamma_debt: float = 0.85,
) -> tuple[FitResult, pd.DataFrame]:
    series = load_phase_series(
        sleep_path, timezone, start, end,
        t_star_h=t_star_h, gamma_debt=gamma_debt,
    )
    n_window = (end - start).days + 1
    if len(series) < 5:
        return _nan_fit(label, start, end, len(series), n_window, t_star_h, gamma_debt), series

    n = series["n"].to_numpy()
    phi = series["phi_h"].to_numpy()
    weekend = weekend_indicator(series.index)

    # 1) Linear baseline
    alpha0, beta0, r2_lin, resid_lin = fit_linear(n, phi)

    # 2) LS seed + oscillator-only fit
    top_P, top_A = fft_top_peaks(resid_lin, n, k=3)
    P_fft = top_P[0] if top_P else float("nan")
    A_fft = top_A[0] if top_A else float("nan")
    osc = fit_oscillator(n, phi, alpha0, beta0, P_fft, A_fft)
    if osc is None:
        tau_full = alpha_full = A_full = P_full = psi_full = float("nan")
        r2_full = std_full = float("nan")
        resid_full = None
    else:
        params, resid_full = osc
        tau_full = 24.0 + params["alpha"]; alpha_full = params["alpha"]
        A_full = params["A"]; P_full = params["P"]; psi_full = params["psi"]
        r2_full = r2_of(phi, resid_full); std_full = float(np.std(resid_full))

    # 3) Weekly model (Fri/Sat → Sat/Sun mornings)
    alpha_w, beta_w, dw, r2_w, resid_w = fit_weekly(n, phi, weekend)

    # 4) Combined oscillator + weekly
    comb = fit_combined(n, phi, weekend, alpha0, beta0, P_fft, A_fft, dw)
    if comb is None:
        tau_c = A_c = P_c = dw_c = r2_c = std_c = float("nan")
        resid_c = None
    else:
        params_c, resid_c = comb
        tau_c = 24.0 + params_c["alpha"]
        A_c = params_c["A"]; P_c = params_c["P"]; dw_c = params_c["dw"]
        r2_c = r2_of(phi, resid_c); std_c = float(np.std(resid_c))

    # 5) Double sinusoid : seeded by top-2 LS peaks ordered by period
    # Find a short (P1) and long (P2) seed from the top peaks
    P1_seed = P2_seed = float("nan"); A1_seed = A2_seed = float("nan")
    if len(top_P) >= 2:
        ordered = sorted(zip(top_P, top_A), key=lambda x: x[0])
        P1_seed, A1_seed = ordered[0]
        P2_seed, A2_seed = ordered[-1]
    elif len(top_P) == 1:
        P1_seed, A1_seed = top_P[0], top_A[0]
        P2_seed, A2_seed = max(2 * P1_seed, 7.0), A1_seed / 2.0
    dbl = fit_double_oscillator(n, phi, alpha0, beta0,
                                P1_seed, A1_seed, P2_seed, A2_seed)
    if dbl is None:
        tau_d = float("nan"); A1d = P1d = psi1d = float("nan")
        A2d = P2d = psi2d = float("nan")
        r2_d = std_d = float("nan"); resid_d = None
    else:
        params_d, resid_d = dbl
        tau_d = 24.0 + params_d["alpha"]
        A1d = params_d["A1"]; P1d = params_d["P1"]; psi1d = params_d["psi1"]
        A2d = params_d["A2"]; P2d = params_d["P2"]; psi2d = params_d["psi2"]
        # Re-order so that short period comes first
        if P1d > P2d:
            P1d, P2d = P2d, P1d
            A1d, A2d = A2d, A1d
            psi1d, psi2d = psi2d, psi1d
        r2_d = r2_of(phi, resid_d); std_d = float(np.std(resid_d))

    # 6) Debt-oscillator (model E) : φ = α·n + β + A·sin(2π·n/P + ψ) + κ·D(n)
    if "debt_before_h" in series.columns:
        D = series["debt_before_h"].to_numpy()
        deb = fit_debt_oscillator(n, phi, D, alpha0, beta0, P_fft, A_fft)
    else:
        deb = None
    if deb is None:
        tau_e = A_e = P_e = psi_e = kappa_e = float("nan")
        r2_e = std_e = float("nan"); resid_e = None
    else:
        params_e, resid_e = deb
        tau_e = 24.0 + params_e["alpha"]
        A_e = params_e["A"]; P_e = params_e["P"]; psi_e = params_e["psi"]
        kappa_e = params_e["kappa"]
        r2_e = r2_of(phi, resid_e); std_e = float(np.std(resid_e))

    # 7) AIC / BIC per model
    n_data = len(phi)
    def ssr(r):
        return float(np.sum(r ** 2)) if r is not None else float("nan")
    aic_l, bic_l = aic_bic(n_data, ssr(resid_lin), 2)     # α, β
    aic_o, bic_o = aic_bic(n_data, ssr(resid_full), 5)    # α, β, A, P, ψ
    aic_w, bic_w = aic_bic(n_data, ssr(resid_w), 3)       # α, β, ΔW
    aic_c, bic_c = aic_bic(n_data, ssr(resid_c), 6)       # α, β, A, P, ψ, ΔW
    aic_d, bic_d = aic_bic(n_data, ssr(resid_d), 8)       # α, β, A1, P1, ψ1, A2, P2, ψ2
    aic_e, bic_e = aic_bic(n_data, ssr(resid_e), 6)       # α, β, A, P, ψ, κ

    candidates_aic = {
        "linear": aic_l, "oscillator": aic_o, "weekly": aic_w,
        "combined": aic_c, "double": aic_d, "debt": aic_e,
    }
    candidates_bic = {
        "linear": bic_l, "oscillator": bic_o, "weekly": bic_w,
        "combined": bic_c, "double": bic_d, "debt": bic_e,
    }
    finite_aic = {k: v for k, v in candidates_aic.items() if np.isfinite(v)}
    finite_bic = {k: v for k, v in candidates_bic.items() if np.isfinite(v)}
    best_aic = min(finite_aic, key=finite_aic.get) if finite_aic else "?"
    best_bic = min(finite_bic, key=finite_bic.get) if finite_bic else "?"

    return (
        FitResult(
            period_label=label, start=start.isoformat(), end=end.isoformat(),
            n_nights_used=len(series), n_nights_window=n_window,
            tau_linear_h=24.0 + alpha0, alpha_linear_h_per_day=alpha0,
            r2_linear=r2_lin, residual_std_linear_h=float(np.std(resid_lin)),
            tau_full_h=tau_full, alpha_full_h_per_day=alpha_full,
            amplitude_h=A_full, period_days=P_full, phase_rad=psi_full,
            r2_full=r2_full, residual_std_full_h=std_full,
            delta_r2=(r2_full - r2_lin) if np.isfinite(r2_full) else float("nan"),
            fft_dominant_period_days=P_fft, fft_dominant_amplitude_h=A_fft,
            fft_top_periods_days=top_P, fft_top_amplitudes_h=top_A,
            tau_weekly_h=24.0 + alpha_w, weekend_offset_h=dw,
            r2_weekly=r2_w, residual_std_weekly_h=float(np.std(resid_w)),
            tau_combined_h=tau_c, amplitude_combined_h=A_c, period_combined_days=P_c,
            weekend_offset_combined_h=dw_c, r2_combined=r2_c,
            residual_std_combined_h=std_c,
            tau_double_h=tau_d,
            amplitude_double_short_h=A1d, period_double_short_days=P1d, phase_double_short_rad=psi1d,
            amplitude_double_long_h=A2d, period_double_long_days=P2d, phase_double_long_rad=psi2d,
            r2_double=r2_d, residual_std_double_h=std_d,
            t_star_h=t_star_h, gamma_debt=gamma_debt,
            tau_debt_h=tau_e, amplitude_debt_h=A_e, period_debt_days=P_e,
            phase_debt_rad=psi_e, kappa_debt=kappa_e,
            r2_debt=r2_e, residual_std_debt_h=std_e,
            aic_linear=aic_l, bic_linear=bic_l,
            aic_oscillator=aic_o, bic_oscillator=bic_o,
            aic_weekly=aic_w, bic_weekly=bic_w,
            aic_combined=aic_c, bic_combined=bic_c,
            aic_double=aic_d, bic_double=bic_d,
            aic_debt=aic_e, bic_debt=bic_e,
            best_model_aic=best_aic, best_model_bic=best_bic,
        ),
        series,
    )


def plot_window(label: str, series: pd.DataFrame, fit: FitResult, out_path: Path) -> None:
    """4-panel plotly figure : φ(n) + fits, residuals (lin), residual FFT, day-to-day Δφ."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    TEAL, AMBER, CYAN = "#0e9eb0", "#d37c04", "#3be5e7"

    n = series["n"].to_numpy()
    phi = series["phi_h"].to_numpy()
    weekend = weekend_indicator(series.index)
    n_smooth = np.linspace(n.min(), n.max(), 400)
    # For smooth weekend overlay : interpolate weekend indicator (0 or 1) at integer days
    grid = np.arange(int(n.min()), int(n.max()) + 1)
    we_dates = [series.index.min() + pd.Timedelta(days=int(g - n.min())) for g in grid]
    we_grid = weekend_indicator(pd.DatetimeIndex(we_dates))

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            f"φ(n) + fits  ({fit.n_nights_used}/{fit.n_nights_window} nights)  "
            f"·  AIC winner = <b>{fit.best_model_aic}</b>  ·  BIC winner = <b>{fit.best_model_bic}</b>",
            f"residuals comparison  (σ_lin={fit.residual_std_linear_h:.2f}h)",
            "Lomb-Scargle periodogram of linear residuals (top-3 peaks, log P axis)",
            "Night-to-night Δφ (instantaneous τ−24 proxy)",
        ),
        horizontal_spacing=0.10, vertical_spacing=0.14,
    )

    # ── Panel 1 : phase + fits ────────────────────────────────────────────
    fig.add_trace(
        go.Scatter(x=n, y=phi, mode="markers", marker=dict(color=TEAL, size=7),
                   name="onset φ(n)"),
        row=1, col=1,
    )
    if np.isfinite(fit.alpha_linear_h_per_day):
        beta_lin = phi.mean() - fit.alpha_linear_h_per_day * n.mean()
        y_lin = fit.alpha_linear_h_per_day * n_smooth + beta_lin
        fig.add_trace(
            go.Scatter(x=n_smooth, y=y_lin, mode="lines",
                       line=dict(color=AMBER, dash="dash"),
                       name=f"linear  τ={fit.tau_linear_h:.3f}h  R²={fit.r2_linear:.2f}"),
            row=1, col=1,
        )
    if np.isfinite(fit.amplitude_h):
        beta_full = phi.mean() - fit.alpha_full_h_per_day * n.mean() - np.mean(
            fit.amplitude_h * np.sin(2 * np.pi * n / fit.period_days + fit.phase_rad)
        )
        y_full = oscillator_model(n_smooth, fit.alpha_full_h_per_day, beta_full,
                                  fit.amplitude_h, fit.period_days, fit.phase_rad)
        fig.add_trace(
            go.Scatter(x=n_smooth, y=y_full, mode="lines",
                       line=dict(color=CYAN, width=2),
                       name=f"linear+sin  τ={fit.tau_full_h:.3f}h  A={fit.amplitude_h:.2f}h  P={fit.period_days:.1f}d  R²={fit.r2_full:.2f}"),
            row=1, col=1,
        )
    if np.isfinite(fit.weekend_offset_h):
        alpha_w = fit.tau_weekly_h - 24.0
        beta_w = phi.mean() - alpha_w * n.mean() - fit.weekend_offset_h * weekend.mean()
        y_w_grid = alpha_w * grid + beta_w + fit.weekend_offset_h * we_grid
        fig.add_trace(
            go.Scatter(x=grid, y=y_w_grid, mode="lines",
                       line=dict(color="#7c5cff", width=1.5, dash="dot"),
                       name=f"linear+weekly  τ={fit.tau_weekly_h:.3f}h  ΔW={fit.weekend_offset_h:+.2f}h  R²={fit.r2_weekly:.2f}"),
            row=1, col=1,
        )
    if np.isfinite(fit.r2_combined):
        alpha_c = fit.tau_combined_h - 24.0
        beta_c = (phi.mean() - alpha_c * n.mean()
                  - np.mean(fit.amplitude_combined_h * np.sin(2 * np.pi * n / fit.period_combined_days))
                  - fit.weekend_offset_combined_h * weekend.mean())
        y_c_grid = (alpha_c * grid + beta_c
                    + fit.amplitude_combined_h * np.sin(2 * np.pi * grid / fit.period_combined_days)
                    + fit.weekend_offset_combined_h * we_grid)
        fig.add_trace(
            go.Scatter(x=grid, y=y_c_grid, mode="lines",
                       line=dict(color="#1d8a4a", width=1.5),
                       name=f"linear+sin+weekly  τ={fit.tau_combined_h:.3f}h  A={fit.amplitude_combined_h:.2f}h  P={fit.period_combined_days:.1f}d  ΔW={fit.weekend_offset_combined_h:+.2f}h  R²={fit.r2_combined:.2f}"),
            row=1, col=1,
        )
    # Debt-oscillator (model E) — needs the per-night debt vector
    if np.isfinite(fit.r2_debt) and "debt_before_h" in series.columns:
        alpha_e = fit.tau_debt_h - 24.0
        D_at_n = series["debt_before_h"].to_numpy()
        sin_at_n = fit.amplitude_debt_h * np.sin(2 * np.pi * n / fit.period_debt_days + fit.phase_debt_rad)
        beta_e = phi.mean() - alpha_e * n.mean() - np.mean(sin_at_n) - fit.kappa_debt * D_at_n.mean()
        y_e_at_n = (alpha_e * n + beta_e
                    + sin_at_n
                    + fit.kappa_debt * D_at_n)
        # Plotted at integer n only (D is defined only at observed nights);
        # connect points by lines to show the model's trajectory.
        order = np.argsort(n)
        fig.add_trace(
            go.Scatter(x=n[order], y=y_e_at_n[order], mode="lines+markers",
                       line=dict(color="#2a2a2a", width=2),
                       marker=dict(size=5, color="#2a2a2a"),
                       name=f"linear+sin+κD  τ={fit.tau_debt_h:.3f}h  "
                            f"A={fit.amplitude_debt_h:.2f}h  P={fit.period_debt_days:.1f}d  "
                            f"κ={fit.kappa_debt:+.3f}h/h  R²={fit.r2_debt:.2f}"),
            row=1, col=1,
        )

    # Double sinusoid (key addition)
    if np.isfinite(fit.r2_double):
        alpha_d = fit.tau_double_h - 24.0
        # Re-center so the fit sits at the data centroid
        sin_at_n = (fit.amplitude_double_short_h * np.sin(2 * np.pi * n / fit.period_double_short_days + fit.phase_double_short_rad)
                    + fit.amplitude_double_long_h * np.sin(2 * np.pi * n / fit.period_double_long_days + fit.phase_double_long_rad))
        beta_d = phi.mean() - alpha_d * n.mean() - np.mean(sin_at_n)
        y_d = (alpha_d * n_smooth + beta_d
               + fit.amplitude_double_short_h * np.sin(2 * np.pi * n_smooth / fit.period_double_short_days + fit.phase_double_short_rad)
               + fit.amplitude_double_long_h * np.sin(2 * np.pi * n_smooth / fit.period_double_long_days + fit.phase_double_long_rad))
        fig.add_trace(
            go.Scatter(x=n_smooth, y=y_d, mode="lines",
                       line=dict(color="#c5198d", width=2),
                       name=f"linear+2sin  τ={fit.tau_double_h:.3f}h  "
                            f"P₁={fit.period_double_short_days:.1f}d/A₁={fit.amplitude_double_short_h:.1f}h  "
                            f"P₂={fit.period_double_long_days:.1f}d/A₂={fit.amplitude_double_long_h:.1f}h  "
                            f"R²={fit.r2_double:.2f}"),
            row=1, col=1,
        )
    fig.update_xaxes(title_text="day index n", row=1, col=1)
    fig.update_yaxes(title_text="φ(n) = onset − 24·n  (hours)", row=1, col=1)

    # ── Panel 2 : residuals comparison (linear vs best model) ────────────
    if np.isfinite(fit.alpha_linear_h_per_day):
        beta_lin = phi.mean() - fit.alpha_linear_h_per_day * n.mean()
        resid_lin = phi - (fit.alpha_linear_h_per_day * n + beta_lin)
        fig.add_trace(
            go.Scatter(x=n, y=resid_lin, mode="markers",
                       marker=dict(color=TEAL, size=6),
                       name=f"linear  σ={fit.residual_std_linear_h:.2f}h"),
            row=1, col=2,
        )
    # Pick the model with the best R² to overlay residuals
    candidates = [
        ("oscillator", fit.r2_full, fit.residual_std_full_h, CYAN),
        ("weekly", fit.r2_weekly, fit.residual_std_weekly_h, "#7c5cff"),
        ("combined", fit.r2_combined, fit.residual_std_combined_h, "#1d8a4a"),
    ]
    candidates = [c for c in candidates if np.isfinite(c[1])]
    if candidates:
        best = max(candidates, key=lambda c: c[1])
        name, r2_b, std_b, color_b = best
        # Recompute residuals for the best model
        if name == "oscillator":
            beta_full = phi.mean() - fit.alpha_full_h_per_day * n.mean() - np.mean(
                fit.amplitude_h * np.sin(2 * np.pi * n / fit.period_days + fit.phase_rad)
            )
            pred = oscillator_model(n, fit.alpha_full_h_per_day, beta_full,
                                    fit.amplitude_h, fit.period_days, fit.phase_rad)
        elif name == "weekly":
            alpha_w = fit.tau_weekly_h - 24.0
            beta_w = phi.mean() - alpha_w * n.mean() - fit.weekend_offset_h * weekend.mean()
            pred = alpha_w * n + beta_w + fit.weekend_offset_h * weekend
        else:  # combined
            alpha_c = fit.tau_combined_h - 24.0
            beta_c = (phi.mean() - alpha_c * n.mean()
                      - np.mean(fit.amplitude_combined_h * np.sin(2 * np.pi * n / fit.period_combined_days))
                      - fit.weekend_offset_combined_h * weekend.mean())
            pred = (alpha_c * n + beta_c
                    + fit.amplitude_combined_h * np.sin(2 * np.pi * n / fit.period_combined_days)
                    + fit.weekend_offset_combined_h * weekend)
        resid_b = phi - pred
        fig.add_trace(
            go.Scatter(x=n, y=resid_b, mode="markers",
                       marker=dict(color=color_b, size=6, symbol="x"),
                       name=f"{name}  σ={std_b:.2f}h"),
            row=1, col=2,
        )
    fig.add_hline(y=0, line=dict(color="black", width=0.5), row=1, col=2)
    fig.update_xaxes(title_text="day index n", row=1, col=2)
    fig.update_yaxes(title_text="residual (h)", row=1, col=2)

    # ── Panel 3 : Lomb-Scargle periodogram ───────────────────────────────
    if np.isfinite(fit.alpha_linear_h_per_day) and len(n) >= 6:
        beta_lin = phi.mean() - fit.alpha_linear_h_per_day * n.mean()
        resid_lin_for_ls = phi - (fit.alpha_linear_h_per_day * n + beta_lin)
        # Reuse same logic as the seeding code
        from_ls_periods, from_ls_amps = lomb_scargle_periodogram(resid_lin_for_ls, n)
        if len(from_ls_periods):
            fig.add_trace(
                go.Scatter(x=from_ls_periods, y=from_ls_amps, mode="lines",
                           line=dict(color=AMBER), showlegend=False,
                           name="Lomb-Scargle amplitude"),
                row=2, col=1,
            )
        for rank, (Pi, Ai) in enumerate(zip(fit.fft_top_periods_days, fit.fft_top_amplitudes_h)):
            color = [CYAN, "#7c5cff", "#1d8a4a"][rank] if rank < 3 else "gray"
            fig.add_vline(
                x=Pi, line=dict(color=color, dash="dot"),
                annotation_text=f"#{rank+1}  P={Pi:.1f}d  A={Ai:.2f}h",
                annotation_position="top right" if rank == 0 else "top left",
                row=2, col=1,
            )
        # 7-day reference (work-week)
        fig.add_vline(x=7.0, line=dict(color="gray", dash="dash"),
                      annotation_text="7d ref", annotation_position="bottom right",
                      row=2, col=1)
        # If double sinusoid fit converged, also mark P1 and P2 from the fit
        if np.isfinite(fit.r2_double):
            fig.add_vline(x=fit.period_double_short_days,
                          line=dict(color="#c5198d", dash="solid", width=1),
                          annotation_text=f"P₁ fit={fit.period_double_short_days:.1f}d",
                          annotation_position="bottom left",
                          row=2, col=1)
            fig.add_vline(x=fit.period_double_long_days,
                          line=dict(color="#c5198d", dash="solid", width=1),
                          annotation_text=f"P₂ fit={fit.period_double_long_days:.1f}d",
                          annotation_position="bottom right",
                          row=2, col=1)
        upper = max(15.0, (fit.fft_dominant_period_days * 2) if np.isfinite(fit.fft_dominant_period_days) else 15.0)
        fig.update_xaxes(title_text="period (days)", range=[1.5, upper], row=2, col=1, type="log")
        fig.update_yaxes(title_text="amplitude (h)", row=2, col=1)

    # ── Panel 4 : night-to-night Δφ ──────────────────────────────────────
    if len(n) >= 2:
        order = np.argsort(n)
        ns, phis = n[order], phi[order]
        dphi = np.diff(phis)
        dn = np.diff(ns)
        delta_per_day = dphi / dn
        fig.add_trace(
            go.Scatter(x=ns[1:], y=delta_per_day, mode="markers",
                       marker=dict(color=TEAL, size=7), showlegend=False,
                       name="Δφ"),
            row=2, col=2,
        )
        fig.add_hline(y=0, line=dict(color="black", width=0.5), row=2, col=2)
        if np.isfinite(fit.alpha_linear_h_per_day):
            fig.add_hline(
                y=fit.alpha_linear_h_per_day,
                line=dict(color=AMBER, dash="dash"),
                annotation_text=f"mean slope = {fit.alpha_linear_h_per_day:.2f}h/d",
                annotation_position="top right",
                row=2, col=2,
            )
        fig.update_xaxes(title_text="day index n", row=2, col=2)
        fig.update_yaxes(title_text="Δφ per day (h)", row=2, col=2)

    fig.update_layout(
        title=dict(text=f"<b>Oscillator-on-drift fit — {label}</b><br>"
                        f"<sub>{fit.start} → {fit.end}  ·  {fit.n_nights_used}/{fit.n_nights_window} nights</sub>",
                   x=0.02, xanchor="left"),
        height=820, width=1300,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1.0,
                    font=dict(size=10)),
        margin=dict(t=120, l=70, r=30, b=60),
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn")


def parse_periods(spec: str) -> list[tuple[str, date_, date_]]:
    """Parse 'label1=YYYY-MM-DD:YYYY-MM-DD,label2=...' or 'YYYY-MM-DD:YYYY-MM-DD,...'."""
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
    ap.add_argument(
        "--periods",
        required=True,
        help="Comma-separated 'label=YYYY-MM-DD:YYYY-MM-DD' specs",
    )
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="Output dir for plots + summary.json (default: <data_dir>/oscillator_explore)")
    ap.add_argument("--t-star", type=float, default=8.99,
                    help="Ideal sleep duration T★ in hours (default 8.99 = winter25 TST median)")
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
    print(f"T★ = {args.t_star:.2f}h  ·  γ_debt = {args.gamma_debt:.2f}")
    print(f"\n{'label':<10} {'nights':<10} "
          f"{'τ_lin':>7} {'τ_osc':>7} {'τ_dbl':>7} {'τ_deb':>7}  |  "
          f"{'P_sin':>6} {'A_sin':>5}  |  "
          f"{'P1':>5} {'A1':>5} {'P2':>5} {'A2':>5}  |  "
          f"{'κ':>6}  |  "
          f"{'R²L':>5} {'R²O':>5} {'R²W':>5} {'R²C':>5} {'R²D':>5} {'R²E':>5}  |  "
          f"{'best_AIC':>10} {'best_BIC':>10}")
    print("-" * 180)
    for label, a, b in periods:
        fit, series = fit_window(
            sleep_path, args.timezone, label, a, b,
            t_star_h=args.t_star, gamma_debt=args.gamma_debt,
        )
        html = out_dir / f"{label}.html"
        plot_window(label, series, fit, html)
        summary.append(asdict(fit))
        nights = f"{fit.n_nights_used}/{fit.n_nights_window}"
        print(
            f"{label:<10} {nights:<10} "
            f"{fit.tau_linear_h:>7.3f} {fit.tau_full_h:>7.3f} {fit.tau_double_h:>7.3f} {fit.tau_debt_h:>7.3f}  |  "
            f"{fit.period_days:>6.1f} {fit.amplitude_h:>5.2f}  |  "
            f"{fit.period_double_short_days:>5.1f} {fit.amplitude_double_short_h:>5.2f} "
            f"{fit.period_double_long_days:>5.1f} {fit.amplitude_double_long_h:>5.2f}  |  "
            f"{fit.kappa_debt:>+6.3f}  |  "
            f"{fit.r2_linear:>5.2f} {fit.r2_full:>5.2f} {fit.r2_weekly:>5.2f} "
            f"{fit.r2_combined:>5.2f} {fit.r2_double:>5.2f} {fit.r2_debt:>5.2f}  |  "
            f"{fit.best_model_aic:>10} {fit.best_model_bic:>10}"
        )

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nSummary written to {out_dir/'summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
