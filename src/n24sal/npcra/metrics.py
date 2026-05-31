"""Non-parametric circadian rhythm analysis (NPCRA) metrics.

Implementations of the rest-activity rhythm indicators introduced by
Van Someren et al. (1999) and the composite Circadian Function Index of
Ortiz-Tudela et al. (2010). All formulas operate on a 1-D activity series
sampled at uniform epochs.

References (full citations in ``BIBLIO.md``):

* Van Someren EJW et al. 1999. Chronobiology International 16(4):505-518.
* Witting W et al. 1990. Biological Psychiatry 27(6):563-572.
* Ortiz-Tudela E et al. 2010. PLoS Comput Biol 6(11):e1000996.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

ArrayLike = np.ndarray | list[float]


class L5M10Result(NamedTuple):
    """Result of the L5 / M10 window search on the averaged 24h profile."""

    l5_value: float
    l5_phase_hours: float
    m10_value: float
    m10_phase_hours: float


def _as_1d_float(activity: ArrayLike) -> np.ndarray:
    arr = np.asarray(activity, dtype=float)
    if arr.ndim != 1:
        raise ValueError("activity must be 1-dimensional")
    return arr


def interdaily_stability(activity: ArrayLike, epochs_per_day: int) -> float:
    """Interdaily Stability (IS).

    IS = (N * Σ_h (x̄_h - x̄)²) / (p * Σ_i (x_i - x̄)²)

    where ``N`` is the total number of epochs, ``p`` the number of epochs per
    day, ``x̄_h`` the mean activity at epoch-of-day ``h`` averaged across days,
    and ``x̄`` the grand mean.

    Bounded in ``[0, 1]``. Closer to 1 = stronger day-to-day reproducibility
    of the 24h profile. Returns ``NaN`` for a constant signal or for less than
    two complete days.
    """

    arr = _as_1d_float(activity)
    if epochs_per_day <= 0:
        raise ValueError("epochs_per_day must be positive")

    n_days = len(arr) // epochs_per_day
    if n_days < 2:
        return float("nan")

    truncated = arr[: n_days * epochs_per_day]
    profile = truncated.reshape(n_days, epochs_per_day).mean(axis=0)
    grand_mean = float(truncated.mean())

    numerator = len(truncated) * float(np.sum((profile - grand_mean) ** 2))
    denominator = epochs_per_day * float(np.sum((truncated - grand_mean) ** 2))
    if denominator == 0.0:
        return float("nan")
    return numerator / denominator


def intradaily_variability(activity: ArrayLike) -> float:
    """Intradaily Variability (IV).

    IV = (N * Σ(x_{i+1} - x_i)²) / ((N-1) * Σ(x_i - x̄)²)

    Higher IV = more fragmented rhythm (frequent transitions between rest and
    activity). Returns ``NaN`` for a constant signal or fewer than two epochs.
    """

    arr = _as_1d_float(activity)
    n = len(arr)
    if n < 2:
        return float("nan")
    grand_mean = float(arr.mean())
    denominator = (n - 1) * float(np.sum((arr - grand_mean) ** 2))
    if denominator == 0.0:
        return float("nan")
    numerator = n * float(np.sum(np.diff(arr) ** 2))
    return numerator / denominator


def _circular_window_means(profile: np.ndarray, window_size: int) -> np.ndarray:
    """Rolling-window means with wrap-around (last hours stitch back to first)."""
    if window_size <= 0 or window_size > len(profile):
        raise ValueError("window_size must be in (0, len(profile)]")
    padded = np.concatenate([profile, profile[: window_size - 1]])
    cumsum = np.cumsum(np.insert(padded, 0, 0.0))
    sums = cumsum[window_size:] - cumsum[:-window_size]
    return sums[: len(profile)] / window_size


def l5_m10(
    activity: ArrayLike,
    epochs_per_hour: int,
    epochs_per_day: int,
) -> L5M10Result:
    """L5 and M10 on the averaged 24h profile.

    L5  = mean activity of the 5h-consecutive window of minimum activity.
    M10 = mean activity of the 10h-consecutive window of maximum activity.

    Phases are reported as the **start hour** of the corresponding window on
    the averaged 24h profile (range ``[0, 24)``).

    Returns ``NaN`` everywhere if fewer than one full day is available.
    """

    arr = _as_1d_float(activity)
    if epochs_per_hour <= 0 or epochs_per_day <= 0:
        raise ValueError("epochs_per_hour and epochs_per_day must be positive")

    n_days = len(arr) // epochs_per_day
    if n_days < 1:
        return L5M10Result(float("nan"), float("nan"), float("nan"), float("nan"))

    truncated = arr[: n_days * epochs_per_day]
    profile = truncated.reshape(n_days, epochs_per_day).mean(axis=0)

    l5_window = 5 * epochs_per_hour
    m10_window = 10 * epochs_per_hour

    l5_series = _circular_window_means(profile, l5_window)
    m10_series = _circular_window_means(profile, m10_window)

    l5_idx = int(np.argmin(l5_series))
    m10_idx = int(np.argmax(m10_series))

    return L5M10Result(
        l5_value=float(l5_series[l5_idx]),
        l5_phase_hours=l5_idx / epochs_per_hour,
        m10_value=float(m10_series[m10_idx]),
        m10_phase_hours=m10_idx / epochs_per_hour,
    )


def relative_amplitude(l5: float, m10: float) -> float:
    """Relative Amplitude (RA) = (M10 - L5) / (M10 + L5).

    Bounded in ``[0, 1]`` for non-negative activity. Returns ``NaN`` if
    either input is NaN or if the denominator is zero.
    """

    if np.isnan(l5) or np.isnan(m10):
        return float("nan")
    denom = m10 + l5
    if denom == 0.0:
        return float("nan")
    return float((m10 - l5) / denom)


def circadian_function_index(
    is_val: float,
    iv_val: float,
    ra: float,
    iv_max: float = 2.0,
) -> float:
    """Circadian Function Index (Ortiz-Tudela 2010).

    Composite of IS, normalised IV, and RA. Bounded in ``[0, 1]``.

    Parameters
    ----------
    iv_max
        Theoretical maximum for IV used to normalise it onto ``[0, 1]``.
        Default ``2.0`` matches the typical upper bound observed on real
        actigraphy data.
    """

    if iv_max <= 0.0:
        raise ValueError("iv_max must be positive")
    if any(np.isnan(v) for v in (is_val, iv_val, ra)):
        return float("nan")
    iv_norm = 1.0 - min(iv_val / iv_max, 1.0)
    return float(np.mean([is_val, iv_norm, ra]))
