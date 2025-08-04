"""
Live Trading Module for Weather Markets
"""

import logging
import time
import pandas as pd
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from scipy.stats import norm  # For CDF calculations
import glob
import re
import joblib

# Local imports
from config import MINIMUM_EDGE_CENTS, MAX_RISK_PER_TRADE
from src.data_collection.kalshi_scanner import KalshiWeatherScanner
from src.data_collection.noaa_downloader import NOAADownloader
from src.feature_engineering.feature_generator import WeatherFeatureGenerator
from src.modeling.predictor import WeatherPredictor

logger = logging.getLogger(__name__)

MINIMUM_EDGE_CENTS = 7  # Minimum edge required to place a trade


def parse_market_bounds_from_ticker(market: Dict[str, Any]) -> Tuple[float, float]:
    """
    Parse temperature bounds from market ticker and title.
    Returns (lower_f, upper_f) in Fahrenheit, or (None, None) if parsing fails.
    """
    ticker = market.get('ticker', '')
    title = market.get('title', '')
    
    # Between markets: KXHIGHPHIL-25AUG04-B85.5 -> bounds (85.0, 86.0)
    between_match = re.search(r'-B(\d+\.?\d*)$', ticker)
    if between_match:
        center = float(between_match.group(1))
        return (center - 0.5, center + 0.5)
    
    # Threshold markets: KXHIGHPHIL-25AUG04-T86
    threshold_match = re.search(r'-T(\d+\.?\d*)$', ticker)
    if threshold_match:
        threshold = float(threshold_match.group(1))
        # Check title for direction
        if '>' in title:
            return (threshold, float('inf'))
        elif '<' in title:
            return (float('-inf'), threshold)
    
    logger.warning(f"Could not parse bounds for ticker: {ticker}")
    return (None, None)


def fahrenheit_to_celsius(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (f - 32) * 5 / 9


def celsius_to_fahrenheit(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return c * 9 / 5 + 32


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
                # Use a 45-day look-back to ensure all rolling features (up to 30-day windows) are fully populated
                start_date = end_date - timedelta(days=45)
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
                # -------------------- Build a proper "today" prediction row --------------------
                yesterday_features = features.iloc[-1].copy()
                today_prediction_row = yesterday_features.copy()

                # Update calendar-based features to reflect today (local timezone assumed)
                today_date = datetime.now()
                if 'day_of_year' in today_prediction_row:
                    today_prediction_row['day_of_year'] = today_date.timetuple().tm_yday
                if 'month' in today_prediction_row:
                    today_prediction_row['month'] = today_date.month
                if 'day_of_week' in today_prediction_row:
                    today_prediction_row['day_of_week'] = today_date.weekday()
                if 'is_weekend' in today_prediction_row:
                    today_prediction_row['is_weekend'] = int(today_date.weekday() >= 5)
                if 'is_summer' in today_prediction_row:
                    today_prediction_row['is_summer'] = int(today_date.month in [6, 7, 8])
                if 'is_winter' in today_prediction_row:
                    today_prediction_row['is_winter'] = int(today_date.month in [12, 1, 2])

                # Manually shift key lag features forward one day
                # max temp lags
                if 'max_temp_lag_1' in today_prediction_row and 'target_max_temp' in yesterday_features:
                    today_prediction_row['max_temp_lag_2'] = today_prediction_row.get('max_temp_lag_1', 0)
                    today_prediction_row['max_temp_lag_1'] = yesterday_features['target_max_temp']
                if 'min_temp_lag_1' in today_prediction_row and 'min_temp' in yesterday_features:
                    today_prediction_row['min_temp_lag_2'] = today_prediction_row.get('min_temp_lag_1', 0)
                    today_prediction_row['min_temp_lag_1'] = yesterday_features.get('min_temp', 0)

                # Simple diff update example
                if 'max_temp_diff_1' in today_prediction_row and 'max_temp_lag_1' in today_prediction_row:
                    prev_day = yesterday_features.get('max_temp_lag_1', 0)
                    today_prediction_row['max_temp_diff_1'] = today_prediction_row['max_temp_lag_1'] - prev_day

                # Convert to DataFrame and ensure numeric dtypes
                prediction_features = today_prediction_row.to_frame().T
                prediction_features = prediction_features.apply(pd.to_numeric, errors='coerce').fillna(0)
                logger.debug("Prediction row (transposed):\n" + str(prediction_features.T))
                
                # 5. Make prediction using regression model
                # Load the latest trained regressor model
                model_files = glob.glob("models/philly_weather_xgb_regressor_target_max_temp_*.joblib")
                if model_files:
                    # Use the most recent model file
                    model_files.sort(reverse=True)
                    model_path = model_files[0]
                    logger.info(f"Using model: {model_path}")
                else:
                    model_path = "models/weather_model.pkl"  # Fallback to old model
                
                # Remove date column for model prediction
                if 'date' in prediction_features.columns:
                    prediction_features = prediction_features.drop(columns=['date'])
                
                if os.path.exists(model_path):
                    # Load model and associated metrics
                    model_dict = joblib.load(model_path)
                    regressor_model = model_dict['model']
                    model_rmse = model_dict['rmse']
                    
                    # Align prediction_features columns to model's expected feature order
                    if hasattr(regressor_model, 'get_booster'):
                        feature_names = regressor_model.get_booster().feature_names
                        if feature_names:
                            prediction_features = prediction_features.reindex(columns=feature_names, fill_value=0)
                    
                    # Predict the actual temperature (mu)
                    predicted_temp_c = regressor_model.predict(prediction_features)[0]
                    
                    # Parse market bounds
                    lower_f, upper_f = parse_market_bounds_from_ticker(market)
                    if lower_f is None or upper_f is None:
                        logger.warning(f"Skipping {ticker} due to bounds parsing failure")
                        continue
                    
                    # Convert bounds to Celsius
                    lower_c = fahrenheit_to_celsius(lower_f) if lower_f != float('-inf') else float('-inf')
                    upper_c = fahrenheit_to_celsius(upper_f) if upper_f != float('inf') else float('inf')
                    
                    # Calculate probability using normal distribution CDF
                    lower_cdf = 0.0 if lower_c == float('-inf') else norm.cdf(lower_c, loc=predicted_temp_c, scale=model_rmse)
                    upper_cdf = 1.0 if upper_c == float('inf') else norm.cdf(upper_c, loc=predicted_temp_c, scale=model_rmse)
                    prob_in_range = upper_cdf - lower_cdf
                    
                    # Convert to fair value in cents
                    fair_value = prob_in_range * 100
                    
                    logger.info(f"Model prediction: {predicted_temp_c:.2f}°C ({celsius_to_fahrenheit(predicted_temp_c):.1f}°F)")
                    logger.info(f"Market bounds: [{lower_f}, {upper_f}]°F -> [{lower_c:.2f}, {upper_c:.2f}]°C")
                    logger.info(f"Probability in range: {prob_in_range:.4f}, Fair value: {fair_value:.2f} cents")
                else:
                    logger.warning(f"Model file {model_path} not found. Using placeholder prediction.")
                    # Use a placeholder prediction if no model is available
                    predicted_temp_c = 20.0  # 20°C placeholder
                    model_rmse = 5.0         # 5°C placeholder RMSE
                    fair_value = 50.0        # 50 cents placeholder fair value
                
                # 6. Calculate fair value
                fair_value = prob_in_range * 100  # Convert to cents
                
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
                    # For regression, we don't use a certainty threshold in the same way
                    # Instead, we rely on the edge calculation which already incorporates model confidence (RMSE)
                    
                    if yes_edge >= MINIMUM_EDGE_CENTS:
                        # Place YES trade
                        # Use the probability for position sizing
                        position_size = trade_executor.calculate_position_size(yes_edge, prob_in_range)
                        if position_size > 0:
                            logger.info(f"Placing YES trade on {ticker} with {position_size} contracts at {yes_ask} cents")
                            trade_response = trade_executor.place_trade(ticker, 'yes', position_size, yes_ask)
                            logger.info(f"Trade response: {trade_response}")
                    elif no_edge >= MINIMUM_EDGE_CENTS:
                        # Place NO trade
                        # Use the probability for position sizing
                        position_size = trade_executor.calculate_position_size(no_edge, 1 - prob_in_range)
                        if position_size > 0:
                            logger.info(f"Placing NO trade on {ticker} with {position_size} contracts at {no_ask} cents")
                            trade_response = trade_executor.place_trade(ticker, 'no', position_size, no_ask)
                            logger.info(f"Trade response: {trade_response}")
                    else:
                        if prob_in_range >= 0.6 or prob_in_range <= 0.4:
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
