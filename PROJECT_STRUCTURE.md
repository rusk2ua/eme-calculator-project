# EME Dish Calculator - Project Structure

```
eme-dish-calculator/
├── README.md                 # Main project documentation
├── DEPLOYMENT.md            # AWS deployment guide
├── USAGE.md                 # End-user guide
├── PROJECT_STRUCTURE.md     # This file
├── LICENSE                  # MIT license
├── .gitignore              # Git ignore patterns
├── requirements.txt         # Python dependencies
├── template.yaml           # AWS SAM template
│
├── src/                    # Core calculation modules
│   ├── eme_calculator.py   # Main EME calculator class
│   ├── rf_analysis.py      # Advanced RF analysis
│   ├── terrain.py          # Direction-aware terrain/obstruction horizon model
│   └── sky_noise.py        # EME degradation: galactic sky noise + lunar-distance path loss
│
├── data/
│   ├── site_profiles/      # Site obstruction profiles (JSON)
│   │   └── k2ua_fn12fr46wo.json
│   └── sky_noise/
│       └── galactic_408mhz_grid.json  # Synthesized 408MHz galactic-noise lookup grid
│
├── scripts/
│   ├── generate_polar_plots.py         # Annual per-region polar scatter plots + monthly az/el tables
│   └── generate_monthly_track_plots.py # One plot/month: every region's single best-day pass track
│
├── lambda/                 # AWS Lambda function
│   └── lambda_function.py  # API handler (not yet updated to the terrain model -- see README)
│
├── layer/                  # Lambda layer for dependencies
│   ├── requirements.txt    # Layer dependencies
│   ├── build.sh           # Layer build script
│   └── python/            # Built dependencies (generated)
│
├── web/                    # Web interface
│   ├── index.html         # Main web page
│   ├── style.css          # Styling
│   └── script.js          # Frontend JavaScript
│
├── deploy/                 # Deployment automation
│   └── deploy.py          # Web file deployment Lambda
│
├── tests/
│   ├── test_terrain.py         # Obstruction geometry sanity checks
│   └── test_eme_calculator.py  # Pass-counting, degradation-ranking, and pass-track regression tests
│
└── docs/
    ├── SITE_PROFILE_GUIDE.md   # How to build a site profile JSON for your own property (K2UA worked example)
    ├── plots/                  # Generated annual per-region polar scatter plot PNGs
    │   └── monthly_tracks/     # Generated monthly best-day pass track plot PNGs (one per month, all regions overlaid)
    └── monthly_conditions.md   # Generated monthly peak-condition az/el tables
```

## File Descriptions

### Root Files
- **README.md**: Main project overview, features, and quick start
- **DEPLOYMENT.md**: Complete AWS deployment guide with troubleshooting
- **USAGE.md**: Comprehensive user guide for the calculator
- **LICENSE**: MIT license for open source distribution
- **requirements.txt**: Python package dependencies
- **template.yaml**: AWS SAM infrastructure as code

### Documentation (`docs/`)
- **SITE_PROFILE_GUIDE.md**: How to build a site profile JSON for your own property — schema field by field, why the polar plots' gray wedge looks the way it does, why moonrise/moonset aren't available at every azimuth, and a full worked example (K2UA, FN12fr46wo)

### Source Code (`src/`)
- **eme_calculator.py**: Core EME calculation engine
  - Maidenhead grid conversion
  - Moon position calculations
  - Wind loading analysis
  - Recommendation generation
- **rf_analysis.py**: Advanced RF calculations
  - Frequency-specific characteristics
  - Link budget calculations
  - Dish size recommendations
  - Tree loss modeling
- **terrain.py**: Direction-aware obstruction horizon
  - Site obstruction profile loading (`data/site_profiles/*.json`)
  - Line-segment and azimuth-arc obstruction geometry
  - USGS EPQS regional terrain floor (sparse-sampled + interpolated)
  - Antenna-offset support for "what if I moved the dish" re-runs
- **sky_noise.py**: EME degradation model
  - Galactic sky-noise temperature (synthesized `data/sky_noise/galactic_408mhz_grid.json`, ITU-R P.372-12 frequency scaling)
  - Lunar-distance (range factor) path loss
  - Receiver noise-figure to noise-temperature conversion
  - Combined into a single degradation dB figure used to rank each month's "best day"

### Lambda Function (`lambda/`)
- **lambda_function.py**: AWS Lambda handler
  - HTTP request processing
  - Input validation
  - CORS handling
  - Error management

### Lambda Layer (`layer/`)
- **requirements.txt**: Dependencies for Lambda layer
- **build.sh**: Script to build layer with dependencies
- **python/**: Generated directory with installed packages

### Web Interface (`web/`)
- **index.html**: Single-page application
  - Responsive form interface
  - Results display
  - Error handling
- **style.css**: Modern CSS styling
  - Mobile-responsive design
  - Professional appearance
  - Accessibility features
- **script.js**: Frontend JavaScript
  - Form handling
  - API communication
  - Results visualization

### Deployment (`deploy/`)
- **deploy.py**: Lambda function for web deployment
  - Uploads web files to S3
  - Updates API endpoints
  - CloudFormation integration

## Architecture Components

### Frontend (Web Interface)
- **Technology**: HTML5, CSS3, JavaScript (ES6+)
- **Hosting**: S3 + CloudFront
- **Features**: Responsive, accessible, fast loading

### Backend (API)
- **Technology**: Python 3.9, AWS Lambda
- **Framework**: Serverless (AWS SAM)
- **Features**: Auto-scaling, cost-effective, reliable

### Infrastructure
- **Deployment**: AWS SAM (CloudFormation)
- **API**: API Gateway with CORS
- **CDN**: CloudFront for global distribution
- **Storage**: S3 for web hosting

## Development Workflow

### Local Development
1. **Setup**: `python3 -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`), then `pip install -r requirements.txt` -- see README's [Virtual Environment Setup](README.md#virtual-environment-setup)
2. **Test**: `python src/eme_calculator.py --grid FN12fr46 --band 1296`
3. **Web**: Open `web/index.html` in browser
4. **API**: `sam local start-api`

### Testing
1. **Unit Tests**: `python -m pytest tests/`
2. **Manual**: Use web interface with known inputs

### Deployment
1. **Build Layer**: `cd layer && ./build.sh`
2. **Build SAM**: `sam build`
3. **Deploy**: `sam deploy`

## Key Features

### Calculator Engine
- Accurate astronomical calculations using PyEphem
- Comprehensive RF analysis for all amateur bands
- Environmental factor modeling
- Multi-region EME opportunity analysis

### Web Interface
- Intuitive form-based input
- Real-time validation
- Comprehensive results display
- Mobile-friendly design

### AWS Infrastructure
- Serverless architecture for cost efficiency
- Global CDN for fast access
- Auto-scaling for traffic spikes
- Infrastructure as Code for reliability

## Extension Points

### Adding New Features
1. **New Calculations**: Extend `EMECalculator` class
2. **New Bands**: Update `BAND_CHARACTERISTICS` in `rf_analysis.py`
3. **New Regions**: Add to `TARGET_REGIONS` mapping
4. **New UI Elements**: Modify web interface files

### Integration Options
1. **API Access**: RESTful API for external tools
2. **Batch Processing**: Command-line interface
3. **Mobile App**: Use existing API backend
4. **Desktop App**: Embed calculation engine

## Dependencies

### Python Packages
- **ephem**: Astronomical calculations
- **boto3**: AWS SDK (Lambda only)
- **requests**: HTTP client (development)
- **matplotlib / numpy**: Polar az/el plot generation (`scripts/generate_polar_plots.py`, `scripts/generate_monthly_track_plots.py`)
- **pytest**: Test suite (dev/test only)

### AWS Services
- **Lambda**: Serverless compute
- **API Gateway**: HTTP API management
- **S3**: Static website hosting
- **CloudFront**: Content delivery network
- **CloudFormation**: Infrastructure management

### Development Tools
- **AWS SAM CLI**: Local development and deployment
- **AWS CLI**: AWS service management
- **Git**: Version control
- **Python 3.9+**: Runtime environment

## Security Considerations

### Input Validation
- Grid square format validation
- Numeric range checking
- SQL injection prevention
- XSS protection

### API Security
- CORS properly configured
- Rate limiting via API Gateway
- Input sanitization
- Error message sanitization

### Infrastructure Security
- Minimal IAM permissions
- No hardcoded secrets
- HTTPS everywhere
- Regular security updates

## Performance Characteristics

### Calculation Performance
- **Typical Response**: <2 seconds
- **Complex Scenarios**: <5 seconds
- **Memory Usage**: <100MB
- **CPU Usage**: Minimal

### Web Performance
- **Page Load**: <1 second (cached)
- **API Calls**: <3 seconds
- **Mobile Performance**: Optimized
- **Offline Capability**: Partial (cached resources)

## Maintenance

### Regular Tasks
- Update Python dependencies
- Monitor AWS costs
- Review error logs
- Update documentation

### Monitoring
- CloudWatch metrics
- Error rate tracking
- Performance monitoring
- Cost analysis

---

This structure provides a solid foundation for the EME Dish Calculator while remaining extensible for future enhancements.
