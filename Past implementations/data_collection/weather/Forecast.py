# import os
# api_key=os.getenv("WEATHER_API_KEY")
# lat, long=(42.360001, -71.092003)

# import requests
# from datetime import datetime, timedelta


# import requests

# def get_forecast(city_id, api_key):
#     # OpenWeatherMap 5-day forecast API endpoint
#     url = f"http://api.openweathermap.org/data/2.5/forecast?id={city_id}&appid={api_key}"
    
#     # Send GET request
#     response = requests.get(url)
    
#     # Check if the request was successful
#     if response.status_code == 200:
#         # Parse JSON data
#         forecast_data = response.json()
        
#         # Print forecast header
#         city_name = forecast_data['city']['name']
#         print(f"5-day forecast for {city_name}:\n")
        
#         # Iterate over each forecast entry (3-hour intervals)
#         for forecast in forecast_data['list']:
#             # Convert timestamp to readable date and time
#             timestamp = forecast['dt']
#             forecast_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
#             # Extract weather data
#             temp = forecast['main']['temp']
#             humidity = forecast['main']['humidity']
#             description = forecast['weather'][0]['description']
#             wind_speed = forecast['wind']['speed']
            
#             # Print each forecast
#             print(f"Date & Time: {forecast_time}")
#             print(f"Temperature: {temp}K")
#             print(f"Humidity: {humidity}%")
#             print(f"Weather: {description.capitalize()}")
#             print(f"Wind Speed: {wind_speed} m/s")
#             print("-" * 30)
#     else:
#         # Print error message if something goes wrong
#         print("Error fetching data. Please check the city ID or API key.")

# # Usage example
# city_id = 524901  # City ID for Moscow (replace with desired city ID)
# get_forecast(city_id, api_key)

import os
import sqlite3
import requests
from datetime import datetime

# Retrieve API key from environment variables
api_key = os.getenv("WEATHER_API_KEY")
lat, long = (42.360001, -71.092003)

# Connect to SQLite database
conn = sqlite3.connect("weather_database.db")
cursor = conn.cursor()

# Create ForecastData table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS ForecastData (
    forecast_id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id INTEGER,
    city_name TEXT,
    forecast_time TEXT,
    temperature REAL,
    humidity REAL,
    description TEXT,
    wind_speed REAL
);
""")
conn.commit()

# Function to fetch and store forecast data
def get_forecast(city_id, api_key):
    # OpenWeatherMap 5-day forecast API endpoint
    url = f"http://api.openweathermap.org/data/2.5/forecast?id={city_id}&appid={api_key}"
    
    # Send GET request
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse JSON data
        forecast_data = response.json()
        
        # Get city name for the forecast
        city_name = forecast_data['city']['name']
        print(f"5-day forecast for {city_name}:\n")
        
        # Iterate over each forecast entry (3-hour intervals)
        for forecast in forecast_data['list']:
            # Convert timestamp to readable date and time
            timestamp = forecast['dt']
            forecast_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            # Extract weather data
            temp = forecast['main']['temp']
            humidity = forecast['main']['humidity']
            description = forecast['weather'][0]['description']
            wind_speed = forecast['wind']['speed']
            
            # Insert data into ForecastData table
            cursor.execute("""
            INSERT INTO ForecastData (city_id, city_name, forecast_time, temperature, humidity, description, wind_speed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (city_id, city_name, forecast_time, temp, humidity, description, wind_speed))
            
            print(f"Date & Time: {forecast_time}")
            print(f"Temperature: {temp}K")
            print(f"Humidity: {humidity}%")
            print(f"Weather: {description.capitalize()}")
            print(f"Wind Speed: {wind_speed} m/s")
            print("-" * 30)
        
        # Commit the transaction to save all entries
        conn.commit()
        print(f"Forecast data stored successfully for {city_name}.")
    else:
        # Print error message if something goes wrong
        print("Error fetching data. Please check the city ID or API key.")

# Usage example
city_id = 5368361  # City ID for Los Angeles (replace with desired city ID)
get_forecast(city_id, api_key)

# Close the database connection
conn.close()
