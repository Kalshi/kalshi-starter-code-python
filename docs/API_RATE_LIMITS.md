# API rate limits

Kalshi enforces rate limits on its API to ensure fair usage.

## Demo environment

- Request limit: 60 requests per minute
- Burst: 20 requests per second
- Consequence: Exceeding the limit returns HTTP 429

## Production environment

- Request limit: 180 requests per minute
- Burst: 60 requests per second
- Rate limits may vary by account tier

If you encounter 429 responses, implement exponential backoff and respect the `Retry-After` header.
