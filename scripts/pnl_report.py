"""
Compute net profit and loss across all positions.

Requires kalshi-python SDK and API credentials.
"""

import os
from kalshi_python import KalshiClient, Configuration  # type: ignore

def build_client():
    cfg = Configuration(host=os.getenv("KALSHI_API_HOST", "https://api.elections.kalshi.com/trade-api/v2"))
    cfg.api_key_id = os.getenv("KALSHI_API_KEY_ID")
    with open(os.getenv("KALSHI_PRIVATE_KEY_PATH"), "r", encoding="utf-8") as f:
        cfg.private_key_pem = f.read()
    return KalshiClient(cfg)

def main() -> None:
    client = build_client()
    positions = client.trader_api.get_positions().positions  # type: ignore
    total_pnl = sum(p.realized_pnl + p.unrealized_pnl for p in positions)  # type: ignore
    print(f"Total PnL across positions: {total_pnl:.2f}")

if __name__ == "__main__":
    main()
