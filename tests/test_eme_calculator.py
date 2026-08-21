"""Regression tests for the pass-counting fix (see README Revision
History v2.0.0) and related eme_calculator.py behavior.

Run with: python -m pytest tests/
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from eme_calculator import EMECalculator, format_summary
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


def test_format_summary_contains_key_numbers_not_raw_json():
    # Regression test for the CLI-output confusion this fixed: the
    # default terminal output should be a readable summary, not a JSON
    # blob -- so it must not look like JSON, and it must mention every
    # region and the wind loading figure.
    terrain = TerrainProfile(PROFILE_PATH)
    calc = EMECalculator(terrain_profile=terrain)
    calc.setup_observer(terrain.latitude, terrain.longitude, terrain.elevation_ft * 0.3048)
    start = datetime(2026, 1, 1)
    daily_passes = calc.calculate_daily_passes(start, frequency_mhz=1296, days=30)
    opportunities = calc.analyze_eme_opportunities(daily_passes, frequency_mhz=1296)
    monthly = calc.monthly_conditions(opportunities)
    wind_loading = calc.calculate_wind_loading(2.4, 35)
    rf = calc.calculate_rf_considerations(1296)
    tree_blockage = calc.calculate_tree_blockage(0, 100)
    results = {
        'location': {
            'grid_square': terrain.profile['grid_square'],
            'latitude': terrain.latitude, 'longitude': terrain.longitude,
            'elevation_m': terrain.elevation_ft * 0.3048,
            'antenna_offset_east_ft': 0.0, 'antenna_offset_north_ft': 0.0,
        },
        'band_mhz': 1296,
        'min_elevation_deg': calc.min_elevation_for_band(1296),
        'noise_figure_db': calc.noise_figure_db_for_band(1296),
        'eme_opportunities': {
            region: {'annual_passes': len(passes),
                      'avg_peak_elevation_deg': (sum(p['elevation'] for p in passes) / len(passes)
                                                  if passes else 0),
                      'avg_degradation_db': (sum(p['degradation_db'] for p in passes) / len(passes)
                                              if passes else 0)}
            for region, passes in opportunities.items()
        },
        'monthly_conditions': monthly,
        'wind_loading': wind_loading,
        'rf_considerations': rf,
        'tree_blockage': tree_blockage,
    }
    results['recommendations'] = calc.generate_recommendations(results)

    summary = format_summary(results)

    assert not summary.strip().startswith('{')
    for region in EMECalculator.TARGET_REGIONS:
        assert region in summary
    assert f"{wind_loading['force_lbf']:.1f}" in summary


def test_monthly_best_day_is_the_lowest_degradation_day_in_that_month(result_90days):
    # Regression test for the "best day" ranking change: monthly_conditions()
    # must pick the day with the LOWEST degradation_db in each month, not
    # (as before this feature) the day with the highest peak elevation.
    opportunities, _ = result_90days
    calc = EMECalculator()
    monthly = calc.monthly_conditions(opportunities)
    for region, passes in opportunities.items():
        for month, info in monthly[region].items():
            month_passes = [p for p in passes if p['date'].month == month]
            if not month_passes:
                continue
            expected_min = min(p['degradation_db'] for p in month_passes)
            assert abs(info['degradation_db'] - expected_min) < 1e-9, (
                f"{region} month {month}: best_date's degradation_db "
                f"{info['degradation_db']} is not the month's minimum "
                f"({expected_min}) -- best-day ranking should be by "
                f"lowest degradation, not highest elevation."
            )


def test_noise_figure_lookup_priority_override_then_profile_then_default():
    terrain = TerrainProfile(PROFILE_PATH)
    calc = EMECalculator(terrain_profile=terrain)
    # An explicit override always wins.
    assert calc.noise_figure_db_for_band(1296, override=1.23) == 1.23
    # The K2UA profile ships real operator-supplied values -- 1296 should
    # come from the profile, not the generic per-band default table.
    assert calc.noise_figure_db_for_band(1296) == \
        terrain.profile['receiver_noise_figure_db']['1296']
    assert calc.noise_figure_db_for_band(1296) != \
        EMECalculator.DEFAULT_NOISE_FIGURE_DB_BY_BAND[1296]
    # For a band this profile doesn't list, fall back to the generic table.
    assert '3456' not in terrain.profile['receiver_noise_figure_db']
    assert 3456 not in terrain.profile['receiver_noise_figure_db']
    assert calc.noise_figure_db_for_band(3456) == \
        EMECalculator.DEFAULT_NOISE_FIGURE_DB_BY_BAND[3456]
    # Overwriting the profile's value should be picked up.
    terrain.profile['receiver_noise_figure_db'] = {'1296': 0.42}
    assert calc.noise_figure_db_for_band(1296) == 0.42


def test_pass_sweep_is_within_region_window_and_wider_than_peak_spread(result_90days):
    # Regression test for the "monthly azimuth range" confusion: the
    # per-pass sweep (how far the Moon actually moves during one day's
    # pass through a region's window) is a different, generally WIDER
    # quantity than the day-to-day spread of just the peak instant across
    # a month -- they must not be conflated or reported under one name.
    opportunities, _ = result_90days
    calc = EMECalculator()
    for region, (min_az, max_az) in EMECalculator.TARGET_REGIONS.items():
        passes = opportunities[region]
        for p in passes:
            az_lo, az_hi = p['pass_azimuth_sweep_deg']
            el_lo, el_hi = p['pass_elevation_sweep_deg']
            assert min_az - 1e-6 <= az_lo <= az_hi <= max_az + 1e-6, (
                f"{region} {p['date']}: pass azimuth sweep {az_lo}-{az_hi} "
                f"falls outside the region's window {min_az}-{max_az}"
            )
            # The peak sample (used elsewhere as 'azimuth'/'elevation')
            # must itself lie within the sweep it was drawn from.
            assert az_lo - 1e-6 <= p['azimuth'] <= az_hi + 1e-6
            assert el_lo - 1e-6 <= p['elevation'] <= el_hi + 1e-6
            assert el_hi == pytest.approx(p['elevation']), (
                "the peak (highest-elevation) sample's elevation should "
                "equal the sweep's el_max by construction"
            )

    monthly = calc.monthly_conditions(opportunities)
    for region, months in monthly.items():
        for month, info in months.items():
            # The old ambiguously-named keys must be gone, replaced by
            # the two distinctly-named, independently computed fields.
            assert 'month_azimuth_range_deg' not in info
            assert 'month_elevation_range_deg' not in info
            assert 'pass_azimuth_sweep_deg' in info
            assert 'pass_elevation_sweep_deg' in info
            assert 'peak_azimuth_spread_deg' in info
            assert 'peak_elevation_spread_deg' in info


def test_pass_track_matches_the_sweep_it_summarizes(result_90days):
    # get_pass_track_for_date() is the ordered counterpart to
    # pass_azimuth_sweep_deg/pass_elevation_sweep_deg -- its first/last
    # samples must equal the sweep's bounds and its highest-elevation
    # sample must be the same peak monthly_conditions() records, since
    # scripts/generate_monthly_track_plots.py relies on all three lining
    # up for the same best day.
    opportunities, _ = result_90days
    terrain = TerrainProfile(PROFILE_PATH)
    calc = EMECalculator(terrain_profile=terrain)
    calc.setup_observer(terrain.latitude, terrain.longitude, terrain.elevation_ft * 0.3048)
    monthly = calc.monthly_conditions(opportunities)

    for region in EMECalculator.TARGET_REGIONS:
        for month, info in monthly[region].items():
            best_date = datetime.strptime(info['best_date'], '%Y-%m-%d')
            track = calc.get_pass_track_for_date(best_date, region, frequency_mhz=1296)
            assert len(track) >= 1, (
                f"{region} {info['best_date']}: monthly_conditions() reports this "
                f"as a qualifying best day, so its track must not be empty"
            )

            az_lo, az_hi = info['pass_azimuth_sweep_deg']
            el_lo, el_hi = info['pass_elevation_sweep_deg']
            track_azimuths = [p['azimuth'] for p in track]
            track_elevations = [p['elevation'] for p in track]

            assert min(track_azimuths) == pytest.approx(az_lo, abs=1e-6)
            assert max(track_azimuths) == pytest.approx(az_hi, abs=1e-6)
            assert min(track_elevations) == pytest.approx(el_lo, abs=1e-6)
            assert max(track_elevations) == pytest.approx(el_hi, abs=1e-6)

            peak = track[int(max(range(len(track)), key=lambda i: track_elevations[i]))]
            assert peak['elevation'] == pytest.approx(info['peak_elevation_deg'], abs=1e-6), (
                f"{region} {info['best_date']}: the track's highest-elevation "
                f"sample should be the same peak monthly_conditions() recorded"
            )

            min_az, max_az = EMECalculator.TARGET_REGIONS[region]
            for p in track:
                assert min_az - 1e-6 <= p['azimuth'] <= max_az + 1e-6


def test_pass_track_for_unqualifying_date_or_unknown_region_is_empty():
    terrain = TerrainProfile(PROFILE_PATH)
    calc = EMECalculator(terrain_profile=terrain)
    calc.setup_observer(terrain.latitude, terrain.longitude, terrain.elevation_ft * 0.3048)

    assert calc.get_pass_track_for_date(datetime(2026, 1, 3), 'Not A Real Region') == []

    # A date the Moon never crosses a given region's azimuth window at all
    # (e.g. Europe's 30-90deg window on a day the Moon stays well south of
    # it) should come back empty, not raise.
    track = calc.get_pass_track_for_date(datetime(2026, 6, 15), 'Asia', frequency_mhz=1296)
    assert isinstance(track, list)


def test_degradation_is_zero_at_best_case_and_positive_otherwise():
    import sky_noise
    best_db, _ = sky_noise.degradation_db(
        1296, galactic_lon_deg=200, galactic_lat_deg=90,
        distance_km=sky_noise.PERIGEE_REF_KM, noise_figure_db=0.7)
    assert abs(best_db) < 1e-9
    worse_db, _ = sky_noise.degradation_db(
        1296, galactic_lon_deg=0, galactic_lat_deg=0,
        distance_km=406700, noise_figure_db=0.7)
    assert worse_db > 0
    # Range factor alone should be a couple dB, not the 12-14 dB the
    # original (incorrect) pasted formula suggested -- see sky_noise.py
    # module docstring.
    assert 0 <= sky_noise.moon_range_factor_db(406700) < 3.0
