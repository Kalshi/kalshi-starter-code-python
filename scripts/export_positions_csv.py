"""
Export all current positions to a CSV file.

Prerequisites:
  - kalshi-python SDK installed
  - Environment variables KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH set

Usage:
  python scripts/export_positions_csv.py positions.csv
"""

import csv
import os
import sys
from kalshi_python import KalshiClient, Configuration  # type: ignore[import-not-found]

def build_client() -> KalshiClient:
    key_id = os.getenv("KALSHI_API_KEY_ID")
    priv_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    if not key_id or not priv_path:
        raise RuntimeError("KALSHI_API_KEY_ID or KALSHI_PRIVATE_KEY_PATH not set")
    with open(priv_path, "r", encoding="utf-8") as f:
        key_pem = f.read()
    conf = Configuration(host="https://api.elections.kalshi.com/trade-api/v2")
    conf.api_key_id = key_id
    conf.private_key_pem = key_pem
    return KalshiClient(conf)

def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "positions.csv"
    client = build_client()
    positions = client.trader_api.get_positions().positions  # type: ignore[attr-defined]

    with open(out_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["ticker", "size", "side", "average_price"])
        for p in positions:
            writer.writerow([p.ticker, p.size, p.side, p.avg_price])

    print(f"Wrote {len(positions)} positions to {out_path}")

if __name__ == "__main__":
    main()
