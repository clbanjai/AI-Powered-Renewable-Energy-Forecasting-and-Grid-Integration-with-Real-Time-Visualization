# with day of week

import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
import sqlite3

def get_season(month):
    if month in [12, 1, 2]: return 1
    elif month in [3, 4, 5]: return 2
    elif month in [6, 7, 8]: return 3
    else: return 4

def prepare_data():
    # Connect to SQLite database
    conn = sqlite3.connect('energy_data_NE.db')
    cursor = conn.cursor()

    # Load data from tables
    cursor.execute("SELECT * FROM weather_data")
    weather_data = cursor.fetchall()
    weather_df = pd.DataFrame(weather_data, columns=['id', 'location', 'timestamp', 'temperature', 'humidity', 'windspeed', 'cloudcover'])

    cursor.execute("SELECT * FROM energy_production")
    energy_data = cursor.fetchall()
    energy_df = pd.DataFrame(energy_data, columns=['id', 'location', 'timestamp', 'source_type', 'value'])

    cursor.execute("SELECT * FROM demand_data_NE")
    demand_data = cursor.fetchall()
    demand_df = pd.DataFrame(demand_data, columns=['id', 'datetime', 'region', 'Demand', 'Net Generation'])

    # Convert timestamps
    weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
    energy_df['timestamp'] = pd.to_datetime(energy_df['timestamp'])
    demand_df['datetime'] = pd.to_datetime(demand_df['datetime'])

    # Filter for wind energy
    energy_df = energy_df[energy_df['source_type'] == 'wind']

    # Add time features
    weather_df['season'] = weather_df['timestamp'].dt.month.map(get_season)
    weather_df['hour'] = weather_df['timestamp'].dt.hour
    weather_df['day_of_week'] = weather_df['timestamp'].dt.dayofweek
    demand_df['hour'] = demand_df['datetime'].dt.hour
    demand_df['day_of_week'] = demand_df['datetime'].dt.dayofweek

    # Create multiple rolling averages
    for window in [3, 6, 12, 24]:
        weather_df[f'temp_{window}h'] = weather_df.groupby('location')['temperature'].rolling(window).mean().reset_index(0, drop=True)
        weather_df[f'wind_{window}h'] = weather_df.groupby('location')['windspeed'].rolling(window).mean().reset_index(0, drop=True)
        weather_df[f'humid_{window}h'] = weather_df.groupby('location')['humidity'].rolling(window).mean().reset_index(0, drop=True)

    # Merge datasets
    df = pd.merge(weather_df, energy_df, on='timestamp', how='inner')
    df = pd.merge(df, demand_df, left_on='timestamp', right_on='datetime', how='inner')
    print(f"Shape after merge: {df.shape}")

    # Base features
    base_features = [
        'temperature', 'humidity', 'windspeed', 'cloudcover', 'season', 'hour',
        'day_of_week', 'Demand', 'Net Generation'
    ]

    # Add rolling average features
    rolling_features = [col for col in weather_df.columns if any(x in col for x in ['_3h', '_6h', '_12h', '_24h'])]
    base_features.extend(rolling_features)

    X = df[base_features].copy()

    # Enhanced seasonal interactions
    X['wind_by_season'] = X['windspeed'] * X['season']
    X['wind_by_season_squared'] = X['wind_by_season'] ** 2
    X['temp_by_season'] = X['temperature'] * X['season']
    X['humid_by_season'] = X['humidity'] * X['season']

    # Time-based interactions
    X['wind_by_hour'] = X['windspeed'] * X['hour']
    X['temp_by_hour'] = X['temperature'] * X['hour']
    X['wind_by_dayofweek'] = X['windspeed'] * X['day_of_week']

    # Complex interactions
    X['wind_cubed'] = X['windspeed'] ** 3
    X['temp_squared'] = X['temperature'] ** 2
    X['wind_temp_humid'] = X['windspeed'] * X['temperature'] * X['humidity']

    # Target variable
    y = df['value']

    # Close database connection
    conn.close()

    return X, y

def train_model(X, y):
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Grid search parameters
    param_grid = {
        'n_estimators': [200, 300, 400],
        'max_depth': [6, 8, 10],
        'learning_rate': [0.01, 0.03, 0.05],
        'min_child_weight': [1, 3, 5],
        'subsample': [0.7, 0.8, 0.9],
        'colsample_bytree': [0.7, 0.8, 0.9],
        'gamma': [0, 1, 2]
    }

    # Initialize base model for grid search
    base_model = XGBRegressor(random_state=42)

    # Perform grid search
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=param_grid,
        cv=5,
        n_jobs=-1,
        verbose=2,
        scoring='neg_root_mean_squared_error'
    )

    grid_search.fit(X_train, y_train)

    # Get best model
    model = grid_search.best_estimator_
    print(f"Best parameters: {grid_search.best_params_}")

    # Make predictions
    y_pred = model.predict(X_test)

    # Calculate metrics
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    # Feature importance
    importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    # Plotting
    plt.figure(figsize=(15, 6))
    plt.subplot(1, 2, 1)
    importance.head(15).plot(x='feature', y='importance', kind='bar')
    plt.title('Top 15 Feature Importance')
    plt.xticks(rotation=45)

    plt.subplot(1, 2, 2)
    plt.scatter(y_test, y_pred, alpha=0.5)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
    plt.xlabel('Actual Energy Output (MWh)')
    plt.ylabel('Predicted Energy Output (MWh)')
    plt.title('Actual vs Predicted')

    plt.tight_layout()
    plt.savefig('wind_model_results_enhanced.png')

    return model, rmse, r2, importance

if __name__ == "__main__":
    X, y = prepare_data()
    model, rmse, r2, importance = train_model(X, y)

    print(f"\nModel Performance:")
    print(f"RMSE: {rmse:.2f} MWh")
    print(f"R² Score: {r2:.2f}")
    print("\nTop 15 Features:")
    print(importance.head(15))
