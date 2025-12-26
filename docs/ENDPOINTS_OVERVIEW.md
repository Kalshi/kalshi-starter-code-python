# Kalshi API endpoints overview

This document summarizes some common API endpoints used by the examples in this repository. It complements the official API documentation.

| Endpoint                         | Purpose                                    | Method |
|---------------------------------|--------------------------------------------|--------|
| `/markets`                      | List markets with optional filters         | GET    |
| `/markets/{ticker}`             | Get details of a specific market           | GET    |
| `/orders`                       | Place a new order                          | POST   |
| `/orders/{order_id}`            | Retrieve or cancel an existing order       | GET/DELETE |
| `/positions`                    | List current positions                     | GET    |

See the official Kalshi API docs for query parameters and response schemas. Use these endpoints with the SDK or via direct HTTP if needed.

When adding new example scripts, please reference or update this overview.
