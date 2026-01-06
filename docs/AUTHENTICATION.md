# API authentication guide

This guide explains how to authenticate with the Kalshi API.

## Creating credentials

1. Log in to your Kalshi account.
2. Generate an API key ID and download your private key.

## Setting environment variables

- `KALSHI_API_KEY_ID` — your API key ID.
- `KALSHI_PRIVATE_KEY_PATH` — absolute path to the PEM file.
- `KALSHI_API_HOST` — optional, override for demo or production.

## Python usage

Load your credentials:

```python
from kalshi_python import KalshiClient, Configuration

cfg = Configuration(host=os.getenv("KALSHI_API_HOST"))
cfg.api_key_id = os.getenv("KALSHI_API_KEY_ID")
with open(os.getenv("KALSHI_PRIVATE_KEY_PATH")) as f:
    cfg.private_key_pem = f.read()
client = KalshiClient(cfg)
