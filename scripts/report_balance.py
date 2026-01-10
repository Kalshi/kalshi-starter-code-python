"""
Generate a simple report of cash balance and open positions.

Requires the kalshi-python SDK and appropriate API credentials.
"""

import os
from kalshi_python import KalshiClient, Configuration # type: ignore

def build_client() -> KalshiClient:
cfg = Configuration(host=os.getenv("KALSHI_API_HOST", "https://api.kalshi.com/trade-api/v2
"))
cfg.api_key_id = os.getenv("KALSHI_API_KEY_ID")
with open(os.getenv("KALSHI_PRIVATE_KEY_PATH"), "r", encoding="utf-8") as f:
cfg.private_key_pem = f.read()
return KalshiClient(cfg)

def main() -> None:
client = build_client()
account = client.trader_api.get_accounts().accounts[0] # type: ignore
print(f"Cash: {account.cash_balance}")
positions = client.trader_api.get_positions().positions # type: ignore
for pos in positions:
pnl = pos.realized_pnl + pos.unrealized_pnl # type: ignore
print(f"{pos.ticker} – Size: {pos.size}, PnL: {pnl}")

if name == "main":
main()
