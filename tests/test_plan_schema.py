import json

import pytest

from backend.schema.plan import (SCHEMA_VERSION, Floor, Plan, Room, ScaleInfo,
                                 load_plan, save_plan)


def make_plan(source="cubicasa_lookalike"):
    rooms = [
        Room(id="R0", type="bedroom", polygon=[(0, 0), (3, 0), (3, 4), (0, 4)], area_sqm=12.0),
        Room(id="R1", type="bathroom", polygon=[(3, 0), (5, 0), (5, 2), (3, 2)], area_sqm=4.0),
        Room(id="R2", type="outdoor", polygon=[(0, 4), (5, 4), (5, 5), (0, 5)], area_sqm=5.0),
    ]
    plan = Plan(plan_id="t", source=source, scale=ScaleInfo(method="native"),
                floors=[Floor(level=0, rooms=rooms)], total_area_sqm=0)
    plan.recompute_total_area()
    return plan


def test_round_trip(tmp_path):
    plan = make_plan()
    path = save_plan(plan, tmp_path / "plan.json")
    loaded = load_plan(path)
    assert loaded == plan
    assert json.loads(path.read_text())["schema_version"] == SCHEMA_VERSION


def test_total_area_excludes_outdoor():
    assert make_plan().total_area_sqm == 16.0


def test_counts_and_source_warning():
    plan = make_plan("generated")
    assert plan.count("bedroom") == 1 and plan.count("bathroom") == 1
    assert "AI-generated" in plan.source_warning


def test_rejects_unknown_schema_version(tmp_path):
    path = save_plan(make_plan(), tmp_path / "plan.json")
    data = json.loads(path.read_text())
    data["schema_version"] = 2
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_plan(path)


def test_real_plans_load():
    plan = load_plan("data/plans/PROP_1002.json")
    assert plan.source == "cubicasa_lookalike" and plan.source_ref == "cubicasa:9623"
