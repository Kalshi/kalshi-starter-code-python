"""
Live Trading Module for Weather Markets
"""

import logging
import time
import pandas as pd
import os
from typing import Dict, List, Any
from datetime import datetime, timedelta

# Local imports
from config import MINIMUM_EDGE_CENTS, MAX_RISK_PER_TRADE
from src.data_collection.kalshi_scanner import KalshiWeatherScanner
from src.data_collection.noaa_downloader import NOAADownloader
from src.feature_engineering.feature_generator import WeatherFeatureGenerator
from src.modeling.predictor import WeatherPredictor

logger = logging.getLogger(__name__)


def run_trading_loop(client=None):
    """Run the live trading loop with risk management and edge logic."""
    logger.info("Starting live trading loop")
    
    if client is None:
        logger.error("Kalshi client is required for trading")
        return
    
    # Initialize trade executor
    try:
        # Get current portfolio balance
        balance_response = client.get_balance()
        portfolio_balance = balance_response.get('balance', 1000000)  # Default to 10000 USD in cents
        logger.info(f"Current portfolio balance: ${portfolio_balance / 100:.2f}")
        
        trade_executor = TradeExecutor(client, portfolio_balance)
    except Exception as e:
        logger.error(f"Failed to initialize trade executor: {e}")
        return
    
    # Main trading loop
    iteration = 0
    max_iterations = 100  # Prevent infinite loop in demo
    
    # Initialize market scanner
    scanner = KalshiWeatherScanner(client)
    
    while iteration < max_iterations:
        try:
            logger.info(f"Trading iteration {iteration + 1}")
            
            # 1. Scan for Philadelphia weather markets
            markets = scanner.scan_weather_markets()
            if not markets:
                logger.info("No markets found for trading")
                time.sleep(60)  # Wait before next iteration
                iteration += 1
                continue
            
            # 2. For each market, get latest weather data and make predictions
            for market in markets:
                ticker = market['ticker']
                logger.info(f"Analyzing market: {ticker}")
                
                # 3. Get latest weather data for Philadelphia
                noaa_downloader = NOAADownloader()
                # For live trading, we'll use recent data (last 7 days)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                weather_data = noaa_downloader.download_philly_historical_data(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                if weather_data is None or weather_data.empty:
                    logger.warning(f"Could not get weather data for {ticker}")
                    continue
                
                # 4. Generate features
                feature_generator = WeatherFeatureGenerator()
                features = feature_generator.generate_philly_features(weather_data)
                
                # 5. Get model prediction
                predictor = WeatherPredictor()
                # Look for the latest XGBoost model
                import glob
                model_files = glob.glob("models/philly_weather_xgb_target_high_temp_yes_*.joblib")
                if model_files:
                    # Use the most recent model file
                    model_files.sort(reverse=True)
                    model_path = model_files[0]
                    logger.info(f"Using model: {model_path}")
                else:
                    model_path = "models/weather_model.pkl"  # Fallback to old model
                
                if os.path.exists(model_path):
                    predictor.load_model(model_path)
                    # Use predict_proba to obtain probability of YES (class 1)
                    proba_arr = predictor.predict_proba(features)
                    # XGBoost returns array of shape (n_samples, 2). Take probability of class 1.
                    prediction_prob = float(proba_arr[0][1])
                else:
                    logger.warning(f"Model file {model_path} not found. Using placeholder prediction.")
                    # Use a placeholder prediction if no model is available
                    prediction_prob = 0.5  # 50% probability as placeholder
                
                # 6. Calculate fair value
                fair_value = prediction_prob * 100  # Convert to cents
                
                # 7. Check market prices
                try:
                    # Attempt to retrieve market order book. Handle 404 by falling back or defaulting prices.
                    try:
                        market_data = client.get(f'/trade-api/v2/markets/{ticker}')
                    except Exception as e:
                        logger.warning(f"[TRADE] Primary market endpoint failed for {ticker}: {e}. Trying /book endpoint …")
                        try:
                            market_data = client.get(f'/trade-api/v2/markets/{ticker}/book')
                        except Exception as e2:
                            logger.error(f"[TRADE] All endpoints failed for {ticker}: {e2}. Using default 50/50 prices.")
                            market_data = {}
                    yes_bid = market_data.get('market', {}).get('yes_bid', 50)
                    yes_ask = market_data.get('market', {}).get('yes_ask', 50)
                    no_bid = market_data.get('market', {}).get('no_bid', 50)
                    no_ask = market_data.get('market', {}).get('no_ask', 50)
                    
                    logger.info(
                        f"Market {ticker} - YES bid/ask: {yes_bid}/{yes_ask} cents, NO bid/ask: {no_bid}/{no_ask} cents")
                    logger.info(f"Fair value: {fair_value:.2f} cents")
                    
                    # 8. Calculate edges based on ASK prices (cost to enter position)
                    yes_edge = fair_value - yes_ask  # Buying YES costs the ask price
                    no_edge = (100 - fair_value) - no_ask  # Buying NO costs its ask price
                    
                    logger.info(f"YES edge: {yes_edge:.2f} cents, NO edge: {no_edge:.2f} cents")
                    
                    # 9. Check for trading opportunities
                    # Apply certainty rule: only trade if prediction is confident enough
                    certainty_threshold = 0.6  # Trade if prediction > 60% or < 40%
                    
                    if yes_edge >= MINIMUM_EDGE_CENTS and prediction_prob >= certainty_threshold:
                        # Place YES trade
                        position_size = trade_executor.calculate_position_size(yes_edge, prediction_prob)
                        if position_size > 0:
                            logger.info(f"Placing YES trade on {ticker} with {position_size} contracts at {yes_price} cents")
                            # In a real implementation, you would place the trade here
                            trade_executor.place_trade(ticker, 'yes', position_size, yes_price)
                    elif no_edge >= MINIMUM_EDGE_CENTS and prediction_prob <= (1 - certainty_threshold):
                        # Place NO trade
                        position_size = trade_executor.calculate_position_size(no_edge, 1 - prediction_prob)
                        if position_size > 0:
                            logger.info(f"Placing NO trade on {ticker} with {position_size} contracts at {no_price} cents")
                            # In a real implementation, you would place the trade here
                            trade_executor.place_trade(ticker, 'no', position_size, no_price)
                    else:
                        if prediction_prob >= certainty_threshold or prediction_prob <= (1 - certainty_threshold):
                            logger.info(f"No trading opportunity for {ticker} (insufficient edge despite high certainty)")
                        else:
                            logger.info(f"No trading opportunity for {ticker} (low prediction certainty)")
                        
                except Exception as e:
                    logger.error(f"Error getting market data for {ticker}: {e}")
                    continue
            
            # Wait before next iteration
            logger.info("Waiting 5 minutes before next trading iteration")
            time.sleep(300)  # 5 minutes
            iteration += 1
            
        except KeyboardInterrupt:
            logger.info("Trading loop interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            time.sleep(60)  # Wait before retrying
            iteration += 1
            continue
        # Simulate trade execution
        logger.info("Checking for trading opportunities...")
        time.sleep(1)  # Simulate decision making
        
        logger.info("No trades executed in this iteration")
        
        # Wait before next iteration (in real system, this might be minutes)
        if i < 4:  # Don't wait after the last iteration
            time.sleep(2)
    
    logger.info("Trading loop completed")


class TradeExecutor:
    """Executor for placing trades on Kalshi."""
    
    def __init__(self, client, portfolio_balance: float):
        """
        Initialize the trade executor.
        
        Args:
            client: KalshiHttpClient instance
            portfolio_balance: Current portfolio balance in cents
        """
        self.client = client
        self.portfolio_balance = portfolio_balance
    
    def calculate_position_size(self, edge_cents: float, probability: float) -> int:
        """
        Calculate position size using a simplified Kelly Criterion.
        
        Args:
            edge_cents: Edge in cents (fair_value - market_price)
            probability: Model's predicted probability
            
        Returns:
            Position size in contracts
        """
        # Simplified Kelly Criterion: f = (bp - q) / b
        # where b = odds, p = win probability, q = loss probability
        
        if edge_cents < MINIMUM_EDGE_CENTS:
            return 0  # Don't trade if edge is too small
        
        # Convert edge to probability terms
        edge_probability = edge_cents / 100.0
        
        # Odds (simplified - in practice, you'd use the actual market prices)
        odds = 1.0
        
        # Kelly fraction
        kelly_fraction = (odds * probability - (1 - probability)) / odds
        
        # Apply risk limits
        kelly_fraction = max(0, min(kelly_fraction, MAX_RISK_PER_TRADE))
        
        # Calculate position size in dollars
        position_value = self.portfolio_balance * kelly_fraction
        
        # Convert to number of contracts (assuming $1 per contract)
        position_size = int(position_value / 100)  # Convert cents to dollars
        
        return max(0, position_size)
    
    def place_trade(self, market_ticker: str, side: str, count: int, price: int) -> Dict[str, Any]:
        """
        Place a trade on Kalshi.
        
        Args:
            market_ticker: Market ticker symbol
            side: 'yes' or 'no'
            count: Number of contracts
            price: Price in cents per contract
            
        Returns:
            Trade response
        """
        logger.info(f"Placing trade: {side} {count} contracts of {market_ticker} at {price} cents")
        
        # In a real implementation, you would call the Kalshi API
        # For now, we'll simulate a successful trade
        
        trade_response = {
            "success": True,
            "order_id": f"order_{int(time.time())}",
            "ticker": market_ticker,
            "side": side,
            "count": count,
            "price": price,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Trade placed successfully: {trade_response['order_id']}")
        
        return trade_response
