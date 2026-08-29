"""
Tests for app/ml/synthetic_data.py (Phase 16.3): shape, reproducibility,
and the "realistic class imbalance, not a balanced set" requirement.
"""
import numpy as np

from app.ml.features import FEATURE_NAMES
from app.ml.synthetic_data import TARGET_LABEL_DEFINITION, generate_dataset


def test_target_label_is_explicitly_defined():
    """Phase 16.1: 'Define the label explicitly and put the definition on
    a slide.' Not a numeric check -- just guards against this constant
    being silently deleted/emptied later."""
    assert len(TARGET_LABEL_DEFINITION) > 50
    assert "critical outcome" in TARGET_LABEL_DEFINITION.lower()


def test_shape_and_no_missing_values():
    X, y, ages = generate_dataset(n_samples=500, seed=1)
    assert X.shape == (500, len(FEATURE_NAMES))
    assert y.shape == (500,)
    assert ages.shape == (500,)
    assert not np.isnan(X).any()


def test_reproducible_with_same_seed():
    X1, y1, ages1 = generate_dataset(n_samples=200, seed=7)
    X2, y2, ages2 = generate_dataset(n_samples=200, seed=7)
    assert np.array_equal(X1, X2)
    assert np.array_equal(y1, y2)
    assert np.array_equal(ages1, ages2)


def test_different_seeds_differ():
    X1, _, _ = generate_dataset(n_samples=200, seed=1)
    X2, _, _ = generate_dataset(n_samples=200, seed=2)
    assert not np.array_equal(X1, X2)


def test_realistic_class_imbalance_not_a_balanced_set():
    """Phase 16.3: 'Deliberately generate a realistic class imbalance
    rather than a balanced set.'"""
    _, y, _ = generate_dataset(n_samples=5000, seed=42)
    positive_rate = y.mean()
    assert 0.03 < positive_rate < 0.25  # a minority class, not ~50/50


def test_ages_span_all_three_bands():
    _, _, ages = generate_dataset(n_samples=2000, seed=42)
    assert (ages < 16).any()
    assert ((ages >= 16) & (ages < 65)).any()
    assert (ages >= 65).any()
