import numpy as np
import pytest

from n24sal.npcra import (
    circadian_function_index,
    interdaily_stability,
    intradaily_variability,
    l5_m10,
    relative_amplitude,
)
from n24sal.npcra.tau import bootstrap_tau_ci, estimate_tau, m10_phases_per_day
from n24sal.synthetic import generate_synthetic_actigraphy

EPOCHS_PER_HOUR = 60
EPOCHS_PER_DAY = 1440


# -------------------- IS --------------------


def test_is_constant_signal_is_nan():
    activity = np.ones(EPOCHS_PER_DAY * 5)
    assert np.isnan(interdaily_stability(activity, EPOCHS_PER_DAY))


def test_is_less_than_two_days_is_nan():
    activity = np.random.default_rng(0).normal(size=EPOCHS_PER_DAY)
    assert np.isnan(interdaily_stability(activity, EPOCHS_PER_DAY))


def test_is_entrained_signal_high():
    df = generate_synthetic_actigraphy(n_days=14, tau_hours=24.0, noise_sd=2.0, seed=0)
    is_val = interdaily_stability(df["activity"].to_numpy(), EPOCHS_PER_DAY)
    assert 0.5 < is_val <= 1.0


def test_is_n24_signal_lower_than_entrained():
    df_n24 = generate_synthetic_actigraphy(n_days=14, tau_hours=24.7, noise_sd=5.0, seed=1)
    df_norm = generate_synthetic_actigraphy(n_days=14, tau_hours=24.0, noise_sd=5.0, seed=1)
    is_n24 = interdaily_stability(df_n24["activity"].to_numpy(), EPOCHS_PER_DAY)
    is_norm = interdaily_stability(df_norm["activity"].to_numpy(), EPOCHS_PER_DAY)
    assert is_n24 < is_norm


def test_is_n24_long_recording_matches_published_signature():
    df = generate_synthetic_actigraphy(n_days=35, tau_hours=24.7, noise_sd=5.0, seed=1)
    is_val = interdaily_stability(df["activity"].to_numpy(), EPOCHS_PER_DAY)
    assert is_val < 0.20


# -------------------- IV --------------------


def test_iv_constant_signal_is_nan():
    activity = np.ones(EPOCHS_PER_DAY * 5)
    assert np.isnan(intradaily_variability(activity))


def test_iv_short_signal_is_nan():
    assert np.isnan(intradaily_variability(np.array([1.0])))


def test_iv_noisy_higher_than_smooth():
    rng = np.random.default_rng(0)
    t = np.linspace(0, 2 * np.pi * 5, EPOCHS_PER_DAY * 5)
    smooth = np.sin(t)
    noisy = smooth + rng.normal(0, 1.0, size=len(smooth))
    assert intradaily_variability(noisy) > intradaily_variability(smooth)


# -------------------- L5 / M10 / RA --------------------


def test_l5_m10_ordering_entrained():
    df = generate_synthetic_actigraphy(n_days=10, tau_hours=24.0, noise_sd=1.0, seed=0)
    res = l5_m10(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    assert res.m10_value > res.l5_value
    assert 0.0 <= res.l5_phase_hours < 24.0
    assert 0.0 <= res.m10_phase_hours < 24.0


def test_l5_m10_returns_nan_on_empty_signal():
    res = l5_m10(np.array([]), EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    assert np.isnan(res.l5_value)
    assert np.isnan(res.m10_value)


def test_relative_amplitude_in_unit_interval():
    df = generate_synthetic_actigraphy(n_days=10, noise_sd=1.0, seed=0)
    res = l5_m10(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    ra = relative_amplitude(res.l5_value, res.m10_value)
    assert 0.0 <= ra <= 1.0


def test_relative_amplitude_nan_propagation():
    assert np.isnan(relative_amplitude(float("nan"), 1.0))
    assert np.isnan(relative_amplitude(1.0, float("nan")))


# -------------------- CFI --------------------


def test_cfi_within_unit_interval():
    assert 0.0 <= circadian_function_index(0.6, 0.8, 0.9) <= 1.0


def test_cfi_nan_propagation():
    assert np.isnan(circadian_function_index(float("nan"), 0.5, 0.5))


def test_cfi_iv_max_validated():
    with pytest.raises(ValueError, match="iv_max"):
        circadian_function_index(0.5, 0.5, 0.5, iv_max=0.0)


# -------------------- tau --------------------


def test_tau_too_few_days_returns_nan():
    df = generate_synthetic_actigraphy(n_days=2, tau_hours=24.5, seed=0)
    est = estimate_tau(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    assert np.isnan(est.tau_hours)
    assert est.n_days == 2


def test_tau_recovery_entrained():
    df = generate_synthetic_actigraphy(n_days=21, tau_hours=24.0, noise_sd=2.0, seed=0)
    est = estimate_tau(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    assert abs(est.tau_hours - 24.0) < 0.15
    assert est.n_days == 21


def test_tau_recovery_n24_classic():
    df = generate_synthetic_actigraphy(n_days=21, tau_hours=24.7, noise_sd=3.0, seed=7)
    est = estimate_tau(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    assert abs(est.tau_hours - 24.7) < 0.2
    assert est.r_squared > 0.85


def test_tau_recovery_n24_strong_drift():
    df = generate_synthetic_actigraphy(n_days=14, tau_hours=25.2, noise_sd=3.0, seed=3)
    est = estimate_tau(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    assert abs(est.tau_hours - 25.2) < 0.3
    assert est.r_squared > 0.85


def test_m10_phases_per_day_length():
    df = generate_synthetic_actigraphy(n_days=10, tau_hours=24.5, seed=0)
    phases = m10_phases_per_day(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    assert len(phases) == 10
    assert ((phases >= 0) & (phases < 24)).all()


# -------------------- Bootstrap tau CI --------------------


def test_bootstrap_tau_too_few_days():
    df = generate_synthetic_actigraphy(n_days=2, seed=0)
    ci = bootstrap_tau_ci(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY, n_iter=100)
    assert np.isnan(ci.tau_hours)
    assert ci.n_iterations == 0
    assert ci.n_days_used == 2


def test_bootstrap_tau_ci_contains_point_estimate():
    df = generate_synthetic_actigraphy(n_days=21, tau_hours=24.7, noise_sd=3.0, seed=7)
    ci = bootstrap_tau_ci(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY, n_iter=300)
    # CI must straddle the point estimate by construction (percentile method)
    assert ci.ci_low_hours <= ci.tau_hours <= ci.ci_high_hours
    # Point estimate must be near the true tau (separate property from CI coverage)
    assert abs(ci.tau_hours - 24.7) < 0.1
    assert ci.n_iterations == 300
    assert ci.n_days_used == 21
    assert ci.confidence == 0.95
    # CI width should be non-zero (i.e. bootstrap actually resampled)
    assert ci.ci_high_hours - ci.ci_low_hours > 0.0


def test_bootstrap_tau_ci_narrows_with_more_days():
    """More days → tighter CI."""
    df_short = generate_synthetic_actigraphy(n_days=10, tau_hours=24.7, noise_sd=3.0, seed=0)
    df_long = generate_synthetic_actigraphy(n_days=40, tau_hours=24.7, noise_sd=3.0, seed=0)
    ci_short = bootstrap_tau_ci(df_short["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY, n_iter=200)
    ci_long = bootstrap_tau_ci(df_long["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY, n_iter=200)
    width_short = ci_short.ci_high_hours - ci_short.ci_low_hours
    width_long = ci_long.ci_high_hours - ci_long.ci_low_hours
    assert width_long < width_short


def test_bootstrap_tau_ci_rejects_invalid_confidence():
    df = generate_synthetic_actigraphy(n_days=5, seed=0)
    with pytest.raises(ValueError, match="confidence"):
        bootstrap_tau_ci(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY, confidence=1.5)


def test_bootstrap_tau_ci_rejects_low_n_iter():
    df = generate_synthetic_actigraphy(n_days=5, seed=0)
    with pytest.raises(ValueError, match="n_iter"):
        bootstrap_tau_ci(df["activity"].to_numpy(), EPOCHS_PER_HOUR, EPOCHS_PER_DAY, n_iter=5)


# -------------------- Coverage filtering --------------------


def _make_dense_with_synthetic_gaps(n_days: int, tau: float, gap_day_indices: list[int], seed: int = 0):
    """Generate dense synthetic data, then zero-out specific calendar days."""
    df = generate_synthetic_actigraphy(n_days=n_days, tau_hours=tau, noise_sd=2.0, seed=seed)
    arr = df["activity"].to_numpy().copy()
    present = np.ones(len(arr), dtype=bool)
    for d in gap_day_indices:
        s = d * EPOCHS_PER_DAY
        e = (d + 1) * EPOCHS_PER_DAY
        arr[s:e] = 0.0
        present[s:e] = False
    return arr, present


def test_estimate_tau_filter_drops_zeroed_days():
    """Days with no recording (zero-filled, present=False) should be excluded
    by min_daily_coverage and not bias the regression."""
    arr, present = _make_dense_with_synthetic_gaps(
        n_days=21, tau=24.7, gap_day_indices=[5, 10, 15]
    )
    # Without mask → noisy days included → tau may be biased
    no_filter = estimate_tau(arr, EPOCHS_PER_HOUR, EPOCHS_PER_DAY)
    # With mask + threshold → bad days dropped → cleaner estimate
    filtered = estimate_tau(
        arr, EPOCHS_PER_HOUR, EPOCHS_PER_DAY,
        present_mask=present, min_daily_coverage=0.5,
    )
    assert filtered.n_days == 18  # 21 - 3 gap days
    assert abs(filtered.tau_hours - 24.7) < 0.2


def test_estimate_tau_filter_zero_threshold_keeps_all_days():
    arr, present = _make_dense_with_synthetic_gaps(n_days=14, tau=24.5, gap_day_indices=[3])
    res = estimate_tau(
        arr, EPOCHS_PER_HOUR, EPOCHS_PER_DAY,
        present_mask=present, min_daily_coverage=0.0,
    )
    assert res.n_days == 14


def test_estimate_tau_filter_no_mask_ignores_threshold():
    arr, _ = _make_dense_with_synthetic_gaps(n_days=14, tau=24.5, gap_day_indices=[3])
    res = estimate_tau(
        arr, EPOCHS_PER_HOUR, EPOCHS_PER_DAY,
        min_daily_coverage=0.9,
    )
    assert res.n_days == 14  # no mask → no filtering applied


def test_bootstrap_tau_ci_filter_respects_present_mask():
    arr, present = _make_dense_with_synthetic_gaps(
        n_days=21, tau=24.7, gap_day_indices=[2, 7, 12]
    )
    ci = bootstrap_tau_ci(
        arr, EPOCHS_PER_HOUR, EPOCHS_PER_DAY,
        n_iter=200,
        present_mask=present, min_daily_coverage=0.5,
    )
    assert ci.n_days_used == 18
    assert ci.ci_low_hours <= ci.tau_hours <= ci.ci_high_hours


def test_estimate_tau_rejects_mismatched_mask():
    arr = np.zeros(EPOCHS_PER_DAY * 5)
    short_mask = np.ones(EPOCHS_PER_DAY * 2, dtype=bool)
    with pytest.raises(ValueError, match="present_mask length"):
        estimate_tau(
            arr, EPOCHS_PER_HOUR, EPOCHS_PER_DAY,
            present_mask=short_mask, min_daily_coverage=0.5,
        )
