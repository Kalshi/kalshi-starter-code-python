import os

def load_config():
    """
    Loads basic configuration values from environment variables.
    """
    return {
        "api_key": os.getenv("KALSHI_API_KEY"),
        "api_secret": os.getenv("KALSHI_API_SECRET"),
        "base_url": os.getenv("KALSHI_API_BASE_URL"),
    }
