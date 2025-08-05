#!/usr/bin/env python3

from main import load_kalshi_client

def test_client():
    print("Loading Kalshi client...")
    client = load_kalshi_client('demo')
    print("Client loaded successfully")
    
    print("Testing balance call...")
    try:
        balance = client.get_balance()
        print(f"Balance: {balance}")
    except Exception as e:
        print(f"Error: {e}")
        
    print("Testing exchange status call...")
    try:
        status = client.get_exchange_status()
        print(f"Exchange status: {status}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_client()
