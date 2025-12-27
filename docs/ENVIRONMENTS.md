# Environment differences: demo vs production

| Field/Behavior        | Demo (KALSHI_ENV=demo)                     | Production (KALSHI_ENV=prod)          |
|-----------------------|---------------------------------------------|----------------------------------------|
| API host              | api.demo.kalshi.com                         | api.kalshi.com                         |
| Positions and balances| Fake balances for testing                  | Real balances and positions            |
| Trade settlement      | Simulated                                  | Real financial settlement              |
| Rate limits           | Lower in demo                              | Higher but enforced based on account   |
| Use case              | Experimentation, testing strategies         | Live trading with real funds           |

When switching to production, ensure that:
- Your API key and private key correspond to a live account.
- You understand the regulatory requirements for live trading.
- You test strategies extensively in demo first.
