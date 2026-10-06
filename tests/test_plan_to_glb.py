import trimesh
from shapely.geometry import Polygon

from backend.schema.plan import load_plan
from backend.services.plan_to_glb import export_glb, plan_to_scene


def test_glb_export(tmp_path):
    plan = load_plan("data/plans/PROP_1002.json")
    out = export_glb(plan, tmp_path / "m.glb")
    scene = trimesh.load(out, force="scene")
    assert len(scene.geometry) > 10
    height = scene.extents[1]  # glTF is y-up
    assert 2.6 < height < 2.9


def test_walls_have_openings():
    plan = load_plan("data/plans/PROP_1002.json")
    floor = plan.floors[0]
    scene = plan_to_scene(plan)
    door_wall = floor.doors[0].wall_id
    wall_mesh = scene.geometry[f"L0_wall_{door_wall}"]
    wall = next(w for w in floor.walls if w.id == door_wall)
    full = trimesh.creation.extrude_polygon(Polygon(wall.polygon), wall.height_m)
    assert wall_mesh.volume < full.volume  # door cut out of the wall
