# Environment Configuration Examples

This document illustrates a few example `.env` configurations for the Kalshi starter.

## 1. Demo environment

A basic configuration for running against a demo or sandbox environment:

    KALSHI_API_HOST=https://demo-api.kalshi.com/trade-api/v2
    KALSHI_API_KEY_ID=your-demo-key-id
    KALSHI_PRIVATE_KEY_PATH=./demo_private_key.pem

## 2. Production-like configuration

An example for production-style setups:

    KALSHI_API_HOST=https://api.elections.kalshi.com/trade-api/v2
    KALSHI_API_KEY_ID=your-prod-key-id
    KALSHI_PRIVATE_KEY_PATH=./prod_private_key.pem

## 3. Logging and timeouts

You can add optional variables to control behaviour in `main.py`:

    LOG_LEVEL=INFO
    REQUEST_TIMEOUT_SECONDS=10

Keep secrets such as private keys out of version control and rotate them according to your security policy.
