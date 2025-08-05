# config.py

# --- Trading Strategy Parameters ---
TARGET_CITIES = {
    # City Name: {NOAA Station ID}
    "Philadelphia": {"station_id": "GHCND:USW00013739"}, # PHL Airport
}

# The NOAA API Token for fetching historical weather data
# This should be set in your .env file
NOAA_API_TOKEN_ENV_VAR = "NOAA_API_TOKEN"

# The minimum profitable edge (in cents) required to place a trade.
# This must be greater than Kalshi's fees. Start conservatively.
MINIMUM_EDGE_CENTS = 0.1

# The maximum percentage of your portfolio to risk on a single trade.
MAX_RISK_PER_TRADE = 0.05 # Represents 5%
