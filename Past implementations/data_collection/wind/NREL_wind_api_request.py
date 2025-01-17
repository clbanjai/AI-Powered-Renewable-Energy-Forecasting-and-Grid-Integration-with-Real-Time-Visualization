import os
import requests
import sqlite3
from datetime import datetime
import logging
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

NREL_API_KEY = "R2vNqhGv3VfgYVMfndazifkZG6G2VDdTlkwDy9S0"
NREL_EMAIL = "jenn.turliuk@gmail.com"

class DatabaseConnection:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def __enter__(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            return self
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

def initialize_database(db_conn):
    """Initialize database with required table"""
    try:
        db_conn.cursor.execute("""
        CREATE TABLE IF NOT EXISTS WindProduction (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            year INTEGER NOT NULL,
            state TEXT NOT NULL,
            location_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            wind_speed REAL NOT NULL,
            wind_direction REAL,
            power REAL,
            temperature REAL,
            pressure REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, latitude, longitude)
        );
        """)
        db_conn.conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise

def get_wind_data(state_code: str, latitude: float, longitude: float, db_conn) -> bool:
    """Fetch and store wind data using NREL Wind Toolkit API"""
    
    base_url = "https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-download"
    
    # Format the location ID as a string with 4 decimal places
    location_id = f"{latitude:.4f},{longitude:.4f}"
    
    # Simplified parameters for a single year
    params = {
        'api_key': NREL_API_KEY,
        'email': NREL_EMAIL,
        'location_ids': location_id,
        'attributes': 'windspeed,winddirection,power,temperature,pressure',  # Simplified attributes
        'names': '2012',  # Single year
        'utc': 'true'
    }

    try:
        logger.info(f"Requesting data for coordinates: {latitude}, {longitude}")
        logger.info(f"Request URL: {base_url}")
        logger.info(f"Parameters: {params}")
        
        response = requests.get(base_url, params=params, timeout=30)
        
        # Log full response for debugging
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Content: {response.text[:1000]}...")
        
        if response.status_code != 200:
            logger.error(f"Error response: {response.text}")
            return False
        
        data = response.json()
        logger.info(f"Initial response data: {json.dumps(data, indent=2)[:1000]}...")
        
        if 'outputs' not in data:
            logger.error(f"Invalid data structure in API response: {data}")
            return False

        download_url = data['outputs'].get('downloadUrl')
        if not download_url:
            logger.error("No download URL provided in response")
            return False

        logger.info(f"Downloading wind data from: {download_url}")
        download_response = requests.get(download_url, timeout=30)
        download_response.raise_for_status()
        
        try:
            wind_data = download_response.json()
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from download response: {download_response.text[:1000]}...")
            return False
        
        location_name = f"Location at {latitude}, {longitude}"
        processed_count = 0
        
        for entry in wind_data.get('entries', []):
            try:
                date = datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S')
                
                db_conn.cursor.execute("""
                INSERT OR REPLACE INTO WindProduction 
                (date, year, state, location_name, latitude, longitude, 
                wind_speed, wind_direction, power, temperature, pressure, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    date.strftime('%Y-%m-%d'),
                    date.year,
                    state_code,
                    location_name,
                    latitude,
                    longitude,
                    entry.get('windspeed', 0),
                    entry.get('winddirection', 0),
                    entry.get('power', 0),
                    entry.get('temperature', 0),
                    entry.get('pressure', 0)
                ))
                
                processed_count += 1
                if processed_count % 1000 == 0:  # Log progress every 1000 entries
                    logger.info(f"Processed {processed_count} entries for {location_name}")
                
            except (ValueError, sqlite3.Error) as e:
                logger.error(f"Error storing data: {e}")
                continue
        
        db_conn.conn.commit()
        logger.info(f"Successfully stored {processed_count} wind data entries for {location_name}")
        return True
        
    except requests.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Error response: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

def main():
    # Test with a single location first
    locations = [
        {"name": "Altamont Pass", "state": "CA", "lat": 37.7349, "lon": -121.6452}
    ]

    try:
        with DatabaseConnection("wind_production.db") as db:
            initialize_database(db)
            
            for location in locations:
                logger.info(f"\nProcessing data for {location['name']}, {location['state']}")
                success = get_wind_data(
                    state_code=location['state'],
                    latitude=location['lat'],
                    longitude=location['lon'],
                    db_conn=db
                )
                
                if not success:
                    logger.error(f"Failed to process data for {location['name']}")
                    continue
                
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        return

if __name__ == "__main__":
    main()