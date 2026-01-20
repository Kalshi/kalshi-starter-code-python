# Configuration

The Kalshi client can be configured using environment variables.

## Supported variables

- `KALSHI_API_KEY`
- `KALSHI_API_SECRET`
- `KALSHI_ENV` (e.g. `demo` or `prod`)

## Example

```python
import os
from kalshi_client import KalshiClient

client = KalshiClient(
    api_key=os.getenv("KALSHI_API_KEY"),
    api_secret=os.getenv("KALSHI_API_SECRET"),
    environment=os.getenv("KALSHI_ENV", "demo")
)
