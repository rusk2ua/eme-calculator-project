#!/usr/bin/env python3
"""
EME Dish Siting Calculator
Modular library for calculating optimal EME dish placement
"""

import math
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import ephem

try:
    from terrain import TerrainProfile
except ImportError:
    from src.terrain import TerrainProfile

try:
    from rf_analysis import RFAnalyzer
except ImportError:
    from src.rf_analysis import RFAnalyzer


class EMECalculator:
    """Main calculator class for EME dish siting analysis"""

    # Frequency band definitions
    BANDS = {
        144: {"name": "2m", "wavelength_cm": 208.3, "tree_sensitivity": "low"},
        432: {"name": "70cm", "wavelength_cm": 69.4, "tree_sensitivity": "medium"},
        902: {"name": "33cm", "wavelength_cm": 33.2, "tree_sensitivity": "medium"},
        1296: {"name": "23cm", "wavelength_cm": 23.1, "tree_sensitivity": "high"},
        2304: {"name": "13cm", "wavelength_cm": 13.0, "tree_sensitivity": "very_high"},
        3456: {"name": "9cm", "wavelength_cm": 8.7, "tree_sensitivity": "extreme"},
        5760: {"name": "6cm", "wavelength_cm": 5.2, "tree_sensitivity": "extreme"},
        10000: {"name": "3cm", "wavelength_cm": 3.0, "tree_sensitivity": "extreme"},
        10368: {"name": "3cm", "wavelength_cm": 2.9, "tree_sensitivity": "extreme"}
    }

    # Fallback minimum elevation (degrees) when a band isn't in
    # RFAnalyzer.BAND_CHARACTERISTICS for some reason.
    DEFAULT_MIN_ELEVATION_DEG = 10

    # Target region azimuth ranges (approximate)
    TARGET_REGIONS = {
        'Europe': (30, 90),
        'Caribbean': (120, 180),
        'South America': (150, 210),
        'Africa': (60, 120),
        'Asia': (300, 360),
        'Oceania': (240, 300)
    }

    def __init__(self, terrain_profile: Optional[TerrainProfile] = None,
                 offset_east_ft: float = 0.0, offset_north_ft: float = 0.0):
        self.observer = ephem.Observer()
        self.terrain = terrain_profile
        self.offset_east_ft = offset_east_ft
        self.offset_north_ft = offset_north_ft
        self._rf = RFAnalyzer()

    def maidenhead_to_latlon(self, grid: str) -> Tuple[float, float]:
        """Convert Maidenhead grid square to lat/lon coordinates"""
        grid = grid.upper()

        # First pair (field)
        lon = (ord(grid[0]) - ord('A')) * 20 - 180
        lat = (ord(grid[1]) - ord('A')) * 10 - 90

        # Second pair (square)
        lon += int(grid[2]) * 2
        lat += int(grid[3]) * 1

        # Third pair (subsquare) - 6 digits minimum
        if len(grid) >= 6:
            lon += (ord(grid[4].upper()) - ord('A')) * (2/24)
            lat += (ord(grid[5].upper()) - ord('A')) * (1/24)

        # Fourth pair (extended square) - 8 digits
        if len(grid) >= 8:
            lon += int(grid[6]) * (2/240)
            lat += int(grid[7]) * (1/240)

        # Fifth pair (extended subsquare) - 10 digits
        if len(grid) >= 10:
            lon += (ord(grid[8].upper()) - ord('A')) * (2/5760)
            lat += (ord(grid[9].upper()) - ord('A')) * (1/5760)

        return lat, lon

    def setup_observer(self, lat: float, lon: float, elevation_m: float = 0):
        """Setup observer location"""
        self.observer.lat = str(lat)
        self.observer.lon = str(lon)
        self.observer.elevation = elevation_m

    def min_elevation_for_band(self, frequency_mhz: float) -> float:
        """Band-specific minimum usable elevation (degrees), from
        RFAnalyzer.BAND_CHARACTERISTICS -- keeps the pass-counting logic
        and the RF analysis using one shared definition instead of two
        different hardcoded thresholds."""
        band = self._rf.BAND_CHARACTERISTICS.get(int(frequency_mhz))
        if band:
            return band["min_elevation_deg"]
        return self.DEFAULT_MIN_ELEVATION_DEG

    def horizon_angle_deg(self, azimuth_deg: float) -> float:
        """Effective local horizon (terrain + tree obstruction) at this
        azimuth, degrees. 0 if no terrain profile was supplied (flat,
        unobstructed horizon -- the old behavior)."""
        if self.terrain is None:
            return 0.0
        return self.terrain.horizon_angle_deg(
            azimuth_deg, self.offset_east_ft, self.offset_north_ft
        )

    def calculate_daily_passes(self, start_date: datetime, frequency_mhz: float = 1296,
                                days: int = 365, sample_minutes: int = 10,
                                max_window_hours: float = 20.0) -> List[Dict]:
        """For each day, find the Moon's rise-to-set track and record
        every sample point above both the band's minimum elevation AND
        the local terrain/obstruction horizon at that sample's azimuth.

        This replaces the old fixed 0-6-hour, 1-hour-step sampling: each
        calendar day now produces at most ONE 'daily track' record (this
        is the fix for the annual-passes bug -- a day is a day, it isn't
        recounted per hourly sample later)."""
        moon = ephem.Moon()
        min_elev = self.min_elevation_for_band(frequency_mhz)
        days_out = []

        current_date = start_date
        for _ in range(days):
            self.observer.date = current_date
            try:
                moonrise = self.observer.next_rising(moon)
                self.observer.date = moonrise
                try:
                    moonset = self.observer.next_setting(moon)
                except (ephem.NeverUpError, ephem.AlwaysUpError):
                    moonset = moonrise + timedelta(hours=max_window_hours)

                window_hours = (moonset - moonrise) * 24.0
                if window_hours <= 0 or window_hours > max_window_hours:
                    window_hours = max_window_hours

                n_samples = max(1, int(window_hours * 60 / sample_minutes))
                usable_positions = []
                for i in range(n_samples + 1):
                    t = moonrise + (i * sample_minutes) * ephem.minute
                    self.observer.date = t
                    moon.compute(self.observer)
                    az_deg = math.degrees(moon.az)
                    alt_deg = math.degrees(moon.alt)

                    horizon = max(min_elev, self.horizon_angle_deg(az_deg))
                    if alt_deg >= horizon:
                        usable_positions.append({
                            'time': ephem.Date(t),
                            'azimuth': az_deg,
                            'elevation': alt_deg,
                            'local_horizon_deg': horizon,
                        })

                if usable_positions:
                    days_out.append({
                        'date': current_date,
                        'moonrise': moonrise,
                        'moonset': moonset,
                        'positions': usable_positions,
                    })
            except (ephem.NeverUpError, ephem.AlwaysUpError):
                pass

            current_date += timedelta(days=1)

        return days_out

    def calculate_moonrise_windows(self, start_date: datetime, days: int = 365) -> List[Dict]:
        """Retained for backward compatibility with existing callers --
        thin wrapper reproducing the original 6-hour/1-hour-step legacy
        shape. NOTE: analyze_eme_opportunities() no longer accepts this
        shape directly -- use calculate_daily_passes() for new code."""
        moon = ephem.Moon()
        windows = []
        current_date = start_date
        for _ in range(days):
            self.observer.date = current_date
            try:
                moonrise = self.observer.next_rising(moon)
                window_positions = []
                for hour_offset in range(7):
                    self.observer.date = moonrise + hour_offset * ephem.hour
                    moon.compute(self.observer)
                    az_deg = math.degrees(moon.az)
                    alt_deg = math.degrees(moon.alt)
                    if alt_deg > 5:
                        window_positions.append({
                            'time': self.observer.date,
                            'azimuth': az_deg,
                            'elevation': alt_deg,
                            'hour_after_rise': hour_offset
                        })
                if window_positions:
                    windows.append({
                        'date': current_date,
                        'moonrise': moonrise,
                        'positions': window_positions
                    })
            except (ephem.NeverUpError, ephem.AlwaysUpError):
                pass
            current_date += timedelta(days=1)
        return windows

    def analyze_eme_opportunities(self, daily_passes: List[Dict],
                                   target_regions: List[str] = None) -> Dict:
        """Analyze EME opportunities by region.

        FIXED (see README Revision History): each qualifying calendar
        day now contributes at most ONE pass per region -- the sample
        with the highest elevation (least atmospheric/obstruction
        degradation) among that day's usable-window positions that fall
        in the region's azimuth range is used as the day's representative
        pass. Previously every hourly sample within a region's azimuth
        window was counted separately, which could count a single
        moonrise 2-7x and produced 'annual pass' counts above 365 --
        physically impossible, since the Moon rises at most once a day.
        """
        if target_regions is None:
            target_regions = list(self.TARGET_REGIONS.keys())

        region_passes = {region: [] for region in target_regions}

        for day in daily_passes:
            # Track the best (highest-elevation) qualifying sample per
            # region for THIS day only, so each day yields <=1 pass/region.
            best_by_region: Dict[str, Dict] = {}
            for pos in day['positions']:
                az = pos['azimuth']
                for region in target_regions:
                    if region not in self.TARGET_REGIONS:
                        continue
                    min_az, max_az = self.TARGET_REGIONS[region]
                    if not (min_az <= az <= max_az):
                        continue
                    current_best = best_by_region.get(region)
                    if current_best is None or pos['elevation'] > current_best['elevation']:
                        best_by_region[region] = pos

            for region, pos in best_by_region.items():
                region_passes[region].append({
                    'date': day['date'],
                    'moonrise': day['moonrise'],
                    'moonset': day['moonset'],
                    'peak_time': pos['time'],
                    'azimuth': pos['azimuth'],
                    'elevation': pos['elevation'],
                    'local_horizon_deg': pos['local_horizon_deg'],
                })

        return region_passes

    def monthly_conditions(self, region_passes: Dict[str, List[Dict]]) -> Dict[str, Dict[int, Dict]]:
        """For each region and each calendar month, find the single best
        (highest peak-elevation -- least atmospheric absorption, most
        terrain/tree clearance) qualifying pass, and report the azimuth
        and elevation range the Moon sweeps through during that specific
        pass ('peak moon conditions' / minimum-degradation window)."""
        result: Dict[str, Dict[int, Dict]] = {}
        for region, passes in region_passes.items():
            by_month: Dict[int, List[Dict]] = {m: [] for m in range(1, 13)}
            for p in passes:
                month = ephem.Date(p['date']).datetime().month
                by_month[month].append(p)

            result[region] = {}
            for month, month_passes in by_month.items():
                if not month_passes:
                    continue
                best = max(month_passes, key=lambda p: p['elevation'])
                azimuths = [p['azimuth'] for p in month_passes]
                elevations = [p['elevation'] for p in month_passes]
                result[region][month] = {
                    'best_date': str(ephem.Date(best['date']).datetime().date()),
                    'peak_azimuth_deg': best['azimuth'],
                    'peak_elevation_deg': best['elevation'],
                    'peak_time_utc': str(ephem.Date(best['peak_time']).datetime()),
                    'local_horizon_deg': best['local_horizon_deg'],
                    'month_azimuth_range_deg': (min(azimuths), max(azimuths)),
                    'month_elevation_range_deg': (min(elevations), max(elevations)),
                    'qualifying_days_in_month': len(month_passes),
                }
        return result

    def calculate_wind_loading(self, dish_diameter_m: float,
                                wind_speed_mph: float) -> Dict:
        """Calculate wind loading on dish"""
        dish_area = math.pi * (dish_diameter_m/2)**2  # m^2
        wind_speed_ms = wind_speed_mph * 0.44704  # Convert mph to m/s

        air_density = 1.225  # kg/m^3
        pressure_pa = 0.5 * air_density * wind_speed_ms**2
        force_n = pressure_pa * dish_area
        force_lbf = force_n / 4.448  # Convert to pounds-force

        return {
            'dish_area_m2': dish_area,
            'wind_speed_mph': wind_speed_mph,
            'wind_speed_ms': wind_speed_ms,
            'pressure_pa': pressure_pa,
            'force_n': force_n,
            'force_lbf': force_lbf
        }

    def calculate_rf_considerations(self, frequency_mhz: float,
                                     tree_height_ft: float = 0,
                                     tree_distance_ft: float = 100) -> Dict:
        """Calculate RF considerations for frequency band"""
        if frequency_mhz not in self.BANDS:
            closest_freq = min(self.BANDS.keys(),
                                key=lambda x: abs(x - frequency_mhz))
            band_info = self.BANDS[closest_freq].copy()
            band_info['wavelength_cm'] = 29979.2458 / frequency_mhz
        else:
            band_info = self.BANDS[frequency_mhz].copy()

        tree_loss_db = 0
        if tree_height_ft > 0:
            freq_factor = frequency_mhz / 144
            tree_loss_db = min(30, freq_factor * 2 * (tree_height_ft / 50))

        rain_fade_db = 0
        if frequency_mhz > 1000:
            rain_fade_db = (frequency_mhz / 1000) * 0.5

        return {
            'frequency_mhz': frequency_mhz,
            'band_name': band_info['name'],
            'wavelength_cm': band_info['wavelength_cm'],
            'tree_sensitivity': band_info['tree_sensitivity'],
            'estimated_tree_loss_db': tree_loss_db,
            'estimated_rain_fade_db': rain_fade_db
        }

    def calculate_tree_blockage(self, tree_height_ft: float,
                                 tree_distance_ft: float) -> Dict:
        """Calculate elevation angle blocked by trees (single-direction
        legacy helper; prefer a TerrainProfile for direction-aware
        obstruction)."""
        if tree_distance_ft <= 0:
            return {'blockage_angle_deg': 90}

        tree_height_m = tree_height_ft * 0.3048
        tree_distance_m = tree_distance_ft * 0.3048

        blockage_angle = math.degrees(math.atan(tree_height_m / tree_distance_m))

        return {
            'tree_height_ft': tree_height_ft,
            'tree_distance_ft': tree_distance_ft,
            'blockage_angle_deg': blockage_angle
        }

    def generate_recommendations(self, analysis_results: Dict) -> Dict:
        """Generate siting recommendations based on analysis"""
        recommendations = {
            'optimal_location': 'East or southeast of reference point',
            'reasoning': [],
            'technical_requirements': [],
            'operational_notes': []
        }

        if 'tree_blockage' in analysis_results:
            blockage = analysis_results['tree_blockage']['blockage_angle_deg']
            if blockage > 30:
                recommendations['reasoning'].append(
                    f"Avoid areas within {analysis_results['tree_blockage']['tree_distance_ft']}ft "
                    f"of {analysis_results['tree_blockage']['tree_height_ft']}ft trees "
                    f"({blockage:.1f}deg elevation blockage)"
                )

        if 'wind_loading' in analysis_results:
            force_lbf = analysis_results['wind_loading']['force_lbf']
            recommendations['technical_requirements'].append(
                f"Foundation rated for {force_lbf:.0f}+ lbf wind loading"
            )

        if 'rf_considerations' in analysis_results:
            rf = analysis_results['rf_considerations']
            if rf['tree_sensitivity'] in ['high', 'very_high', 'extreme']:
                recommendations['reasoning'].append(
                    f"Clear line of sight critical for {rf['band_name']} "
                    f"({rf['frequency_mhz']} MHz)"
                )

        return recommendations


def format_summary(results: Dict) -> str:
    """Short, human-readable rendering of a results dict (see main()) --
    the default terminal output. Pass --json or --output for the full
    machine-readable JSON instead."""
    loc = results['location']
    lines = []
    lines.append("EME Dish Siting Calculator -- Results Summary")
    lines.append("=" * 48)
    lines.append(f"Site: {loc['grid_square']}  "
                  f"({loc['latitude']:.6f}, {loc['longitude']:.6f})  "
                  f"{loc['elevation_m']:.1f} m ASL")
    if loc['antenna_offset_east_ft'] or loc['antenna_offset_north_ft']:
        lines.append(f"Antenna offset: {loc['antenna_offset_east_ft']:+.0f}ft E, "
                      f"{loc['antenna_offset_north_ft']:+.0f}ft N of the profile location")
    lines.append(f"Band: {results['band_mhz']} MHz   "
                  f"Min. usable elevation: {results['min_elevation_deg']:.0f}°")
    lines.append("")
    lines.append("Annual EME opportunities by region:")
    lines.append(f"  {'Region':<16}{'Passes/yr':>11}{'Avg peak el.':>15}")
    for region, opp in results['eme_opportunities'].items():
        avg_el = f"{opp['avg_peak_elevation_deg']:.1f}°" if opp['annual_passes'] else "--"
        lines.append(f"  {region:<16}{opp['annual_passes']:>11}{avg_el:>15}")
    lines.append("")
    wl = results['wind_loading']
    lines.append(f"Wind loading: {wl['force_lbf']:.1f} lbf at {wl['wind_speed_mph']:.0f} mph "
                  f"(dish area {wl['dish_area_m2']:.2f} m²)")
    rf = results['rf_considerations']
    lines.append(f"RF ({rf['band_name']}, {rf['frequency_mhz']} MHz): "
                  f"wavelength {rf['wavelength_cm']:.1f}cm, "
                  f"tree sensitivity {rf['tree_sensitivity']}, "
                  f"rain fade est. {rf['estimated_rain_fade_db']:.2f} dB")
    if results['tree_blockage'].get('tree_height_ft', 0) > 0:
        tb = results['tree_blockage']
        lines.append(f"Single-direction tree blockage estimate: {tb['blockage_angle_deg']:.1f}° "
                      f"({tb['tree_height_ft']:.0f}ft trees at {tb['tree_distance_ft']:.0f}ft)")
    rec = results['recommendations']
    if rec['reasoning'] or rec['technical_requirements']:
        lines.append("")
        lines.append("Recommendations:")
        for item in rec['reasoning'] + rec['technical_requirements']:
            lines.append(f"  - {item}")
    lines.append("")
    lines.append("Full monthly az/el detail is in this run's data but not shown here --")
    lines.append("use --json or --output <file>.json for the complete breakdown, or:")
    lines.append("  python scripts/generate_polar_plots.py --profile <profile> --band "
                  f"{results['band_mhz']}")
    lines.append("for polar plots + a monthly conditions table.")
    return "\n".join(lines)


def main():
    """Command line interface"""
    import argparse

    parser = argparse.ArgumentParser(description='EME Dish Siting Calculator')
    parser.add_argument('--grid', help='Maidenhead grid square (ignored if --profile is given)')
    parser.add_argument('--profile', help='Path to a site obstruction profile JSON '
                                           '(see data/site_profiles/) -- overrides --grid, '
                                           '--elevation, and --tree-* with a full directional '
                                           'obstruction model')
    parser.add_argument('--band', type=int, default=1296, help='Frequency in MHz')
    parser.add_argument('--dish-diameter', type=float, default=2.4, help='Dish diameter in meters')
    parser.add_argument('--tree-height', type=float, default=0,
                         help='Tree height in feet (ignored if --profile is given)')
    parser.add_argument('--tree-distance', type=float, default=100,
                         help='Distance to trees in feet (ignored if --profile is given)')
    parser.add_argument('--wind-speed', type=float, default=35, help='Max wind speed in mph')
    parser.add_argument('--elevation', type=float, default=0,
                         help='Elevation in meters ASL (ignored if --profile is given)')
    parser.add_argument('--offset-east-ft', type=float, default=0.0,
                         help='Move the antenna this many feet EAST of the profile location '
                              '(negative = west) -- re-run "what if I moved the dish" scenarios '
                              'without re-surveying obstructions')
    parser.add_argument('--offset-north-ft', type=float, default=0.0,
                         help='Move the antenna this many feet NORTH of the profile location '
                              '(negative = south)')
    parser.add_argument('--days', type=int, default=365, help='Number of days to analyze')
    parser.add_argument('--start-date', help='Analysis start date, YYYY-MM-DD (default: '
                                              'the 1st of the current month) -- pin this for '
                                              'reproducible results, since Moon geometry '
                                              'shifts slightly with the exact date range')
    parser.add_argument('--output', help='Save the full results as JSON to this file '
                                          '(a short summary still prints to the terminal too)')
    parser.add_argument('--json', action='store_true',
                         help='Print the full results as JSON to the terminal instead of '
                              'the human-readable summary (useful for piping into other '
                              'tools, e.g. `| jq`). Implied automatically if --output is not '
                              'given and stdout is not a terminal (e.g. when piped/redirected).')

    args = parser.parse_args()

    terrain_profile = None
    if args.profile:
        terrain_profile = TerrainProfile(args.profile)
        lat, lon = terrain_profile.latitude, terrain_profile.longitude
        elevation_m = terrain_profile.elevation_ft * 0.3048
        grid_label = terrain_profile.profile.get('grid_square', args.grid or '')
    else:
        if not args.grid:
            parser.error('--grid is required when --profile is not given')
        calc_tmp = EMECalculator()
        lat, lon = calc_tmp.maidenhead_to_latlon(args.grid)
        elevation_m = args.elevation
        grid_label = args.grid

    calc = EMECalculator(terrain_profile=terrain_profile,
                          offset_east_ft=args.offset_east_ft,
                          offset_north_ft=args.offset_north_ft)
    calc.setup_observer(lat, lon, elevation_m)

    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now().replace(day=1)
    daily_passes = calc.calculate_daily_passes(start_date, frequency_mhz=args.band, days=args.days)
    opportunities = calc.analyze_eme_opportunities(daily_passes)
    monthly = calc.monthly_conditions(opportunities)

    wind_loading = calc.calculate_wind_loading(args.dish_diameter, args.wind_speed)
    rf_considerations = calc.calculate_rf_considerations(args.band, args.tree_height, args.tree_distance)
    tree_blockage = calc.calculate_tree_blockage(args.tree_height, args.tree_distance)

    results = {
        'location': {
            'grid_square': grid_label,
            'latitude': lat,
            'longitude': lon,
            'elevation_m': elevation_m,
            'antenna_offset_east_ft': args.offset_east_ft,
            'antenna_offset_north_ft': args.offset_north_ft,
        },
        'band_mhz': args.band,
        'min_elevation_deg': calc.min_elevation_for_band(args.band),
        'eme_opportunities': {
            region: {
                'annual_passes': len(passes),
                'avg_peak_elevation_deg': (sum(p['elevation'] for p in passes) / len(passes)
                                            if passes else 0),
            }
            for region, passes in opportunities.items()
        },
        'monthly_conditions': monthly,
        'wind_loading': wind_loading,
        'rf_considerations': rf_considerations,
        'tree_blockage': tree_blockage,
    }

    results['recommendations'] = calc.generate_recommendations(results)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {args.output}")
        print()
        print(format_summary(results))
    elif args.json or not sys.stdout.isatty():
        # Explicit --json, or stdout is piped/redirected (e.g. `| jq`,
        # `> file.json`) rather than an interactive terminal -- assume
        # the full machine-readable dump is wanted, not the summary.
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_summary(results))


if __name__ == "__main__":
    main()
