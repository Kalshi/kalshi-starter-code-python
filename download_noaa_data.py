"""
Script to download historical NOAA weather data for Philadelphia.
"""

import logging
from dotenv import load_dotenv
from src.data_collection.noaa_downloader import NOAADownloader
from config import TARGET_CITIES

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to download NOAA data."""
    load_dotenv()  # Load environment variables from .env file
    logger.info("Starting NOAA historical data download...")
    
    # Assuming we are focusing on Philadelphia as per the project setup
    city_config = TARGET_CITIES['Philadelphia']
    # Add lat/lon for PHL airport as it's missing in the config
    city_config['lat'] = 39.8719
    city_config['lon'] = -75.2411
    city_config['name'] = 'Philadelphia'
    
    downloader = NOAADownloader() # Token is loaded from .env within the class
    
    # Define the date range for the download
    start_date = "2015-01-01"
    end_date = "2024-12-31"
    
    # Fetch and save the data
    weather_df = downloader.download_philly_historical_data(start_date, end_date)
    
    if weather_df is not None and not weather_df.empty:
        logger.info(f"Successfully downloaded and saved data for {city_config['name']}.")
        logger.info(f"Total records downloaded: {len(weather_df)}")
    else:
        logger.error("Failed to download NOAA data.")

if __name__ == "__main__":
    main()
