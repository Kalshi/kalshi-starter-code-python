"""
Upgraded Backtesting Framework with Deterministic Simulation and Visualizations for Regression Models.
"""
import logging
import pandas as pd
import numpy as np
import os
import json
import joblib
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from scipy.stats import norm  # For CDF calculations for regression

# Visualization libraries
import matplotlib.pyplot as plt
import seaborn as sns

# Local imports
from src.modeling.predictor import WeatherPredictor
from config import MINIMUM_EDGE_CENTS, MAX_RISK_PER_TRADE
from src.trading.trader import fahrenheit_to_celsius, celsius_to_fahrenheit, parse_market_bounds_from_ticker

logger = logging.getLogger(__name__)


class WalkForwardBacktester:
    """
    Backtester using walk-forward validation with realistic trade simulation for regression models.
    """
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital  # Current capital
        # These will be populated during the run
        self.equity_curve = pd.Series(dtype=float)
        self.trade_log = []
        self.position_log = []  # Track open positions

    def run_walk_forward_backtest(self,
                                  features_df: pd.DataFrame,
                                  model_path: str,
                                  train_window_days: int = 365*5,  # 5 years
                                  test_window_days: int = 90) -> Dict[str, Any]:
        
        logger.info("--- Starting Regression Walk-Forward Backtest ---")
        self.capital = self.initial_capital
        
        # --- Data Preparation ---
        features_df = features_df.sort_values('date').reset_index(drop=True)
        features_df['date'] = pd.to_datetime(features_df['date'])
        
        # Determine the target column for regression
        target_col = 'target_max_temp'
        if target_col not in features_df.columns:
            raise ValueError(f"Target column '{target_col}' not found in features DataFrame")

        # --- Walk-Forward Loop ---
        start_date = features_df['date'].min()
        train_end_date = start_date + timedelta(days=train_window_days)
        test_end_date = train_end_date + timedelta(days=test_window_days)
        
        iteration = 0
        while test_end_date <= features_df['date'].max():
            # In a real system, you would re-train the model here
            # trainer.train_and_save(train_df)
            
            test_mask = (features_df['date'] > train_end_date) & (features_df['date'] <= test_end_date)
            test_df = features_df[test_mask].copy()

            if test_df.empty:
                break
            
            logger.info(f"Iteration {iteration}: Testing from {test_df['date'].min().date()} to {test_df['date'].max().date()}")

            # --- Load regression model and RMSE ---
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")
                
            model_dict = joblib.load(model_path)
            regressor_model = model_dict['model']
            model_rmse_raw = model_dict['rmse']
            
            # Calibrate model confidence (widen the error margin)
            # Create a skepticism factor. Start by doubling the error margin.
            SKEPTICISM_FACTOR = 20.0 
            model_rmse = model_rmse_raw * SKEPTICISM_FACTOR
            
            logger.info(f"Loaded regression model with raw RMSE: {model_rmse_raw:.4f}, inflated RMSE for backtest: {model_rmse:.4f}")

            # --- Simulate trades for each day in test window ---
            self._simulate_regression_trades(test_df, regressor_model, model_rmse)

            train_end_date += timedelta(days=test_window_days)
            test_end_date += timedelta(days=test_window_days)
            iteration += 1
            
        results_df = pd.DataFrame(self.trade_log)
        
        # Handle case where no trades were made
        if results_df.empty:
            logger.warning("No trades were made during backtesting.")
            self.equity_curve = pd.Series([self.initial_capital], name='equity')
            metrics = {"message": "No trades were made during backtesting."}
            self.plot_results(results_df, metrics)
            self._save_backtest_results(metrics, results_df)
            return metrics
        
        self.equity_curve = results_df['capital'].rename('equity')
        
        metrics = self._calculate_metrics(results_df)
        self.plot_results(results_df, metrics)
        
        self._save_backtest_results(metrics, results_df)
        
        logger.info("--- Walk-Forward Backtest Completed ---")
        return metrics

    def _simulate_regression_trades(self, test_df: pd.DataFrame, regressor_model, model_rmse: float):
        """Simulates trades for regression-based strategy using normal distribution probabilities."""
        logger.info(f"Starting simulation for {len(test_df)} days")
        
        # Reset index to ensure proper indexing
        test_df = test_df.reset_index(drop=True)
        
        # Group by date to process one day at a time
        for date, daily_df in test_df.groupby('date'):
            # --- Daily Risk Management ---
            capital_at_start_of_day = self.capital
            daily_pnl = 0.0
            
            # We only expect one row per day, but this loop is robust
            for idx, row in daily_df.iterrows():
                actual_max_temp_celsius = row['target_max_temp']
                actual_max_temp = celsius_to_fahrenheit(actual_max_temp_celsius)

                # Create a proper prediction row for the current date
                # Find the original index in the main test_df to create the prediction row
                original_idx = test_df.index.get_loc(row.name)
                prediction_row = self._create_prediction_row(test_df, original_idx)
                
                if prediction_row is None: continue

                # Predict temperature
                try:
                    if hasattr(regressor_model, 'feature_names_in_'):
                        model_features = regressor_model.feature_names_in_
                        common_features = [col for col in model_features if col in prediction_row.columns]
                        prediction_row = prediction_row[common_features]
                    
                    predicted_temp_celsius = regressor_model.predict(prediction_row)[0]
                    predicted_temp_f = celsius_to_fahrenheit(predicted_temp_celsius)
                except Exception as e:
                    logger.warning(f"{date.date()}: Prediction failed: {e}")
                    continue

                # --- Market Simulation ---
                bin_width_f = 2.0
                bin_centers_f = [round(predicted_temp_f) + i * bin_width_f for i in range(-2, 3)]
                bin_edges_f = [c - bin_width_f/2 for c in bin_centers_f] + [bin_centers_f[-1] + bin_width_f/2]

                # Calculate probabilities
                bin_probabilities = []
                for i in range(len(bin_edges_f)-1):
                    lower_c = fahrenheit_to_celsius(bin_edges_f[i])
                    upper_c = fahrenheit_to_celsius(bin_edges_f[i+1])
                    prob = norm.cdf(upper_c, loc=predicted_temp_celsius, scale=model_rmse) - \
                           norm.cdf(lower_c, loc=predicted_temp_celsius, scale=model_rmse)
                    bin_probabilities.append(prob)
                
                fair_values_cents = [p * 100 for p in bin_probabilities]

                # Simulate market prices
                import random
                market_consensus_prices = [fv + random.uniform(-2.0, 2.0) for fv in fair_values_cents]
                market_bid_prices = [max(0, min(100, mid - random.uniform(0.1, 0.5))) for mid in market_consensus_prices]
                market_ask_prices = [max(0, min(100, mid + random.uniform(0.1, 0.5))) for mid in market_consensus_prices]

                # --- Edge Calculation & Trade Execution ---
                edges_to_buy = [fv - ask for fv, ask in zip(fair_values_cents, market_ask_prices)]
                edges_to_sell = [bid - fv for fv, bid in zip(fair_values_cents, market_bid_prices)]
                best_edge = max(max(edges_to_buy, default=0), max(edges_to_sell, default=0))

                if best_edge >= MINIMUM_EDGE_CENTS:
                    if max(edges_to_buy, default=0) >= max(edges_to_sell, default=0):
                        best_bin_index, best_edge_type, market_price = edges_to_buy.index(max(edges_to_buy)), 'buy', market_ask_prices[edges_to_buy.index(max(edges_to_buy))]
                    else:
                        best_bin_index, best_edge_type, market_price = edges_to_sell.index(max(edges_to_sell)), 'sell', market_bid_prices[edges_to_sell.index(max(edges_to_sell))]
                    
                    logger.info(f"{date.date()}: Making trade with edge {best_edge:.2f}")

                    # --- PnL Calculation with Daily Risk Budget ---
                    bin_lower_f, bin_upper_f = bin_edges_f[best_bin_index], bin_edges_f[best_bin_index+1]
                    actual_outcome = int(bin_lower_f <= actual_max_temp < bin_upper_f)
                    
                    ABSOLUTE_MAX_RISK = 0.05
                    # Use capital at START of day for risk calculation
                    capital_to_risk = capital_at_start_of_day * min(MAX_RISK_PER_TRADE, ABSOLUTE_MAX_RISK)

                    if best_edge_type == 'buy':
                        price_per_contract_dollars = market_price / 100.0
                        if price_per_contract_dollars <= 0: continue
                        num_contracts = capital_to_risk / price_per_contract_dollars
                        pnl = num_contracts * (1.0 - price_per_contract_dollars) if actual_outcome == 1 else - (num_contracts * price_per_contract_dollars)
                    else: # sell
                        price_per_contract_dollars = (100.0 - market_price) / 100.0
                        if price_per_contract_dollars <= 0: continue
                        num_contracts = capital_to_risk / price_per_contract_dollars
                        pnl = num_contracts * (1.0 - price_per_contract_dollars) if actual_outcome == 0 else - (num_contracts * price_per_contract_dollars)

                    # Apply stop-loss
                    MAX_LOSS_PER_TRADE = 0.5 * capital_to_risk
                    if abs(pnl) > MAX_LOSS_PER_TRADE:
                        pnl = -MAX_LOSS_PER_TRADE
                    
                    daily_pnl += pnl
            
            # --- End of Day Capital Update & Logging ---
            if daily_pnl != 0:
                self.capital += daily_pnl
                self.trade_log.append({
                    'date': date,
                    'capital': self.capital,
                    'pnl': daily_pnl
                })
                logger.info(f"{date.date()}: Day's trades completed. Daily PnL: {daily_pnl:.2f}, New capital: {self.capital:.2f}")

    def _create_prediction_row(self, features_df: pd.DataFrame, current_idx: int) -> pd.DataFrame:
        """
        Create a proper prediction row for the current date, shifting lagged features.
        This mirrors the logic in trader.py.
        """
        if current_idx == 0:
            return None  # Need at least one previous day
            
        # Get yesterday's features
        yesterday_features = features_df.iloc[current_idx - 1].copy()
        today_prediction_row = yesterday_features.copy()
        
        # Update calendar-based features to reflect today
        current_date = features_df.iloc[current_idx]['date']
        if 'day_of_year' in today_prediction_row:
            today_prediction_row['day_of_year'] = current_date.timetuple().tm_yday
        if 'month' in today_prediction_row:
            today_prediction_row['month'] = current_date.month
        if 'day_of_week' in today_prediction_row:
            today_prediction_row['day_of_week'] = current_date.weekday()
        if 'is_weekend' in today_prediction_row:
            today_prediction_row['is_weekend'] = int(current_date.weekday() >= 5)
        if 'is_summer' in today_prediction_row:
            today_prediction_row['is_summer'] = int(current_date.month in [6, 7, 8])
        if 'is_winter' in today_prediction_row:
            today_prediction_row['is_winter'] = int(current_date.month in [12, 1, 2])

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
        
        return prediction_features
        
    def _calculate_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates key performance metrics from the trade log."""
        if trades_df.empty:
            return {"message": "No trades were made."}
            
        metrics = {}
        equity = pd.concat([pd.Series([self.initial_capital]), trades_df['capital']]).reset_index(drop=True)
        
        metrics['total_return_pct'] = (equity.iloc[-1] / self.initial_capital - 1) * 100
        metrics['num_trades'] = len(trades_df)
        
        # Calculate Drawdown
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max
        metrics['max_drawdown_pct'] = abs(drawdown.min()) * 100
        
        # Calculate Sharpe Ratio (annualized)
        daily_returns = trades_df.set_index('date')['pnl'] / trades_df.set_index('date')['capital'].shift(1).fillna(self.initial_capital)
        if daily_returns.std() > 0:
            metrics['sharpe_ratio'] = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        else:
            metrics['sharpe_ratio'] = 0.0

        metrics['win_rate_pct'] = (trades_df['pnl'] > 0).mean() * 100
        
        return metrics
        
    def plot_results(self, trades_df: pd.DataFrame, metrics: Dict[str, Any]):
        """Generates and displays all performance visualizations."""
        if trades_df.empty:
            logger.info("No trades to plot.")
            return
            
        sns.set_style("whitegrid")
        plt.figure(figsize=(20, 12))
        
        # --- 1. Equity Curve ---
        ax1 = plt.subplot(2, 2, 1)
        equity_series = pd.concat([pd.Series([self.initial_capital], index=[trades_df['date'].min() - timedelta(days=1)]), trades_df.set_index('date')['capital']])
        ax1.plot(equity_series.index, equity_series, label='Equity', color='navy')
        ax1.set_title('Equity Curve', fontsize=16)
        ax1.set_ylabel('Portfolio Value ($)')
        
        # --- 2. Drawdown Plot ---
        ax2 = plt.subplot(2, 2, 2)
        equity = equity_series.reset_index(drop=True)
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max.replace(0, np.nan) * 100
        ax2.fill_between(equity_series.index, drawdown, 0, color='red', alpha=0.3)
        ax2.set_title('Drawdown Curve', fontsize=16)
        ax2.set_ylabel('Drawdown (%)')

        # --- 3. Monthly P&L Bar Chart ---
        ax3 = plt.subplot(2, 1, 2)
        monthly_pnl = trades_df.set_index('date')['pnl'].resample('ME').sum()
        monthly_pnl.plot(kind='bar', ax=ax3, color=(monthly_pnl > 0).map({True: 'g', False: 'r'}), alpha=0.7)
        ax3.set_title('Monthly P&L', fontsize=16)
        ax3.set_ylabel('Profit / Loss ($)')
        ax3.tick_params(axis='x', rotation=45)
        
        plt.suptitle(f"Backtest Performance Results\n"
                     f"Total Return: {metrics.get('total_return_pct', 0):.2f}% | Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}% | Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}",
                     fontsize=20)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()

    def _save_backtest_results(self, results: Dict[str, Any], trades: pd.DataFrame):
        """Saves backtest metrics and trade log to files."""
        os.makedirs('backtests', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save metrics
        metrics_filename = f"backtests/backtest_metrics_{timestamp}.json"
        with open(metrics_filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save trade log
        if not trades.empty:
            trades.to_csv(f"backtests/trade_log_{timestamp}.csv", index=False)
            
        logger.info(f"Backtest results saved with timestamp {timestamp}")