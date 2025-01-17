import os
import sqlite3
import requests
from datetime import datetime, timedelta
import logging
import json
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# Get API key from environment variable
NREL_API_KEY = os.getenv('NREL_API_KEY')

print(NREL_API_KEY)
# print(NREL_API_KEY)
if not NREL_API_KEY:
    raise ValueError("NREL_API_KEY environment variable is not set")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        CREATE TABLE IF NOT EXISTS SolarProductionHourly (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT NOT NULL,
            state TEXT NOT NULL,
            location_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            ac_output REAL NOT NULL,
            solar_radiation REAL NOT NULL,
            capacity_factor REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(datetime, latitude, longitude)
        );
        """)
        db_conn.conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise

def get_solar_production(state_code: str, latitude: float, longitude: float, db_conn) -> bool:
    """Fetch and store solar production data using PVWatts API with hourly resolution"""
    url = "https://developer.nrel.gov/api/pvwatts/v6.json"
    
    params = {
        'api_key': NREL_API_KEY,
        'lat': latitude,
        'lon': longitude,
        'system_capacity': 4,  # 4 kW system
        'azimuth': 180,       # South facing
        'tilt': 20,           # 20 degree tilt
        'array_type': 1,      # Fixed roof mount
        'module_type': 1,     # Standard module
        'losses': 14,         # Default losses
        'timeframe': 'hourly' # Set to hourly data
    }

    try:
        logger.info(f"Fetching data for coordinates: {latitude}, {longitude}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"API Response: {json.dumps(data, indent=2)}")
        
        if 'outputs' not in data or 'ac' not in data['outputs']:
            logger.error("Invalid data structure in API response")
            return False

        # Get location info
        station_info = data['station_info']
        location_name = f"{station_info['city']}, {station_info['state']}"
        if not location_name.strip():
            location_name = f"Location at {latitude}, {longitude}"
        
        # Get hourly data
        ac_output = data['outputs']['ac']  # AC output per hour
        solar_rad = data['outputs'].get('solrad_hourly', [0] * 8760)  # Solar radiation per hour
        capacity_factor = float(data['outputs'].get('capacity_factor', 0))  # Overall capacity factor
        print(f"{capacity_factor}")
        # Current year start date
        current_date = datetime(datetime.now().year, 1, 1)

        # Store hourly data
        for hour in range(8760):  # 24 hours * 365 days = 8760 hours in a non-leap year
            try:
                # Compute the datetime for each hour
                date_time = current_date + timedelta(hours=hour)
                
                db_conn.cursor.execute("""
                INSERT OR REPLACE INTO SolarProductionHourly 
                (datetime, state, location_name, latitude, longitude, ac_output, 
                solar_radiation, capacity_factor, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    date_time.strftime("%Y-%m-%d %H:%M:%S"), 
                    state_code,
                    location_name,
                    latitude,
                    longitude,
                    ac_output[hour],
                    solar_rad[hour],
                    capacity_factor,
                ))
                
                logger.info(f"Stored data for {location_name} - {date_time}")
                logger.info(f"  AC Output: {ac_output[hour]:.2f} kWh")
                logger.info(f"  Solar Radiation: {solar_rad[hour]:.2f} kWh/m2")
                
            except (ValueError, sqlite3.Error) as e:
                logger.error(f"Error storing data for hour {hour}: {e}")
                continue
        
        db_conn.conn.commit()
        logger.info(f"Successfully stored all hourly data for {location_name}")
        return True
        
    except requests.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

def main():
    # California locations to collect data for
    locations = [
        {"name": "San Francisco", "state": "CA", "lat": 37.7749, "lon": -122.4194},
        {"name": "Los Angeles", "state": "CA", "lat": 34.0522, "lon": -118.2437},
        {"name": "Sacramento", "state": "CA", "lat": 38.5816, "lon": -121.4944},
        {"name": "San Diego", "state": "CA", "lat": 32.7157, "lon": -117.1611}
    ]

    try:
        with DatabaseConnection("hourly_solar_production.db") as db:
            # Initialize database
            initialize_database(db)
            
            # Process data for each location
            for location in locations:
                logger.info(f"\nProcessing data for {location['name']}, {location['state']}")
                success = get_solar_production(
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
