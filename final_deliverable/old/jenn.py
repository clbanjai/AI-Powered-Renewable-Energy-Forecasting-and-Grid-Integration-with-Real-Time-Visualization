import os
import sqlite3
import requests
import datetime
from meteostat import Point, Hourly

# Retrieve API keys from environment variables
eia_api_key = os.getenv("EIA_API_KEY")
nrel_api_key = os.getenv("NREL_API_KEY")

# Define locations and time periods
locations = ['Boston', 'New York', 'California']
start_date = datetime.datetime.now() - datetime.timedelta(days=3*365)  # 3 years ago
end_date = datetime.datetime.now()

# Connect to SQLite database
conn = sqlite3.connect('energy_weather_data.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS weather_data (
    id INTEGER PRIMARY KEY,
    location TEXT,
    timestamp DATETIME,
    temperature REAL,
    humidity REAL,
    windspeed REAL,
    cloudcover REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS energy_production (
    id INTEGER PRIMARY KEY,
    location TEXT,
    timestamp DATETIME,
    source_type TEXT,
    value REAL
)
""")

# Fetch and store weather data from Meteostat
for location in locations:
    lat, lon = get_location_coordinates(location)
    point = Point(lat, lon)
    data = Hourly(point, start_date, end_date)
    data = data.fetch()

    for index, row in data.iterrows():
        cursor.execute("""
        INSERT INTO weather_data (location, timestamp, temperature, humidity, windspeed, cloudcover)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (location, index.strftime('%Y-%m-%d %H:%M:%S'), row['temp'], row['rhum'], row['wspd'], row['coco']))

# Fetch and store energy data from EIA and NREL
for location in locations:
    eia_data = fetch_eia_data(location, start_date, end_date, eia_api_key)
    nrel_data = fetch_nrel_data(location, start_date, end_date, nrel_api_key)

    for record in eia_data:
        cursor.execute("""
        INSERT INTO energy_production (location, timestamp, source_type, value)
        VALUES (?, ?, ?, ?)
        """, (location, record['timestamp'], record['source_type'], record['value']))

    for record in nrel_data:
        cursor.execute("""
        INSERT INTO energy_production (location, timestamp, source_type, value)
        VALUES (?, ?, ?, ?)
        """, (location, record['timestamp'], record['source_type'], record['value']))

conn.commit()
conn.close()

print("Data has been inserted into the database successfully.")

def get_location_coordinates(location):
    # Lookup the latitude and longitude for the given location
    if location == 'Boston':
        return 42.3601, -71.0589
    elif location == 'New York':
        return 40.7128, -74.0060
    elif location == 'California':
        return 36.7783, -119.4179
    else:
        raise ValueError(f"Unknown location: {location}")

def fetch_eia_data(location, start_date, end_date, api_key):
    # Fetch energy data from the EIA API for the given location and time period
    data = []
    source_types = ['solar', 'wind', 'gas', 'demand']
    for source_type in source_types:
        url = f"https://api.eia.gov/v2/electricity/rto/region-data/data/"
        params = {
            "api_key": api_key,
            "start": start_date.strftime('%Y-%m-%d'),
            "end": end_date.strftime('%Y-%m-%d'),
            "data": ["value"],
            "facets": {"type": [source_type]},
            "frequency": "hourly"
        }
        response = requests.get(url, params=params)
        data.extend(process_eia_data(response.json(), source_type, location))
    return data

def fetch_nrel_data(location, start_date, end_date, api_key):
    # Fetch energy data from the NREL API for the given location and time period
    data = []
    source_types = ['solar', 'wind']
    for source_type in source_types:
        url = f"https://developer.nrel.gov/api/solar/nsrdb_psm3_hourly_{source_type}.json"
        params = {
            "api_key": api_key,
            "latitude": get_location_coordinates(location)[0],
            "longitude": get_location_coordinates(location)[1],
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_datÅe.strftime('%Y-%m-%d')
        }
        response = requests.get(url, params=params)
        data.extend(process_nrel_data(response.json(), source_type, location))
    return data

def process_eia_data(raw_data, source_type, location):
    processed_data = []
    try:
        for record in raw_data['response']['data']:
            processed_data.append({
                'timestamp': record['period'],
                'source_type': source_type,
                'value': float(record['value']),
                'location': location
            })
    except KeyError as e:
        print(f"Error processing EIA data: {e}")
    return processed_data

def process_nrel_data(raw_data, source_type, location):
    processed_data = []
    try:
        for record in raw_data['outputs']['meta']['time_index']:
            processed_data.append({
                'timestamp': record,
                'source_type': source_type,
                'value': raw_data['outputs'][source_type][record],
                'location': location
            })
    except KeyError as e:
        print(f"Error processing NREL data: {e}")
    return processed_data
