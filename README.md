# EME Dish Siting Calculator

A comprehensive tool for calculating optimal Earth-Moon-Earth (EME) dish placement based on location, frequency band, and environmental factors.

## Overview

This calculator helps amateur radio operators determine the best location on their property for EME dish installations by analyzing:

- Moon position calculations throughout the year
- Optimal azimuth ranges for target regions
- Wind loading considerations
- Tree/obstruction analysis
- Frequency-specific RF considerations

## Features

- **Location Input**: Maidenhead grid square or lat/lon coordinates
- **Multi-band Support**: 144 MHz, 432 MHz, 1296 MHz, 2304 MHz, 3456 MHz, 5760 MHz, 10 GHz+
- **Target Regions**: Europe, Caribbean, South America, Africa, Asia, Oceania
- **Environmental Factors**: Tree heights, wind speeds, property boundaries
- **Operating Schedule**: Moonrise-based operating windows
- **Web Interface**: Easy-to-use calculator with visual results
- **Serverless Deployment**: AWS Lambda-based backend

## Quick Start

### Web Interface
Visit the deployed calculator at: `https://your-api-gateway-url.amazonaws.com`

### Local Development
```bash
git clone https://github.com/yourusername/eme-dish-calculator.git
cd eme-dish-calculator
pip install -r requirements.txt
python src/eme_calculator.py --grid FN12fr46 --band 1296
```

## Example Case Study: FN12fr46 on 23cm

**Location**: FN12fr46 (42.73°N, 77.55°W, 500m ASL)  
**Band**: 1296 MHz (23cm)  
**Constraints**: 80-foot trees west of house, 30-50 mph winds  

**Recommendation**: Place 2.4m dish 150-200 feet east of house
- **Coverage**: 30°-210° azimuth range
- **Annual Opportunities**: 
  - Europe: 240 passes
  - Caribbean: 752 passes  
  - South America: 499 passes
  - Africa: 617 passes
- **Wind Loading**: 112 lbf @ 35mph, 313 lbf @ 50mph gusts

## Installation & Deployment

### Local Setup
```bash
# Clone repository
git clone https://github.com/yourusername/eme-dish-calculator.git
cd eme-dish-calculator

# Install dependencies
pip install -r requirements.txt

# Run calculations
python src/eme_calculator.py --help
```

### AWS Deployment
```bash
# Install AWS SAM CLI
pip install aws-sam-cli

# Build and deploy
sam build
sam deploy --guided
```

## API Usage

### Calculate EME Windows
```bash
curl -X POST https://your-api.amazonaws.com/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "grid_square": "FN12fr46",
    "frequency_mhz": 1296,
    "dish_diameter_m": 2.4,
    "tree_height_ft": 80,
    "tree_distance_ft": 100,
    "max_wind_mph": 50,
    "target_regions": ["Europe", "Caribbean"]
  }'
```

### Response Format
```json
{
  "location": {
    "grid_square": "FN12fr46",
    "latitude": 42.733333,
    "longitude": -77.550000,
    "elevation_m": 500
  },
  "recommendations": {
    "optimal_location": "150-200 feet east of house",
    "azimuth_range": "30°-210°",
    "foundation_requirements": "Reinforced concrete for 400+ lbf"
  },
  "eme_windows": {
    "Europe": {
      "annual_passes": 240,
      "avg_hours_after_moonrise": 2.7
    }
  },
  "rf_considerations": {
    "frequency_mhz": 1296,
    "wavelength_cm": 23.1,
    "tree_loss_db": 15.2,
    "rain_fade_db": 2.1
  }
}
```

## Frequency Band Considerations

| Band | Frequency | Wavelength | Tree Sensitivity | Rain Fade |
|------|-----------|------------|------------------|-----------|
| 2m   | 144 MHz   | 208 cm     | Low              | Minimal   |
| 70cm | 432 MHz   | 69 cm      | Medium           | Low       |
| 33cm | 902 MHz   | 33 cm      | Medium           | Medium    |
| 23cm | 1296 MHz  | 23 cm      | High             | Medium    |
| 13cm | 2304 MHz  | 13 cm      | Very High        | High      |
| 9cm  | 3456 MHz  | 9 cm       | Extreme          | High      |
| 6cm  | 5760 MHz  | 5 cm       | Extreme          | Very High |
| 3cm  | 10 GHz    | 3 cm       | Extreme          | Very High |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- PyEphem library for astronomical calculations
- Amateur radio EME community for operational insights
- AWS for serverless infrastructure

## Support

- Create an issue for bug reports or feature requests
- Join the discussion in the amateur radio EME forums
- Contact: [your-callsign]@[your-domain].com

---

**73 de [YOUR-CALLSIGN]**  
*Making EME accessible to everyone*
