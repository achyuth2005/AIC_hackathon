"""
Training script for the ML Risk Challenger (Phase 3.3 Layer 3, Phase 16).

Phase 15's own stack recommendation: "scikit-learn (logistic regression and
gradient boosting) with probability calibration ... Interpretable, trains
in seconds, calibration is the point." This uses LogisticRegression (the
simpler of the two named options) inside a CalibratedClassifierCV, per
Phase 3.3's "Hackathon recommendation: build Layer 3 as a simple calibrated
model ... honestly presented as a mechanism demonstration."

Phase 16.5: report sensitivity/recall, false-negative COUNT, calibration
(Brier score), AUPRC and per-age-band recall as the PRIMARY metrics.
Accuracy is deliberately never computed here -- "with realistic class
imbalance it is meaningless and a knowledgeable judge will say so."

Run directly: `python -m app.ml.train` (regenerates the artifact in
app/ml/artifacts/). Not run automatically at API startup -- the challenger
loads whatever artifact already exists (app/ml/challenger.py).
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional

import numpy as np
from joblib import dump
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.config.hospital_profile import load_hospital_profile
from app.ml.features import FEATURE_NAMES
from app.ml.synthetic_data import TARGET_LABEL_DEFINITION, generate_dataset

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "model.joblib")
METADATA_PATH = os.path.join(ARTIFACT_DIR, "metadata.json")

MODEL_VERSION = "ml-challenger-v1"

# [Requires clinical validation]: a missed critical patient is weighted 10x
# a false alarm, per the problem statement's own "under-triage is
# categorically worse" framing -- but the specific ratio is this project's
# choice, not a clinician's. Phase 16.5: "choose it with a clinician and
# say who."
FN_TO_FP_COST_RATIO = 10.0

# [Requires clinical validation]: the operating point at which metrics are
# REPORTED and which app/ml/challenger.py's default probability_to_esi
# band is built around. sklearn's own predict() uses a fixed 0.5 cutoff,
# which is the wrong number to report against here -- Phase 3.3 and the
# problem statement both require the system to be "deliberately tuned to
# bias toward escalation under uncertainty", so the threshold used for
# every metric below is chosen to hit this recall floor, trading precision
# for it deliberately rather than reporting sklearn's default and calling
# it a day.
TARGET_RECALL = 0.85


def _choose_operating_threshold(y_true: np.ndarray, probs: np.ndarray, target_recall: float) -> float:
    """Highest probability threshold whose recall is still >= target_recall
    -- maximizes precision subject to the recall floor, rather than picking
    the lowest (most trivial) threshold that clears it."""
    precisions, recalls, thresholds = precision_recall_curve(y_true, probs)
    # precision_recall_curve returns len(thresholds) == len(precisions) - 1;
    # recalls/precisions are monotonically non-increasing/non-decreasing
    # respectively as threshold rises, evaluated at thresholds[i].
    candidates = [t for t, r in zip(thresholds, recalls[:-1]) if r >= target_recall]
    if not candidates:
        return 0.0  # target recall unreachable even at threshold 0 -- escalate on everything
    return float(max(candidates))


def _per_age_band_recall(preds: np.ndarray, y: np.ndarray, ages: np.ndarray, profile) -> dict:
    bands: dict = {}
    for band_name in ["PAEDIATRIC", "ADULT", "GERIATRIC"]:
        mask = np.array([profile.age_band_for(a) == band_name for a in ages])
        n = int(mask.sum())
        n_positive = int(y[mask].sum()) if n > 0 else 0
        if n == 0 or n_positive == 0:
            # Small test slices can land here, especially for PAEDIATRIC at
            # a modest n_samples -- reported explicitly as "no positive
            # cases in this test slice" rather than a misleading recall of
            # 0.0 (which would look like the model failed, when really
            # there was nothing to detect).
            bands[band_name] = {"n": n, "n_positive": n_positive, "recall": None}
            continue
        bands[band_name] = {
            "n": n,
            "n_positive": n_positive,
            "recall": float(recall_score(y[mask], preds[mask], zero_division=0)),
        }
    return bands


def train_and_save(n_samples: int = 8000, seed: int = 42, out_dir: Optional[str] = None) -> dict:
    """Generates data, trains, evaluates, and saves the artifact. Returns
    the metadata dict (same content written to METADATA_PATH) so callers
    (tests, a CLI) can assert on it directly without re-reading the file."""
    X, y, ages = generate_dataset(n_samples=n_samples, seed=seed)
    X_train, X_test, y_train, y_test, ages_train, ages_test = train_test_split(
        X, y, ages, test_size=0.25, random_state=seed, stratify=y
    )

    base_pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    # Probability calibration (Phase 15): an escalation-only design depends
    # on the probability meaning something, not just the class prediction.
    model = CalibratedClassifierCV(base_pipeline, method="sigmoid", cv=5)
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)[:, 1]
    operating_threshold = _choose_operating_threshold(y_test, probs, TARGET_RECALL)
    preds = (probs >= operating_threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
    cost = FN_TO_FP_COST_RATIO * fn + fp

    metrics = {
        "n_train": len(y_train),
        "n_test": len(y_test),
        "positive_rate_test": float(y_test.mean()),
        "operating_threshold": operating_threshold,
        "target_recall": TARGET_RECALL,
        # Primary (Phase 16.5):
        "recall_sensitivity": float(recall_score(y_test, preds, zero_division=0)),
        "false_negative_count": int(fn),
        "brier_score": float(brier_score_loss(y_test, probs)),  # calibration is threshold-independent, unaffected
        "auprc": float(average_precision_score(y_test, probs)),  # also threshold-independent
        "per_age_band": _per_age_band_recall(preds, y_test, ages_test, load_hospital_profile("default")),
        # Secondary (Phase 16.5):
        "precision": float(precision_score(y_test, preds, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if (tn + fp) > 0 else None,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "cost_weighted": {"fn_to_fp_ratio": FN_TO_FP_COST_RATIO, "total_cost": float(cost)},
    }

    artifact_dir = out_dir or ARTIFACT_DIR
    os.makedirs(artifact_dir, exist_ok=True)
    model_path = os.path.join(artifact_dir, "model.joblib")
    metadata_path = os.path.join(artifact_dir, "metadata.json")

    dump(model, model_path)
    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_label_definition": TARGET_LABEL_DEFINITION,  # Phase 16.1: travels with the artifact, not just the source
        "feature_names": FEATURE_NAMES,
        "n_samples_generated": n_samples,
        "seed": seed,
        "metrics": metrics,
        "notes": (
            "Trained entirely on synthetic data from app/ml/synthetic_data.py "
            "(documented generative process, not a clinical dataset). This "
            "demonstrates the escalation-only mechanism (Phase 3.3 Layer 3) and "
            "is NOT clinically validated. Production use requires the Phase "
            "16.4 path: retrospective data, clinician-adjudicated labels, "
            "subgroup evaluation, silent shadow mode, then escalation-only "
            "deployment."
        ),
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return metadata


if __name__ == "__main__":
    result = train_and_save()
    print(json.dumps(result["metrics"], indent=2))
