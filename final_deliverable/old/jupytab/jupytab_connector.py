from jupytab import DatabricksDatabases, DataConnector, Table, Column
import pandas as pd
import sqlite3
import numpy as np

class EnergyDataConnector(DataConnector):
    def get_tables(self):
        return [
            Table(
                name='weather',
                columns=[
                    Column(name='datetime', data_type='datetime'),
                    Column(name='temperature', data_type='float'),
                    Column(name='dwpt', data_type='float'),
                    Column(name='humidity', data_type='float'),
                    Column(name='precipitation', data_type='float'),
                    Column(name='wdir', data_type='float'),
                    Column(name='windspeed', data_type='float'),
                    Column(name='pres', data_type='float'),
                    Column(name='cloudcover', data_type='float')
                ]
            ),
            Table(
                name='generation',
                columns=[
                    Column(name='datetime', data_type='datetime'),
                    Column(name='source', data_type='string'),
                    Column(name='value', data_type='float')
                ]
            ),
            Table(
                name='demand',
                columns=[
                    Column(name='datetime', data_type='datetime'),
                    Column(name='Demand', data_type='float')
                ]
            )
        ]

    def get_data(self, table_name, columns):
        conn = sqlite3.connect("energy_data_NE.db")

        if table_name == 'weather':
            query = """
            SELECT time as datetime, temperature, dwpt, humidity, precipitation,
                   wdir, windspeed, pres, cloudcover
            FROM historical_weather_data
            """
            df = pd.read_sql_query(query, conn)

        elif table_name == 'generation':
            query = """
            SELECT datetime, 'Solar' as source, value
            FROM SUN_data_NE
            UNION ALL
            SELECT datetime, 'Wind' as source, value
            FROM WND_data_NE
            UNION ALL
            SELECT datetime, 'Natural Gas' as source, value
            FROM NG_data_NE
            """
            df = pd.read_sql_query(query, conn)

        elif table_name == 'demand':
            query = """
            SELECT datetime, Demand
            FROM demand_data_NE
            """
            df = pd.read_sql_query(query, conn)

        conn.close()

        # Convert datetime strings to datetime objects
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])

        return df[columns]

# Create an instance of the connector
connector = EnergyDataConnector()
