// EME Dish Calculator JavaScript

// API endpoint - update this with your deployed API Gateway URL
const API_ENDPOINT = 'https://your-api-gateway-url.amazonaws.com/calculate';

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('eme-form');
    const loadingDiv = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const errorDiv = document.getElementById('error');

    form.addEventListener('submit', handleFormSubmit);
});

async function handleFormSubmit(event) {
    event.preventDefault();
    
    // Show loading, hide results/error
    showLoading();
    hideResults();
    hideError();
    
    try {
        const formData = collectFormData();
        const results = await calculateEME(formData);
        displayResults(results);
    } catch (error) {
        console.error('Calculation error:', error);
        showError(error.message || 'An error occurred during calculation');
    }
}

function collectFormData() {
    const form = document.getElementById('eme-form');
    const formData = new FormData(form);
    
    // Convert form data to object
    const data = {};
    
    // Simple fields
    data.grid_square = formData.get('grid_square').toUpperCase();
    data.elevation_m = parseFloat(formData.get('elevation')) || 0;
    data.frequency_mhz = parseInt(formData.get('frequency_mhz'));
    data.dish_diameter_m = parseFloat(formData.get('dish_diameter_m'));
    data.tree_height_ft = parseFloat(formData.get('tree_height_ft')) || 0;
    data.tree_distance_ft = parseFloat(formData.get('tree_distance_ft')) || 100;
    data.max_wind_mph = parseFloat(formData.get('max_wind_mph'));
    
    // Target regions (checkboxes)
    data.target_regions = [];
    const regionCheckboxes = document.querySelectorAll('input[name="target_regions"]:checked');
    regionCheckboxes.forEach(checkbox => {
        data.target_regions.push(checkbox.value);
    });
    
    return data;
}

async function calculateEME(data) {
    // For development/testing, use local calculation
    if (API_ENDPOINT.includes('your-api-gateway-url')) {
        return simulateCalculation(data);
    }
    
    const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
}

function simulateCalculation(data) {
    // Simulate API response for development
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                location: {
                    grid_square: data.grid_square,
                    latitude: 42.733333,
                    longitude: -77.550000,
                    elevation_m: data.elevation_m
                },
                recommendations: {
                    optimal_location: "150-200 feet east of reference point",
                    reasoning: [
                        `Avoid areas within ${data.tree_distance_ft}ft of ${data.tree_height_ft}ft trees (38.7° elevation blockage)`,
                        `Clear line of sight critical for ${getBandName(data.frequency_mhz)} (${data.frequency_mhz} MHz)`
                    ],
                    technical_requirements: [
                        `Foundation rated for ${Math.round(calculateWindForce(data.dish_diameter_m, data.max_wind_mph))}+ lbf wind loading`
                    ]
                },
                eme_opportunities: {
                    Europe: { annual_passes: 240, avg_hours_after_moonrise: 2.7 },
                    Caribbean: { annual_passes: 752, avg_hours_after_moonrise: 3.5 },
                    "South America": { annual_passes: 499, avg_hours_after_moonrise: 4.1 },
                    Africa: { annual_passes: 617, avg_hours_after_moonrise: 3.1 }
                },
                wind_loading: {
                    dish_area_m2: Math.PI * Math.pow(data.dish_diameter_m / 2, 2),
                    force_lbf: calculateWindForce(data.dish_diameter_m, data.max_wind_mph)
                },
                rf_considerations: {
                    frequency_mhz: data.frequency_mhz,
                    band_name: getBandName(data.frequency_mhz),
                    wavelength_cm: 29979.2458 / data.frequency_mhz,
                    tree_sensitivity: getTreeSensitivity(data.frequency_mhz),
                    estimated_tree_loss_db: calculateTreeLoss(data.frequency_mhz, data.tree_height_ft),
                    estimated_rain_fade_db: calculateRainFade(data.frequency_mhz)
                },
                tree_blockage: {
                    tree_height_ft: data.tree_height_ft,
                    tree_distance_ft: data.tree_distance_ft,
                    blockage_angle_deg: Math.atan(data.tree_height_ft * 0.3048 / (data.tree_distance_ft * 0.3048)) * 180 / Math.PI
                }
            });
        }, 2000); // Simulate 2-second calculation time
    });
}

function displayResults(results) {
    hideLoading();
    
    // Location Information
    const locationInfo = document.getElementById('location-info');
    locationInfo.innerHTML = `
        <div class="info-grid">
            <div class="info-item">
                <strong>Grid Square:</strong> ${results.location.grid_square}
            </div>
            <div class="info-item">
                <strong>Coordinates:</strong> ${results.location.latitude.toFixed(6)}°N, ${Math.abs(results.location.longitude).toFixed(6)}°W
            </div>
            <div class="info-item">
                <strong>Elevation:</strong> ${results.location.elevation_m}m ASL
            </div>
        </div>
    `;
    
    // Recommendations
    const recommendations = document.getElementById('recommendations');
    recommendations.innerHTML = `
        <div class="recommendation-box">
            <h4>🎯 Optimal Location</h4>
            <p><strong>${results.recommendations.optimal_location}</strong></p>
        </div>
        <div class="warning-box">
            <h4>⚠️ Important Considerations</h4>
            <ul>
                ${results.recommendations.reasoning.map(reason => `<li>${reason}</li>`).join('')}
            </ul>
        </div>
        <div class="info-grid">
            ${results.recommendations.technical_requirements.map(req => `
                <div class="info-item">
                    <strong>Technical Requirement:</strong> ${req}
                </div>
            `).join('')}
        </div>
    `;
    
    // EME Opportunities
    const opportunities = document.getElementById('eme-opportunities');
    const opportunityCards = Object.entries(results.eme_opportunities)
        .filter(([region, data]) => data.annual_passes > 0)
        .map(([region, data]) => `
            <div class="opportunity-card">
                <h4>${region}</h4>
                <div class="opportunity-count">${data.annual_passes}</div>
                <p>passes/year</p>
                <p><small>Avg ${data.avg_hours_after_moonrise.toFixed(1)}h after moonrise</small></p>
            </div>
        `).join('');
    
    opportunities.innerHTML = `
        <div class="opportunities-grid">
            ${opportunityCards}
        </div>
    `;
    
    // Technical Specifications
    const technicalSpecs = document.getElementById('technical-specs');
    technicalSpecs.innerHTML = `
        <div class="info-grid">
            <div class="info-item">
                <strong>Dish Area:</strong> ${results.wind_loading.dish_area_m2.toFixed(1)} m²
            </div>
            <div class="info-item">
                <strong>Wind Force:</strong> ${Math.round(results.wind_loading.force_lbf)} lbf
            </div>
            <div class="info-item">
                <strong>Tree Blockage:</strong> ${results.tree_blockage.blockage_angle_deg.toFixed(1)}° elevation
            </div>
        </div>
    `;
    
    // RF Considerations
    const rfConsiderations = document.getElementById('rf-considerations');
    rfConsiderations.innerHTML = `
        <div class="info-grid">
            <div class="info-item">
                <strong>Band:</strong> ${results.rf_considerations.band_name} (${results.rf_considerations.frequency_mhz} MHz)
            </div>
            <div class="info-item">
                <strong>Wavelength:</strong> ${results.rf_considerations.wavelength_cm.toFixed(1)} cm
            </div>
            <div class="info-item">
                <strong>Tree Sensitivity:</strong> ${results.rf_considerations.tree_sensitivity}
            </div>
            <div class="info-item">
                <strong>Est. Tree Loss:</strong> ${results.rf_considerations.estimated_tree_loss_db.toFixed(1)} dB
            </div>
            <div class="info-item">
                <strong>Est. Rain Fade:</strong> ${results.rf_considerations.estimated_rain_fade_db.toFixed(1)} dB
            </div>
        </div>
    `;
    
    showResults();
}

// Helper functions
function getBandName(frequency) {
    const bands = {
        144: '2m',
        432: '70cm',
        902: '33cm',
        1296: '23cm',
        2304: '13cm',
        3456: '9cm',
        5760: '6cm',
        10000: '3cm',
        10368: '3cm'
    };
    return bands[frequency] || `${(29979.2458 / frequency).toFixed(1)}cm`;
}

function getTreeSensitivity(frequency) {
    if (frequency < 500) return 'low';
    if (frequency < 1500) return 'medium';
    if (frequency < 3000) return 'high';
    if (frequency < 6000) return 'very high';
    return 'extreme';
}

function calculateWindForce(diameter, windSpeed) {
    const area = Math.PI * Math.pow(diameter / 2, 2);
    const windSpeedMs = windSpeed * 0.44704;
    const pressure = 0.5 * 1.225 * Math.pow(windSpeedMs, 2);
    const forceN = pressure * area;
    return forceN / 4.448; // Convert to lbf
}

function calculateTreeLoss(frequency, treeHeight) {
    if (treeHeight <= 0) return 0;
    const freqFactor = frequency / 144;
    return Math.min(30, freqFactor * 2 * (treeHeight / 50));
}

function calculateRainFade(frequency) {
    if (frequency < 1000) return 0;
    return (frequency / 1000) * 0.5;
}

// UI helper functions
function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

function showResults() {
    document.getElementById('results').classList.remove('hidden');
}

function hideResults() {
    document.getElementById('results').classList.add('hidden');
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    document.getElementById('error').classList.remove('hidden');
}

function hideError() {
    document.getElementById('error').classList.add('hidden');
}
