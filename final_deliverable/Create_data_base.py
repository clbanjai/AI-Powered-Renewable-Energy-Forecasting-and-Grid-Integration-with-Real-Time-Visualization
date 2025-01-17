import pandas as pd
import sqlite3

# File paths for the CSV files
csv_files = {
    "NG_data_NE": "NG_data_NE.csv",
    "SUN_data_NE": "SUN_data_NE.csv",
    "WND_data_NE": "WND_data_NE.csv",
    "historical_weather_data": "historical_weather_data.csv",
    "demand_data_NE": "demand_data_NE.csv"
}

# Database file name
database_name = "energy_data_NE.db"

# Connect to the SQLite database (creates the database if it doesn't exist)
conn = sqlite3.connect(database_name)
cursor = conn.cursor()

# Load each CSV file into the database
for table_name, file_path in csv_files.items():
    print(f"Processing {file_path}...")

    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    # Write the DataFrame to a table in the SQL database
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    print(f"Table '{table_name}' created successfully.")

# Verify tables were created
print("Tables in the database:")
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print([table[0] for table in tables])

# Close the database connection
conn.close()

print(f"Data from CSV files successfully loaded into {database_name}.")
