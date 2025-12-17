"""
Placeholder script for printing Kalshi positions.

Replace the placeholder implementation in `fetch_positions` with real
client calls when integrating with the Kalshi API.
"""

from __future__ import annotations


def fetch_positions() -> list[dict]:
    """
    Return a small static list of example positions.

    In a real implementation, this function would call the Kalshi API
    using the credentials and environment configured in your .env file.
    """
    return [
        {"ticker": "TEMP-DEMO-1", "size": 1, "side": "yes"},
        {"ticker": "TEMP-DEMO-2", "size": 2, "side": "no"},
    ]


def main() -> None:
    print("Listing example positions (placeholder data):\n")

    positions = fetch_positions()
    for position in positions:
        ticker = position.get("ticker", "<unknown>")
        size = position.get("size", 0)
        side = position.get("side", "?")
        print(f"- {ticker}: size={size}, side={side}")


if __name__ == "__main__":
    main()
