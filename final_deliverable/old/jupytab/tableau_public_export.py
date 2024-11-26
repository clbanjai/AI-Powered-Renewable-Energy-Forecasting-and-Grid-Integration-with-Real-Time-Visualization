# tableau_public_export.py
import pandas as pd
import sqlite3
from datetime import datetime

def prepare_data_for_tableau_public():
    """Prepare and export data in a format ready for Tableau Public"""
    conn = sqlite3.connect("energy_data_NE.db")

    # Create a complete dataset with all necessary information
    generation_query = """
    WITH all_generation AS (
        SELECT datetime, 'Solar' as source, value
        FROM SUN_data_NE
        UNION ALL
        SELECT datetime, 'Wind' as source, value
        FROM WND_data_NE
        UNION ALL
        SELECT datetime, 'Natural Gas' as source, value
        FROM NG_data_NE
    ),
    weather_data AS (
        SELECT
            time as datetime,
            temperature,
            windspeed,
            cloudcover,
            humidity
        FROM historical_weather_data
    ),
    demand_data AS (
        SELECT datetime, Demand
        FROM demand_data_NE
    )
    SELECT
        g.datetime,
        g.source,
        g.value as generation,
        w.temperature,
        w.windspeed,
        w.cloudcover,
        w.humidity,
        d.Demand,
        strftime('%H', g.datetime) as hour,
        strftime('%m', g.datetime) as month,
        CASE
            WHEN strftime('%m', g.datetime) IN ('12','01','02') THEN 'Winter'
            WHEN strftime('%m', g.datetime) IN ('03','04','05') THEN 'Spring'
            WHEN strftime('%m', g.datetime) IN ('06','07','08') THEN 'Summer'
            ELSE 'Fall'
        END as season,
        CASE
            WHEN strftime('%H', g.datetime) < '06' THEN 'Night'
            WHEN strftime('%H', g.datetime) < '12' THEN 'Morning'
            WHEN strftime('%H', g.datetime) < '18' THEN 'Afternoon'
            ELSE 'Evening'
        END as time_of_day
    FROM all_generation g
    LEFT JOIN weather_data w ON g.datetime = w.datetime
    LEFT JOIN demand_data d ON g.datetime = d.datetime
    ORDER BY g.datetime
    """

    # Load and process data
    df = pd.read_sql_query(generation_query, conn)
    conn.close()

    # Convert datetime
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Add some calculated fields
    df['demand_met_percentage'] = (df['generation'] / df['Demand'] * 100).round(2)
    df['hour'] = df['datetime'].dt.hour
    df['date'] = df['datetime'].dt.date

    # Export to CSV
    output_file = 'tableau_public_data.csv'
    df.to_csv(output_file, index=False)
    print(f"Data exported to {output_file}")

    # Print some statistics
    print("\nDataset Overview:")
    print(f"Time range: {df['datetime'].min()} to {df['datetime'].max()}")
    print(f"Total records: {len(df):,}")
    print(f"\nGeneration sources: {', '.join(df['source'].unique())}")

    return output_file

if __name__ == "__main__":
    output_file = prepare_data_for_tableau_public()
