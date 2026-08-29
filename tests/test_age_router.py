from app.config.hospital_profile import load_hospital_profile
from app.scoring import age_router

PROFILE = load_hospital_profile("default")


def test_routes_paediatric_adult_geriatric():
    assert age_router.route(3, PROFILE).age_band == "PAEDIATRIC"
    assert age_router.route(30, PROFILE).age_band == "ADULT"
    assert age_router.route(70, PROFILE).age_band == "GERIATRIC"


def test_boundary_ages():
    assert age_router.route(15.99, PROFILE).age_band == "PAEDIATRIC"
    assert age_router.route(16, PROFILE).age_band == "ADULT"
    assert age_router.route(64.99, PROFILE).age_band == "ADULT"
    assert age_router.route(65, PROFILE).age_band == "GERIATRIC"


def test_unknown_age_does_not_default_to_adult():
    result = age_router.route(None, PROFILE)
    assert result.age_band is None
    assert "not recorded" in result.reason
