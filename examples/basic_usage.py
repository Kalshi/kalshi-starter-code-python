"""
Basic example showing how to initialize the Kalshi client
and make a simple request.
"""

from kalshi_client import KalshiClient


def main():
    client = KalshiClient(
        api_key="YOUR_API_KEY",
        api_secret="YOUR_API_SECRET",
        environment="demo"
    )

    markets = client.get_markets(limit=5)
    for market in markets:
        print(market["ticker"])


if __name__ == "__main__":
    main()
