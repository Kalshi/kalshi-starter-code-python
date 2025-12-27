"""
Fetch and print a brief summary of current active markets.

Requires kalshi-python SDK and proper API credentials.
"""

import os
from kalshi_python import KalshiClient, Configuration  # type: ignore

def build_client() -> KalshiClient:
    cfg = Configuration(host=os.getenv("KALSHI_API_HOST", "https://api.elections.kalshi.com/trade-api/v2"))
    cfg.api_key_id = os.getenv("KALSHI_API_KEY_ID")
    with open(os.getenv("KALSHI_PRIVATE_KEY_PATH"), "r", encoding="utf-8") as f:
        cfg.private_key_pem = f.read()
    return KalshiClient(cfg)

def main() -> None:
    client = build_client()
    markets = client.markets_api.get_markets(limit=5)  # type: ignore
    for m in markets.markets:  # type: ignore
        print(f"{m.ticker} | {m.title} | Yes price: {m.yes_price}")

if __name__ == "__main__":
    main()
