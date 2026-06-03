import os
import json
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
import asyncio

from clients import KalshiHttpClient, KalshiWebSocketClient, Environment
from event_helper import EventHelper, find_event, search_events

# Load environment variables
load_dotenv()
# env = clearEnvironment.DEMO # toggle environment her
env = Environment.PROD if os.getenv('USE_DEMO_ENVIRONMENT', 'False').lower() == 'false' else Environment.DEMO

print(f"Using environment: {env.value}")
KEYID = os.getenv('DEMO_KEYID') if env == Environment.DEMO else os.getenv('PROD_KEYID')
KEYFILE = os.getenv('DEMO_KEYFILE') if env == Environment.DEMO else os.getenv('PROD_KEYFILE')

try:
    with open(KEYFILE, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None  # Provide the password if your key is encrypted
        )
except FileNotFoundError:
    raise FileNotFoundError(f"Private key file not found at {KEYFILE}")
except Exception as e:
    raise Exception(f"Error loading private key: {str(e)}")

# Initialize the HTTP client
client = KalshiHttpClient(
    key_id=KEYID,
    private_key=private_key,
    environment=env
)

# Helper function to format monetary values
def format_money(value):
    try:
        return f"{float(value)/100:.2f}"
    except (TypeError, ValueError):
        return "0.00"

# Helper function to load/save events cache
def load_events_cache():
    try:
        with open('events_cache.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_events_cache(events_dict):
    with open('events_cache.json', 'w') as f:
        json.dump(events_dict, f, indent=2)

# Helper function to load/save open events cache
def load_open_events_cache():
    try:
        with open('open_events_cache.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_open_events_cache(open_events_dict):
    with open('open_events_cache.json', 'w') as f:
        json.dump(open_events_dict, f, indent=2)

# Function to fetch all events efficiently
def get_all_events():
    print("Loading events cache...")
    events_dict = load_events_cache()
    print(f"Found {len(events_dict)} cached events")
    
    cursor = None
    new_events_count = 0
    
    while True:
        # Build URL with cursor if available
        url = "/trade-api/v2/events"
        if cursor:
            url += f"&cursor={cursor}"
        
        print(f"Fetching events page... (cursor: {'Yes' if cursor else 'First page'})")
        response = client.get(url)
        events = response.get('events', [])
        
        if not events:
            break
            
        # Add new events to our dictionary
        for event in events:
            event_id = event.get('event_ticker')
            event_name = event.get('title')
            
            if event_id and event_id not in events_dict:
                events_dict[event_id] = {
                    'id': event_id,
                    'name': event_name
                }
                new_events_count += 1
        
        # Get cursor for next page
        cursor = response.get('cursor')
        if not cursor:
            break
    
    print(f"Added {new_events_count} new events")
    print(f"Total events: {len(events_dict)}")
    
    # Save updated cache
    save_events_cache(events_dict)
    return events_dict

# Function to fetch only open events using API filtering
def get_open_events(force_refresh=False):
    print("Loading open events cache...")
    
    # Load cached open events unless force refresh
    if not force_refresh:
        open_events_dict = load_open_events_cache()
        if open_events_dict:
            print(f"Found {len(open_events_dict)} cached open events")
            return open_events_dict
    
    print("Fetching open events from API...")
    open_events_dict = {}
    
    cursor = None
    total_open = 0
    
    while True:
        # Build URL with status=open filter and cursor if available
        url = "/trade-api/v2/events?status=open"
        if cursor:
            url += f"&cursor={cursor}"
        
        print(f"Fetching open events page... (cursor: {'Yes' if cursor else 'First page'})")
        response = client.get(url)
        events = response.get('events', [])
        
        if not events:
            break
            
        # Add open events to our dictionary
        for event in events:
            event_id = event.get('event_ticker')
            event_name = event.get('title')
            
            if event_id:
                open_events_dict[event_id] = {
                    'id': event_id,
                    'name': event_name,
                    'status': 'open'
                }
                total_open += 1
        
        # Get cursor for next page
        cursor = response.get('cursor')
        if not cursor:
            break
    
    print(f"Found {total_open} open events")
    
    # Save the cache
    save_open_events_cache(open_events_dict)
    print("Open events cached successfully!")
    
    return open_events_dict

# Get account balance
balance = client.get_balance()
print("Balance:", format_money(balance.get('balance', 0)))

# # Get all events efficiently
# print("\n" + "="*50)
# print("FETCHING ALL EVENTS")
# print("="*50)
# events_dict = get_all_events()

# # Display first 10 events as example
# print("\nFirst 10 events:")
# for i, (event_id, event_data) in enumerate(list(events_dict.items())[:10]):
#     print(f"{i+1}. {event_id}: {event_data['name']}")

# Get open events using API filtering
print("\n" + "="*50)
print("FETCHING OPEN EVENTS")
print("="*50)
open_events = get_open_events()

print(f"\nOpen events: {len(open_events)} total")
print("\nFirst 10 OPEN events:")
for i, (event_id, event_data) in enumerate(list(open_events.items())[:10]):
    print(f"{i+1}. {event_id}: {event_data['name']}")

print(f"\nYou can now access any event by ID: open_events['EVENT_ID']")
print(f"Open events available: {len(open_events)}")

# Initialize Event Helper for easy searching
print("\n" + "="*50)
print("EVENT HELPER DEMO")
print("="*50)

event_helper = EventHelper(events_dict={}, open_events_dict=open_events)

# Demo searches
print("\nExample: Search for 'Trump' events:")
trump_results = event_helper.search_event_by_name("trump", max_results=3)
event_helper.print_search_results(trump_results)

print("\nExample: Find event ID for 'election':")
election_id = find_event("election", {}, open_events)
if election_id:
    print(f"First election event ID: {election_id}")
else:
    print("No election events found")

print(f"\n{'='*50}")
print("HOW TO USE EVENT HELPER:")
print("1. event_helper.search_event_by_name('search term')")
print("2. find_event('partial name', {}, open_events)")
print("3. Run: python event_helper.py for interactive mode")
print("\nCACHE INFO:")
print("- All events cached in: events_cache.json")
print("- Open events cached in: open_events_cache.json") 
print("- To refresh open events: get_open_events(force_refresh=True)")
print(f"{'='*50}")

positions = client.get("/trade-api/v2/portfolio/positions")

print("Market Positions:")
for pos in positions.get('market_positions', []):
    if pos.get('position', 0) != 0:
        ticker = pos.get('ticker')
        market = client.get(f"/trade-api/v2/markets/{ticker}")
        market_title = market.get('market', {}).get('title', 'Unknown')
        print("---")
        print(f"Ticker: {ticker}")
        print(f"Event: {market_title}")
        print(f"Total Traded: {format_money(pos.get('total_traded', 0))}")
        print(f"Position: {float(pos.get('position', 0)):.2f}")
        print(f"Market Exposure: {format_money(pos.get('market_exposure', 0))}")
        print(f"Realized PnL: {format_money(pos.get('realized_pnl', 0))}")
        print(f"Resting Orders Count: {float(pos.get('resting_orders_count', 0)):.2f}")
        print(f"Fees Paid: {format_money(pos.get('fees_paid', 0))}")
        print(f"Last Updated: {pos.get('last_updated_ts')}")


# ...existing code...

# Get all orders (pending, open, etc.)
orders = client.get("/trade-api/v2/portfolio/orders?cursor=EhIKEAnPLuins0i5pLfKfpANAL8aDAiN6d7BBhConqPRAw")

# print(orders)
print("\nOrders:")
for order in orders.get("orders", [])[:5]:
    ticker = order.get("ticker")
    market = client.get(f"/trade-api/v2/markets/{ticker}")
    market_title = market.get("market", {}).get("title", "Unknown")
    print("---")
    print(f"Market:  {market_title}")
    print(f"Ticker:  {ticker}")
    print(f"Order ID: {order.get('order_id')}")
    print(f"User ID: {order.get('user_id')}")
    print(f"Status: {order.get('status')}")
    print(f"Yes Price: {format_money(order.get('yes_price'))}")
    print(f"No Price: {format_money(order.get('no_price'))}")
    print(f"Created Time: {order.get('created_time')}")
    print(f"Taker Fill Cost: {format_money(order.get('taker_fill_cost'))}")
    print(f"Maker Fill Cost: {format_money(order.get('maker_fill_cost'))}")
    print(f"Fill Count: {order.get('fill_count')}")
    print(f"Remaining Count: {order.get('remaining_count')}")
    print(f"Initial Count: {order.get('initial_count')}")
    print(f"Self Trade Prevention Type: {order.get('self_trade_prevention_type')}")
    print(f"Queue Position: {order.get('queue_position')}")
    print(f"Expiration Time: {order.get('expiration_time')}")
    print(f"Taker Fees: {format_money(order.get('taker_fees'))}")
    print(f"Maker Fees: {format_money(order.get('maker_fees'))}")
    print(f"Action: {order.get('action')}")
    print(f"Side: {order.get('side')}")
    print(f"Type: {order.get('type')}")
    print(f"Last Update Time: {order.get('last_update_time')}")
    print(f"Client Order ID: {order.get('client_order_id')}")
    print(f"Order Group ID: {order.get('order_group_id')}")

# trades = client.get_trades()
# print("Trades:")
# for trade in trades.get('trades', []):
#     trade_id = trade.get('trade_id')
#     ticker = trade.get('ticker')
#     # Fetch market details for this ticker
#     market = client.get(f"/trade-api/v2/markets/{ticker}")
#     market_title = market.get('market', {}).get('title', 'Unknown')
#     print(f"Trade ID: {trade_id} | Ticker: {ticker} | Event: {market_title}")

# print("Exchange Status:", client.get_exchange_status())

# # Initialize the WebSocket client
# ws_client = KalshiWebSocketClient(
#     key_id=KEYID,
#     private_key=private_key,
#     environment=env
# )

# # Connect via WebSocket
# asyncio.run(ws_client.connect())