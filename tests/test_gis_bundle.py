"""GIS bundle validation tests.

Verifies data/gis/hanoi/ after fetch_gis.py completes. Each test skips cleanly
when the bundle is absent so the existing 12 illustrative tests still pass.
"""
from __future__ import annotations
import json
import math
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIS_DIR = ROOT / "data" / "gis" / "hanoi"
SCENE = GIS_DIR / "scene.json"
MANIFEST = GIS_DIR / "manifest.json"
CONFIG_PATH = ROOT / "data" / "hanoi_gis.json"


def _load_scene():
    return json.loads(SCENE.read_text(encoding="utf-8"))


def _load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _skip_if_missing(*paths):
    for p in paths:
        if not Path(p).is_file():
            raise unittest.SkipTest(f"GIS bundle not yet built: {p}")


class GisBundleFilesTest(unittest.TestCase):
    """All expected files must exist after fetch-gis."""

    def test_required_files_present(self):
        _skip_if_missing(SCENE)
        required = [
            "dem_wgs84.tif", "dem_utm_float.tif", "heightmap_16.tif",
            "heightmap_16.png", "heightmap_16.pgw", "scene.json",
            "manifest.json", "landmarks.geojson", "map_vectors.geojson",
            "vietnam_boundary.geojson", "map_check.png", "ATTRIBUTION.txt",
        ]
        missing = [f for f in required if not (GIS_DIR / f).is_file()]
        self.assertFalse(missing, f"Missing GIS files: {missing}")


class GisSceneSchemaTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE)
        self.scene = _load_scene()
        self.config = _load_config()

    def test_schema_version(self):
        self.assertEqual(self.scene.get("schema_version"), 1)

    def test_top_level_keys(self):
        required = {"schema_version", "metadata", "grid", "landmarks",
                    "roads", "water", "town_instances", "country"}
        missing = required - set(self.scene)
        self.assertFalse(missing, f"Missing top-level keys: {missing}")

    def test_metadata_crs(self):
        self.assertEqual(self.scene["metadata"]["projected_crs"], "EPSG:32648")

    def test_meters_per_unit(self):
        self.assertEqual(self.scene["metadata"]["meters_per_unit"], 10)


class GisBboxTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE)
        self.scene = _load_scene()
        self.config = _load_config()

    def test_bbox_wgs84_matches_config(self):
        cfg = self.config["bbox_wgs84"]
        sc = self.scene["metadata"]["bbox_wgs84"]
        for a, b in zip(cfg, sc):
            self.assertAlmostEqual(a, b, places=6)

    def test_utm_bounds_positive_area(self):
        l, b, r, t = self.scene["metadata"]["bounds_projected_m"]
        self.assertGreater(r, l)
        self.assertGreater(t, b)

    def test_utm_extent_approx_km(self):
        l, b, r, t = self.scene["metadata"]["bounds_projected_m"]
        w = (r - l) / 1000
        h = (t - b) / 1000
        self.assertGreater(w, 2.0)
        self.assertLess(w, 8.0)
        self.assertGreater(h, 1.5)
        self.assertLess(h, 6.0)


class GisGridTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE)
        self.scene = _load_scene()

    def test_grid_dimensions(self):
        g = self.scene["grid"]
        self.assertGreater(g["cols"], 1)
        self.assertGreater(g["rows"], 1)
        self.assertEqual(len(g["heights"]), g["rows"])
        self.assertEqual(len(g["heights"][0]), g["cols"])

    def test_grid_north_up(self):
        self.assertLess(self.scene["grid"]["dy"], 0,
                        "dy must be negative: row 0 is northernmost")

    def test_grid_resolution_approx_30m(self):
        g = self.scene["grid"]
        u = self.scene["metadata"]["meters_per_unit"]
        self.assertAlmostEqual(abs(g["dx"]) * u, 30, delta=5)
        self.assertAlmostEqual(abs(g["dy"]) * u, 30, delta=5)

    def test_heights_finite_and_reasonable(self):
        g = self.scene["grid"]
        u = self.scene["metadata"]["meters_per_unit"]
        z0 = self.scene["metadata"]["z_origin_m"]
        for row in g["heights"]:
            for z in row:
                self.assertTrue(math.isfinite(z))
                raw = z * u + z0
                self.assertGreater(raw, -10)
                self.assertLess(raw, 500)


class GisUint16DecodeTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE)
        self.enc = _load_scene()["metadata"]["heightmap_encoding"]

    def test_keys_present(self):
        for k in ("scale_m_per_code", "offset_m", "nodata_code", "min_m", "max_m"):
            self.assertIn(k, self.enc)

    def test_nodata_is_zero(self):
        self.assertEqual(self.enc["nodata_code"], 0)

    def test_scale_positive_and_small(self):
        s = self.enc["scale_m_per_code"]
        self.assertGreater(s, 0)
        self.assertLess(s, 1.0)

    def test_round_trip_min_max(self):
        s, o = self.enc["scale_m_per_code"], self.enc["offset_m"]
        self.assertAlmostEqual(1 * s + o, self.enc["min_m"], delta=s * 2)
        self.assertAlmostEqual(65535 * s + o, self.enc["max_m"], delta=s * 2)


class GisLandmarkTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE)
        self.scene = _load_scene()
        self.config = _load_config()

    def test_landmark_ids_present(self):
        ids = {lm["id"] for lm in self.scene["landmarks"]}
        for c in self.config["landmarks"]:
            self.assertIn(c["id"], ids)

    def test_landmark_positions_3d(self):
        for lm in self.scene["landmarks"]:
            self.assertEqual(len(lm["position"]), 3)
            for v in lm["position"]:
                self.assertTrue(math.isfinite(v))

    def test_landmark_separation_metres(self):
        u = self.scene["metadata"]["meters_per_unit"]
        p = next(lm for lm in self.scene["landmarks"] if lm["id"] == "pagoda")
        f = next(lm for lm in self.scene["landmarks"] if lm["id"] == "flag_tower")
        d = math.hypot((p["position"][0]-f["position"][0])*u,
                       (p["position"][1]-f["position"][1])*u)
        self.assertGreater(d, 500, f"Separation {d:.0f} m too small")
        self.assertLess(d, 2000, f"Separation {d:.0f} m too large")

    def test_geodesic_vs_projected(self):
        meta = self.scene["metadata"]
        if "landmark_distance_m" not in meta:
            self.skipTest("Distance metadata not recorded")
        ratio = abs(meta["landmark_distance_m"] / meta["geodesic_landmark_distance_m"] - 1)
        self.assertLess(ratio, 0.001)

    def test_source_url(self):
        for lm in self.scene["landmarks"]:
            self.assertTrue(lm.get("source", "").startswith("http"))


class GisNorthOrientationTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE)
        self.scene = _load_scene()

    def test_pagoda_north_of_flag(self):
        p = next(lm for lm in self.scene["landmarks"] if lm["id"] == "pagoda")
        f = next(lm for lm in self.scene["landmarks"] if lm["id"] == "flag_tower")
        self.assertGreater(p["position"][1], f["position"][1],
                           "pagoda.y must > flag_tower.y (north is +Y in UTM)")

    def test_pagoda_west_of_flag(self):
        p = next(lm for lm in self.scene["landmarks"] if lm["id"] == "pagoda")
        f = next(lm for lm in self.scene["landmarks"] if lm["id"] == "flag_tower")
        self.assertLess(p["position"][0], f["position"][0],
                        "pagoda.x must < flag_tower.x (west is -X in UTM)")


class GisWaterRoadsTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE)
        self.scene = _load_scene()

    def test_water_is_list(self):
        self.assertIsInstance(self.scene["water"], list)

    def test_roads_is_list(self):
        self.assertIsInstance(self.scene["roads"], list)

    def test_water_has_outer(self):
        for w in self.scene["water"]:
            self.assertIn("outer", w)
            self.assertGreaterEqual(len(w["outer"]), 3)

    def test_roads_have_points(self):
        for r in self.scene["roads"]:
            self.assertGreaterEqual(len(r.get("points", [])), 2)

    def test_water_triangles_ccw(self):
        for w in self.scene.get("water", []):
            for tri in w.get("triangles", []):
                if len(tri) < 3:
                    continue
                ax, ay = tri[0][0], tri[0][1]
                bx, by = tri[1][0], tri[1][1]
                cx, cy = tri[2][0], tri[2][1]
                cross = (bx-ax)*(cy-ay) - (by-ay)*(cx-ax)
                self.assertGreaterEqual(cross, 0, "Water triangle has CW winding")


class GisTownInstancesTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE)
        self.scene = _load_scene()

    def test_nonempty(self):
        self.assertGreater(len(self.scene.get("town_instances", [])), 0)

    def test_required_keys(self):
        req = {"id", "model_id", "seed", "position", "rotation", "scale",
               "start_frame", "end_frame", "params"}
        for inst in self.scene.get("town_instances", [])[:20]:
            self.assertFalse(req - set(inst), f"{inst.get('id')}: missing keys")

    def test_placement_source(self):
        for inst in self.scene.get("town_instances", []):
            self.assertIn("placement_source", inst)

    def test_not_at_origin(self):
        for inst in self.scene.get("town_instances", []):
            pos = inst["position"]
            self.assertGreater(math.hypot(pos[0], pos[1]), 0.01)


class GisCountryOverviewTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE)
        self.scene = _load_scene()

    def test_country_keys(self):
        for k in ("vertices", "faces", "colors", "borders"):
            self.assertIn(k, self.scene.get("country", {}))

    def test_vertex_count(self):
        self.assertGreater(len(self.scene["country"]["vertices"]), 100)

    def test_face_indices_valid(self):
        n = len(self.scene["country"]["vertices"])
        for face in self.scene["country"]["faces"]:
            for idx in face:
                self.assertLess(idx, n)

    def test_borders_nonempty(self):
        self.assertGreater(len(self.scene["country"]["borders"]), 0)


class GisMapCheckImageTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE, GIS_DIR / "map_check.png")

    def test_png_valid(self):
        data = (GIS_DIR / "map_check.png").read_bytes()
        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
        w = struct.unpack(">I", data[16:20])[0]
        h = struct.unpack(">I", data[20:24])[0]
        self.assertGreater(w, 100)
        self.assertGreater(h, 100)


class GisManifestConsistencyTest(unittest.TestCase):
    def setUp(self):
        _skip_if_missing(SCENE, MANIFEST)
        self.scene = _load_scene()
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_crs_matches(self):
        self.assertEqual(self.manifest.get("projected_crs"),
                         self.scene["metadata"]["projected_crs"])

    def test_bbox_matches(self):
        for a, b in zip(self.scene["metadata"]["bbox_wgs84"],
                        self.manifest.get("bbox_wgs84", [])):
            self.assertAlmostEqual(a, b, places=6)

    def test_layout_sha256_present(self):
        self.assertIn("layout_sha256", self.manifest)


if __name__ == "__main__":
    unittest.main()
