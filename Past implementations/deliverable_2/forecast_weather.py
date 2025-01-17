import datetime
import pandas as pd
from meteostat import Point, Hourly


# Define the location (latitude and longitude for Boston)
latitude = 42.3601
longitude = -71.0589
location_name = "Boston"

# Define the time period (past 2 months)
start = datetime.datetime.now()
end = start + datetime.timedelta(days=2)  # 2 months ago

# Fetch hourly data
point = Point(latitude, longitude)
data = Hourly(point, start, end)
data = data.fetch()

# Add location name to the DataFrame
data['location'] = location_name

# Rename columns to match the database schema
data = data.rename(columns={
    'temp': 'temperature',
    'rhum': 'humidity',
    'prcp': 'precipitation',
    'wspd': 'windspeed',
    'coco': 'cloudcover'
})

# Save the data to a CSV file
data.to_csv('deliverable_2/predict_weather_data.csv', index_label='time')

print("Data for the past 2 months has been saved to 'historical_weather_data.csv' successfully.")
