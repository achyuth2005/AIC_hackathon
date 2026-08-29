"""
PEWS-style paediatric scoring (Phase 3.3 Layer 2, paediatric backbone).

See PEWSConfig's docstring (app/config/hospital_profile.py) for the
deliberate design simplification here: respiratory rate, heart rate and
systolic BP are scored by deviation from an age-band-specific normal range
rather than hand-authored point tables, because no single canonical PEWS
point table is cited in the source architecture document to reproduce
faithfully (and it explicitly says not to reproduce copyrighted charts
anyway). [Requires clinical validation] end to end.

SpO2, temperature, consciousness and work-of-breathing follow the same
banded/coded pattern as NEWS2 (news2.py) -- Phase 3.3: "qualitative signs
such as work of breathing and consciousness matter more than numbers" for
this age group, which is why work_of_breathing is scored at all (NEWS2 has
no equivalent parameter).
"""
from __future__ import annotations

from typing import Dict, Optional

from app.config.hospital_profile import PEWSAgeBand, PEWSConfig
from app.models.enums import MeasurementStatus
from app.scoring import concepts
from app.scoring.banding import deviation_points, evaluate_acuity_bands, evaluate_coded_points, evaluate_range_bands
from app.scoring.models import ClinicalScoreResult, ScoreComponent, VitalReading

_LABELS = {
    concepts.RESP_RATE: "Respiratory rate",
    concepts.SPO2: "Oxygen saturation (SpO2)",
    concepts.SUPPLEMENTAL_OXYGEN: "Supplemental oxygen",
    concepts.SYSTOLIC_BP: "Systolic blood pressure",
    concepts.HEART_RATE: "Heart rate",
    concepts.CONSCIOUSNESS_LEVEL: "Consciousness (AVPU)",
    concepts.TEMPERATURE: "Temperature",
    concepts.WORK_OF_BREATHING: "Work of breathing",
}


def _missing_component(concept_code: str, reading: Optional[VitalReading]) -> Optional[ScoreComponent]:
    if reading is None:
        return ScoreComponent(concept_code=concept_code, label=_LABELS[concept_code], is_missing=True, missing_reason="NO_OBSERVATION_RECORDED")
    if reading.measurement_status != MeasurementStatus.MEASURED:
        return ScoreComponent(
            concept_code=concept_code, label=_LABELS[concept_code], is_missing=True,
            missing_reason=reading.measurement_status.value,
            observation_id=reading.observation_id, observed_at=reading.observed_at,
            reliability_tier=reading.reliability_tier,
        )
    if reading.is_stale:
        return ScoreComponent(
            concept_code=concept_code, label=_LABELS[concept_code], raw_value=reading.value,
            is_missing=True, missing_reason="STALE",
            observation_id=reading.observation_id, observed_at=reading.observed_at,
            reliability_tier=reading.reliability_tier,
        )
    return None


def _score_deviation_parameter(concept_code, reading, normal_range, thresholds, unit=None) -> ScoreComponent:
    missing = _missing_component(concept_code, reading)
    if missing is not None:
        return missing
    low, high = normal_range
    points = deviation_points(reading.value, low, high, thresholds)
    return ScoreComponent(
        concept_code=concept_code, label=_LABELS[concept_code], raw_value=reading.value, unit=unit,
        points=points, observation_id=reading.observation_id, observed_at=reading.observed_at,
        reliability_tier=reading.reliability_tier,
    )


def _score_range_parameter(concept_code, reading, bands, unit=None) -> ScoreComponent:
    missing = _missing_component(concept_code, reading)
    if missing is not None:
        return missing
    points = evaluate_range_bands(reading.value, bands)
    return ScoreComponent(
        concept_code=concept_code, label=_LABELS[concept_code], raw_value=reading.value, unit=unit,
        points=points, observation_id=reading.observation_id, observed_at=reading.observed_at,
        reliability_tier=reading.reliability_tier,
    )


def _score_coded_parameter(concept_code, reading, mapping: Dict[str, int]) -> ScoreComponent:
    missing = _missing_component(concept_code, reading)
    if missing is not None:
        return missing
    points = evaluate_coded_points(reading.value, mapping)
    return ScoreComponent(
        concept_code=concept_code, label=_LABELS[concept_code], raw_value=reading.value,
        points=points, observation_id=reading.observation_id, observed_at=reading.observed_at,
        reliability_tier=reading.reliability_tier,
    )


def _score_supplemental_oxygen(reading: Optional[VitalReading], points_if_on: int) -> ScoreComponent:
    missing = _missing_component(concepts.SUPPLEMENTAL_OXYGEN, reading)
    if missing is not None:
        return missing
    points = points_if_on if bool(reading.value) else 0
    return ScoreComponent(
        concept_code=concepts.SUPPLEMENTAL_OXYGEN, label=_LABELS[concepts.SUPPLEMENTAL_OXYGEN],
        raw_value=bool(reading.value), points=points,
        observation_id=reading.observation_id, observed_at=reading.observed_at,
        reliability_tier=reading.reliability_tier,
    )


def score_pews(
    readings: Dict[str, Optional[VitalReading]],
    config: PEWSConfig,
    age_sub_band: PEWSAgeBand,
) -> ClinicalScoreResult:
    components = [
        _score_deviation_parameter(concepts.RESP_RATE, readings.get(concepts.RESP_RATE), age_sub_band.respiratory_rate_normal, config.deviation_band_thresholds, "breaths/min"),
        _score_range_parameter(concepts.SPO2, readings.get(concepts.SPO2), config.spo2_scale1, "%"),
        _score_supplemental_oxygen(readings.get(concepts.SUPPLEMENTAL_OXYGEN), config.supplemental_oxygen_points),
        _score_deviation_parameter(concepts.SYSTOLIC_BP, readings.get(concepts.SYSTOLIC_BP), age_sub_band.systolic_bp_normal, config.deviation_band_thresholds, "mmHg"),
        _score_deviation_parameter(concepts.HEART_RATE, readings.get(concepts.HEART_RATE), age_sub_band.heart_rate_normal, config.deviation_band_thresholds, "bpm"),
        _score_coded_parameter(concepts.CONSCIOUSNESS_LEVEL, readings.get(concepts.CONSCIOUSNESS_LEVEL), config.consciousness_points),
        _score_range_parameter(concepts.TEMPERATURE, readings.get(concepts.TEMPERATURE), config.temperature, "°C"),
        _score_coded_parameter(concepts.WORK_OF_BREATHING, readings.get(concepts.WORK_OF_BREATHING), config.work_of_breathing_points),
    ]

    present_points = [c.points for c in components if not c.is_missing]
    has_missing = any(c.is_missing for c in components)
    aggregate = sum(present_points) if present_points else (0 if not has_missing else None)

    single_param_escalation = any(
        (not c.is_missing) and c.points is not None and c.points >= config.single_parameter_red_threshold
        for c in components
    )
    escalation_reason = None
    if single_param_escalation:
        fired = [c.label for c in components if not c.is_missing and c.points is not None and c.points >= config.single_parameter_red_threshold]
        escalation_reason = f"Single-parameter escalation: {', '.join(fired)} scored >= {config.single_parameter_red_threshold}."

    if aggregate is not None:
        aggregate_acuity = evaluate_acuity_bands(aggregate, config.aggregate_to_esi)
    else:
        aggregate_acuity = config.missing_data_cap_esi_level

    candidate_acuities = [aggregate_acuity]
    if single_param_escalation:
        candidate_acuities.append(config.single_parameter_escalation_esi_level)
    if has_missing:
        candidate_acuities.append(config.missing_data_cap_esi_level)

    rule_acuity = min(candidate_acuities)
    cap_applied = has_missing and rule_acuity == config.missing_data_cap_esi_level

    reason_parts = [
        f"PEWS[{age_sub_band.name}] aggregate={aggregate if aggregate is not None else 'n/a'} -> ESI {aggregate_acuity}"
    ]
    if single_param_escalation:
        reason_parts.append(escalation_reason)
    if has_missing:
        reason_parts.append(f"missing/stale data present -> capped at ESI {config.missing_data_cap_esi_level}")

    return ClinicalScoreResult(
        framework="PEWS",
        age_band=age_sub_band.name,
        aggregate_score=aggregate,
        framework_acuity=rule_acuity,  # pre-Layer-4 value; engine.py may lower rule_acuity further
        rule_acuity=rule_acuity,
        components=components,
        single_parameter_escalation=single_param_escalation,
        single_parameter_escalation_reason=escalation_reason,
        missing_data_cap_applied=cap_applied,
        has_any_missing_or_stale=has_missing,
        reason="; ".join(reason_parts),
    )
