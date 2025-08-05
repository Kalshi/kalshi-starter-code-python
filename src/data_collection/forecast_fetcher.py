"""
Module for fetching historical forecast data from Open-Meteo.
"""

import requests
import pandas as pd
from datetime import date
import logging

logger = logging.getLogger(__name__)

class ForecastFetcher:
    """Fetches historical weather forecast data from the Open-Meteo API."""

    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    # Philadelphia's coordinates
    LATITUDE = 39.95
    LONGITUDE = -75.16

    def fetch_historical_forecast(self, forecast_date: date) -> dict:
        """
        Fetches comprehensive daily weather forecast data for a specific date from various models.

        For a given date, it requests the forecast that was available on that day.
        
        Args:
            forecast_date: The date for which to fetch the forecast data.

        Returns:
            A dictionary containing the forecast values for that date.
        """
        params = {
            "latitude": self.LATITUDE,
            "longitude": self.LONGITUDE,
            "start_date": forecast_date.strftime('%Y-%m-%d'),
            "end_date": forecast_date.strftime('%Y-%m-%d'),
            "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,precipitation_sum,shortwave_radiation_sum,windspeed_10m_max",
            "models": "gfs_seamless,ecmwf_ifs", # GFS and ECMWF models
            "timezone": "America/New_York"
        }

        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()

            # The API returns daily data, so we expect one value for each model
            daily_data = data.get('daily', {})
            
            # Extract the first (and only) value from each list for GFS
            gfs_temp_max = daily_data.get('temperature_2m_max_gfs_seamless', [None])[0]
            gfs_temp_min = daily_data.get('temperature_2m_min_gfs_seamless', [None])[0]
            gfs_apparent_temp_max = daily_data.get('apparent_temperature_max_gfs_seamless', [None])[0]
            gfs_precipitation_sum = daily_data.get('precipitation_sum_gfs_seamless', [None])[0]
            gfs_shortwave_radiation_sum = daily_data.get('shortwave_radiation_sum_gfs_seamless', [None])[0]
            gfs_windspeed_max = daily_data.get('windspeed_10m_max_gfs_seamless', [None])[0]
            
            # Extract the first (and only) value from each list for ECMWF
            ecmwf_temp_max = daily_data.get('temperature_2m_max_ecmwf_ifs', [None])[0]
            ecmwf_temp_min = daily_data.get('temperature_2m_min_ecmwf_ifs', [None])[0]
            ecmwf_apparent_temp_max = daily_data.get('apparent_temperature_max_ecmwf_ifs', [None])[0]

            result = {
                'date': pd.to_datetime(forecast_date),
                'gfs_temp_max_c': gfs_temp_max,
                'gfs_temp_min_c': gfs_temp_min,
                'gfs_apparent_temp_max_c': gfs_apparent_temp_max,
                'gfs_precipitation_sum_mm': gfs_precipitation_sum,
                'gfs_shortwave_radiation_sum': gfs_shortwave_radiation_sum,
                'gfs_windspeed_max_kmh': gfs_windspeed_max,
                'ecmwf_temp_max_c': ecmwf_temp_max,
                'ecmwf_temp_min_c': ecmwf_temp_min,
                'ecmwf_apparent_temp_max_c': ecmwf_apparent_temp_max
            }
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for date {forecast_date}: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse forecast data for date {forecast_date}: {e}")
            return None
