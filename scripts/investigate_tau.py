"""Diagnostic: compare tau estimation methods on personal actigraphy data.

Tests two suspected sources of bias in the current ``n24sal.npcra.tau``
implementation when applied to real (gap-rich) data:

1. **Sparse-series reshape bug** (primary) — ``estimate_tau`` does
   ``arr.reshape(n_days, 1440)`` assuming the activity series is dense (1
   epoch per minute, all minutes present). When the input has gaps (Samsung
   Health export skips empty minutes), ``n_days = len(arr) // 1440`` is
   wrong and each "day row" contains epochs from multiple wall-clock days.
   Calendar alignment is destroyed → tau estimate is meaningless.

2. **Low-coverage day noise** (secondary) — even on a properly aligned
   dense grid, days with most epochs missing yield ``argmax`` on a
   nearly-flat profile, producing essentially random M10 phases that
   pollute the regression.

The script reports four estimates side by side:

* ``BUGGY``   — current behavior (sparse reshape)
* ``FIXED``   — dense 1-min grid (gaps zero-filled) before reshape
* ``FILTER``  — dense grid + drop days with coverage below threshold

Run from repo root after ``python -m n24sal.io.samsung ingest ...`` has
produced ``data/personal/<subject>/activity.parquet``.

Usage::

    python scripts/investigate_tau.py [subject_id] [timezone]

Defaults: subject_id=S001, timezone=Europe/Paris.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import linregress

from n24sal.npcra.tau import (
    _circular_window_means,
    _unwrap_phases_hours,
    bootstrap_tau_ci,
    estimate_tau,
)

EPOCHS_PER_HOUR = 60
EPOCHS_PER_DAY = 1440


def main(subject_id: str = "S001", timezone: str = "Europe/Paris") -> None:
    data_dir = Path("data/personal") / subject_id
    parquet_path = data_dir / "activity.parquet"
    if not parquet_path.exists():
        print(f"ERROR: {parquet_path} not found. Run the ingest CLI first.")
        sys.exit(1)

    activity = pd.read_parquet(parquet_path)
    activity["ts_local"] = activity["timestamp"].dt.tz_convert(timezone)
    n_epochs = len(activity)
    duration_days = (activity["ts_local"].max() - activity["ts_local"].min()).days
    print(
        f"Raw: {n_epochs:,} epochs over {duration_days} wall-clock days "
        f"({n_epochs / EPOCHS_PER_DAY:.0f} dense-days worth)"
    )
    print()

    # ---- 1. BUGGY current behavior --------------------------------------
    sparse = activity.sort_values("timestamp")["activity"].to_numpy()
    buggy = estimate_tau(sparse, EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    buggy_ci = bootstrap_tau_ci(sparse, EPOCHS_PER_HOUR, EPOCHS_PER_DAY, n_iter=300)
    print(
        f"[BUGGY    ] tau={buggy.tau_hours:7.3f}h  R²={buggy.r_squared:.3f}  "
        f"CI=[{buggy_ci.ci_low_hours:7.3f},{buggy_ci.ci_high_hours:7.3f}]  "
        f"n_days_used={buggy.n_days}"
    )

    # ---- 2. FIXED dense grid --------------------------------------------
    start = activity["ts_local"].min().floor("D")
    end = activity["ts_local"].max().ceil("D")
    grid = pd.date_range(start, end, freq="1min", tz=timezone, inclusive="left")
    dense = pd.Series(0.0, index=grid)
    dense.loc[activity["ts_local"].values] = activity["activity"].values
    present = pd.Series(False, index=grid)
    present.loc[activity["ts_local"].values] = True
    dense_arr = dense.to_numpy()

    fixed = estimate_tau(dense_arr, EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    fixed_ci = bootstrap_tau_ci(dense_arr, EPOCHS_PER_HOUR, EPOCHS_PER_DAY, n_iter=300)
    print(
        f"[FIXED    ] tau={fixed.tau_hours:7.3f}h  R²={fixed.r_squared:.3f}  "
        f"CI=[{fixed_ci.ci_low_hours:7.3f},{fixed_ci.ci_high_hours:7.3f}]  "
        f"n_days_used={fixed.n_days}"
    )

    # ---- 3. FILTER by per-day coverage ----------------------------------
    dense_matrix = dense_arr.reshape(-1, EPOCHS_PER_DAY)
    present_matrix = present.to_numpy().reshape(-1, EPOCHS_PER_DAY)
    cov_per_day = present_matrix.mean(axis=1)
    n_total_days = len(cov_per_day)
    print()
    print(
        f"Coverage breakdown: total {n_total_days} days  |  "
        f"≥50% cov: {(cov_per_day >= 0.5).sum()}  |  "
        f"≥70%: {(cov_per_day >= 0.7).sum()}  |  "
        f"≥90%: {(cov_per_day >= 0.9).sum()}"
    )
    print()

    m10_window = 10 * EPOCHS_PER_HOUR
    phases_all = np.array(
        [
            float(np.argmax(_circular_window_means(row, m10_window))) / EPOCHS_PER_HOUR
            for row in dense_matrix
        ]
    )
    for threshold in (0.5, 0.7, 0.9):
        mask = cov_per_day >= threshold
        if mask.sum() < 5:
            continue
        day_indices = np.where(mask)[0].astype(float)
        phases_filt = phases_all[mask]
        unwrapped = _unwrap_phases_hours(phases_filt)
        fit = linregress(day_indices, unwrapped)
        print(
            f"[FILTER {threshold * 100:2.0f}%] tau={24.0 + fit.slope:7.3f}h  "
            f"R²={fit.rvalue**2:.3f}  n_days_used={int(mask.sum())}"
        )

    # ---- 4. M10 phase distribution sanity -------------------------------
    print()
    print(f"M10 phase distribution (dense grid, all {n_total_days} days):")
    print(
        f"  mean  = {phases_all.mean():.2f}h    median = {np.median(phases_all):.2f}h    "
        f"std    = {phases_all.std():.2f}h"
    )
    print(f"  min   = {phases_all.min():.2f}h    max    = {phases_all.max():.2f}h")
    print()
    print(
        "Interpretation:\n"
        "  - If BUGGY and FIXED disagree substantially → sparse-reshape bug confirmed.\n"
        "  - If FILTER 70%/90% converge to a stable value → coverage filtering helps.\n"
        "  - High std on M10 phase distribution → daily M10 is noisy ; investigate\n"
        "    polyphasic sleep, multi-peak days, or use circular regression."
    )


if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "S001"
    tz = sys.argv[2] if len(sys.argv) > 2 else "Europe/Paris"
    main(subject, tz)
