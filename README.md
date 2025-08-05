# Kalshi Weather Trading Bot

This is a modular, robust trading bot for Kalshi weather markets focused exclusively on Philadelphia markets. The bot uses XGBoost-based predictive modeling integrated into a CLI for training, backtesting, and live trading.

## Project Structure

```
kalshi_weather_bot/
│
├── data/              # Data storage directory
│   └── (holds downloaded csv files)
│
├── models/            # Model storage directory
│   └── (holds saved model files)
│
├── backtests/         # Backtesting results
│   └── (holds backtest results and metrics)
│
├── src/               # Source code modules
│   ├── data_collection/
│   ├── feature_engineering/
│   ├── modeling/
│   ├── backtesting/
│   └── trading/
│
├── .env.example       # Example environment file
├── .env               # Your API credentials (not in repo)
├── clients.py         # Kalshi API client
├── config.py          # Configuration parameters
├── main.py            # Main controller with CLI interface
├── requirements.txt   # Python dependencies
├── deploy.sh          # Deployment script
└── README.md          # This file
        ├── __init__.py
        └── trader.py
python main.py
```
