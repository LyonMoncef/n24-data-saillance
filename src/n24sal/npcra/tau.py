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


def estimate_tau(
    activity: np.ndarray,
    epochs_per_hour: int,
    epochs_per_day: int,
) -> TauEstimate:
    """Estimate the intrinsic circadian period via M10 phase drift regression.

    Steps:

    1. Compute the M10 start-hour per calendar day.
    2. Circularly unwrap the resulting phase series (24h wrap → continuous).
    3. Regress phase against day index. ``slope`` is in hours per day.
    4. ``tau_hours = 24.0 + slope``.

    Requires at least three full days. With fewer days the returned
    ``TauEstimate`` is filled with ``NaN`` except ``n_days``.
    """

    phases = m10_phases_per_day(activity, epochs_per_hour, epochs_per_day)
    n = len(phases)
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

    days = np.arange(n, dtype=float)
    unwrapped = _unwrap_phases_hours(phases)
    result = linregress(days, unwrapped)

    return TauEstimate(
        tau_hours=24.0 + float(result.slope),
        slope_hours_per_day=float(result.slope),
        intercept_hours=float(result.intercept),
        r_squared=float(result.rvalue**2),
        p_value=float(result.pvalue),
        std_err=float(result.stderr),
        n_days=n,
    )
