import json
import re

from shapely.geometry import Point, Polygon

from backend.schema.plan import load_plan
from backend.services.walkthrough import build_walkthrough, viewer_hints


def test_spawn_is_inside_entry_room():
    plan = load_plan("data/plans/PROP_1002.json")
    hints = viewer_hints(plan)
    floor = hints["floors"][0]
    entries = [r for r in plan.floors[0].rooms if r.type == "entry"]
    assert any(Polygon(r.polygon).contains(Point(floor["spawn"])) for r in entries)
    assert hints["source_warning"].startswith("Representative layout")


def test_every_floor_gets_a_spawn_point():
    plan = load_plan("data/plans/PROP_1001.json")   # two-floor plan 4770
    hints = viewer_hints(plan)
    assert [f["level"] for f in hints["floors"]] == [0, 1]
    for f, fh in zip(plan.floors, hints["floors"]):
        assert any(Polygon(r.polygon).buffer(1e-6).contains(Point(fh["spawn"])) for r in f.rooms)


def test_html_is_self_contained(tmp_path):
    out = build_walkthrough("data/plans/PROP_1002.json", tmp_path / "w.html",
                            listing={"property_id": "PROP_1002", "title": "Test </script> title"})
    html = out.read_text(encoding="utf-8")
    assert "__PLAN_JSON__" not in html and "__GLB_B64__" not in html
    assert html.count("</script>") == html.count("<script")       # nothing broke out of a JSON block
    plan_json = re.search(r'id="plan-data">(.*?)</script>', html, re.S).group(1)
    assert json.loads(plan_json)["schema_version"] == 1
