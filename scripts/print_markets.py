"""
Placeholder script for printing Kalshi markets.

This script does not perform real API calls, but shows where to plug in
your own client logic. It is intended as a starting point for users
exploring the starter code.
"""

from __future__ import annotations


def fetch_markets() -> list[dict]:
  """
  Replace this function with a call to the real Kalshi client.

  For now, it returns a small static list of example market-like entries.
  """
  return [
      {"ticker": "TEMP-DEMO-1", "description": "Example demo market #1"},
      {"ticker": "TEMP-DEMO-2", "description": "Example demo market #2"},
  ]


def main() -> None:
  print("Listing example Kalshi markets (placeholder data):\n")

  markets = fetch_markets()
  for market in markets:
      ticker = market.get("ticker", "<unknown>")
      desc = market.get("description", "")
      print(f"- {ticker}: {desc}")


if __name__ == "__main__":
  main()
