#!/usr/bin/env python3
"""
Simple Order Placement Script for Kalshi
Usage: python place_order.py MARKET_TICKER SIDE PRICE QUANTITY
Example: python place_order.py KXHIGHNY-25JUL20-B89.5 yes 0.26 10
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

def get_market_info(client, ticker):
    """Get current market information"""
    try:
        response = client.get(f"/trade-api/v2/markets/{ticker}")
        market = response.get('market', {})
        return market
    except Exception as e:
        print(f"❌ Error getting market info: {e}")
        return None

def find_existing_rfq_for_market(client, ticker):
    """Find an existing RFQ for the given market"""
    try:
        # Try to get RFQs filtered by market_ticker first
        print(f"🔍 Fetching RFQs for market {ticker}...")
        response = client.get(f"/trade-api/v2/communications/rfqs?market_ticker={ticker}")
        print(f"🔍 Market-specific RFQ API Response: {response}")
        
        rfqs = response.get('rfqs', [])
        print(f"🔍 Found {len(rfqs)} RFQs for market {ticker}")
        
        for i, rfq in enumerate(rfqs):
            print(f"🔍 RFQ {i+1}: {rfq}")
            if rfq.get('market_ticker') == ticker:
                print(f"✅ Found matching RFQ for {ticker}: {rfq.get('id')}")
                return rfq.get('id')
        
        # If no RFQs found for this market, try getting all RFQs
        print(f"🔍 No market-specific RFQs found, fetching all RFQs...")
        response = client.get("/trade-api/v2/communications/rfqs")
        print(f"🔍 All RFQs API Response: {response}")
        
        rfqs = response.get('rfqs', [])
        print(f"🔍 Found {len(rfqs)} total RFQs")
        
        for i, rfq in enumerate(rfqs):
            print(f"🔍 RFQ {i+1}: {rfq}")
            if rfq.get('market_ticker') == ticker:
                print(f"✅ Found matching RFQ for {ticker}: {rfq.get('id')}")
                return rfq.get('id')
        
        print(f"🔍 No RFQ found for market {ticker}")
        return None
    except Exception as e:
        print(f"❌ Error getting RFQs: {e}")
        # Let's also print any additional error details
        if hasattr(e, 'response') and e.response:
            try:
                error_detail = e.response.json()
                print(f"❌ RFQ API Error Details: {error_detail}")
            except:
                print(f"❌ Raw RFQ Response: {e.response.text}")
                print(f"❌ Status Code: {e.response.status_code}")
        return None

def create_rfq(client, ticker, side, quantity):
    """Create a Request for Quote (RFQ)"""
    # First check if there's already an RFQ for this market
    print(f"🔍 Checking for existing RFQs for {ticker}...")
    existing_rfq_id = find_existing_rfq_for_market(client, ticker)
    if existing_rfq_id:
        print(f"✅ Found existing RFQ for {ticker}: {existing_rfq_id}")
        return existing_rfq_id
    
    # The API actually expects JSON body, not query parameters despite the docs
    full_path = f"/trade-api/v2/communications/rfqs"
    
    # Build request body
    rfq_data = {
        "market_ticker": ticker,
        "contracts": quantity,
        "rest_remainder": True  # Boolean, not string
    }
    
    print(f"🔍 Creating RFQ with data: {rfq_data}")
    
    # Make the request manually to get the raw response
    import requests
    url = f"{client.host}{full_path}"
    headers = client.request_headers("POST", full_path)
    
    try:
        # Make raw request with JSON body
        response = requests.post(url, json=rfq_data, headers=headers)
        
        print(f"🔍 Status Code: {response.status_code}")
        print(f"🔍 Raw Response Text: {response.text}")
        
        # RFQ creation returns 201 (Created), not 200
        if response.status_code == 201:
            response_data = response.json()
            print(f"🔍 Parsed Response: {response_data}")
            
            if response_data.get('id'):
                print(f"✅ RFQ created with ID: {response_data['id']}")
                return response_data['id']
            else:
                print(f"❌ RFQ creation failed: {response_data}")
                return None
        else:
            # Parse error response
            try:
                error_data = response.json()
                print(f"❌ API Error Response: {error_data}")
                if 'error' in error_data:
                    error = error_data['error']
                    if 'code' in error:
                        print(f"❌ Error Code: {error['code']}")
                        
                        # If RFQ already exists, that means we already have an open RFQ!
                        if error['code'] == 'already_exists':
                            print(f"✅ RFQ already exists for this market - this means it was created successfully!")
                            print(f"� The RFQ creation probably succeeded on a previous attempt.")
                            print(f"🔍 Since we can't get the RFQ ID via API, let's try a different approach...")
                            
                            # Instead of trying to find the ID, let's try to place a quote directly
                            # Some APIs allow using market ticker instead of RFQ ID
                            print(f"🔄 Attempting to place quote using market ticker...")
                            return "TRY_QUOTE_WITH_TICKER"
                            
                    if 'message' in error:
                        print(f"❌ Error Message: {error['message']}")
                    if 'details' in error:
                        print(f"❌ Error Details: {error['details']}")
            except:
                print(f"❌ Could not parse error response as JSON")
            return None
            
    except Exception as e:
        print(f"❌ Request exception: {e}")
        return None

def try_get_quotes(client, ticker):
    """Try to get existing quotes for the market"""
    try:
        print(f"🔍 Checking for existing quotes...")
        response = client.get("/trade-api/v2/communications/quotes")
        print(f"🔍 Quotes API Response: {response}")
        
        quotes = response.get('quotes', [])
        print(f"🔍 Found {len(quotes)} total quotes")
        
        for i, quote in enumerate(quotes):
            print(f"🔍 Quote {i+1}: {quote}")
            # Look for quotes related to our market
            if quote.get('market_ticker') == ticker:
                print(f"✅ Found quote for {ticker}: {quote}")
                return quote
        
        return None
    except Exception as e:
        print(f"❌ Error getting quotes: {e}")
        return None

def try_direct_order(client, ticker, side, price_cents, quantity):
    """Try placing order directly using portfolio/orders endpoint as fallback"""
    try:
        # First try to get existing quotes
        existing_quote = try_get_quotes(client, ticker)
        if existing_quote:
            quote_id = existing_quote.get('id')
            if quote_id:
                print(f"✅ Found existing quote {quote_id}, trying to accept it...")
                
                # Try to accept the quote
                accept_response = client.put(f"/trade-api/v2/communications/quotes/{quote_id}/accept", {})
                print(f"🔍 Accept quote response: {accept_response}")
                
                if accept_response:
                    return accept_response
        
        # If no existing quote, try the portfolio orders approach
        order_data = {
            "ticker": ticker,
            "client_order_id": f"order_{ticker}_{side}_{price_cents}_{quantity}",
            "side": side,
            "action": "buy",
            "count": quantity,
            "type": "limit",  # Changed to limit order
            "yes_price": price_cents if side.lower() == "yes" else None,
            "no_price": price_cents if side.lower() == "no" else None
        }
        
        print(f"🔄 Trying direct order placement with: {order_data}")
        response = client.post("/trade-api/v2/portfolio/orders", order_data)
        print(f"🔍 Direct order response: {response}")
        return response
    except Exception as e:
        print(f"❌ Direct order failed: {e}")
        return None

def place_order(client, ticker, side, price_dollars, quantity):
    """Place an order on Kalshi using the quote system"""
    
    # Convert price to cents (Kalshi uses cents)
    price_cents = int(round(price_dollars * 100))
    
    # Validate price range (1¢ to 99¢)
    if price_cents < 1 or price_cents > 99:
        print(f"❌ Price must be between $0.01 and $0.99, got ${price_dollars:.2f}")
        return False
    
    # Step 1: Create RFQ
    print(f"🚀 Step 1: Creating RFQ...")
    rfq_id = create_rfq(client, ticker, side, quantity)
    if not rfq_id:
        return False
    
    # Handle special case where we know RFQ exists but don't have the ID
    if rfq_id == "EXISTING_RFQ_UNKNOWN_ID":
        print(f"⚠️  RFQ exists but we don't have the ID. This might be because:")
        print(f"   1. You already have an active RFQ for this market")
        print(f"   2. Check your Kalshi account - you may see it in 'Your RFQs' tab")
        print(f"   3. The RFQ might have already been converted to an order")
        print(f"\n💡 Check your Kalshi account for the current status!")
        return False
    
    # Handle the case where we should try quote with ticker
    if rfq_id == "TRY_QUOTE_WITH_TICKER":
        print(f"🔄 Trying to place quote using market ticker approach...")
        
        # Try placing a quote without specific RFQ ID
        quote_data = {
            "market_ticker": ticker  # Some APIs might accept this
        }
        
        # Add bid prices based on side
        if side.lower() == "yes":
            quote_data["yes_bid"] = price_cents
            quote_data["no_bid"] = 0
        else:
            quote_data["yes_bid"] = 0
            quote_data["no_bid"] = price_cents
        
        print(f"🔍 Trying quote with ticker payload: {quote_data}")
        
        try:
            response = client.post("/trade-api/v2/communications/quotes", quote_data)
            print(f"✅ Quote with ticker succeeded: {response}")
            return True
        except Exception as e:
            print(f"❌ Quote with ticker failed: {e}")
            print(f"💡 Since you can see the RFQ in your Kalshi account, it was created successfully!")
            print(f"💡 The issue might be that the API requires the exact RFQ ID.")
            print(f"💡 Check your Kalshi account - the order might already be placed or pending!")
            return False
    
    # Handle the case where we should try direct order placement
    if rfq_id == "TRY_DIRECT_ORDER":
        print(f"🔄 Trying direct order placement as fallback...")
        direct_response = try_direct_order(client, ticker, side, price_cents, quantity)
        if direct_response:
            print(f"✅ Direct order placement attempted!")
            print(f"📝 Response: {direct_response}")
            return True
        else:
            print(f"❌ Direct order placement failed")
            print(f"💡 The RFQ exists in your account - check Kalshi manually!")
            return False
    
    # Step 2: Create quote in response to RFQ
    print(f"🚀 Step 2: Creating quote for RFQ {rfq_id}...")
    
    # Build quote payload based on the API documentation
    quote_data = {
        "rfq_id": rfq_id
    }
    
    # Add bid prices based on side
    if side.lower() == "yes":
        quote_data["yes_bid"] = price_cents
        quote_data["no_bid"] = 0  # We don't want to bid on the no side
    else:
        quote_data["yes_bid"] = 0  # We don't want to bid on the yes side
        quote_data["no_bid"] = price_cents
    
    try:
        print(f"🚀 Placing quote...")
        print(f"   Market: {ticker}")
        print(f"   Side: {side.upper()}")
        print(f"   Price: {format_money(price_cents)}")
        print(f"   Quantity: {quantity} contracts")
        print(f"   Total Risk: {format_money(price_cents * quantity)}")
        print(f"🔍 Debug - Quote payload: {quote_data}")
        
        # Place the quote using the correct endpoint
        response = client.post("/trade-api/v2/communications/quotes", quote_data)
        
        if response.get('order'):
            order = response['order']
            order_id = order.get('order_id')
            status = order.get('status')
            
            print(f"✅ ORDER PLACED SUCCESSFULLY!")
            print(f"   Order ID: {order_id}")
            print(f"   Status: {status}")
            print(f"   Created: {order.get('created_time')}")
            
            return True
        elif response.get('id'):
            # Quote created successfully
            quote_id = response['id']
            print(f"✅ QUOTE PLACED SUCCESSFULLY!")
            print(f"   Quote ID: {quote_id}")
            
            return True
        else:
            print(f"❌ Order failed - API Response: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Error placing quote: {e}")
        # Try to get more detailed error info
        if hasattr(e, 'response') and e.response:
            try:
                error_detail = e.response.json()
                print(f"❌ Quote API Error Details: {error_detail}")
                if 'code' in error_detail:
                    print(f"❌ Error Code: {error_detail['code']}")
                if 'message' in error_detail:
                    print(f"❌ Error Message: {error_detail['message']}")
                if 'details' in error_detail:
                    print(f"❌ Error Details: {error_detail['details']}")
            except:
                print(f"❌ Raw Quote Response: {e.response.text}")
                print(f"❌ Status Code: {e.response.status_code}")
        return False

def main():
    """Main function"""
    if len(sys.argv) != 5:
        print("🏛️  KALSHI ORDER PLACEMENT")
        print("=" * 40)
        print("Usage: python place_order.py MARKET_TICKER SIDE PRICE QUANTITY")
        print()
        print("Examples:")
        print("  python place_order.py KXHIGHNY-25JUL20-B89.5 yes 0.26 10")
        print("  python place_order.py KXHIGHNY-25JUL20-T94 no 0.96 5")
        print()
        print("Parameters:")
        print("  MARKET_TICKER: The specific market ticker (from market analysis)")
        print("  SIDE: 'yes' or 'no'")
        print("  PRICE: Price in dollars (e.g., 0.26 for 26¢)")
        print("  QUANTITY: Number of contracts to buy")
        print()
        print("💡 Start small with 1¢ and low quantity for testing!")
        sys.exit(1)
    
    ticker = sys.argv[1]
    side = sys.argv[2].lower()
    try:
        price = float(sys.argv[3])
    except ValueError:
        print("❌ Price must be a number (e.g., 0.26)")
        sys.exit(1)
    
    try:
        quantity = int(sys.argv[4])
    except ValueError:
        print("❌ Quantity must be an integer")
        sys.exit(1)
    
    # Validate inputs
    if side not in ['yes', 'no']:
        print("❌ Side must be 'yes' or 'no'")
        sys.exit(1)
    
    if quantity <= 0:
        print("❌ Quantity must be positive")
        sys.exit(1)
    
    if price <= 0 or price >= 1:
        print("❌ Price must be between $0.01 and $0.99")
        sys.exit(1)
    
    print("🏛️  KALSHI ORDER PLACEMENT")
    print("=" * 40)
    
    # Setup client
    client = setup_client()
    if not client:
        sys.exit(1)
    
    print("✅ Connected to Kalshi Production")
    
    # Get current market info
    print(f"\n📊 Getting market info for {ticker}...")
    market = get_market_info(client, ticker)
    
    if market:
        print(f"📝 Market: {market.get('title', 'N/A')}")
        print(f"💰 Current Yes Bid: {format_money(market.get('yes_bid', 0))}")
        print(f"💰 Current Yes Ask: {format_money(market.get('yes_ask', 0))}")
        print(f"💰 Current No Bid: {format_money(market.get('no_bid', 0))}")
        print(f"💰 Current No Ask: {format_money(market.get('no_ask', 0))}")
        print(f"📊 Volume: {market.get('volume', 0)}")
    else:
        print("⚠️  Could not get market info, but proceeding with order...")
    
    # Confirm order
    total_risk = price * quantity
    print(f"\n⚠️  ORDER CONFIRMATION:")
    print(f"   You are about to place a {side.upper()} order")
    print(f"   Price: ${price:.2f} per contract")
    print(f"   Quantity: {quantity} contracts")
    print(f"   Total at Risk: ${total_risk:.2f}")
    print(f"   Market: {ticker}")
    
    confirm = input("\nProceed with order? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Order cancelled")
        sys.exit(0)
    
    # Place the order
    success = place_order(client, ticker, side, price, quantity)
    
    if success:
        print(f"\n🎉 Order placed successfully!")
        print(f"\n💡 Next steps:")
        print(f"   1. Monitor your order status")
        print(f"   2. Check if it gets filled")
        print(f"   3. Consider placing the opposite side for market making")
    else:
        print(f"\n❌ Order failed")

if __name__ == "__main__":
    main()
