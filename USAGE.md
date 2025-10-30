# EME Dish Calculator - Usage Guide

A comprehensive guide for using the EME Dish Siting Calculator to find the optimal location for your Earth-Moon-Earth dish installation.

## Quick Start

1. **Visit the Calculator**: Go to the deployed web interface
2. **Enter Your Location**: Input your Maidenhead grid square
3. **Select Equipment**: Choose frequency band and dish size
4. **Add Constraints**: Enter tree heights, wind speeds, etc.
5. **Calculate**: Get optimal placement recommendations

## Input Parameters

### 📍 Location Information

#### Maidenhead Grid Square
- **Format**: 8 characters (e.g., FN12fr46)
- **Required**: Yes
- **Example**: FN12fr46 (Rochester, NY area)
- **Tip**: Use online grid square calculators if unsure

#### Elevation (ASL)
- **Units**: Meters above sea level
- **Range**: 0-9000m
- **Default**: 0m
- **Impact**: Higher elevation = better horizon clearance

### 📡 Equipment Specifications

#### Frequency Band
Available bands with characteristics:

| Band | Frequency | Wavelength | Typical Use | Difficulty |
|------|-----------|------------|-------------|------------|
| 2m   | 144 MHz   | 208 cm     | Beginner EME | Easy |
| 70cm | 432 MHz   | 69 cm      | Popular EME | Medium |
| 33cm | 902 MHz   | 33 cm      | Intermediate EME | Medium |
| 23cm | 1296 MHz  | 23 cm      | Advanced EME | Hard |
| 13cm | 2304 MHz  | 13 cm      | Microwave | Very Hard |
| 9cm  | 3456 MHz  | 9 cm       | Microwave | Extreme |
| 6cm  | 5760 MHz  | 5 cm       | Microwave | Extreme |
| 3cm  | 10 GHz    | 3 cm       | Microwave | Extreme |

#### Dish Diameter
- **Units**: Meters
- **Range**: 0.5-10m
- **Common Sizes**: 1.2m, 1.8m, 2.4m, 3.0m, 4.0m
- **Impact**: Larger = more gain, narrower beamwidth

### 🌳 Environmental Factors

#### Tree Height
- **Units**: Feet
- **Range**: 0-300ft
- **Impact**: Blocks low-elevation moon passes
- **Tip**: Measure tallest trees near potential dish location

#### Distance to Trees
- **Units**: Feet  
- **Range**: 10-1000ft
- **Impact**: Determines elevation blockage angle
- **Tip**: Measure from dish location to tree base

#### Maximum Wind Speed
- **Units**: Miles per hour
- **Range**: 10-150 mph
- **Impact**: Determines foundation requirements
- **Tip**: Check local weather records for historical maximums

### 🌍 Target Regions

Select regions you want to work:

#### Europe
- **Azimuth Range**: 30°-90° (Northeast)
- **Best Times**: Evening/night in North America
- **Peak Activity**: Winter months

#### Caribbean  
- **Azimuth Range**: 120°-180° (Southeast)
- **Best Times**: Late evening/early morning
- **Peak Activity**: Year-round

#### South America
- **Azimuth Range**: 150°-210° (South-Southwest)  
- **Best Times**: Early morning hours
- **Peak Activity**: Spring/Fall

#### Africa
- **Azimuth Range**: 60°-120° (East-Southeast)
- **Best Times**: Evening hours
- **Peak Activity**: Winter months

#### Asia
- **Azimuth Range**: 300°-360° (Northwest-North)
- **Best Times**: Early morning
- **Peak Activity**: Limited from North America

#### Oceania
- **Azimuth Range**: 240°-300° (Southwest-West)
- **Best Times**: Late night/early morning
- **Peak Activity**: Limited from North America

## Understanding Results

### 📍 Location Information
- **Coordinates**: Decimal degrees for verification
- **Grid Square**: Confirms your input
- **Elevation**: Height above sea level

### 🎯 Recommendations

#### Optimal Location
- **Primary Recommendation**: Best spot on your property
- **Reasoning**: Why this location is optimal
- **Alternatives**: Secondary options if available

#### Important Considerations
- **Tree Blockage**: Elevation angles blocked by vegetation
- **RF Considerations**: Frequency-specific concerns
- **Wind Loading**: Structural requirements

### 🌙 EME Opportunities

For each target region:
- **Annual Passes**: Number of favorable EME windows per year
- **Average Hours After Moonrise**: Typical operating time
- **Peak Months**: Best times for that region

### ⚡ Technical Specifications

#### Wind Loading
- **Dish Area**: Surface area exposed to wind
- **Force at Max Wind**: Structural load in pounds-force
- **Foundation Requirements**: Concrete specifications

#### Tree Blockage Analysis
- **Blockage Angle**: Elevation angle blocked by trees
- **Clearance Distance**: Minimum distance for clear path
- **Impact Assessment**: Effect on EME operations

### 📡 RF Considerations

#### Frequency-Specific Data
- **Band Name**: Common amateur designation
- **Wavelength**: Physical wavelength
- **Tree Sensitivity**: How vegetation affects this frequency

#### Loss Estimates
- **Tree Loss**: Signal attenuation through vegetation (dB)
- **Rain Fade**: Weather-related signal loss (dB)
- **Path Loss**: Free-space loss to moon and back (dB)

## Interpreting Recommendations

### Excellent Locations (Score 80-100)
- ✅ Clear line of sight to target regions
- ✅ Minimal tree blockage
- ✅ Appropriate dish size for frequency
- ✅ Manageable wind loading

### Good Locations (Score 60-79)
- ⚠️ Some minor obstructions
- ⚠️ Adequate but not optimal dish size
- ⚠️ Moderate tree losses acceptable

### Marginal Locations (Score 40-59)
- ⚠️ Significant tree blockage
- ⚠️ Undersized dish for frequency
- ⚠️ High wind loading concerns

### Poor Locations (Score <40)
- ❌ Major obstructions
- ❌ Inadequate equipment
- ❌ Severe environmental challenges

## Optimization Tips

### Improving Your Score

#### Reduce Tree Blockage
- Move dish farther from trees
- Choose higher elevation on property
- Consider tree removal (with permits)
- Use taller tower/mast

#### Optimize Equipment
- Larger dish = better performance
- Lower frequency = more forgiving
- Better location > bigger dish

#### Environmental Mitigation
- Reinforced foundation for wind
- Guy wires for stability
- Fold-down capability for storms
- Underground cable runs

### Frequency Band Selection

#### Beginners (First EME)
- **Recommended**: 144 MHz (2m)
- **Dish Size**: 4m+ for good results
- **Advantages**: Forgiving, active community

#### Intermediate Operators
- **Recommended**: 432 MHz (70cm)
- **Dish Size**: 2.4m minimum
- **Advantages**: Good balance of performance/difficulty

#### Advanced Operators
- **Recommended**: 1296 MHz (23cm)
- **Dish Size**: 1.8m minimum
- **Advantages**: Smaller dishes, less crowded

#### Microwave Enthusiasts
- **Bands**: 2304 MHz and up
- **Dish Size**: <2m typical
- **Challenges**: Weather sensitive, precise pointing

## Common Scenarios

### Scenario 1: Suburban Property
- **Constraints**: Limited space, nearby trees
- **Strategy**: Optimize location, consider 70cm/23cm
- **Solutions**: Smaller dish, higher frequency

### Scenario 2: Rural Property  
- **Advantages**: Space, fewer obstructions
- **Strategy**: Larger dish, lower frequency
- **Opportunities**: Multiple band capability

### Scenario 3: High Wind Area
- **Constraints**: Structural challenges
- **Strategy**: Fold-down dish, reinforced foundation
- **Solutions**: Smaller dish, guy wires

### Scenario 4: Dense Tree Cover
- **Constraints**: Limited clear areas
- **Strategy**: Find best compromise location
- **Solutions**: Tree removal, tower height

## Troubleshooting

### Low Opportunity Counts
- **Check**: Target region selections
- **Verify**: Grid square accuracy
- **Consider**: Different frequency bands

### High Wind Loading
- **Review**: Dish diameter selection
- **Consider**: Fold-down mechanisms
- **Plan**: Reinforced foundations

### Excessive Tree Loss
- **Evaluate**: Alternative locations
- **Consider**: Tree management
- **Explore**: Tower solutions

### Poor Suitability Score
- **Analyze**: Individual factors
- **Prioritize**: Most impactful changes
- **Compromise**: Balance all factors

## Advanced Features

### API Access
For automated calculations or integration:

```bash
curl -X POST https://your-api-endpoint/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "grid_square": "FN12fr46",
    "frequency_mhz": 1296,
    "dish_diameter_m": 2.4,
    "tree_height_ft": 80,
    "max_wind_mph": 50
  }'
```

### Batch Processing
Calculate multiple scenarios:
- Different frequencies
- Various dish sizes
- Multiple locations

### Export Results
- Save calculations as JSON
- Print-friendly reports
- Share with other operators

## Best Practices

### Planning Phase
1. **Survey Property**: Walk entire area
2. **Measure Accurately**: Use proper tools
3. **Check Regulations**: Zoning, HOA rules
4. **Consider Future**: Tree growth, construction

### Installation Phase
1. **Professional Help**: For foundations, towers
2. **Safety First**: Proper equipment, procedures
3. **Test Thoroughly**: Before final installation
4. **Document Everything**: For future reference

### Operation Phase
1. **Regular Maintenance**: Keep system optimal
2. **Weather Monitoring**: Protect equipment
3. **Performance Tracking**: Log results
4. **Community Engagement**: Share experiences

## Getting Help

### Calculator Issues
- Check input format and ranges
- Try different browsers
- Clear browser cache
- Report bugs on GitHub

### EME Questions
- Join EME mailing lists
- Attend hamfests and conventions
- Connect with local EME operators
- Read EME-specific publications

### Technical Support
- Consult antenna modeling software
- Professional RF engineering help
- Manufacturer technical support
- Amateur radio forums

---

**Good luck with your EME adventures!**  
**73 de [YOUR-CALLSIGN]**
