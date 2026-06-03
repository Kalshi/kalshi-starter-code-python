#!/usr/bin/env python3
"""
Kalshi Market Scanner - Find Best Market Making Opportunities
Fetches all open events and their markets, analyzes bid-ask spreads

Usage: python fetch_open_markets.py
"""

import os
import sys
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from clients import KalshiHttpClient, Environment

load_dotenv()

def format_money(value):
    """Format cents to dollars"""
    try:
        return f"${float(value)/100:.2f}"
    except:
        return "$0.00"

def setup_client():
    """Setup Kalshi client"""
    try:
        with open(os.getenv('PROD_KEYFILE'), "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        
        client = KalshiHttpClient(
            key_id=os.getenv('PROD_KEYID'),
            private_key=private_key,
            environment=Environment.PROD
        )
        return client
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return None

def get_open_events(client):
    """Get all open events"""
    try:
        print("🔍 Fetching open events...")
        response = client.get("/trade-api/v2/events?status=open")
        events = response.get('events', [])
        print(f"✅ Found {len(events)} open events")
        return events
    except Exception as e:
        print(f"❌ Error getting events: {e}")
        return []

def get_markets_for_event(client, event_ticker):
    """Get all markets for a specific event using the markets endpoint"""
    try:
        print(f"   🔍 Fetching markets for event: {event_ticker}")
        
        # Use the markets endpoint with event_ticker filter
        response = client.get(f"/trade-api/v2/markets?event_ticker={event_ticker}&status=open")
        markets = response.get('markets', [])
        
        print(f"   ✅ Found {len(markets)} markets for {event_ticker}")
        return markets
        
    except Exception as e:
        print(f"   ❌ Error getting markets for event {event_ticker}: {e}")
        return []

def analyze_market_opportunity(market):
    """Analyze a market for trading opportunities"""
    ticker = market.get('ticker', 'N/A')
    title = market.get('title', 'N/A')
    
    yes_bid = market.get('yes_bid', 0)
    yes_ask = market.get('yes_ask', 0)
    no_bid = market.get('no_bid', 0) 
    no_ask = market.get('no_ask', 0)
    
    volume = market.get('volume', 0)
    open_interest = market.get('open_interest', 0)
    
    # Calculate spreads
    yes_spread = yes_ask - yes_bid if yes_ask > 0 and yes_bid > 0 else 0
    no_spread = no_ask - no_bid if no_ask > 0 and no_bid > 0 else 0
    
    # Check if there are gaps (no current bids/asks) - good for market making
    yes_gap = yes_bid == 0 or yes_ask == 0
    no_gap = no_bid == 0 or no_ask == 0
    
    # Market making opportunity score
    opportunity_score = 0
    opportunity_reasons = []
    
    # Wide spreads are good for market making
    if yes_spread >= 3:  # 3¢ or more spread
        opportunity_score += yes_spread
        opportunity_reasons.append(f"YES spread: {format_money(yes_spread)}")
    
    if no_spread >= 3:
        opportunity_score += no_spread  
        opportunity_reasons.append(f"NO spread: {format_money(no_spread)}")
    
    # Gaps in the market are excellent opportunities
    if yes_gap:
        opportunity_score += 10
        opportunity_reasons.append("YES side has gaps")
        
    if no_gap:
        opportunity_score += 10
        opportunity_reasons.append("NO side has gaps")
    
    # Volume indicates activity
    if volume > 100:
        opportunity_score += 5
        opportunity_reasons.append(f"High volume: {volume}")
    
    return {
        'ticker': ticker,
        'title': title,
        'yes_bid': yes_bid,
        'yes_ask': yes_ask,
        'no_bid': no_bid,
        'no_ask': no_ask,
        'yes_spread': yes_spread,
        'no_spread': no_spread,
        'yes_gap': yes_gap,
        'no_gap': no_gap,
        'volume': volume,
        'open_interest': open_interest,
        'opportunity_score': opportunity_score,
        'opportunity_reasons': opportunity_reasons
    }

def scan_all_markets(client):
    """Scan all open markets directly"""
    print("🚀 Starting comprehensive market scan...")
    
    # Get all open events first
    events = get_open_events(client)
    
    if not markets:
        print("❌ No open markets found")
        return []
    
    all_opportunities = []
    
    print(f"\n🔍 Analyzing {len(markets)} markets for opportunities...")
    
    # Analyze each market
    for i, market in enumerate(markets, 1):
        if i % 100 == 0:  # Progress indicator
            print(f"   � Processed {i}/{len(markets)} markets...")
            
        opportunity = analyze_market_opportunity(market)
        
        # Add event info from market data
        opportunity['event_ticker'] = market.get('event_ticker', 'N/A')
        opportunity['event_title'] = market.get('event_title', 'N/A')
        
        all_opportunities.append(opportunity)
    
    print(f"\n✅ Analysis complete!")
    print(f"   Total markets analyzed: {len(markets)}")
    
    return all_opportunities

def display_best_opportunities(opportunities, limit=20):
    """Display the best market making opportunities"""
    
    # Sort by opportunity score (highest first)
    sorted_opportunities = sorted(opportunities, key=lambda x: x['opportunity_score'], reverse=True)
    
    # Filter out markets with no opportunity
    good_opportunities = [opp for opp in sorted_opportunities if opp['opportunity_score'] > 0]
    
    print(f"\n🎯 TOP {min(limit, len(good_opportunities))} MARKET MAKING OPPORTUNITIES")
    print("=" * 100)
    
    if not good_opportunities:
        print("❌ No good market making opportunities found")
        print("💡 Try looking for:")
        print("   - Markets with wide bid-ask spreads (3¢+)")
        print("   - Markets with missing bids or asks")
        print("   - Markets with recent activity")
        return
    
    for i, opp in enumerate(good_opportunities[:limit], 1):
        print(f"\n{i}. {opp['ticker']}")
        print(f"   📝 {opp['title'][:80]}...")
        print(f"   🏛️  Event: {opp['event_ticker']}")
        
        # Current market state
        print(f"   💰 YES: {format_money(opp['yes_bid'])} × {format_money(opp['yes_ask'])} (spread: {format_money(opp['yes_spread'])})")
        print(f"   💰 NO:  {format_money(opp['no_bid'])} × {format_money(opp['no_ask'])} (spread: {format_money(opp['no_spread'])})")
        
        # Opportunity details
        print(f"   📊 Volume: {opp['volume']}, Open Interest: {opp['open_interest']}")
        print(f"   🎯 Opportunity Score: {opp['opportunity_score']}")
        
        if opp['opportunity_reasons']:
            print(f"   ✨ Reasons: {', '.join(opp['opportunity_reasons'])}")
        
        # Market making suggestions
        suggestions = []
        
        if opp['yes_gap'] and opp['yes_bid'] == 0:
            suggestions.append(f"Place YES bid at 1¢-5¢")
        elif opp['yes_spread'] >= 3:
            mid_price = (opp['yes_bid'] + opp['yes_ask']) // 2
            suggestions.append(f"YES bid: {format_money(mid_price-1)}, ask: {format_money(mid_price+1)}")
            
        if opp['no_gap'] and opp['no_bid'] == 0:
            suggestions.append(f"Place NO bid at 1¢-5¢")
        elif opp['no_spread'] >= 3:
            mid_price = (opp['no_bid'] + opp['no_ask']) // 2
            suggestions.append(f"NO bid: {format_money(mid_price-1)}, ask: {format_money(mid_price+1)}")
        
        if suggestions:
            print(f"   💡 Suggestions: {' | '.join(suggestions)}")

def save_opportunities_to_file(opportunities, filename="market_opportunities.txt"):
    """Save opportunities to a text file"""
    try:
        with open(filename, 'w') as f:
            f.write("KALSHI MARKET MAKING OPPORTUNITIES\n")
            f.write("=" * 50 + "\n\n")
            
            # Sort by opportunity score
            sorted_opportunities = sorted(opportunities, key=lambda x: x['opportunity_score'], reverse=True)
            good_opportunities = [opp for opp in sorted_opportunities if opp['opportunity_score'] > 0]
            
            for i, opp in enumerate(good_opportunities, 1):
                f.write(f"{i}. {opp['ticker']}\n")
                f.write(f"   Title: {opp['title']}\n")
                f.write(f"   Event: {opp['event_ticker']}\n")
                f.write(f"   YES: {format_money(opp['yes_bid'])} × {format_money(opp['yes_ask'])} (spread: {format_money(opp['yes_spread'])})\n")
                f.write(f"   NO:  {format_money(opp['no_bid'])} × {format_money(opp['no_ask'])} (spread: {format_money(opp['no_spread'])})\n")
                f.write(f"   Volume: {opp['volume']}, Open Interest: {opp['open_interest']}\n")
                f.write(f"   Opportunity Score: {opp['opportunity_score']}\n")
                if opp['opportunity_reasons']:
                    f.write(f"   Reasons: {', '.join(opp['opportunity_reasons'])}\n")
                f.write("\n")
        
        print(f"\n💾 Results saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving to file: {e}")

def main():
    """Main function"""
    print("🔍 KALSHI MARKET SCANNER")
    print("=" * 40)
    print("Finding the best market making opportunities...")
    
    # Setup client
    client = setup_client()
    if not client:
        sys.exit(1)
    
    print("✅ Connected to Kalshi Production")
    
    # Scan all markets
    opportunities = scan_all_markets(client)
    
    if not opportunities:
        print("❌ No markets found")
        sys.exit(1)
    
    # Display best opportunities
    display_best_opportunities(opportunities)
    
    # Save to file
    save_opportunities_to_file(opportunities)
    
    print(f"\n💡 Next steps:")
    print(f"   1. Pick a market with good opportunity score")
    print(f"   2. Use market_maker.py to place bid/ask orders")
    print(f"   3. Or use simple_order.py for single orders")
    print(f"   4. Monitor and adjust your prices")

if __name__ == "__main__":
    main()
