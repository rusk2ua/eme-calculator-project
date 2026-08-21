"""Regression tests for src/site_survey.py -- the measurement helpers
behind scripts/build_site_profile.py and scripts/map_pixel_to_geo.py.
"""
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import ephem

import site_survey as ss
from terrain import TerrainProfile

K2UA_LAT, K2UA_LON, K2UA_ELEV_FT = 42.735913, -77.54235, 1573.88


def test_bearing_distance_ft_cardinal_directions():
    # ~111.32 km per degree of latitude at any longitude -- 0.001 deg
    # north is ~111.32m north, i.e. bearing 0, distance ~365.3ft.
    bearing, dist_ft = ss.bearing_distance_ft(K2UA_LAT, K2UA_LON, K2UA_LAT + 0.001, K2UA_LON)
    assert bearing == pytest.approx(0.0, abs=0.5)
    assert dist_ft == pytest.approx(111.32 / ss.FT_PER_M, rel=0.02)

    bearing, dist_ft = ss.bearing_distance_ft(K2UA_LAT, K2UA_LON, K2UA_LAT, K2UA_LON + 0.001)
    assert bearing == pytest.approx(90.0, abs=0.5)

    bearing, _ = ss.bearing_distance_ft(K2UA_LAT, K2UA_LON, K2UA_LAT - 0.001, K2UA_LON)
    assert bearing == pytest.approx(180.0, abs=0.5)

    bearing, _ = ss.bearing_distance_ft(K2UA_LAT, K2UA_LON, K2UA_LAT, K2UA_LON - 0.001)
    assert bearing == pytest.approx(270.0, abs=0.5)


def test_meters_per_pixel_matches_known_web_mercator_values():
    # Standard, widely-cited Web Mercator ground resolution figures.
    assert ss.meters_per_pixel(0, 0) == pytest.approx(156543.03392, rel=1e-6)
    # Doubling zoom halves the ground resolution.
    assert ss.meters_per_pixel(0, 1) == pytest.approx(156543.03392 / 2, rel=1e-6)
    assert ss.meters_per_pixel(0, 10) == pytest.approx(156543.03392 / 1024, rel=1e-6)
    # Resolution shrinks toward the poles (cos(lat) factor).
    assert ss.meters_per_pixel(60, 10) == pytest.approx(ss.meters_per_pixel(0, 10) * 0.5, rel=1e-3)


def test_pixel_offset_to_bearing_distance_screen_directions():
    pin_px, pin_py = 500, 500
    zoom = 19

    # Target straight "up" on screen (smaller y) = due north.
    bearing, dist_ft = ss.pixel_offset_to_bearing_distance(pin_px, pin_py, pin_px, pin_py - 100,
                                                             K2UA_LAT, zoom)
    assert bearing == pytest.approx(0.0, abs=1e-6)
    expected_ft = 100 * ss.meters_per_pixel(K2UA_LAT, zoom) / ss.FT_PER_M
    assert dist_ft == pytest.approx(expected_ft, rel=1e-9)

    # Target straight right on screen (larger x) = due east.
    bearing, _ = ss.pixel_offset_to_bearing_distance(pin_px, pin_py, pin_px + 100, pin_py,
                                                       K2UA_LAT, zoom)
    assert bearing == pytest.approx(90.0, abs=1e-6)

    # Target straight down on screen (larger y) = due south.
    bearing, _ = ss.pixel_offset_to_bearing_distance(pin_px, pin_py, pin_px, pin_py + 100,
                                                       K2UA_LAT, zoom)
    assert bearing == pytest.approx(180.0, abs=1e-6)

    # A pixel offset of 0 is the pin itself -- zero distance.
    _, dist_ft = ss.pixel_offset_to_bearing_distance(pin_px, pin_py, pin_px, pin_py, K2UA_LAT, zoom)
    assert dist_ft == pytest.approx(0.0, abs=1e-6)


def test_line_feature_from_points_matches_hand_computed_geometry():
    # Antenna at local origin. Line runs due north-south (line_bearing 0),
    # 100ft due east of the antenna (bearing_deg 90), from 50ft north of
    # the perpendicular foot to 30ft south of it.
    result = ss.line_feature_from_points(
        pin_east_ft=0, pin_north_ft=0,
        end1_east_ft=100, end1_north_ft=50,   # north end
        end2_east_ft=100, end2_north_ft=-30,  # south end
    )
    assert result["bearing_deg"] == pytest.approx(90.0, abs=0.1)
    assert result["perp_distance_ft"] == pytest.approx(100.0, abs=0.1)
    # line runs from end1 (north) to end2 (south) => line_bearing ~180
    assert result["line_bearing_deg"] == pytest.approx(180.0, abs=0.1)
    along = sorted([result["along_line_start_ft"], result["along_line_end_ft"]])
    assert along[0] == pytest.approx(-50.0, abs=0.1)
    assert along[1] == pytest.approx(30.0, abs=0.1)


def test_line_feature_from_points_rejects_coincident_endpoints():
    with pytest.raises(ValueError):
        ss.line_feature_from_points(0, 0, 10, 10, 10, 10)


def test_line_feature_from_points_round_trips_through_terrainprofile():
    # The whole point of line_feature_from_points() is to produce fields
    # that terrain.py's horizon_angle_deg() interprets correctly -- prove
    # it end to end: fit a line from three points, drop it into a real
    # site profile, and confirm the resulting obstruction horizon matches
    # simple trigonometry at the fitted bearing, and clears (falls back
    # to the DEM floor) just past the fitted line ends.
    height_ft = 80.0
    geom = ss.line_feature_from_points(
        pin_east_ft=0, pin_north_ft=0,
        end1_east_ft=-120, end1_north_ft=100,
        end2_east_ft=-120, end2_north_ft=-300,
    )
    profile = {
        "profile_name": "unit test",
        "latitude": K2UA_LAT, "longitude": K2UA_LON, "elevation_ft": K2UA_ELEV_FT,
        "line_obstructions": [dict(geom, name="test line", height_ft=height_ft)],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(profile, f)
        path = f.name
    try:
        tp = TerrainProfile(path)
        expected_angle = math.degrees(math.atan2(height_ft, geom["perp_distance_ft"]))
        assert tp.horizon_angle_deg(geom["bearing_deg"]) == pytest.approx(expected_angle, abs=0.05)
        # An azimuth 90 degrees away from the line should see none of it
        # (falls back to the DEM floor, 0.0 -- no dem_octant_samples_ft
        # in this synthetic profile).
        assert tp.horizon_angle_deg((geom["bearing_deg"] + 90) % 360) == pytest.approx(0.0, abs=0.5)
    finally:
        os.unlink(path)


def test_shadow_height_ft_self_consistent_with_ephem_sun_position():
    lat, lon, elev_ft = K2UA_LAT, K2UA_LON, K2UA_ELEV_FT
    capture = datetime(2026, 6, 21, 16, 0, 0)  # afternoon, summer -- sun well up

    obs = ephem.Observer()
    obs.lat, obs.lon, obs.elevation = str(lat), str(lon), elev_ft * ss.FT_PER_M
    obs.date = capture
    sun = ephem.Sun()
    sun.compute(obs)
    expected_sun_elev_deg = math.degrees(sun.alt)
    assert expected_sun_elev_deg > 5  # sanity check the test's own scenario

    known_height_ft = 80.0
    shadow_length_ft = known_height_ft / math.tan(math.radians(expected_sun_elev_deg))

    result = ss.shadow_height_ft(shadow_length_ft, lat, lon, elev_ft, capture)
    assert result["height_ft"] == pytest.approx(known_height_ft, abs=0.5)
    assert result["sun_elevation_deg"] == pytest.approx(expected_sun_elev_deg, abs=0.01)


def test_shadow_height_ft_rejects_low_sun_angle():
    # Middle of the night -- sun well below the horizon.
    with pytest.raises(ValueError):
        ss.shadow_height_ft(50.0, K2UA_LAT, K2UA_LON, K2UA_ELEV_FT,
                             datetime(2026, 1, 15, 6, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None))
