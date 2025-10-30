#!/usr/bin/env python3
"""
RF Analysis Module for EME Dish Calculator
Advanced frequency-specific calculations and considerations
"""

import math
from typing import Dict, Tuple

class RFAnalyzer:
    """Advanced RF analysis for EME operations"""
    
    # Detailed frequency band characteristics
    BAND_CHARACTERISTICS = {
        144: {
            "name": "2m",
            "wavelength_cm": 208.3,
            "tree_attenuation_db_per_m": 0.1,
            "rain_rate_coefficient": 0.0001,
            "atmospheric_noise_k": 290,
            "typical_dish_sizes": [2.4, 4.0, 6.0, 8.0],
            "min_elevation_deg": 5,
            "doppler_shift_hz_per_ms": 0.48,
            "path_loss_free_space_db": 32.4 + 20 * math.log10(144)
        },
        432: {
            "name": "70cm", 
            "wavelength_cm": 69.4,
            "tree_attenuation_db_per_m": 0.3,
            "rain_rate_coefficient": 0.0003,
            "atmospheric_noise_k": 150,
            "typical_dish_sizes": [2.4, 3.0, 4.0, 6.0],
            "min_elevation_deg": 8,
            "doppler_shift_hz_per_ms": 1.44,
            "path_loss_free_space_db": 32.4 + 20 * math.log10(432)
        },
        902: {
            "name": "33cm",
            "wavelength_cm": 33.2,
            "tree_attenuation_db_per_m": 0.5,
            "rain_rate_coefficient": 0.001,
            "atmospheric_noise_k": 100,
            "typical_dish_sizes": [1.8, 2.4, 3.0, 4.0],
            "min_elevation_deg": 10,
            "doppler_shift_hz_per_ms": 3.01,
            "path_loss_free_space_db": 32.4 + 20 * math.log10(902)
        },
        1296: {
            "name": "23cm",
            "wavelength_cm": 23.1,
            "tree_attenuation_db_per_m": 1.0,
            "rain_rate_coefficient": 0.002,
            "atmospheric_noise_k": 50,
            "typical_dish_sizes": [1.8, 2.4, 3.0, 4.0],
            "min_elevation_deg": 10,
            "doppler_shift_hz_per_ms": 4.32,
            "path_loss_free_space_db": 32.4 + 20 * math.log10(1296)
        },
        2304: {
            "name": "13cm",
            "wavelength_cm": 13.0,
            "tree_attenuation_db_per_m": 2.0,
            "rain_rate_coefficient": 0.008,
            "atmospheric_noise_k": 30,
            "typical_dish_sizes": [1.2, 1.8, 2.4, 3.0],
            "min_elevation_deg": 15,
            "doppler_shift_hz_per_ms": 7.68,
            "path_loss_free_space_db": 32.4 + 20 * math.log10(2304)
        },
        3456: {
            "name": "9cm",
            "wavelength_cm": 8.7,
            "tree_attenuation_db_per_m": 3.5,
            "rain_rate_coefficient": 0.015,
            "atmospheric_noise_k": 25,
            "typical_dish_sizes": [0.9, 1.2, 1.8, 2.4],
            "min_elevation_deg": 20,
            "doppler_shift_hz_per_ms": 11.52,
            "path_loss_free_space_db": 32.4 + 20 * math.log10(3456)
        },
        5760: {
            "name": "6cm",
            "wavelength_cm": 5.2,
            "tree_attenuation_db_per_m": 5.0,
            "rain_rate_coefficient": 0.035,
            "atmospheric_noise_k": 20,
            "typical_dish_sizes": [0.6, 0.9, 1.2, 1.8],
            "min_elevation_deg": 25,
            "doppler_shift_hz_per_ms": 19.2,
            "path_loss_free_space_db": 32.4 + 20 * math.log10(5760)
        },
        10000: {
            "name": "3cm",
            "wavelength_cm": 3.0,
            "tree_attenuation_db_per_m": 7.5,
            "rain_rate_coefficient": 0.075,
            "atmospheric_noise_k": 15,
            "typical_dish_sizes": [0.3, 0.6, 0.9, 1.2],
            "min_elevation_deg": 30,
            "doppler_shift_hz_per_ms": 33.33,
            "path_loss_free_space_db": 32.4 + 20 * math.log10(10000)
        },
        10368: {
            "name": "3cm",
            "wavelength_cm": 2.9,
            "tree_attenuation_db_per_m": 8.0,
            "rain_rate_coefficient": 0.08,
            "atmospheric_noise_k": 15,
            "typical_dish_sizes": [0.3, 0.6, 0.9, 1.2],
            "min_elevation_deg": 30,
            "doppler_shift_hz_per_ms": 34.56,
            "path_loss_free_space_db": 32.4 + 20 * math.log10(10368)
        }
    }
    
    def __init__(self):
        pass
    
    def analyze_frequency_band(self, frequency_mhz: int, 
                             dish_diameter_m: float,
                             tree_height_ft: float = 0,
                             tree_distance_ft: float = 100,
                             rain_rate_mm_hr: float = 5) -> Dict:
        """Comprehensive frequency band analysis"""
        
        if frequency_mhz not in self.BAND_CHARACTERISTICS:
            raise ValueError(f"Unsupported frequency: {frequency_mhz} MHz")
        
        band = self.BAND_CHARACTERISTICS[frequency_mhz]
        
        # Basic calculations
        wavelength_m = band["wavelength_cm"] / 100
        dish_diameter_wavelengths = dish_diameter_m / wavelength_m
        
        # Antenna gain calculation (parabolic dish)
        efficiency = 0.6  # Typical dish efficiency
        gain_db = 10 * math.log10(efficiency * (math.pi * dish_diameter_m / wavelength_m) ** 2)
        
        # Beamwidth calculation
        beamwidth_deg = 70 * wavelength_m / dish_diameter_m
        
        # Tree loss calculation
        tree_loss_db = self.calculate_tree_loss(
            frequency_mhz, tree_height_ft, tree_distance_ft
        )
        
        # Rain fade calculation
        rain_fade_db = self.calculate_rain_fade(frequency_mhz, rain_rate_mm_hr)
        
        # Path loss (EME distance ~770,000 km round trip)
        eme_distance_km = 770000
        path_loss_db = band["path_loss_free_space_db"] + 20 * math.log10(eme_distance_km)
        
        # System noise temperature
        system_noise_k = band["atmospheric_noise_k"] + 50  # Add receiver noise
        
        # Doppler considerations
        max_doppler_hz = band["doppler_shift_hz_per_ms"] * 1000  # Max relative velocity ~1 km/s
        
        return {
            "frequency_mhz": frequency_mhz,
            "band_name": band["name"],
            "wavelength_cm": band["wavelength_cm"],
            "wavelength_m": wavelength_m,
            "dish_diameter_wavelengths": dish_diameter_wavelengths,
            "antenna_gain_db": gain_db,
            "beamwidth_deg": beamwidth_deg,
            "tree_loss_db": tree_loss_db,
            "rain_fade_db": rain_fade_db,
            "path_loss_db": path_loss_db,
            "system_noise_k": system_noise_k,
            "max_doppler_hz": max_doppler_hz,
            "min_elevation_deg": band["min_elevation_deg"],
            "typical_dish_sizes": band["typical_dish_sizes"],
            "suitability_score": self.calculate_suitability_score(
                frequency_mhz, dish_diameter_m, tree_loss_db
            )
        }
    
    def calculate_tree_loss(self, frequency_mhz: int, 
                          tree_height_ft: float, 
                          tree_distance_ft: float) -> float:
        """Calculate RF loss through vegetation"""
        
        if tree_height_ft <= 0 or tree_distance_ft <= 0:
            return 0
        
        band = self.BAND_CHARACTERISTICS[frequency_mhz]
        
        # Convert to meters
        tree_height_m = tree_height_ft * 0.3048
        tree_distance_m = tree_distance_ft * 0.3048
        
        # Calculate elevation angle to clear trees
        clearance_angle_rad = math.atan(tree_height_m / tree_distance_m)
        clearance_angle_deg = math.degrees(clearance_angle_rad)
        
        # If moon is below clearance angle, calculate path through vegetation
        # Simplified model: assume path through vegetation at grazing angle
        if clearance_angle_deg > band["min_elevation_deg"]:
            # Path length through vegetation (simplified)
            path_through_trees_m = tree_height_m / math.sin(clearance_angle_rad)
            loss_db = band["tree_attenuation_db_per_m"] * path_through_trees_m
            return min(loss_db, 40)  # Cap at 40 dB
        
        return 0
    
    def calculate_rain_fade(self, frequency_mhz: int, rain_rate_mm_hr: float) -> float:
        """Calculate rain fade using ITU-R model (simplified)"""
        
        band = self.BAND_CHARACTERISTICS[frequency_mhz]
        
        # ITU-R P.838 coefficients (simplified)
        k = band["rain_rate_coefficient"]
        alpha = 1.0  # Simplified
        
        # Rain fade in dB/km
        fade_db_per_km = k * (rain_rate_mm_hr ** alpha)
        
        # Effective path length through rain (assume 5 km average)
        effective_path_km = 5
        
        return fade_db_per_km * effective_path_km
    
    def calculate_suitability_score(self, frequency_mhz: int, 
                                  dish_diameter_m: float,
                                  tree_loss_db: float) -> float:
        """Calculate overall suitability score (0-100)"""
        
        band = self.BAND_CHARACTERISTICS[frequency_mhz]
        
        # Base score
        score = 100
        
        # Penalize for small dish relative to frequency
        wavelength_m = band["wavelength_cm"] / 100
        dish_wavelengths = dish_diameter_m / wavelength_m
        
        if dish_wavelengths < 10:
            score -= 30
        elif dish_wavelengths < 20:
            score -= 15
        
        # Penalize for tree losses
        if tree_loss_db > 20:
            score -= 40
        elif tree_loss_db > 10:
            score -= 20
        elif tree_loss_db > 5:
            score -= 10
        
        # Frequency-specific adjustments
        if frequency_mhz >= 3456:  # Microwave bands
            score -= 10  # More challenging
        elif frequency_mhz <= 432:  # VHF/UHF
            score += 10  # More forgiving
        
        return max(0, min(100, score))
    
    def recommend_dish_size(self, frequency_mhz: int, 
                          target_gain_db: float = None) -> Dict:
        """Recommend optimal dish size for frequency"""
        
        band = self.BAND_CHARACTERISTICS[frequency_mhz]
        wavelength_m = band["wavelength_cm"] / 100
        
        recommendations = []
        
        for dish_size in band["typical_dish_sizes"]:
            efficiency = 0.6
            gain_db = 10 * math.log10(efficiency * (math.pi * dish_size / wavelength_m) ** 2)
            beamwidth_deg = 70 * wavelength_m / dish_size
            
            recommendations.append({
                "diameter_m": dish_size,
                "gain_db": gain_db,
                "beamwidth_deg": beamwidth_deg,
                "suitability": "excellent" if gain_db > 30 else "good" if gain_db > 25 else "marginal"
            })
        
        # Find optimal size
        if target_gain_db:
            optimal_diameter = wavelength_m * math.sqrt(10 ** (target_gain_db / 10) / (efficiency * math.pi))
            optimal_diameter = round(optimal_diameter * 4) / 4  # Round to nearest 0.25m
        else:
            optimal_diameter = band["typical_dish_sizes"][1]  # Second option usually good compromise
        
        return {
            "frequency_mhz": frequency_mhz,
            "band_name": band["name"],
            "optimal_diameter_m": optimal_diameter,
            "recommendations": recommendations
        }
    
    def calculate_link_budget(self, frequency_mhz: int,
                            dish_diameter_m: float,
                            tx_power_w: float = 100,
                            elevation_deg: float = 15) -> Dict:
        """Calculate EME link budget"""
        
        analysis = self.analyze_frequency_band(frequency_mhz, dish_diameter_m)
        
        # Transmit power
        tx_power_dbw = 10 * math.log10(tx_power_w)
        
        # Antenna gains (assume same dish for TX and RX)
        tx_gain_db = analysis["antenna_gain_db"]
        rx_gain_db = analysis["antenna_gain_db"]
        
        # Path loss
        path_loss_db = analysis["path_loss_db"]
        
        # Additional losses
        misc_losses_db = 3  # Feedline, mismatch, etc.
        
        # Elevation-dependent losses
        if elevation_deg < 10:
            elevation_loss_db = (10 - elevation_deg) * 0.5
        else:
            elevation_loss_db = 0
        
        # Calculate received signal level
        rx_signal_dbw = (tx_power_dbw + tx_gain_db + rx_gain_db - 
                        path_loss_db - misc_losses_db - elevation_loss_db)
        
        # Noise floor
        bandwidth_hz = 2500  # Typical SSB bandwidth
        noise_floor_dbw = 10 * math.log10(1.38e-23 * analysis["system_noise_k"] * bandwidth_hz)
        
        # Signal-to-noise ratio
        snr_db = rx_signal_dbw - noise_floor_dbw
        
        return {
            "frequency_mhz": frequency_mhz,
            "tx_power_dbw": tx_power_dbw,
            "tx_gain_db": tx_gain_db,
            "rx_gain_db": rx_gain_db,
            "path_loss_db": path_loss_db,
            "misc_losses_db": misc_losses_db,
            "elevation_loss_db": elevation_loss_db,
            "rx_signal_dbw": rx_signal_dbw,
            "noise_floor_dbw": noise_floor_dbw,
            "snr_db": snr_db,
            "link_margin_db": snr_db - 10,  # 10 dB required for reliable copy
            "feasible": snr_db > 10
        }

def main():
    """Test the RF analyzer"""
    analyzer = RFAnalyzer()
    
    # Test analysis for 23cm band
    analysis = analyzer.analyze_frequency_band(1296, 2.4, 80, 100, 5)
    print("RF Analysis for 23cm band:")
    for key, value in analysis.items():
        print(f"  {key}: {value}")
    
    print("\nDish recommendations:")
    recommendations = analyzer.recommend_dish_size(1296)
    for rec in recommendations["recommendations"]:
        print(f"  {rec['diameter_m']}m: {rec['gain_db']:.1f} dB gain, {rec['beamwidth_deg']:.1f}° beamwidth ({rec['suitability']})")
    
    print("\nLink budget:")
    link_budget = analyzer.calculate_link_budget(1296, 2.4, 100, 15)
    print(f"  SNR: {link_budget['snr_db']:.1f} dB")
    print(f"  Link margin: {link_budget['link_margin_db']:.1f} dB")
    print(f"  Feasible: {link_budget['feasible']}")

if __name__ == "__main__":
    main()
