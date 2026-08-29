from app.config.hospital_profile import load_hospital_profile


def test_default_profile_loads_and_resolves_age_bands():
    profile = load_hospital_profile("default")

    assert profile.acuity_framework == "ESI-5"
    assert profile.age_band_for(3) == "PAEDIATRIC"
    assert profile.age_band_for(15.9) == "PAEDIATRIC"
    assert profile.age_band_for(16) == "ADULT"
    assert profile.age_band_for(64.9) == "ADULT"
    assert profile.age_band_for(65) == "GERIATRIC"
    assert profile.age_band_for(90) == "GERIATRIC"


def test_reassessment_intervals_are_inversely_proportional_to_urgency():
    profile = load_hospital_profile("default")
    m2 = profile.reassessment_minutes_for(2)
    m3 = profile.reassessment_minutes_for(3)
    m5 = profile.reassessment_minutes_for(5)
    assert m2 < m3 < m5


def test_resource_scope_matches_phase_6_1_mvp_decision():
    profile = load_hospital_profile("default")
    assert set(profile.resource_types_enabled) == {"CLINICIAN", "TREATMENT_SPACE", "RESUSCITATION_BAY"}
