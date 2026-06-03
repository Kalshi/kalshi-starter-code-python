#!/usr/bin/env python3
"""
Quick script to get open markets from Kalshi (Production only)
Usage: python quick_open_markets.py
"""

import os
import json
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from clients import KalshiHttpClient, Environment

# Load environment variables
load_dotenv()

# Force production environment
env = Environment.PROD
KEYID = os.getenv('PROD_KEYID')
KEYFILE = os.getenv('PROD_KEYFILE')

# Initialize client
try:
    with open(KEYFILE, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)
    
    client = KalshiHttpClient(
        key_id=KEYID,
        private_key=private_key,
        environment=env
    )
    print("✅ Connected to Kalshi Production")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

def format_money(value):
    """Format cents to dollars"""
    try:
        return f"${float(value)/100:.2f}"
    except:
        return "$0.00"

def get_open_markets_simple():
    """Get all open markets - simple and fast"""
    print("🔍 Fetching open markets...")
    
    all_markets = {}
    cursor = None
    page = 1
    
    while True:
        # Build URL for open events only
        url = "/trade-api/v2/events?status=open"
        if cursor:
            url += f"&cursor={cursor}"
        
        print(f"   Page {page}...", end=" ")
        
        try:
            response = client.get(url)
            events = response.get('events', [])
            
            if not events:
                break
            
            # Add to our collection
            for event in events:
                event_id = event.get('event_ticker')
                event_name = event.get('title')
                
                if event_id:
                    all_markets[event_id] = {
                        'id': event_id,
                        'name': event_name
                    }
            
            print(f"✅ ({len(events)} events)")
            
            # Get next page cursor
            cursor = response.get('cursor')
            if not cursor:
                break
                
            page += 1
            
        except Exception as e:
            print(f"❌ Error on page {page}: {e}")
            break
    
    print(f"\n🎯 Found {len(all_markets)} open markets total!")
    return all_markets

def search_market(markets, search_term):
    """Quick search through markets"""
    search_term = search_term.lower()
    results = []
    
    for market_id, market_data in markets.items():
        if search_term in market_data['name'].lower():
            results.append((market_id, market_data['name']))
    
    return results

def main():
    """Main function"""
    print("=" * 60)
    print("🏛️  KALSHI OPEN MARKETS - QUICK ACCESS")
    print("=" * 60)
    
    # Get balance
    try:
        balance = client.get_balance()
        print(f"💰 Balance: {format_money(balance.get('balance', 0))}")
    except:
        print("💰 Balance: Unable to fetch")
    
    # Get open markets
    markets = get_open_markets_simple()
    
    if not markets:
        print("❌ No open markets found!")
        return
    
    # Show first 10 as preview
    print(f"\n📋 First 10 open markets:")
    print("-" * 40)
    for i, (market_id, market_data) in enumerate(list(markets.items())[:10], 1):
        name = market_data['name']
        if len(name) > 50:
            name = name[:47] + "..."
        print(f"{i:2d}. {market_id}")
        print(f"    {name}")
    
    # Interactive search
    print(f"\n🔍 SEARCH MARKETS (Total: {len(markets)})")
    print("Type search terms or 'quit' to exit")
    print("-" * 40)
    
    while True:
        try:
            search_term = input("Search> ").strip()
            
            if search_term.lower() in ['quit', 'exit', 'q']:
                break
            
            if not search_term:
                continue
            
            results = search_market(markets, search_term)
            
            if results:
                print(f"\n✅ Found {len(results)} matches for '{search_term}':")
                for i, (market_id, name) in enumerate(results[:10], 1):
                    print(f"{i:2d}. ID: {market_id}")
                    if len(name) > 55:
                        name = name[:52] + "..."
                    print(f"    {name}")
                
                if len(results) > 10:
                    print(f"    ... and {len(results) - 10} more")
            else:
                print(f"❌ No matches for '{search_term}'")
            
            print()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
