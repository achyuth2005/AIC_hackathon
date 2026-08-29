"""
Shared table-evaluation primitives used by both NEWS2 and PEWS scoring
(Phase 3.2: "Vital sign abnormality flagging -> Deterministic, age-banded
tables ... must be inspectable, reproducible and configurable per
hospital"). One evaluator per table *shape*, reused across parameters and
frameworks, so a clinician correcting a threshold only ever edits YAML
(app/config/hospital_profiles/*.yaml) and never touches this code.
"""
from __future__ import annotations

from typing import Dict, List

from app.config.hospital_profile import AcuityBand, RangeBand


class UnbandedValueError(ValueError):
    """Raised when a value matches none of a configured table's bands --
    always a configuration gap (bands should be exhaustive), never treated
    as 0/normal by default (Phase 3.3 'missing is not normal' applies
    equally to 'unbanded is not normal')."""


def evaluate_range_bands(value: float, bands: List[RangeBand]) -> int:
    for band in bands:
        lower_ok = band.min is None or value >= band.min
        upper_ok = band.max is None or value <= band.max
        if lower_ok and upper_ok:
            return band.points
    raise UnbandedValueError(f"value {value} matched no configured range band in {bands!r}")


def evaluate_acuity_bands(aggregate_score: float, bands: List[AcuityBand]) -> int:
    for band in bands:
        lower_ok = aggregate_score >= band.min_score
        upper_ok = band.max_score is None or aggregate_score <= band.max_score
        if lower_ok and upper_ok:
            return band.esi_level
    raise UnbandedValueError(f"aggregate score {aggregate_score} matched no configured acuity band in {bands!r}")


def evaluate_coded_points(code: str, mapping: Dict[str, int]) -> int:
    if code not in mapping:
        raise UnbandedValueError(f"code {code!r} is not in the configured mapping {sorted(mapping)!r}")
    return mapping[code]


def deviation_points(value: float, low: float, high: float, thresholds: List[float]) -> int:
    """Phase 3.3 PEWS design (see PEWSConfig docstring): 0 points inside
    [low, high]; otherwise points scale with how far outside, as a fraction
    of the bound crossed. `thresholds` must be ascending, e.g. [0.15, 0.30]
    -> <=15% over/under = 1 point, <=30% = 2 points, beyond that = 3
    points (len(thresholds) + 1)."""
    if low <= value <= high:
        return 0

    if value < low:
        deviation = (low - value) / low if low != 0 else float("inf")
    else:
        deviation = (value - high) / high if high != 0 else float("inf")

    for i, threshold in enumerate(thresholds):
        if deviation <= threshold:
            return i + 1
    return len(thresholds) + 1
