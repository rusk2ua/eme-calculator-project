#!/usr/bin/env python3
"""
EME Dish Siting Calculator
Modular library for calculating optimal EME dish placement
"""

import math
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import ephem

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
    
    # Target region azimuth ranges (approximate)
    TARGET_REGIONS = {
        'Europe': (30, 90),
        'Caribbean': (120, 180),
        'South America': (150, 210),
        'Africa': (60, 120),
        'Asia': (300, 360),
        'Oceania': (240, 300)
    }
    
    def __init__(self):
        self.observer = ephem.Observer()
        
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
    
    def calculate_moonrise_windows(self, start_date: datetime, days: int = 365) -> List[Dict]:
        """Calculate moonrise times and operating windows"""
        moon = ephem.Moon()
        windows = []
        
        current_date = start_date
        for day in range(days):
            self.observer.date = current_date
            
            try:
                moonrise = self.observer.next_rising(moon)
                
                # Calculate positions during 6-hour window after moonrise
                window_positions = []
                for hour_offset in range(7):  # 0-6 hours
                    self.observer.date = moonrise + hour_offset * ephem.hour
                    moon.compute(self.observer)
                    
                    az_deg = math.degrees(moon.az)
                    alt_deg = math.degrees(moon.alt)
                    
                    if alt_deg > 5:  # Moon above horizon
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
    
    def analyze_eme_opportunities(self, windows: List[Dict], 
                                target_regions: List[str] = None) -> Dict:
        """Analyze EME opportunities by region"""
        if target_regions is None:
            target_regions = list(self.TARGET_REGIONS.keys())
        
        region_windows = {region: [] for region in target_regions}
        
        for window in windows:
            for pos in window['positions']:
                az = pos['azimuth']
                alt = pos['elevation']
                
                if alt > 10:  # Good EME elevation
                    for region in target_regions:
                        if region in self.TARGET_REGIONS:
                            min_az, max_az = self.TARGET_REGIONS[region]
                            if min_az <= az <= max_az:
                                region_windows[region].append({
                                    'date': window['date'],
                                    'moonrise': window['moonrise'],
                                    'operating_time': pos['time'],
                                    'azimuth': az,
                                    'elevation': alt,
                                    'hours_after_rise': pos['hour_after_rise']
                                })
        
        return region_windows
    
    def calculate_wind_loading(self, dish_diameter_m: float, 
                             wind_speed_mph: float) -> Dict:
        """Calculate wind loading on dish"""
        dish_area = math.pi * (dish_diameter_m/2)**2  # m²
        wind_speed_ms = wind_speed_mph * 0.44704  # Convert mph to m/s
        
        # Dynamic pressure = 0.5 * density * velocity²
        air_density = 1.225  # kg/m³
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
            # Find closest band
            closest_freq = min(self.BANDS.keys(), 
                             key=lambda x: abs(x - frequency_mhz))
            band_info = self.BANDS[closest_freq].copy()
            band_info['wavelength_cm'] = 29979.2458 / frequency_mhz  # c/f
        else:
            band_info = self.BANDS[frequency_mhz].copy()
        
        # Tree loss estimation (simplified)
        tree_loss_db = 0
        if tree_height_ft > 0:
            # Higher frequencies more affected by vegetation
            freq_factor = frequency_mhz / 144  # Relative to 2m
            tree_loss_db = min(30, freq_factor * 2 * (tree_height_ft / 50))
        
        # Rain fade estimation (simplified)
        rain_fade_db = 0
        if frequency_mhz > 1000:
            rain_fade_db = (frequency_mhz / 1000) * 0.5  # Rough estimate
        
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
        """Calculate elevation angle blocked by trees"""
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
        
        # Add reasoning based on results
        if 'tree_blockage' in analysis_results:
            blockage = analysis_results['tree_blockage']['blockage_angle_deg']
            if blockage > 30:
                recommendations['reasoning'].append(
                    f"Avoid areas within {analysis_results['tree_blockage']['tree_distance_ft']}ft "
                    f"of {analysis_results['tree_blockage']['tree_height_ft']}ft trees "
                    f"({blockage:.1f}° elevation blockage)"
                )
        
        # Wind loading requirements
        if 'wind_loading' in analysis_results:
            force_lbf = analysis_results['wind_loading']['force_lbf']
            recommendations['technical_requirements'].append(
                f"Foundation rated for {force_lbf:.0f}+ lbf wind loading"
            )
        
        # RF considerations
        if 'rf_considerations' in analysis_results:
            rf = analysis_results['rf_considerations']
            if rf['tree_sensitivity'] in ['high', 'very_high', 'extreme']:
                recommendations['reasoning'].append(
                    f"Clear line of sight critical for {rf['band_name']} "
                    f"({rf['frequency_mhz']} MHz)"
                )
        
        return recommendations

def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EME Dish Siting Calculator')
    parser.add_argument('--grid', required=True, help='Maidenhead grid square')
    parser.add_argument('--band', type=int, default=1296, help='Frequency in MHz')
    parser.add_argument('--dish-diameter', type=float, default=2.4, help='Dish diameter in meters')
    parser.add_argument('--tree-height', type=float, default=0, help='Tree height in feet')
    parser.add_argument('--tree-distance', type=float, default=100, help='Distance to trees in feet')
    parser.add_argument('--wind-speed', type=float, default=35, help='Max wind speed in mph')
    parser.add_argument('--elevation', type=float, default=0, help='Elevation in meters ASL')
    parser.add_argument('--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    # Initialize calculator
    calc = EMECalculator()
    
    # Setup location
    lat, lon = calc.maidenhead_to_latlon(args.grid)
    calc.setup_observer(lat, lon, args.elevation)
    
    # Calculate moonrise windows
    start_date = datetime.now().replace(day=1)  # Start of current month
    windows = calc.calculate_moonrise_windows(start_date)
    
    # Analyze opportunities
    opportunities = calc.analyze_eme_opportunities(windows)
    
    # Calculate technical factors
    wind_loading = calc.calculate_wind_loading(args.dish_diameter, args.wind_speed)
    rf_considerations = calc.calculate_rf_considerations(args.band, args.tree_height, args.tree_distance)
    tree_blockage = calc.calculate_tree_blockage(args.tree_height, args.tree_distance)
    
    # Compile results
    results = {
        'location': {
            'grid_square': args.grid,
            'latitude': lat,
            'longitude': lon,
            'elevation_m': args.elevation
        },
        'eme_opportunities': {
            region: {
                'annual_passes': len(ops),
                'avg_hours_after_moonrise': sum(op['hours_after_rise'] for op in ops) / len(ops) if ops else 0
            }
            for region, ops in opportunities.items()
        },
        'wind_loading': wind_loading,
        'rf_considerations': rf_considerations,
        'tree_blockage': tree_blockage
    }
    
    # Generate recommendations
    results['recommendations'] = calc.generate_recommendations(results)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {args.output}")
    else:
        print(json.dumps(results, indent=2, default=str))

if __name__ == "__main__":
    main()
