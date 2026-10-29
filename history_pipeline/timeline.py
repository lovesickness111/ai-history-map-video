"""Validated, Blender-independent timeline and reproducible town layout."""
from __future__ import annotations

import copy
import json
import math
import random
import hashlib
from pathlib import Path

MODEL_IDS = {"chua_mot_cot", "cot_co", "nha_co"}
MODEL_PARAMS = {
    "chua_mot_cot": {"size"}, "cot_co": {"size"},
    "nha_co": {"width", "depth", "height", "variant"},
}
STAGE_COUNTS = {"chua_mot_cot": 4, "cot_co": 5, "nha_co": 3}
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMELINE = ROOT / "data" / "hanoi_timeline.json"


def _number(value, name, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f"{name}: expected a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name}: must be >= {minimum}")
    return value


def _integer(value, name, minimum=1):
    _number(value, name, minimum)
    if not isinstance(value, int):
        raise ValueError(f"{name}: expected an integer")
    return value


def _vector(value, name, positive=False):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name}: expected [x, y, z]")
    for component in value:
        _number(component, name)
        if positive and component <= 0:
            raise ValueError(f"{name}: components must be positive")


def town_instances(seed=1049, layout="compact"):
    """Fixed lots, jittered dimensions; never rejection-sample occupied space."""
    rng = random.Random(seed)
    if layout == "district":
        lots = [(-5+bx*4.65+col*1.02, -14.1+by*7.1+row*1.3)
                for by in range(4) for bx in range(6) for row in range(5) for col in range(4)]
    elif layout == "compact":
        lots = [(x, y) for y in (-5.25, -3.75, -2.25, -.75, .75, 2.25, 3.75, 5.25)
                for x in (-.5, .55, 1.6, 2.65, 3.7, 4.75)]
    else:
        raise ValueError(f"Unknown town layout: {layout}")
    rng.shuffle(lots)
    result = []
    wave_size = len(lots)//3
    for i, (x, y) in enumerate(lots):
        offset = round((i%wave_size)*30/(wave_size-1))
        start = (241, 421, 781)[i // wave_size] + offset
        width = rng.choice((.68,.72,.76)) if layout=="district" else round(rng.uniform(.70,.82),4)
        depth = rng.choice((.91,.97,1.03)) if layout=="district" else round(rng.uniform(.91,1.0),4)
        height = rng.choice((.62,.78,.95,1.12,1.32)) if layout=="district" else round(rng.uniform(.58,1.),4)
        result.append({
            "id": f"house_{i + 1:02d}", "model_id": "nha_co", "seed": seed + i,
            "position": [x, y, .025], "rotation": [0, 0, 0], "scale": [1, 1, 1],
            "start_frame": start, "end_frame": start + 24,
            "params": {"width": width, "depth": depth, "height": height, "variant": i % 5},
        })
    return result


def footprint(instance):
    """Conservative XY bounds, including roof overhang and rotated corners."""
    kind, params = instance["model_id"], instance.get("params", {})
    if kind == "nha_co":
        w, d = params.get("width", .76) + .12, params.get("depth", 1.) + .22
    else:
        w, d = {"chua_mot_cot": (3.15, 5.8), "cot_co": (3.25, 4.1)}[kind]
        w, d = w*params.get("size", 1.), d*params.get("size", 1.)
    sx, sy, _ = instance["scale"]
    a = math.radians(instance["rotation"][2])
    w, d = abs(math.cos(a))*w*sx + abs(math.sin(a))*d*sy, abs(math.sin(a))*w*sx + abs(math.cos(a))*d*sy
    x, y, _ = instance["position"]
    return (x-w/2, y-d/2, x+w/2, y+d/2)


def intersects(a, b, gap=0.):
    return not (a[2]+gap <= b[0] or b[2]+gap <= a[0] or
                a[3]+gap <= b[1] or b[3]+gap <= a[1])


def reserved_regions(profile):
    if profile=="landscape":
        regions=[(-19,-11,-6,12),(23.5,-70,33,70)]
        regions += [(x-.20,-16,x+.20,15) for x in (-5.7,-1.05,3.6,8.25,12.9,17.55,22.2)]
        regions += [(-5.9,y-.20,22.45,y+.20) for y in (-15.05,-7.95,-.85,6.25,13.35)]
        return regions
    regions=[(-7.0,-.8,-2.4,3.8),(6.,-7,9.5,7)]
    regions += [(-1.6,-6.3,-1.2,6.3),(5.4,-6.3,5.8,6.3)]
    regions += [(-1.6,y-.10,5.8,y+.10) for y in (-6,-3,0,3,6)]
    return regions


def validate_layout(instances, profile="diorama"):
    houses = [i for i in instances if i["model_id"] == "nha_co"]
    landmarks = [i for i in instances if i["model_id"] != "nha_co"]
    forbidden = reserved_regions(profile)
    forbidden += [footprint(i) for i in landmarks]
    bounds = [footprint(i) for i in houses]
    for i, box in enumerate(bounds):
        limit = (-45,-35,45,35) if profile=="landscape" else (-9.5,-6.5,9.5,6.5)
        if box[0] < limit[0] or box[1] < limit[1] or box[2] > limit[2] or box[3] > limit[3]:
            raise ValueError(f"{houses[i]['id']}: outside the diorama")
        if any(intersects(box, area, .035) for area in forbidden):
            raise ValueError(f"{houses[i]['id']}: overlaps a landmark, water, or road")
        if any(intersects(box, other, .025) for other in bounds[:i]):
            raise ValueError(f"{houses[i]['id']}: overlaps another house")


def validate(data):
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data.get("schema_version") != 1:
        raise ValueError("Expected a timeline object with schema_version=1")
    fps = _integer(data.get("fps"), "fps")
    if fps > 60:
        raise ValueError("fps must be <= 60 for centisecond ASS subtitle timing")
    total = _integer(data.get("frame_end"), "frame_end", 2)
    if total % fps:
        raise ValueError("frame_end must be divisible by fps")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise ValueError("title is required")
    anchors = data.get("anchors", [])
    if not isinstance(anchors, list) or len(anchors) < 2:
        raise ValueError("At least two year/frame anchors are required")
    prev_frame, prev_year = 0, -math.inf
    for anchor in anchors:
        if not isinstance(anchor, dict):
            raise ValueError("Every anchor must be an object")
        frame = _integer(anchor.get("frame"), "anchor.frame")
        year = _integer(anchor.get("year"), "anchor.year", 0)
        if frame <= prev_frame or frame > total or year < prev_year:
            raise ValueError("Anchors must have increasing frames and nondecreasing years")
        prev_frame, prev_year = frame, year
    if anchors[0]["frame"] != 1 or anchors[-1]["frame"] != total:
        raise ValueError("Anchors must cover frames 1 through frame_end")
    ids = set()
    instances = data.get("instances")
    if not isinstance(instances, list) or not instances:
        raise ValueError("instances must be a nonempty list")
    for item in instances:
        if not isinstance(item, dict):
            raise ValueError("Every instance must be an object")
        name = item.get("id")
        if not isinstance(name, str) or not name or name in ids:
            raise ValueError(f"Missing or duplicate instance id: {name}")
        ids.add(name)
        kind = item.get("model_id")
        if kind not in MODEL_IDS:
            raise ValueError(f"{name}: unknown model_id {kind!r}")
        _vector(item.get("position"), f"{name}.position")
        _vector(item.get("rotation"), f"{name}.rotation")
        _vector(item.get("scale"), f"{name}.scale", positive=True)
        _integer(item.get("seed"), f"{name}.seed", 0)
        start = _integer(item.get("start_frame"), f"{name}.start_frame")
        end = _integer(item.get("end_frame"), f"{name}.end_frame")
        if not 1 <= start < end <= total:
            raise ValueError(f"{name}: construction must satisfy 1 <= start < end <= {total}")
        if end-start < STAGE_COUNTS[kind]*2:
            raise ValueError(f"{name}: allow at least two frames per construction stage")
        params = item.get("params", {})
        if not isinstance(params, dict) or set(params) - MODEL_PARAMS[kind]:
            raise ValueError(f"{name}: unsupported builder parameters")
        for key, value in params.items():
            if key == "variant":
                _integer(value, f"{name}.variant", 0)
            else:
                _number(value, f"{name}.{key}", .05)
        if kind == "nha_co" and (item["rotation"][0] or item["rotation"][1]):
            raise ValueError(f"{name}: town houses must stand upright")
    events = data.get("events", [])
    if not isinstance(events, list):
        raise ValueError("events must be a list")
    previous = 0
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("Every event must be an object")
        start = _integer(event.get("frame"), "event.frame")
        end = _integer(event.get("end_frame"), "event.end_frame")
        if not previous < start <= end <= total:
            raise ValueError("Events must be ordered, nonoverlapping, and inside the timeline")
        if not isinstance(event.get("text"), str) or not event["text"].strip():
            raise ValueError("Event text must be nonempty")
        previous = end
    profile=data.get("scene_profile","diorama")
    if profile not in ("landscape","diorama","geographic"):
        raise ValueError("scene_profile must be landscape, diorama or geographic")
    if profile=='geographic':
        geo=data.get('gis',{})
        houses=[i for i in instances if i['model_id']=='nha_co']
        expected=geo.get('metadata',{}).get('layout_sha256')
        actual=hashlib.sha256(json.dumps(houses,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if not expected or actual!=expected:
            raise ValueError('GIS house placements changed or are unvalidated; regenerate with fetch-gis')
    else:
        validate_layout(data.get("instances", []),profile)
    return data


def load_timeline(path=DEFAULT_TIMELINE):
    with Path(path).open(encoding="utf-8") as handle:
        data = copy.deepcopy(json.load(handle))
    if not isinstance(data, dict):
        raise ValueError("Timeline must be a JSON object")
    if data.get('scene_profile')=='geographic':
        scene_path=Path(path).resolve().parent/data.get('gis_scene','gis/hanoi/scene.json')
        if not scene_path.is_file():
            raise ValueError('GIS bundle missing. Run python pipeline.py fetch-gis first')
        geo=json.loads(scene_path.read_text(encoding='utf-8'))
        if geo.get('schema_version')!=1:
            raise ValueError('Unsupported GIS bundle schema')
        catalog={p['id']:p for p in geo['landmarks']}
        for item in data.get('instances',[]):
            landmark=catalog[item['id']]
            item['position']=landmark['position']
            item['scale']=[1,1,1]
            item['dimensions_m']={k:v for k,v in landmark.items() if k in ('floor_width_m','base_width_m','height_m')}
            item['dimensions_m']['meters_per_unit']=geo['metadata']['meters_per_unit']
            item['geographic_source']=landmark['source']
        data['instances'].extend(geo['town_instances'])
        data['gis']=geo
    town = data.pop("town", None)
    if town is not None:
        if not isinstance(town, dict) or set(town) - {"seed","layout"}:
            raise ValueError("town supports seed and layout parameters")
        if not isinstance(data.setdefault("instances", []), list):
            raise ValueError("instances must be a list")
        data["instances"].extend(town_instances(_integer(town.get("seed", 1049), "town.seed", 0),town.get("layout","compact")))
    return validate(data)


def year_at(data, frame):
    if not 1 <= frame <= data["frame_end"]:
        raise ValueError("Frame outside timeline")
    anchors = data["anchors"]
    for left, right in zip(anchors, anchors[1:]):
        if frame <= right["frame"]:
            fraction = (frame-left["frame"]) / (right["frame"]-left["frame"])
            return math.floor(left["year"] + fraction*(right["year"]-left["year"]) + 1e-9)
    return anchors[-1]["year"]


def event_at(data, frame):
    return next((e["text"] for e in data.get("events", []) if e["frame"] <= frame <= e["end_frame"]), "")


def frame_seconds(frame, fps):
    return (frame - 1) / fps
