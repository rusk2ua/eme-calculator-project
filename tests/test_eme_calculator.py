"""Regression tests for the pass-counting fix (see README Revision
History v2.0.0) and related eme_calculator.py behavior.

Run with: python -m pytest tests/
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from eme_calculator import EMECalculator
from terrain import TerrainProfile

PROFILE_PATH = os.path.join(os.path.dirname(__file__), '..',
                             'data', 'site_profiles', 'k2ua_fn12fr46wo.json')


@pytest.fixture(scope='module')
def result_90days():
    terrain = TerrainProfile(PROFILE_PATH)
    calc = EMECalculator(terrain_profile=terrain)
    calc.setup_observer(terrain.latitude, terrain.longitude, terrain.elevation_ft * 0.3048)
    start = datetime(2026, 1, 1)
    daily_passes = calc.calculate_daily_passes(start, frequency_mhz=1296, days=90)
    opportunities = calc.analyze_eme_opportunities(daily_passes)
    return opportunities, 90


def test_no_region_exceeds_the_number_of_days_analyzed(result_90days):
    opportunities, days = result_90days
    for region, passes in opportunities.items():
        assert len(passes) <= days, (
            f"{region} has {len(passes)} passes over a {days}-day window -- "
            f"the Moon rises at most once/day, this should be impossible."
        )


def test_each_day_contributes_at_most_one_pass_per_region(result_90days):
    opportunities, _ = result_90days
    for region, passes in opportunities.items():
        dates = [p['date'].date() for p in passes]
        assert len(dates) == len(set(dates)), (
            f"{region} has a duplicate calendar day in its pass list -- "
            f"this is exactly the bug v2.0.0 fixed."
        )


def test_band_specific_minimum_elevation_differs_by_band():
    calc = EMECalculator()
    assert calc.min_elevation_for_band(144) == 5
    assert calc.min_elevation_for_band(1296) == 10
    assert calc.min_elevation_for_band(10368) == 30


def test_maidenhead_roundtrip_reasonable():
    calc = EMECalculator()
    lat, lon = calc.maidenhead_to_latlon('FN12fr46wo')
    assert 42.7 < lat < 42.8
    assert -77.6 < lon < -77.5
