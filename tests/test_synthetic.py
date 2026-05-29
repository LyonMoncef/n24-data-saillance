import numpy as np
import pandas as pd
import pytest

from n24sal.synthetic import generate_synthetic_actigraphy


def test_synthetic_basic_shape():
    df = generate_synthetic_actigraphy(n_days=7, epoch_seconds=60)
    assert len(df) == 7 * 1440
    assert set(df.columns) == {"timestamp", "activity"}
    assert (df["activity"] >= 0).all()
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    assert df["timestamp"].dt.tz is not None


def test_synthetic_reproducible_with_seed():
    df1 = generate_synthetic_actigraphy(n_days=3, seed=42)
    df2 = generate_synthetic_actigraphy(n_days=3, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_synthetic_seed_changes_realisation():
    df1 = generate_synthetic_actigraphy(n_days=3, seed=1)
    df2 = generate_synthetic_actigraphy(n_days=3, seed=2)
    assert not np.allclose(df1["activity"].to_numpy(), df2["activity"].to_numpy())


def test_synthetic_rejects_non_dividing_epoch_seconds():
    with pytest.raises(ValueError, match="divide 86400"):
        generate_synthetic_actigraphy(n_days=3, epoch_seconds=37)


def test_synthetic_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="n_days"):
        generate_synthetic_actigraphy(n_days=0)
    with pytest.raises(ValueError, match="tau_hours"):
        generate_synthetic_actigraphy(n_days=3, tau_hours=0.0)


def test_synthetic_n24_has_higher_variance_than_pure_noise():
    df = generate_synthetic_actigraphy(n_days=7, tau_hours=24.7, noise_sd=5.0, seed=0)
    assert df["activity"].std() > 5.0
