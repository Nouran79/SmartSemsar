import pytest

from data.scripts.extract_cubecasa import (build_plan, feet_inches_to_m,
                                           parse_svg)

SVG = "data/cubicasa_svg/12803.svg"


@pytest.fixture(scope="module")
def raw():
    return parse_svg(SVG)


def test_feet_inches():
    assert feet_inches_to_m("8'4\" x 12'10\"") == pytest.approx([2.54, 3.912], abs=1e-3)


def test_native_scale_from_labels(raw):
    # CubiCasa drawings are ~1 px = 1 cm
    assert raw["px_per_m"] == pytest.approx(100, rel=0.03)


def test_native_area_is_realistic(raw):
    plan = build_plan(raw, "t", source="user_upload", target_area_sqm=132.5)
    # user uploads keep their own scale; listing area is only a check
    assert plan.scale.method == "native" and plan.scale.factor == 1.0
    assert 35 < plan.total_area_sqm < 50  # 2-bedroom Finnish flat, ~43 m²


@pytest.mark.parametrize("target", [60.0, 132.5, 250.0])
def test_lookalike_fitted_to_listing_area(raw, target):
    plan = build_plan(raw, "t", source="cubicasa_lookalike", target_area_sqm=target)
    assert plan.scale.method == "fit_listing_area"
    assert plan.total_area_sqm == pytest.approx(target, rel=0.01)
    # uniform scaling: linear factor = sqrt(area ratio)
    assert plan.scale.factor == pytest.approx((target / plan.scale.native_area_sqm) ** 0.5, rel=1e-3)


def test_floor_detection():
    assert len(parse_svg("data/cubicasa_svg/4770.svg")["floors"]) == 2
    assert len(parse_svg("data/cubicasa_svg/12803.svg")["floors"]) == 1


def test_geometry_counts(raw):
    plan = build_plan(raw, "t", target_area_sqm=100)
    f = plan.floors[0]
    assert plan.count("bedroom") == 2 and plan.count("bathroom") == 2
    assert f.walls and f.doors and f.windows
    wall_ids = {w.id for w in f.walls}
    assert all(d.wall_id in wall_ids for d in f.doors + f.windows)
