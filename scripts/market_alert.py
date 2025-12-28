"""
Monitor a specific market and alert when the YES price crosses a threshold.

Set MARKET_TICKER and PRICE_THRESHOLD environment variables.
"""

import os
import time
from kalshi_python import KalshiClient, Configuration  # type: ignore

TICKER = os.getenv("MARKET_TICKER", "TEMP-DEMO-1")
THRESHOLD = float(os.getenv("PRICE_THRESHOLD", "0.75"))

def build_client():
    cfg = Configuration(host=os.getenv("KALSHI_API_HOST", "https://api.elections.kalshi.com/trade-api/v2"))
    cfg.api_key_id = os.getenv("KALSHI_API_KEY_ID")
    with open(os.getenv("KALSHI_PRIVATE_KEY_PATH"), "r", encoding="utf-8") as f:
        cfg.private_key_pem = f.read()
    return KalshiClient(cfg)

def main() -> None:
    client = build_client()
    while True:
        market = client.markets_api.get_market(TICKER).market  # type: ignore
        yes_price = market.yes_price
        if yes_price >= THRESHOLD:
            print(f"Alert: {TICKER} YES price {yes_price} >= threshold {THRESHOLD}")
            break
        time.sleep(60)

if __name__ == "__main__":
    main()
