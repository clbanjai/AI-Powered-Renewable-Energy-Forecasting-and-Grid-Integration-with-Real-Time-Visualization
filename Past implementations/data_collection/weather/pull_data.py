import sqlite3
import logging

def get_last_n_entries(db_name: str, table_name: str, n: int):
    """Fetches the last n entries from the specified table in the given SQLite database.

    Args:
        db_name (str): Name of the SQLite database file.
        table_name (str): Name of the table to query.
        n (int): Number of recent entries to retrieve.

    Returns:
        list[dict]: List of dictionaries containing the last n entries.
    """
    try:
        # Connect to the database
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row  # Allows row data to be accessed as dictionaries
        cursor = conn.cursor()

        # Query to select the last n entries ordered by the record_id or id column
        query = f"""
        SELECT * FROM {table_name}
        ORDER BY record_id DESC
        LIMIT ?
        """
        
        # Execute the query
        cursor.execute(query, (n,))
        rows = cursor.fetchall()

        # Convert rows to list of dictionaries
        result = [dict(row) for row in rows]

        # Close the connection
        conn.close()
        
        # Reverse the list so the entries are in chronological order
        return result[::-1]
        
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return []

print(get_last_n_entries('historical_weather.db','Weather',100))