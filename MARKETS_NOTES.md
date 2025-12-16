# Markets Notes

This file complements the main README by outlining a few practical
considerations when working with Kalshi markets from the starter code.

## Environment

Make sure your environment variables are set correctly:

- `KALSHI_API_KEY`
- `KALSHI_API_SECRET`
- `KALSHI_ENV` (`demo` or `prod`)

Use `check_env.py` to verify that everything is configured before
calling any market-related endpoints.

## Pagination and filtering

The Kalshi API may return paginated results. When you replace the
placeholder logic in `scripts/print_markets.py` with real API calls:

- check whether the client or endpoint supports pagination parameters,
- avoid loading a very large number of markets in a single request.

## Error handling

When fetching markets:

- handle network errors (timeouts, connection resets),
- handle authentication failures (invalid or expired credentials),
- log unexpected responses for debugging.

## Demo vs production

Always verify which environment you are targeting:

- `KALSHI_ENV=demo` for testing,
- `KALSHI_ENV=prod` for live trading.

Never reuse demo credentials in production or vice versa.
