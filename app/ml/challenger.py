"""
Runtime ML Risk Challenger (Phase 3.3 Layer 3).

Loads the artifact app/ml/train.py produces (model.joblib + metadata.json)
once and serves predictions. This module NEVER decides acuity by itself --
it produces a probability and a suggested ESI level; the orchestrator
(app/scoring/risk_orchestrator.py) is what actually folds it into
final_acuity = min(rule_acuity, ml_suggested_acuity, ...), and it can only
ever raise (lower the ESI number), never lower it (Phase 3.1).

Phase 9.5 failure mode: if no artifact exists, or profile.ml_challenger is
disabled, `predict()` returns None. Callers must treat None as "ML
unavailable -> rules-only acuity", exactly like a network-down LLM -- never
as "ML suggests no escalation" (those are different facts).
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel

from app.config.hospital_profile import HospitalProfile
from app.ml.features import MLFeatures
from app.ml.train import METADATA_PATH, MODEL_PATH
from app.scoring.banding import evaluate_acuity_bands

logger = logging.getLogger(__name__)


class MLPrediction(BaseModel):
    probability: float
    suggested_acuity: int
    model_version: str


class _LoadedArtifact:
    __slots__ = ("model", "model_version")

    def __init__(self, model, model_version: str):
        self.model = model
        self.model_version = model_version


@lru_cache(maxsize=1)
def _load_artifact() -> Optional[_LoadedArtifact]:
    if not (os.path.exists(MODEL_PATH) and os.path.exists(METADATA_PATH)):
        return None
    from joblib import load  # deferred: keeps a missing artifact cheap to detect without importing joblib eagerly

    # Audit finding (Medium, dimension 4): this module's own docstring
    # promises "if no artifact exists ... predict() returns None", i.e.
    # degrade to rules-only, never crash the request. That promise was only
    # kept for a *missing* file -- a present-but-corrupt/incompatible one
    # (partial disk write, a joblib/sklearn version mismatch after an
    # upgrade, truncated metadata JSON) raised straight out of every
    # scoring call with no fallback. Any failure to load now degrades to
    # "ML unavailable" exactly like a missing artifact, logged loudly so
    # it's operationally visible without taking scoring down with it.
    try:
        model = load(MODEL_PATH)
        with open(METADATA_PATH) as f:
            metadata = json.load(f)
        return _LoadedArtifact(model=model, model_version=metadata["model_version"])
    except Exception:
        logger.exception(
            "ML challenger artifact at %s/%s exists but failed to load; "
            "degrading to rules-only scoring for this process.",
            MODEL_PATH, METADATA_PATH,
        )
        return None


def reset_artifact_cache() -> None:
    """Test/ops hook: call after retraining so a running process picks up
    the new artifact without a restart."""
    _load_artifact.cache_clear()


class MLChallenger:
    def __init__(self, profile: HospitalProfile):
        self.profile = profile

    def predict(self, features: MLFeatures) -> Optional[MLPrediction]:
        if not self.profile.ml_challenger.enabled:
            return None
        artifact = _load_artifact()
        if artifact is None:
            return None

        vector = [features.to_vector()]
        probability = float(artifact.model.predict_proba(vector)[0][1])
        suggested_acuity = evaluate_acuity_bands(probability, self.profile.ml_challenger.probability_to_esi)
        return MLPrediction(
            probability=probability, suggested_acuity=suggested_acuity, model_version=artifact.model_version
        )
