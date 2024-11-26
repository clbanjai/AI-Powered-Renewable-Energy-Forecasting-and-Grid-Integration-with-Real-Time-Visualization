from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
from meteostat import Point, Hourly
import plotly.graph_objects as go
import plotly
import json

app = Flask(__name__)

# Load models at startup
try:
    models = {
        'solar': pickle.load(open('solar_model.pkl', 'rb')),
        'wind': pickle.load(open('wind_model.pkl', 'rb')),
        'demand': pickle.load(open('demand_model.pkl', 'rb'))
    }
    print("✅ Models loaded successfully")
except Exception as e:
    print(f"Error loading models: {str(e)}")
    models = None

def get_weather_data(start_date, lat=42.3601, lon=-71.0589):
    """Get weather data"""
    try:
        start = pd.to_datetime(start_date)
        end = start + timedelta(days=1)
        location = Point(lat, lon)
        data = Hourly(location, start, end)
        data = data.fetch()
        
        if data.empty:
            return None
            
        # Rename columns
        data = data.rename(columns={
            'temp': 'temperature',
            'dwpt': 'dwpt',
            'rhum': 'humidity',
            'prcp': 'precipitation',
            'wdir': 'wdir',
            'wspd': 'windspeed',
            'pres': 'pres',
            'coco': 'cloudcover'
        })
        
        data = data.reset_index()
        data = data.rename(columns={'time': 'datetime'})
        return data
    except Exception as e:
        print(f"Error getting weather data: {str(e)}")
        return None

def prepare_features(weather_data):
    """Prepare features for prediction"""
    features = weather_data[['temperature', 'dwpt', 'humidity', 'precipitation',
                           'wdir', 'windspeed', 'pres', 'cloudcover']]

    data = weather_data.copy()
    data['hour'] = data['datetime'].dt.hour
    data['month'] = data['datetime'].dt.month
    data['season'] = np.where(data['datetime'].dt.month.isin([12, 1, 2]), 1,
                    np.where(data['datetime'].dt.month.isin([3, 4, 5]), 2,
                    np.where(data['datetime'].dt.month.isin([6, 7, 8]), 3, 4)))
    data['time_of_day'] = np.where(data['datetime'].dt.hour < 6, 1,
                          np.where(data['datetime'].dt.hour < 12, 2,
                          np.where(data['datetime'].dt.hour < 18, 3, 4)))

    return pd.concat([features, data[['hour', 'month', 'season', 'time_of_day']]], axis=1)

def create_plot(predictions):
    """Create plotly figure"""
    fig = go.Figure()
    
    # Convert datetime to string for JSON serialization
    x_values = predictions['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
    
    # Add traces
    fig.add_trace(go.Scatter(x=x_values, y=predictions['solar'].tolist(),
                            name='Solar', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=x_values, y=predictions['wind'].tolist(),
                            name='Wind', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=x_values, y=predictions['demand'].tolist(),
                            name='Demand', line=dict(color='red')))

    fig.update_layout(
        title="Energy Generation and Demand Forecast",
        xaxis_title="Time",
        yaxis_title="MWh",
        showlegend=True
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_forecast', methods=['POST'])
def get_forecast():
    if not models:
        return jsonify({'error': 'Models not loaded'}), 500
        
    try:
        # Get date from request
        date_str = request.form.get('date')
        time_str = request.form.get('time', '00:00')
        start_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
        
        # Get weather data
        weather_data = get_weather_data(start_datetime)
        if weather_data is None:
            return jsonify({'error': 'Could not get weather data'}), 500
            
        # Prepare features and make predictions
        X_pred = prepare_features(weather_data)
        predictions = {'datetime': weather_data['datetime']}
        
        for name, model in models.items():
            predictions[name] = model.predict(X_pred)
            
        predictions = pd.DataFrame(predictions)
        
        # Create plot
        plot_json = create_plot(predictions)
        
        # Create data table
        data_table = predictions.to_dict('records')
        
        return jsonify({
            'plot': plot_json,
            'data': data_table
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)