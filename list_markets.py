import requests
import os

# You can set your API key here if you have one, although it's not strictly necessary for public market data
# It's good practice to use environment variables for keys.
# API_KEY = os.getenv("KALSHI_API_KEY")

headers = {
    "Accept": "application/json",
    # If you were placing trades or accessing private account data, you would need authorization.
    # "Authorization": f"Bearer {API_KEY}",
}

# We are querying for all 'open' markets
url = "https://demo-api.kalshi.co/trade-api/v2/markets?status=open"

# --- Define the tickers you want to search for ---
series_to_find = "KXHIGHPHIL"
event_to_find = "KXHIGHPHIL-25AUG03"
market_to_find = "KXHIGHPHIL-25AUG03-B85.5"

print(f"Searching for Series: {series_to_find}")
print(f"Searching for Event: {event_to_find}")
print(f"Searching for Market: {market_to_find}\n")


try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # This will raise an exception for HTTP errors
    data = response.json()

    # --- Variables to keep track of what we've found ---
    found_series_markets = []
    found_event_market = None
    found_specific_market = None

    # --- Iterate through the markets to find our targets ---
    for market in data.get('markets', []):
        # Check for the series ticker
        if series_to_find in market.get('ticker', ''):
            found_series_markets.append(market)

        # Check for the event ticker
        if event_to_find == market.get('event_ticker', ''):
            found_event_market = market

        # Check for the specific market ticker
        if market_to_find == market.get('ticker', ''):
            found_specific_market = market


    # --- Print the results of our search ---

    print("--- Analysis Complete ---")

    # Report on the specific market
    if found_specific_market:
        print(f"\n[SUCCESS] Found Specific Market: {market_to_find}")
        print(found_specific_market)
    else:
        print(f"\n[INFO] Did not find specific market with ticker: {market_to_find}")

    # Report on the event
    if found_event_market:
        print(f"\n[SUCCESS] Found a market for Event: {event_to_find}")
        print(found_event_market)
    else:
        print(f"\n[INFO] Did not find any markets for event with ticker: {event_to_find}")

    # Report on the series
    if found_series_markets:
        print(f"\n[SUCCESS] Found {len(found_series_markets)} markets in Series: {series_to_find}")
        # To avoid printing too much, let's just show the tickers found
        for market in found_series_markets:
            print(f"  - Ticker: {market['ticker']}, Title: {market['title']}")
    else:
        print(f"\n[INFO] Did not find any markets in series: {series_to_find}")


except requests.exceptions.RequestException as e:
    print(f"Error fetching markets: {e}")
except KeyError:
    print("Error: The key 'markets' was not found in the API response.")