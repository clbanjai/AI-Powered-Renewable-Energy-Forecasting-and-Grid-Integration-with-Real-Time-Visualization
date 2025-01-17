import os
import requests
import sqlite3
from datetime import datetime, timedelta
import logging
import json
import pandas as pd
import matplotlib.pyplot as plt

from dotenv import load_dotenv


# Set up logging
logging.basicConfig(
    level=logging.INFO,
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
    """Initialize database with all required tables"""
    try:
        # Raw energy production data
        db_conn.cursor.execute("""
        CREATE TABLE IF NOT EXISTS EnergyProduction (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,
            respondent TEXT NOT NULL,
            respondent_name TEXT,
            fuel_type TEXT NOT NULL,
            type_name TEXT NOT NULL,
            value REAL NOT NULL,
            units TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(period, respondent, fuel_type)
        );
        """)
        
        # Daily aggregated statistics
        db_conn.cursor.execute("""
        CREATE TABLE IF NOT EXISTS DailyGeneration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            respondent TEXT NOT NULL,
            fuel_type TEXT NOT NULL,
            total_mwh REAL NOT NULL,
            peak_mwh REAL,
            average_mwh REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, respondent, fuel_type)
        );
        """)
        
        # Regional statistics
        db_conn.cursor.execute("""
        CREATE TABLE IF NOT EXISTS RegionalStats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            respondent TEXT NOT NULL,
            date TEXT NOT NULL,
            total_generation_mwh REAL NOT NULL,
            renewable_percentage REAL,
            peak_hour_mwh REAL,
            average_hourly_mwh REAL,
            coal_percentage REAL,
            gas_percentage REAL,
            nuclear_percentage REAL,
            solar_percentage REAL,
            wind_percentage REAL,
            hydro_percentage REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(respondent, date)
        );
        """)
        
        # Create indexes for better query performance
        db_conn.cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_date ON EnergyProduction(period);")
        db_conn.cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_respondent ON EnergyProduction(respondent);")
        db_conn.cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON DailyGeneration(date);")
        db_conn.cursor.execute("CREATE INDEX IF NOT EXISTS idx_regional_date ON RegionalStats(date);")
        
        db_conn.conn.commit()
        logger.info("Database tables initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise

def get_energy_production_data(region: str, start_date: str, end_date: str) -> list:
    """Fetch energy production data from EIA API"""
    endpoint = f"{BASE_URL}/electricity/rto/fuel-type-data/data"
    
    fuel_types = ['SUN', 'WND', 'WAT', 'NUC', 'NG', 'COL']
    params = {
        'api_key': EIA_API_KEY,
        'frequency': 'hourly',
        'data[0]': 'value',
        'facets[respondent][]': region,
        'start': start_date,
        'end': end_date,
        'sort[0][column]': 'period',
        'sort[0][direction]': 'desc',
        'offset': 0,
        'length': 5000
    }
    
    # Add fuel types to parameters
    for i, fuel_type in enumerate(fuel_types):
        params[f'facets[fueltype][{i}]'] = fuel_type

    try:
        logger.info(f"Fetching data for {region} from {start_date} to {end_date}")
        response = requests.get(endpoint, params=params)
        
        if response.status_code != 200:
            logger.error(f"Error response: {response.text}")
            return []
            
        data = response.json()
        records = data['response']['data']
        logger.info(f"Retrieved {len(records)} records for {region}")
        
        return records
        
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return []

def fetch_and_store_data_for_range(region: str, start_date: str, end_date: str, db):
    """Handle multiple API calls for splitting the date range into chunks of 5000 rows."""
    # Convert start_date and end_date to datetime objects
    current_start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')

    while current_start_date < end_date:
        # Calculate the next end date (keep it within the limit of 5000 rows)
        current_end_date = current_start_date + timedelta(days=30)

        # If the calculated current_end_date exceeds the actual end_date, adjust it
        if current_end_date > end_date:
            current_end_date = end_date

        # Convert current_end_date to string for the API call
        current_end_date_str = current_end_date.strftime('%Y-%m-%d')

        # Fetch data for this chunk
        data = get_energy_production_data(region, current_start_date.strftime('%Y-%m-%d'), current_end_date_str)

        if data:  # If data is retrieved
            success = store_data(db, data, region)  # Store data in DB
            if not success:
                logger.error(f"Failed to store data for {region}")
        else:
            logger.warning(f"No data retrieved for {region}")

        # Move to the next chunk by incrementing current_start_date to the next 30-day period
        current_start_date = current_end_date

        if current_start_date != end_date:
            logger.info(f"Moving to next chunk starting at: {current_start_date.strftime('%Y-%m-%d')}")
        else:
            logger.info(f"Retrieval completed for: {region}")

def store_data(db_conn, data: list, region: str) -> bool:
    """Store energy production data in database"""
    try:
        stored_count = 0
        for entry in data:
            try:
                db_conn.cursor.execute("""
                INSERT OR REPLACE INTO EnergyProduction 
                (period, respondent, respondent_name, fuel_type, type_name, value, units, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    entry.get('period'),
                    entry.get('respondent'),
                    entry.get('respondent-name'),
                    entry.get('fueltype'),
                    entry.get('type-name'),
                    float(entry.get('value', 0)),
                    entry.get('value-units')
                ))
                stored_count += 1
                
                if stored_count % 1000 == 0:
                    logger.info(f"Stored {stored_count} records for {region}")
                
            except sqlite3.Error as e:
                logger.error(f"Error storing entry: {e}")
                continue
            
        db_conn.conn.commit()
        logger.info(f"Successfully stored {stored_count} records for {region}")
        
        # After storing raw data, calculate and store statistics
        if stored_count > 0:
            calculate_statistics(db_conn, region)
        
        return True
        
    except Exception as e:
        logger.error(f"Error storing data: {e}")
        return False

def calculate_statistics(db_conn, region: str):
    """Calculate and store daily and regional statistics"""
    try:
        # Calculate daily generation
        db_conn.cursor.execute("""
        INSERT OR REPLACE INTO DailyGeneration 
        (date, respondent, fuel_type, total_mwh, peak_mwh, average_mwh)
        SELECT 
            date(period), 
            respondent, 
            fuel_type,
            SUM(value) as total_mwh,
            MAX(value) as peak_mwh,
            AVG(value) as average_mwh
        FROM EnergyProduction
        WHERE respondent = ?
        GROUP BY date(period), respondent, fuel_type
        """, (region,))
        
        # Calculate regional statistics
        db_conn.cursor.execute("""
        WITH daily_totals AS (
            SELECT 
                date(period) as date,
                respondent,
                SUM(CASE WHEN fuel_type IN ('SUN', 'WND', 'WAT') THEN value ELSE 0 END) as renewable_gen,
                SUM(value) as total_gen,
                MAX(value) as peak_hour,
                AVG(value) as avg_hour,
                SUM(CASE WHEN fuel_type = 'COL' THEN value ELSE 0 END) as coal_gen,
                SUM(CASE WHEN fuel_type = 'NG' THEN value ELSE 0 END) as gas_gen,
                SUM(CASE WHEN fuel_type = 'NUC' THEN value ELSE 0 END) as nuclear_gen,
                SUM(CASE WHEN fuel_type = 'SUN' THEN value ELSE 0 END) as solar_gen,
                SUM(CASE WHEN fuel_type = 'WND' THEN value ELSE 0 END) as wind_gen,
                SUM(CASE WHEN fuel_type = 'WAT' THEN value ELSE 0 END) as hydro_gen
            FROM EnergyProduction
            WHERE respondent = ?
            GROUP BY date(period), respondent
        )
        INSERT OR REPLACE INTO RegionalStats 
        (respondent, date, total_generation_mwh, renewable_percentage, peak_hour_mwh, 
         average_hourly_mwh, coal_percentage, gas_percentage, nuclear_percentage,
         solar_percentage, wind_percentage, hydro_percentage)
        SELECT 
            respondent,
            date,
            total_gen,
            (renewable_gen / total_gen * 100),
            peak_hour,
            avg_hour,
            (coal_gen / total_gen * 100),
            (gas_gen / total_gen * 100),
            (nuclear_gen / total_gen * 100),
            (solar_gen / total_gen * 100),
            (wind_gen / total_gen * 100),
            (hydro_gen / total_gen * 100)
        FROM daily_totals
        """, (region,))
        
        db_conn.conn.commit()
        logger.info(f"Calculated statistics for {region}")
        
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        db_conn.conn.rollback()

def main():
    regions = ['CAISO', 'MISO', 'NYISO', 'PJM', 'ERCOT']
    
    # Calculate date range (last month)
    end_date = datetime.now() - timedelta(days=30)
    start_date = end_date - timedelta(days=365)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"Fetching data from {start_date_str} to {end_date_str}")

    try:
        with DatabaseConnection("energy_production.db") as db:
            initialize_database(db)
            
            for region in regions:
                logger.info(f"\nProcessing region: {region}")
                fetch_and_store_data_for_range(region, start_date_str, end_date_str, db)
                
        logger.info("Data collection and analysis complete")
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        return

if __name__ == "__main__":
    main()