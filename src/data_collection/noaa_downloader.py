"""
NOAA Historical Weather Data Downloader for Philadelphia
"""

import os
import logging
import requests
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

from config import TARGET_CITIES, NOAA_API_TOKEN_ENV_VAR

logger = logging.getLogger(__name__)


class NOAADownloader:
    """Downloader for NOAA historical weather data focused on Philadelphia."""
    
    def __init__(self):
        """Initialize the downloader with API token."""
        self.api_token = os.getenv(NOAA_API_TOKEN_ENV_VAR)
        
        if not self.api_token:
            raise ValueError(f"NOAA API token not found. Please set {NOAA_API_TOKEN_ENV_VAR} in your .env file.")
        
        logger.info(f"NOAA API token loaded: {self.api_token[:10] + '...' if self.api_token else 'None'}")
        
        self.base_url = "https://www.ncei.noaa.gov/cdo-web/api/v2"
        self.headers = {"token": self.api_token}
    
    def download_philly_historical_data(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Download historical weather data for Philadelphia, fetching it in yearly chunks.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with historical weather data or None if failed
        """
        city = "Philadelphia"
        logger.info(f"Downloading historical data for Philadelphia from {start_date} to {end_date}")
        
        if city not in TARGET_CITIES:
            logger.error(f"Philadelphia not found in TARGET_CITIES configuration")
            return None
        
        station_id = TARGET_CITIES[city]['station_id']
        logger.info(f"Using station ID: {station_id}")
        
        # Fetch data in yearly chunks to avoid API limits
        all_data = []
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        current_start = start
        
        while current_start <= end:
            current_end = current_start.replace(year=current_start.year + 1) - timedelta(days=1)
            if current_end > end:
                current_end = end
            
            logger.info(f"Fetching data for range: {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}")
            
            offset = 0
            limit = 1000
            while True:
                data_chunk = self._fetch_noaa_data(station_id, current_start.strftime('%Y-%m-%d'), current_end.strftime('%Y-%m-%d'), offset, limit)
                if data_chunk is not None and len(data_chunk) > 0:
                    all_data.extend(data_chunk)
                    if len(data_chunk) < limit:
                        break
                    offset += limit
                else:
                    break
            
            current_start = current_start.replace(year=current_start.year + 1)

        
        if all_data:
            df = self._process_noaa_data(all_data)
            logger.info(f"Successfully downloaded {len(df)} records for {city}")
            
            # Save to CSV
            os.makedirs('data', exist_ok=True)
            filename = f"data/noaa_philly_{start_date}_to_{end_date}.csv"
            df.to_csv(filename, index=False)
            logger.info(f"Saved NOAA data to {filename}")
            
            return df
        else:
            logger.error(f"Failed to download data for {city}")
            return None
    
    def _fetch_noaa_data(self, station_id: str, start_date: str, end_date: str, offset: int = 0, limit: int = 1000) -> Optional[List[Dict]]:
        """
        Fetch data from NOAA API.
        
        Args:
            station_id: NOAA station ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            offset: Offset for pagination
            limit: Number of records to fetch
            
        Returns:
            List of data records or None if failed
        """
        url = f"{self.base_url}/data"
        params = {
            "datasetid": "GHCND",
            "stationid": station_id,
            "startdate": start_date,
            "enddate": end_date,
            "datatypeid": "TMAX,TMIN,PRCP",  # Max temp, Min temp, Precipitation
            "limit": limit,
            "offset": offset,
            "units": "metric",
            "includemetadata": "false"
        }
        
        try:
            logger.debug(f"Fetching NOAA data from {url} with params: {params}")
            logger.debug(f"Using headers: {self.headers}")
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            if response.status_code != 200:
                logger.debug(f"Response content: {response.text}")
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching NOAA data: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching NOAA data: {e}")
            return None
    
    def _process_noaa_data(self, data: List[Dict]) -> pd.DataFrame:
        """
        Process raw NOAA data into a clean DataFrame.
        
        Args:
            data: List of raw NOAA data records
            
        Returns:
            Cleaned DataFrame
        """
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Pivot to have one row per date with all variables
        if not df.empty:
            df_pivot = df.pivot_table(
                index=['date'],
                columns='datatype',
                values='value',
                aggfunc='first'
            ).reset_index()
            
            # Rename columns to be more descriptive
            column_mapping = {
                'date': 'date',
                'TMAX': 'max_temp',
                'TMIN': 'min_temp',
                'PRCP': 'precipitation'
            }
            
            # Only rename columns that exist
            existing_columns = {k: v for k, v in column_mapping.items() if k in df_pivot.columns}
            df_pivot = df_pivot.rename(columns=existing_columns)
            
            # Convert date column to datetime
            df_pivot['date'] = pd.to_datetime(df_pivot['date'])
            
            # Convert temperature from tenths of degrees Celsius to degrees Celsius
            if 'max_temp' in df_pivot.columns:
                df_pivot['max_temp'] = df_pivot['max_temp'] / 10.0
            if 'min_temp' in df_pivot.columns:
                df_pivot['min_temp'] = df_pivot['min_temp'] / 10.0
            
            # Convert precipitation from tenths of mm to mm
            if 'precipitation' in df_pivot.columns:
                df_pivot['precipitation'] = df_pivot['precipitation'] / 10.0
            
            # Add additional derived features
            if 'max_temp' in df_pivot.columns:
                df_pivot['temp_range'] = df_pivot['max_temp'] - df_pivot['min_temp']
                df_pivot['above_80F'] = (df_pivot['max_temp'] > 26.67).astype(int)  # 80F = 26.67C
                df_pivot['above_90F'] = (df_pivot['max_temp'] > 32.22).astype(int)  # 90F = 32.22C
                df_pivot['above_95F'] = (df_pivot['max_temp'] > 35.00).astype(int)  # 95F = 35.00C
                df_pivot['above_98F'] = (df_pivot['max_temp'] > 36.67).astype(int)  # 98F = 36.67C
            
            return df_pivot
        else:
            return pd.DataFrame()
