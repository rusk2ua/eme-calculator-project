import json
import boto3
import os
import zipfile
import tempfile
from urllib.request import urlopen

def lambda_handler(event, context):
    """
    Lambda function to deploy web files to S3 bucket
    """
    
    try:
        bucket_name = os.environ['BUCKET_NAME']
        api_endpoint = os.environ['API_ENDPOINT']
        
        s3 = boto3.client('s3')
        
        # Web files content
        web_files = {
            'index.html': get_index_html(api_endpoint),
            'style.css': get_style_css(),
            'script.js': get_script_js(api_endpoint),
            'error.html': get_error_html()
        }
        
        # Upload files to S3
        for filename, content in web_files.items():
            content_type = get_content_type(filename)
            
            s3.put_object(
                Bucket=bucket_name,
                Key=filename,
                Body=content,
                ContentType=content_type,
                CacheControl='max-age=300'  # 5 minutes cache
            )
        
        # Send success response to CloudFormation
        send_response(event, context, 'SUCCESS', {
            'Message': f'Web files deployed to {bucket_name}',
            'BucketName': bucket_name,
            'FilesDeployed': list(web_files.keys())
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        send_response(event, context, 'FAILED', {
            'Message': f'Failed to deploy web files: {str(e)}'
        })

def get_content_type(filename):
    """Get content type based on file extension"""
    if filename.endswith('.html'):
        return 'text/html'
    elif filename.endswith('.css'):
        return 'text/css'
    elif filename.endswith('.js'):
        return 'application/javascript'
    else:
        return 'text/plain'

def get_index_html(api_endpoint):
    """Generate index.html with correct API endpoint"""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EME Dish Siting Calculator</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>🛰️ EME Dish Siting Calculator</h1>
            <p>Calculate optimal Earth-Moon-Earth dish placement for amateur radio</p>
        </header>

        <main>
            <form id="eme-form" class="calculator-form">
                <div class="form-section">
                    <h2>📍 Location</h2>
                    <div class="form-group">
                        <label for="grid-square">Maidenhead Grid Square:</label>
                        <input type="text" id="grid-square" name="grid_square" 
                               placeholder="FN12fr46" pattern="[A-Ra-r]{{2}}[0-9]{{2}}[A-Xa-x]{{2}}[0-9]{{2}}" 
                               title="Enter 8-character grid square (e.g., FN12fr46)" required>
                    </div>
                    <div class="form-group">
                        <label for="elevation">Elevation (meters ASL):</label>
                        <input type="number" id="elevation" name="elevation" 
                               value="0" min="0" max="9000" step="1">
                    </div>
                </div>

                <div class="form-section">
                    <h2>📡 Equipment</h2>
                    <div class="form-group">
                        <label for="frequency">Frequency Band:</label>
                        <select id="frequency" name="frequency_mhz" required>
                            <option value="144">144 MHz (2m)</option>
                            <option value="432">432 MHz (70cm)</option>
                            <option value="1296" selected>1296 MHz (23cm)</option>
                            <option value="2304">2304 MHz (13cm)</option>
                            <option value="3456">3456 MHz (9cm)</option>
                            <option value="5760">5760 MHz (6cm)</option>
                            <option value="10368">10368 MHz (3cm)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="dish-diameter">Dish Diameter (meters):</label>
                        <input type="number" id="dish-diameter" name="dish_diameter_m" 
                               value="2.4" min="0.5" max="10" step="0.1" required>
                    </div>
                </div>

                <div class="form-section">
                    <h2>🌳 Environmental Factors</h2>
                    <div class="form-group">
                        <label for="tree-height">Tree Height (feet):</label>
                        <input type="number" id="tree-height" name="tree_height_ft" 
                               value="0" min="0" max="300" step="1">
                    </div>
                    <div class="form-group">
                        <label for="tree-distance">Distance to Trees (feet):</label>
                        <input type="number" id="tree-distance" name="tree_distance_ft" 
                               value="100" min="10" max="1000" step="10">
                    </div>
                    <div class="form-group">
                        <label for="wind-speed">Maximum Wind Speed (mph):</label>
                        <input type="number" id="wind-speed" name="max_wind_mph" 
                               value="35" min="10" max="150" step="5" required>
                    </div>
                </div>

                <div class="form-section">
                    <h2>🌍 Target Regions</h2>
                    <div class="checkbox-group">
                        <label><input type="checkbox" name="target_regions" value="Europe" checked> Europe</label>
                        <label><input type="checkbox" name="target_regions" value="Caribbean" checked> Caribbean</label>
                        <label><input type="checkbox" name="target_regions" value="South America" checked> South America</label>
                        <label><input type="checkbox" name="target_regions" value="Africa" checked> Africa</label>
                        <label><input type="checkbox" name="target_regions" value="Asia"> Asia</label>
                        <label><input type="checkbox" name="target_regions" value="Oceania"> Oceania</label>
                    </div>
                </div>

                <button type="submit" class="calculate-btn">🧮 Calculate Optimal Placement</button>
            </form>

            <div id="loading" class="loading hidden">
                <div class="spinner"></div>
                <p>Calculating moon positions and optimal placement...</p>
            </div>

            <div id="results" class="results hidden">
                <h2>📊 Results</h2>
                
                <div class="result-section">
                    <h3>📍 Location Information</h3>
                    <div id="location-info"></div>
                </div>

                <div class="result-section">
                    <h3>🎯 Recommendations</h3>
                    <div id="recommendations"></div>
                </div>

                <div class="result-section">
                    <h3>🌙 EME Opportunities</h3>
                    <div id="eme-opportunities"></div>
                </div>

                <div class="result-section">
                    <h3>⚡ Technical Specifications</h3>
                    <div id="technical-specs"></div>
                </div>

                <div class="result-section">
                    <h3>📡 RF Considerations</h3>
                    <div id="rf-considerations"></div>
                </div>
            </div>

            <div id="error" class="error hidden">
                <h3>❌ Error</h3>
                <p id="error-message"></p>
            </div>
        </main>

        <footer>
            <p>Created by amateur radio operators for the EME community | 
               <a href="https://github.com/yourusername/eme-dish-calculator">GitHub</a></p>
        </footer>
    </div>

    <script>
        // Set API endpoint
        const API_ENDPOINT = '{api_endpoint}/calculate';
    </script>
    <script src="script.js"></script>
</body>
</html>'''

def get_style_css():
    """Return CSS content"""
    # This would contain the full CSS - truncated for brevity
    return '''/* EME Dish Calculator Styles - Production Version */
:root {
    --primary-color: #2c3e50;
    --secondary-color: #3498db;
    --accent-color: #e74c3c;
    --success-color: #27ae60;
    --warning-color: #f39c12;
    --background-color: #ecf0f1;
    --text-color: #2c3e50;
    --border-color: #bdc3c7;
    --shadow: 0 2px 10px rgba(0,0,0,0.1);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--background-color);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* Add all other CSS styles here - truncated for brevity */
'''

def get_script_js(api_endpoint):
    """Return JavaScript content with correct API endpoint"""
    return f'''// EME Dish Calculator JavaScript - Production Version

const API_ENDPOINT = '{api_endpoint}/calculate';

document.addEventListener('DOMContentLoaded', function() {{
    const form = document.getElementById('eme-form');
    form.addEventListener('submit', handleFormSubmit);
}});

async function handleFormSubmit(event) {{
    event.preventDefault();
    
    showLoading();
    hideResults();
    hideError();
    
    try {{
        const formData = collectFormData();
        const results = await calculateEME(formData);
        displayResults(results);
    }} catch (error) {{
        console.error('Calculation error:', error);
        showError(error.message || 'An error occurred during calculation');
    }}
}}

// Add all other JavaScript functions here - truncated for brevity
'''

def get_error_html():
    """Return error page HTML"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - EME Dish Calculator</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        h1 { color: #e74c3c; }
    </style>
</head>
<body>
    <h1>Oops! Something went wrong</h1>
    <p>Please try refreshing the page or contact support if the problem persists.</p>
    <a href="/">Return to Calculator</a>
</body>
</html>'''

def send_response(event, context, response_status, response_data):
    """Send response to CloudFormation"""
    import urllib3
    
    response_url = event['ResponseURL']
    
    response_body = {
        'Status': response_status,
        'Reason': f'See CloudWatch Log Stream: {context.log_stream_name}',
        'PhysicalResourceId': context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    }
    
    json_response_body = json.dumps(response_body)
    
    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }
    
    http = urllib3.PoolManager()
    response = http.request('PUT', response_url, body=json_response_body, headers=headers)
    
    print(f"Status code: {response.status}")
    return response
