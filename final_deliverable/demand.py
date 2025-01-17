import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import logging

def fetch_and_save_eia_demand_data(start_time, end_time, api_key, region):
    """
    Fetch demand and net generation data from EIA API in 5-day increments.

    Parameters:
    start_time (str): Start time in format 'YYYY-MM-DDT%H'
    end_time (str): End time in format 'YYYY-MM-DDT%H'
    api_key (str): EIA API key
    region (str): Region code for fetching data

    Returns:
    pd.DataFrame: Processed DataFrame with Demand and Net Generation columns
    """
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)

    try:
        # Convert start and end times to datetime objects
        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H")
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H")

        # Validate the time range
        if start_time >= end_time:
            raise ValueError("Start time must be before end time")

        # Initialize a list for all data
        all_data = []

        # Loop through the date range in 5-day increments
        current_time = start_time
        while current_time < end_time:
            next_time = min(current_time + timedelta(days=5), end_time)

            # Construct the API URL
            url = (
                f"https://api.eia.gov/v2/electricity/rto/region-data/data/"
                f"?frequency=hourly&data[0]=value&facets[respondent][]={region}&facets[type][]=D"
                f"&facets[type][]=NG&start={current_time.strftime('%Y-%m-%dT%H')}&end={next_time.strftime('%Y-%m-%dT%H')}"
                f"&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000&api_key={api_key}"
            )

            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Extract and structure the data
                records = [
                    {
                        'datetime': pd.to_datetime(item['period']),  # Explicitly convert to pandas timestamp
                        'region': item['respondent'],
                        'type': item['type'],
                        'value': item['value']
                    }
                    for item in data['response']['data']
                ]

                if records:
                    all_data.append(pd.DataFrame(records))

            except requests.RequestException as e:
                logger.error(f"Error fetching data for {current_time} to {next_time}: {e}")

            current_time = next_time

        # Combine data and structure the output
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)

            # Pivot the data to separate Demand and Net Generation
            pivot_data = combined_data.pivot_table(
                index=['datetime', 'region'],
                columns='type',
                values='value',
                aggfunc='first'
            ).reset_index()

            # Rename columns
            pivot_data = pivot_data.rename(columns={'D': 'Demand', 'NG': 'Net Generation'})

            # Ensure the output directory exists
            os.makedirs('deliverable_2', exist_ok=True)

            # File path
            filename = f'demand_data_{region}.csv'
            output_path = os.path.join('deliverable_2', filename)

            if os.path.exists(output_path):
                existing_data = pd.read_csv(output_path, parse_dates=['datetime'])
                merged_data = pd.concat([existing_data, pivot_data]).drop_duplicates(subset=['datetime']).sort_values('datetime')
                # merged_data.to_csv(output_path, index=False)
                logger.info(f"Data successfully merged and saved to {output_path}")
            else:
                # pivot_data.to_csv(output_path, index=False)
                logger.info(f"Data saved to {output_path}")

            return pivot_data
        else:
            logger.warning("No data was fetched.")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return pd.DataFrame()

def main():
    """
    Main function for demonstration.
    """
    api_key = os.getenv("EIA_API_KEY")
    if not api_key:
        print("Error: EIA_API_KEY environment variable not set")
        return

    start_time = "2024-10-26T00"
    end_time = "2024-10-27T00"
    region = "NE"

    df = fetch_and_save_eia_demand_data(start_time, end_time, api_key, region)

    if not df.empty:
        print(f"Fetched {len(df)} records")
        print(df.head())

if __name__ == "__main__":
    main()