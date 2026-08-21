"""Sanity tests for src/terrain.py's obstruction geometry.

Run with: python -m pytest tests/
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from terrain import TerrainProfile

PROFILE_PATH = os.path.join(os.path.dirname(__file__), '..',
                             'data', 'site_profiles', 'k2ua_fn12fr46wo.json')


@pytest.fixture
def profile():
    return TerrainProfile(PROFILE_PATH)


def test_west_treeline_angle_matches_survey(profile):
    # 80ft trees, 120ft away, due west (270deg) -> atan(80/120)
    expected = math.degrees(math.atan2(80, 120))
    got = profile.horizon_angle_deg(270)
    assert got == pytest.approx(expected, abs=0.05)


def test_east_pine_row_angle_matches_survey(profile):
    # 45ft trees; row's perpendicular bearing is 86.8deg (not due east),
    # so checking at az=90 hits the row 215.34ft out, not exactly
    # perp_distance_ft=215 -- expected value is the ray/line intersection
    # distance at az=90 (verified independently against the row's
    # bearing_deg/perp_distance_ft/line_bearing_deg, not just copied from
    # the code under test).
    expected = math.degrees(math.atan2(45, 215.33575922868968))
    got = profile.horizon_angle_deg(90)
    assert got == pytest.approx(expected, abs=0.05)


def test_se_pine_cluster_angle(profile):
    expected = math.degrees(math.atan2(70, 150))
    got = profile.horizon_angle_deg(130)  # mid of 120-140deg range
    assert got == pytest.approx(expected, abs=0.05)


def test_s_pine_cluster_angle(profile):
    expected = math.degrees(math.atan2(70, 100))
    got = profile.horizon_angle_deg(187)  # mid of 180-195deg range
    assert got == pytest.approx(expected, abs=0.05)


def test_dem_floor_is_small_where_no_near_feature(profile):
    # Due north has no explicit tree feature -- should be within a few
    # degrees of flat (the DEM floor at this gently rolling site).
    got = profile.horizon_angle_deg(0)
    assert -10 < got < 10


def test_moving_antenna_toward_obstruction_increases_angle(profile):
    baseline = profile.horizon_angle_deg(270)
    # Move the antenna 100ft WEST (negative east offset) -- distance to
    # the west treeline shrinks from 120ft to 20ft, angle must increase.
    moved = profile.horizon_angle_deg(270, offset_east_ft=-100)
    assert moved > baseline
    expected = math.degrees(math.atan2(80, 20))
    assert moved == pytest.approx(expected, abs=0.05)


def test_moving_antenna_away_from_obstruction_decreases_angle(profile):
    baseline = profile.horizon_angle_deg(90)
    # Move the antenna 100ft WEST -- distance to the EAST pine row grows
    # (row's perpendicular bearing is 86.8deg, not due east, so this isn't
    # exactly +100ft; expected value is the ray/line intersection distance
    # at az=90 with offset_east_ft=-100, verified independently against
    # the row's line geometry).
    moved = profile.horizon_angle_deg(90, offset_east_ft=-100)
    assert moved < baseline
    expected = math.degrees(math.atan2(45, 315.3357592286897))
    assert moved == pytest.approx(expected, abs=0.05)


def test_west_treeline_asymmetric_extent(profile):
    # Profile: along_line_start_ft=-600 (south end), along_line_end_ft=200
    # (north end), perp_distance_ft=120, height 80ft. Well within the
    # row (e.g. azimuth 260, close to due west) should hit the row;
    # far north of the row's +200ft end (e.g. azimuth 340) should not,
    # and fall back to a small DEM-floor angle instead.
    within = profile.horizon_angle_deg(260)
    beyond_north_end = profile.horizon_angle_deg(340)
    assert within > 25  # solidly within the row's obstruction, not a taper edge
    assert beyond_north_end < 10  # past the row's north end -- DEM floor only


def test_horizon_angle_never_negative_infinite_or_over_90(profile):
    for az in range(0, 360, 5):
        angle = profile.horizon_angle_deg(az)
        assert -90 <= angle <= 90
