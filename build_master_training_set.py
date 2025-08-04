"""
Builds a master training set by combining historical NOAA data with
historical forecast data from Open-Meteo.

This script is a one-time data preparation utility.
"""

import pandas as pd
import logging
import os
from tqdm import tqdm

# Set up paths and logging
from src.data_collection.forecast_fetcher import ForecastFetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define file paths
NOAA_DATA_PATH = 'data/noaa_philly_2015-01-01_to_2024-12-31.csv'
MASTER_TRAINING_SET_PATH = 'data/master_training_set.csv'

def main():
    """Main function to build the dataset."""
    logging.info("Starting to build the master training set...")

    # 1. Load existing NOAA historical data
    if not os.path.exists(NOAA_DATA_PATH):
        logging.error(f"NOAA data file not found at: {NOAA_DATA_PATH}")
        logging.error("Please run the NOAA downloader first.")
        return

    logging.info(f"Loading NOAA data from {NOAA_DATA_PATH}")
    noaa_df = pd.read_csv(NOAA_DATA_PATH, parse_dates=['date'])
    logging.info(f"Loaded {len(noaa_df)} records from NOAA data.")

    # 2. Initialize the forecast fetcher
    fetcher = ForecastFetcher()
    forecasts = []

    # 3. Check if we already have a master training set with forecasts
    existing_forecasts = {}
    if os.path.exists(MASTER_TRAINING_SET_PATH):
        logging.info(f"Loading existing master training set from {MASTER_TRAINING_SET_PATH} to check for existing forecasts...")
        existing_df = pd.read_csv(MASTER_TRAINING_SET_PATH, parse_dates=['date'])
        # Create a dictionary of date -> forecast data for existing records
        # Check for the new column names first, then fall back to old names for compatibility
        for _, row in existing_df.iterrows():
            gfs_temp_max = row.get('gfs_temp_max_c')
            ecmwf_temp_max = row.get('ecmwf_temp_max_c')
            
            # Fallback to old column names for compatibility
            if pd.isna(gfs_temp_max):
                gfs_temp_max = row.get('gfs_forecast_c')
            if pd.isna(ecmwf_temp_max):
                ecmwf_temp_max = row.get('ecmwf_forecast_c')
            
            if pd.notna(gfs_temp_max) and pd.notna(ecmwf_temp_max):
                existing_forecasts[row['date'].date()] = {
                    'date': row['date'].date(),
                    'gfs_temp_max_c': gfs_temp_max,
                    'ecmwf_temp_max_c': ecmwf_temp_max,
                    # Include other new columns if they exist
                    'gfs_temp_min_c': row.get('gfs_temp_min_c'),
                    'gfs_apparent_temp_max_c': row.get('gfs_apparent_temp_max_c'),
                    'gfs_precipitation_sum_mm': row.get('gfs_precipitation_sum_mm'),
                    'gfs_shortwave_radiation_sum': row.get('gfs_shortwave_radiation_sum'),
                    'gfs_windspeed_max_kmh': row.get('gfs_windspeed_max_kmh'),
                    'ecmwf_temp_min_c': row.get('ecmwf_temp_min_c'),
                    'ecmwf_apparent_temp_max_c': row.get('ecmwf_apparent_temp_max_c')
                }
        logging.info(f"Found {len(existing_forecasts)} existing forecast records.")

    # 4. Loop through every date and fetch the corresponding forecast if not already present
    logging.info("Fetching historical forecasts from Open-Meteo...")
    # Use tqdm for a progress bar as this will take a while
    for dt in tqdm(noaa_df['date'], desc="Fetching Forecasts"):
        date_key = dt.date()
        # Check if we already have forecast data for this date
        if date_key in existing_forecasts:
            forecasts.append(existing_forecasts[date_key])
        else:
            forecast_data = fetcher.fetch_historical_forecast(date_key)
            if forecast_data:
                forecasts.append(forecast_data)

    if not forecasts:
        logging.error("No forecast data could be fetched. Aborting.")
        return

    logging.info(f"Successfully fetched/used {len(forecasts)} forecast records.")

    # 4. Convert forecasts to a DataFrame and merge with NOAA data
    forecast_df = pd.DataFrame(forecasts)
    
    # Ensure date columns are of the same type for merging
    forecast_df['date'] = pd.to_datetime(forecast_df['date'])
    noaa_df['date'] = pd.to_datetime(noaa_df['date'])

    logging.info("Merging NOAA data with forecast data...")
    master_df = pd.merge(noaa_df, forecast_df, on='date', how='left')

    # 5. Save the master training set
    # Ensure the 'data' directory exists
    os.makedirs(os.path.dirname(MASTER_TRAINING_SET_PATH), exist_ok=True)
    master_df.to_csv(MASTER_TRAINING_SET_PATH, index=False)

    logging.info(f"Master training set created successfully at: {MASTER_TRAINING_SET_PATH}")
    logging.info(f"The new dataset has {len(master_df)} records and {len(master_df.columns)} columns.")

if __name__ == "__main__":
    main()
