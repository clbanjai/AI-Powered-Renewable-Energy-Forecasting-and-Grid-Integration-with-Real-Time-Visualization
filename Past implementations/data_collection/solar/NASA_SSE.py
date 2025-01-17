import requests
import pandas as pd

# Define your query parameters
latitude = 37.7749  # Latitude of the location (e.g., San Francisco)
longitude = -122.4194  # Longitude of the location (e.g., San Francisco)
start_date = '2023-01-01'  # Start date (format: YYYY-MM-DD)
end_date = '2023-01-31'  # End date (format: YYYY-MM-DD)

# NASA POWER API URL
url = f"https://power.larc.nasa.gov/api/temporal/daily/point?start={start_date}&end={end_date}&latitude={latitude}&longitude={longitude}&parameters=GHI,DNI,DHI&community=RE&format=JSON"

# Fetch data from the API
response = requests.get(url)
data = response.json()
print(data)
# Check if the response contains the requested data
if 'properties' in data and 'parameter' in data['properties']:
    solar_data = data['properties']['parameter']
    
    # Convert the data into a pandas DataFrame for easier handling
    ghi_data = pd.DataFrame(solar_data['GHI'], columns=['GHI'])
    dni_data = pd.DataFrame(solar_data['DNI'], columns=['DNI'])
    dhi_data = pd.DataFrame(solar_data['DHI'], columns=['DHI'])
    
    # Combine the data into a single DataFrame
    solar_df = pd.concat([ghi_data, dni_data, dhi_data], axis=1)
    solar_df.index = pd.to_datetime(list(solar_data['GHI'].keys()), format='%Y%m%d')  # Convert index to datetime
    
    print(solar_df.head())  # Print the first few rows of the data

else:
    print("No data returned. Check the parameters and API response.")
