"""Intrinsic circadian period (``tau``) estimation.

In an entrained rhythm the daily acrophase is locked to the 24h light-dark
cycle ; in a free-running rhythm (e.g. blind N24 or sighted N24 with absent
photic entrainment) it drifts by ``tau - 24`` hours per calendar day. We
exploit that signature by extracting the start hour of the M10 window on a
per-day basis and regressing it linearly against the day index.

Phases are unwrapped circularly before regression so a midnight wrap does
not destroy the slope.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from scipy.stats import linregress


class TauEstimate(NamedTuple):
    """Result of :func:`estimate_tau`."""

    tau_hours: float
    slope_hours_per_day: float
    intercept_hours: float
    r_squared: float
    p_value: float
    std_err: float
    n_days: int


class TauBootstrapCI(NamedTuple):
    """Result of :func:`bootstrap_tau_ci`."""

    tau_hours: float
    ci_low_hours: float
    ci_high_hours: float
    n_iterations: int
    n_days_used: int
    confidence: float


def _unwrap_phases_hours(phases_hours: np.ndarray) -> np.ndarray:
    """Unwrap a series of phases in hours assuming a 24h circular range."""
    rad = phases_hours * (2.0 * np.pi / 24.0)
    return np.unwrap(rad) * (24.0 / (2.0 * np.pi))


def _circular_window_means(profile: np.ndarray, window_size: int) -> np.ndarray:
    """Inline copy of metrics._circular_window_means to keep tau.py standalone."""
    padded = np.concatenate([profile, profile[: window_size - 1]])
    cumsum = np.cumsum(np.insert(padded, 0, 0.0))
    sums = cumsum[window_size:] - cumsum[:-window_size]
    return sums[: len(profile)] / window_size


def m10_phases_per_day(
    activity: np.ndarray,
    epochs_per_hour: int,
    epochs_per_day: int,
) -> np.ndarray:
    """Return the M10 start-hour for each complete calendar day in the series.

    Phases are in ``[0, 24)``. Returns an empty array if fewer than one full
    day is available.
    """

    arr = np.asarray(activity, dtype=float)
    if epochs_per_hour <= 0 or epochs_per_day <= 0:
        raise ValueError("epochs_per_hour and epochs_per_day must be positive")

    n_days = len(arr) // epochs_per_day
    if n_days < 1:
        return np.array([], dtype=float)

    truncated = arr[: n_days * epochs_per_day]
    daily = truncated.reshape(n_days, epochs_per_day)
    m10_window = 10 * epochs_per_hour

    phases = np.empty(n_days, dtype=float)
    for d, day_profile in enumerate(daily):
        means = _circular_window_means(day_profile, m10_window)
        phases[d] = float(np.argmax(means)) / epochs_per_hour
    return phases


def _select_valid_days(
    phases: np.ndarray,
    present_mask: np.ndarray | None,
    epochs_per_day: int,
    min_daily_coverage: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (day_indices, phases) filtered by per-day coverage threshold."""
    n = len(phases)
    if present_mask is None or min_daily_coverage <= 0.0:
        return np.arange(n, dtype=float), phases
    if len(present_mask) < n * epochs_per_day:
        raise ValueError(
            f"present_mask length {len(present_mask)} too short for {n} days × {epochs_per_day} epochs"
        )
    cov = present_mask[: n * epochs_per_day].reshape(n, epochs_per_day).mean(axis=1)
    keep = cov >= min_daily_coverage
    return np.where(keep)[0].astype(float), phases[keep]


def estimate_tau(
    activity: np.ndarray,
    epochs_per_hour: int,
    epochs_per_day: int,
    *,
    present_mask: np.ndarray | None = None,
    min_daily_coverage: float = 0.0,
) -> TauEstimate:
    """Estimate the intrinsic circadian period via M10 phase drift regression.

    Steps:

    1. Compute the M10 start-hour per calendar day.
    2. Optionally drop days whose recording coverage is below
       ``min_daily_coverage`` (requires a boolean ``present_mask`` aligned to
       ``activity``).
    3. Circularly unwrap the remaining phase series (24h wrap → continuous).
    4. Regress phase against day index. ``slope`` is in hours per day.
    5. ``tau_hours = 24.0 + slope``.

    Requires at least three valid days. With fewer days the returned
    ``TauEstimate`` is filled with ``NaN`` except ``n_days``.

    Parameters
    ----------
    present_mask
        Optional boolean array same length as ``activity``. ``True`` where the
        epoch was actually recorded, ``False`` where it was imputed. Required
        if ``min_daily_coverage > 0``.
    min_daily_coverage
        Drop days with fewer than this fraction of recorded epochs.
        ``0.0`` (default) = no filtering.
    """
    phases = m10_phases_per_day(activity, epochs_per_hour, epochs_per_day)
    day_indices, phases_kept = _select_valid_days(
        phases, present_mask, epochs_per_day, min_daily_coverage
    )
    n = len(phases_kept)
    if n < 3:
        return TauEstimate(
            tau_hours=float("nan"),
            slope_hours_per_day=float("nan"),
            intercept_hours=float("nan"),
            r_squared=float("nan"),
            p_value=float("nan"),
            std_err=float("nan"),
            n_days=n,
        )

    unwrapped = _unwrap_phases_hours(phases_kept)
    result = linregress(day_indices, unwrapped)

    return TauEstimate(
        tau_hours=24.0 + float(result.slope),
        slope_hours_per_day=float(result.slope),
        intercept_hours=float(result.intercept),
        r_squared=float(result.rvalue**2),
        p_value=float(result.pvalue),
        std_err=float(result.stderr),
        n_days=n,
    )


def bootstrap_tau_ci(
    activity: np.ndarray,
    epochs_per_hour: int,
    epochs_per_day: int,
    *,
    n_iter: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
    present_mask: np.ndarray | None = None,
    min_daily_coverage: float = 0.0,
) -> TauBootstrapCI:
    """Bootstrap confidence interval for ``tau`` via resampling M10 phases.

    Resamples (day-index, M10-phase) pairs with replacement ``n_iter`` times,
    re-runs the linear regression on each resample, and reports the
    ``confidence``-level percentile interval on the resulting slope
    distribution. Point estimate is from the full (non-resampled) regression.

    ``present_mask`` and ``min_daily_coverage`` behave as in :func:`estimate_tau`.

    Returns ``NaN`` everywhere if fewer than three valid days are available.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0, 1), got {confidence}")
    if n_iter < 10:
        raise ValueError(f"n_iter must be ≥ 10, got {n_iter}")

    phases = m10_phases_per_day(activity, epochs_per_hour, epochs_per_day)
    day_indices, phases_kept = _select_valid_days(
        phases, present_mask, epochs_per_day, min_daily_coverage
    )
    n = len(phases_kept)
    if n < 3:
        return TauBootstrapCI(
            tau_hours=float("nan"),
            ci_low_hours=float("nan"),
            ci_high_hours=float("nan"),
            n_iterations=0,
            n_days_used=n,
            confidence=confidence,
        )

    unwrapped = _unwrap_phases_hours(phases_kept)
    point = linregress(day_indices, unwrapped)

    rng = np.random.default_rng(seed)
    slopes = np.empty(n_iter)
    for i in range(n_iter):
        idx = rng.integers(0, n, size=n)
        if len(np.unique(day_indices[idx])) < 2:
            slopes[i] = float("nan")
            continue
        res = linregress(day_indices[idx], unwrapped[idx])
        slopes[i] = res.slope
    valid = slopes[~np.isnan(slopes)]

    alpha = (1.0 - confidence) / 2.0
    low, high = np.percentile(valid, [alpha * 100.0, (1.0 - alpha) * 100.0])

    return TauBootstrapCI(
        tau_hours=24.0 + float(point.slope),
        ci_low_hours=24.0 + float(low),
        ci_high_hours=24.0 + float(high),
        n_iterations=n_iter,
        n_days_used=n,
        confidence=confidence,
    )
