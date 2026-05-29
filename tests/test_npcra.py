import numpy as np
import pytest

from n24sal.npcra import (
    circadian_function_index,
    interdaily_stability,
    intradaily_variability,
    l5_m10,
    relative_amplitude,
)
from n24sal.npcra.tau import estimate_tau, m10_phases_per_day
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
