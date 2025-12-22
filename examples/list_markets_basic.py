"""
Basic example script for listing a few active Kalshi markets.

Prerequisites:
  - Install the official SDK:
        pip install kalshi-python
  - Set the following environment variables:
        KALSHI_API_KEY_ID
        KALSHI_PRIVATE_KEY_PATH

Usage:
  python examples/list_markets_basic.py
"""

import os
from kalshi_python import Configuration, KalshiClient  # type: ignore[import-not-found]


def build_client() -> KalshiClient:
  api_key_id = os.environ.get("KALSHI_API_KEY_ID")
  private_key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH")

  if not api_key_id or not private_key_path:
    raise RuntimeError(
      "Missing KALSHI_API_KEY_ID or KALSHI_PRIVATE_KEY_PATH environment variables"
    )

  with open(private_key_path, "r", encoding="utf-8") as f:
    private_key_pem = f.read()

  config = Configuration(
    host="https://api.elections.kalshi.com/trade-api/v2",
  )
  config.api_key_id = api_key_id
  config.private_key_pem = private_key_pem

  return KalshiClient(config)


def main() -> None:
  client = build_client()
  markets = client.markets_api.get_markets(limit=5)  # type: ignore[attr-defined]

  print("First 5 markets:")
  for market in markets.markets:  # type: ignore[attr-defined]
    print(f"- {market.ticker} | {market.title}")


if __name__ == "__main__":
  main()
