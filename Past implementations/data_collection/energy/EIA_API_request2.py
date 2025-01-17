import os
import requests
import sqlite3
from datetime import datetime, timedelta
import logging
import json
import pandas as pd
import matplotlib.pyplot as plt

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get API key from environment variable
EIA_API_KEY = os.getenv('EIA_API_KEY')

if not EIA_API_KEY:
    raise ValueError("NREL_API_KEY environment variable is not set")

# EIA API Configuration
BASE_URL = "https://api.eia.gov/v2"

def test_api_connection():
    """Test basic API connectivity"""
    try:
        test_url = f"{BASE_URL}/electricity/rto/fuel-type-data?api_key={EIA_API_KEY}"
        logger.info(f"Testing API connection with URL: {test_url}")
        
        response = requests.get(test_url)
        logger.info(f"API Test Response Status: {response.status_code}")
        logger.info(f"API Test Response: {response.text[:500]}...")  # First 500 chars
        
        return response.status_code == 200
    except Exception as e:
        logger.error(f"API test failed: {str(e)}")
        return False

def get_energy_production_data(region: str, start_date: str, end_date: str) -> list:
    """Fetch energy production data from EIA API"""
    endpoint = f"{BASE_URL}/electricity/rto/fuel-type-data/data"
    
    # Build fuel type parameters correctly
    fuel_types = ['SUN', 'WND', 'WAT', 'NUC', 'NG', 'COL']
    params = {
        'api_key': EIA_API_KEY,
        'frequency': 'hourly',
        'data[0]': 'value',
    }
    
    # Add fuel types to parameters
    for i, fuel_type in enumerate(fuel_types):
        params[f'facets[fueltype][{i}]'] = fuel_type
    
    # Add other parameters
    params.update({
        'facets[respondent][]': region,
        'start': start_date,
        'end': end_date,
        'sort[0][column]': 'period',
        'sort[0][direction]': 'desc',
        'offset': 0,
        'length': 5000
    })

    try:
        logger.info(f"Fetching data for {region}")
        logger.info(f"URL: {endpoint}")
        logger.info(f"Parameters: {json.dumps(params, indent=2)}")
        
        response = requests.get(endpoint, params=params)
        
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response URL: {response.url}")
        logger.debug(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            logger.error(f"Error response: {response.text}")
            return []
        
        data = response.json()
        logger.debug(f"Response Data: {json.dumps(data, indent=2)}")
        
        if 'response' not in data:
            logger.error("No 'response' key in data")
            logger.debug(f"Full response: {data}")
            return []
            
        records = data['response'].get('data', [])
        logger.info(f"Retrieved {len(records)} records for {region}")
        
        return records
        
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        return []

def get_historical_dates():
    """Get appropriate historical date range"""
    try:
        current_date = datetime.now()
        
        # Get last month's date range
        first_of_month = current_date.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        
        start_date = last_month_start - timedelta(days=30)
        end_date = last_month_end
        
        logger.info(f"Calculated date range: {start_date} to {end_date}")
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    except Exception as e:
        logger.error(f"Error calculating dates: {str(e)}")
        raise

def main():
    """Main function with enhanced error handling and logging"""
    try:
        logger.info("Starting EIA data collection")
        
        # Test API connection first
        if not test_api_connection():
            logger.error("Failed to connect to EIA API")
            return
            
        logger.info("Successfully connected to EIA API")
        
        # Set up regions
        regions = ['CAISO', 'MISO', 'NYISO', 'PJM', 'ERCOT']
        
        # Get historical dates
        try:
            start_date, end_date = get_historical_dates()
            logger.info(f"Using date range: {start_date} to {end_date}")
        except Exception as e:
            logger.error(f"Failed to calculate dates: {e}")
            return
            
        # Process each region
        for region in regions:
            try:
                logger.info(f"\nProcessing region: {region}")
                
                data = get_energy_production_data(
                    region=region,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if data:
                    logger.info(f"Successfully retrieved {len(data)} records for {region}")
                    # Add processing code here
                else:
                    logger.warning(f"No data retrieved for {region}")
                    
            except Exception as e:
                logger.error(f"Error processing region {region}: {e}")
                continue
        
        logger.info("Data collection complete")
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        return

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical error in main: {str(e)}")
        raise