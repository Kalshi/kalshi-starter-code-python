"""
Simple API health check example.

This script verifies that the Kalshi API is reachable
and returns a successful response.
"""

from kalshi.client import KalshiClient


def check_api_health() -> None:
    client = KalshiClient()
    response = client.get_exchange_status()
    print("API status:", response)


if __name__ == "__main__":
    check_api_health()
