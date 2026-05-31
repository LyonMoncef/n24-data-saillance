"""Synthetic actigraphy fixtures.

A free-running cosinor signal of period ``tau_hours`` sampled on a calendar
time grid. When ``tau_hours == 24.0`` the signal is entrained ; when
``tau_hours > 24.0`` it models an N24-like rhythm whose acrophase drifts on
the wall clock by ``(tau - 24)`` hours per day.

Used exclusively for unit tests and pedagogical notebooks. The same generator
also serves as a sanity check that the NPCRA implementation recovers a known
``tau`` to within an explicit tolerance.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd


def generate_synthetic_actigraphy(
    n_days: int = 14,
    tau_hours: float = 24.7,
    epoch_seconds: int = 60,
    amplitude: float = 100.0,
    baseline: float = 20.0,
    noise_sd: float = 10.0,
    start: datetime | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a synthetic actigraphy series with a known intrinsic period.

    Parameters
    ----------
    n_days
        Number of calendar days to simulate.
    tau_hours
        Intrinsic period of the underlying cosinor. ``24.0`` for an entrained
        rhythm; a value like ``24.7`` models a typical N24 phase delay.
    epoch_seconds
        Sampling period in seconds. ``60`` yields one sample per minute.
    amplitude, baseline
        Activity is ``baseline + amplitude * max(cos(2 pi t / tau), 0) + noise``
        — the active half of the cycle is shaped like a clipped cosine, the
        rest period is at baseline. Crude but sufficient for testing IS/IV/RA
        and tau recovery.
    noise_sd
        Standard deviation of additive Gaussian noise on the activity signal.
    start
        Calendar start of the recording (tz-aware). Defaults to
        ``2025-01-01T00:00:00+00:00``.
    seed
        RNG seed for reproducibility.

    Returns
    -------
    pandas.DataFrame
        Columns ``timestamp`` (tz-aware UTC) and ``activity`` (float, ≥ 0).
        Length is ``n_days * 86400 / epoch_seconds``.
    """

    if n_days <= 0:
        raise ValueError("n_days must be positive")
    if tau_hours <= 0:
        raise ValueError("tau_hours must be positive")
    if 86400 % epoch_seconds != 0:
        raise ValueError("epoch_seconds must divide 86400 evenly")

    rng = np.random.default_rng(seed)
    epochs_per_day = 86400 // epoch_seconds
    n_epochs = n_days * epochs_per_day

    t_hours = np.arange(n_epochs) * (epoch_seconds / 3600.0)
    cosinor = np.cos(2.0 * np.pi * t_hours / tau_hours)
    activity = baseline + amplitude * np.maximum(cosinor, 0.0)
    activity = activity + rng.normal(0.0, noise_sd, size=n_epochs)
    activity = np.maximum(activity, 0.0)

    if start is None:
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    timestamps = pd.date_range(
        start=start,
        periods=n_epochs,
        freq=pd.Timedelta(seconds=epoch_seconds),
    )

    return pd.DataFrame({"timestamp": timestamps, "activity": activity})
