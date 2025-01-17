import datetime
import pandas as pd
from meteostat import Point, Hourly
import pytz

def update_weather_data(latitude, longitude, location_name, file_path='extra_data.csv', timezone='US/Eastern'):
    """
    Update historical weather data for a given location. Fetches new data and combines it with existing data.

    Parameters:
    latitude (float): Latitude of the location
    longitude (float): Longitude of the location
    location_name (str): Name of the location
    file_path (str): Path to the CSV file for storing data (default: 'extra_data.csv')
    timezone (str): Timezone for the data (default: 'US/Eastern')
    """
    # Load existing data if the file exists
    try:
        existing_data = pd.read_csv(file_path, parse_dates=['time'], index_col='time')
        print("Existing data loaded successfully.")
    except FileNotFoundError:
        existing_data = pd.DataFrame()
        print("No existing data found. Starting fresh.")

    # Define the start and end times for the new data to fetch
    start_time = datetime.datetime(2022, 10, 27,4)
    end_time = datetime.datetime(2024, 10, 27,4)

    # Fetch hourly data for the missing range
    point = Point(latitude, longitude)
    new_data = Hourly(point, start_time, end_time)
    new_data = new_data.fetch()

    # Add location name to the new data
    new_data['location'] = location_name

    # Rename columns to match the database schema
    new_data = new_data.rename(columns={
        'temp': 'temperature',
        'rhum': 'humidity',
        'prcp': 'precipitation',
        'wspd': 'windspeed',
        'coco': 'cloudcover'
    })

    # Convert timezone to specified timezone, then remove the timezone info
    new_data.index = new_data.index.tz_localize('UTC').tz_convert(timezone).tz_localize(None)

    # Combine existing and new data
    if not existing_data.empty:
        combined_data = pd.concat([existing_data, new_data])
    else:
        combined_data = new_data

    # Drop duplicate rows based on the index (time)
    combined_data = combined_data[~combined_data.index.duplicated(keep='first')]

    # Save the updated data back to the CSV file
    combined_data.to_csv(file_path, index_label='time')

    print(f"Historical weather data updated successfully. Data saved to '{file_path}'.")

# Example usage
if __name__ == "__main__":
    update_weather_data(42.3601, -71.0589, "Boston")
