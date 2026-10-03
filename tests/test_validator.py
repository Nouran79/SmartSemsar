import pytest

from backend.schema.plan import load_plan
from backend.services.plan_validator import infer_property_type, validate_plan
from data.scripts.extract_cubecasa import build_plan, parse_svg

LISTING = {"title": "Apartment for rent", "pf_bedrooms": 2, "pf_bathrooms": 2, "pf_area_sqm": 132.5}


@pytest.fixture(scope="module")
def flat_plan():
    return build_plan(parse_svg("data/cubicasa_svg/12803.svg"), "t", target_area_sqm=132.5)


@pytest.mark.parametrize("title,expected", [
    ("Duplex apartment for rent, 220 m, Smouha", "duplex"),
    ("Studio for Rent – Banafseg Villas, New Cairo First", "studio"),
    ("Townhouse corner for rent", "townhouse"),
    ("stand alone for rent", "villa"),
    ("شقة للايجار اكسترا سكن", "apartment"),
    ("Luxurious Living in the Heart of Hyde Park!", "unknown"),
])
def test_infer_property_type(title, expected):
    assert infer_property_type(title) == expected


def test_matching_listing_is_approved(flat_plan):
    res = validate_plan(flat_plan, LISTING)
    assert res["approved"] is True
    assert {c["name"] for c in res["checks"]} == {"bedrooms", "bathrooms", "total_area", "floors_vs_type"}
    assert "Representative layout" in res["source_warning"]
    assert any("scaled" in w for w in res["warnings"])  # x1.76 stretch


def test_bedroom_mismatch_rejected(flat_plan):
    res = validate_plan(flat_plan, {**LISTING, "pf_bedrooms": 3})
    assert res["approved"] is False
    assert [c["name"] for c in res["checks"] if not c["passed"]] == ["bedrooms"]


def test_area_outside_tolerance_rejected():
    # user upload keeps its native ~43 m² -> fails against a 132.5 m² listing
    plan = build_plan(parse_svg("data/cubicasa_svg/12803.svg"), "t", source="user_upload",
                      target_area_sqm=132.5)
    res = validate_plan(plan, LISTING)
    assert not next(c for c in res["checks"] if c["name"] == "total_area")["passed"]


def test_two_floor_plan_rejected_for_apartment():
    # known problem: plan 4770 (two-floor townhouse) on an apartment listing
    plan = load_plan("data/plans/PROP_1001.json")
    res = validate_plan(plan, {**LISTING, "pf_bedrooms": 3, "pf_bathrooms": 3, "pf_area_sqm": 189.0})
    floors = next(c for c in res["checks"] if c["name"] == "floors_vs_type")
    assert floors["passed"] is False and res["approved"] is False
    assert validate_plan(plan, {**LISTING, "title": "Townhouse", "pf_bedrooms": 3,
                                "pf_bathrooms": 3, "pf_area_sqm": 189.0})["approved"] is True
