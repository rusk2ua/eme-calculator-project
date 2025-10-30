import json
import os
import sys
from datetime import datetime

# Add the src directory to the path so we can import our calculator
sys.path.append('/opt/python')

try:
    from eme_calculator import EMECalculator
except ImportError:
    # Fallback for local testing
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    from eme_calculator import EMECalculator

def lambda_handler(event, context):
    """
    AWS Lambda handler for EME dish calculator API
    """
    
    # Enable CORS
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
    
    try:
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Parse request body
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            body = event
        
        # Validate required fields
        required_fields = ['grid_square', 'frequency_mhz', 'dish_diameter_m', 'max_wind_mph']
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': f'Missing required field: {field}',
                        'required_fields': required_fields
                    })
                }
        
        # Extract parameters with defaults
        grid_square = body['grid_square'].upper()
        frequency_mhz = int(body['frequency_mhz'])
        dish_diameter_m = float(body['dish_diameter_m'])
        max_wind_mph = float(body['max_wind_mph'])
        elevation_m = float(body.get('elevation_m', 0))
        tree_height_ft = float(body.get('tree_height_ft', 0))
        tree_distance_ft = float(body.get('tree_distance_ft', 100))
        target_regions = body.get('target_regions', ['Europe', 'Caribbean', 'South America', 'Africa'])
        
        # Validate grid square format
        if not validate_grid_square(grid_square):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Invalid grid square format. Expected format: AB12cd34'
                })
            }
        
        # Initialize calculator
        calc = EMECalculator()
        
        # Setup location
        try:
            lat, lon = calc.maidenhead_to_latlon(grid_square)
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Invalid grid square: {str(e)}'
                })
            }
        
        calc.setup_observer(lat, lon, elevation_m)
        
        # Calculate moonrise windows (limit to 90 days for performance)
        start_date = datetime.now().replace(day=1)
        windows = calc.calculate_moonrise_windows(start_date, days=90)
        
        # Analyze opportunities
        opportunities = calc.analyze_eme_opportunities(windows, target_regions)
        
        # Calculate technical factors
        wind_loading = calc.calculate_wind_loading(dish_diameter_m, max_wind_mph)
        rf_considerations = calc.calculate_rf_considerations(frequency_mhz, tree_height_ft, tree_distance_ft)
        tree_blockage = calc.calculate_tree_blockage(tree_height_ft, tree_distance_ft)
        
        # Compile results
        results = {
            'location': {
                'grid_square': grid_square,
                'latitude': lat,
                'longitude': lon,
                'elevation_m': elevation_m
            },
            'eme_opportunities': {
                region: {
                    'annual_passes': len(ops) * 4,  # Scale 90-day sample to annual
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
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(results, default=str)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")  # CloudWatch logging
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

def validate_grid_square(grid):
    """Validate Maidenhead grid square format"""
    if len(grid) < 6 or len(grid) > 8:
        return False
    
    # First two characters: A-R
    if not (grid[0].isalpha() and grid[1].isalpha() and 
            'A' <= grid[0] <= 'R' and 'A' <= grid[1] <= 'R'):
        return False
    
    # Next two characters: 0-9
    if not (grid[2].isdigit() and grid[3].isdigit()):
        return False
    
    # Next two characters (if present): A-X
    if len(grid) >= 6:
        if not (grid[4].isalpha() and grid[5].isalpha() and
                'A' <= grid[4].upper() <= 'X' and 'A' <= grid[5].upper() <= 'X'):
            return False
    
    # Last two characters (if present): 0-9
    if len(grid) == 8:
        if not (grid[6].isdigit() and grid[7].isdigit()):
            return False
    
    return True

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'body': json.dumps({
            'grid_square': 'FN12fr46',
            'frequency_mhz': 1296,
            'dish_diameter_m': 2.4,
            'tree_height_ft': 80,
            'tree_distance_ft': 100,
            'max_wind_mph': 50,
            'elevation_m': 500,
            'target_regions': ['Europe', 'Caribbean', 'South America', 'Africa']
        })
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
