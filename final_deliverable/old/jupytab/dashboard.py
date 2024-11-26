import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ipywidgets as widgets
from IPython.display import display, clear_output
import joblib

class EnergyDashboard:
    def __init__(self, database_path="energy_data_NE.db"):
        """Initialize dashboard using saved models"""
        self.database_path = database_path
        self.load_saved_models()
        self.create_dashboard()

    def load_saved_models(self):
        """Load the pre-trained models"""
        try:
            self.models = {
                'solar': joblib.load('solar_model.joblib'),
                'wind': joblib.load('wind_model.joblib'),
                'demand': joblib.load('demand_model.joblib')
            }
            print("Successfully loaded pre-trained models")
        except Exception as e:
            print(f"Error loading models: {str(e)}")

    def prepare_features(self, weather_data):
        """Prepare features matching your training data"""
        features = weather_data[['temperature', 'dwpt', 'humidity', 'precipitation',
                               'wdir', 'windspeed', 'pres', 'cloudcover']]

        # Add temporal features
        weather_data['hour'] = weather_data['datetime'].dt.hour
        weather_data['month'] = weather_data['datetime'].dt.month
        weather_data['season'] = np.where(weather_data['datetime'].dt.month.isin([12, 1, 2]), 1,
                                np.where(weather_data['datetime'].dt.month.isin([3, 4, 5]), 2,
                                np.where(weather_data['datetime'].dt.month.isin([6, 7, 8]), 3, 4)))
        weather_data['time_of_day'] = np.where(weather_data['datetime'].dt.hour < 6, 1,
                                      np.where(weather_data['datetime'].dt.hour < 12, 2,
                                      np.where(weather_data['datetime'].dt.hour < 18, 3, 4)))

        return pd.concat([features,
                         weather_data[['hour', 'month', 'season', 'time_of_day']]],
                         axis=1)

    def predict_next_day(self, start_date):
        """Predict generation and demand for next 24 hours"""
        conn = sqlite3.connect(self.database_path)

        query = f"""
        SELECT time as datetime, temperature, dwpt, humidity, precipitation,
               wdir, windspeed, pres, cloudcover
        FROM historical_weather_data
        WHERE time >= datetime('{start_date}')
        AND time < datetime('{start_date}', '+1 day')
        """

        pred_data = pd.read_sql_query(query, conn)
        conn.close()

        if pred_data.empty:
            return None

        # Prepare features
        pred_data['datetime'] = pd.to_datetime(pred_data['datetime'])
        X_pred = self.prepare_features(pred_data)

        # Make predictions
        predictions = {'datetime': pred_data['datetime']}
        for source, model in self.models.items():
            predictions[source] = model.predict(X_pred)

        return pd.DataFrame(predictions)

    def create_plots(self, predictions):
        """Create visualization using plotly"""
        fig = make_subplots(rows=2, cols=1,
                           subplot_titles=('Generation Forecast',
                                         'Demand Forecast'),
                           vertical_spacing=0.15)

        # Generation predictions
        for source in ['solar', 'wind']:
            fig.add_trace(
                go.Scatter(x=predictions['datetime'],
                          y=predictions[source],
                          name=source.title(),
                          mode='lines+markers'),
                row=1, col=1
            )

        # Demand prediction
        fig.add_trace(
            go.Scatter(x=predictions['datetime'],
                      y=predictions['demand'],
                      name='Demand',
                      line=dict(color='red')),
            row=2, col=1
        )

        fig.update_layout(
            height=800,
            title_text="Energy Generation and Demand Forecast",
            showlegend=True
        )

        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Generation (MWh)", row=1, col=1)
        fig.update_yaxes(title_text="Demand (MWh)", row=2, col=1)

        return fig

    def create_dashboard(self):
        """Create interactive dashboard widgets"""
        self.date_picker = widgets.DatePicker(
            description='Start Date:',
            disabled=False
        )

        self.update_button = widgets.Button(
            description='Update Forecast',
            button_style='primary'
        )
        self.update_button.on_click(self.update_visualization)

        self.output = widgets.Output()

        display(widgets.VBox([
            self.date_picker,
            self.update_button,
            self.output
        ]))

    def update_visualization(self, b):
        """Update the visualization based on selected date"""
        with self.output:
            clear_output(wait=True)

            start_date = self.date_picker.value
            if start_date is None:
                print("Please select a date")
                return

            predictions = self.predict_next_day(start_date)
            if predictions is None:
                print("No data available for selected date")
                return

            fig = self.create_plots(predictions)
            fig.show()
