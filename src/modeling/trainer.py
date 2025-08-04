"""
XGBoost-based Weather Model Trainer for Philadelphia
"""

import logging
import pandas as pd
import numpy as np
import joblib
import os
from typing import Any, Dict, Tuple
from datetime import datetime
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss

logger = logging.getLogger(__name__)


class WeatherModelTrainer:
    """XGBoost-based trainer for Philadelphia weather prediction models."""
    
    def __init__(self, model_params: Dict = None):
        """
        Initialize the trainer with XGBoost parameters.
        
        Args:
            model_params: Dictionary of XGBoost parameters
        """
        self.model_params = model_params or {
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42
        }
    
    def train_model(self, features_df: pd.DataFrame, target_column: str) -> Tuple[Any, Dict]:
        """
        Train an XGBoost model for Philadelphia weather prediction.
        
        Args:
            features_df: DataFrame with features
            target_column: Name of the target column
            
        Returns:
            Tuple of (trained model, training metrics)
        """
        logger.info(f"Training XGBoost model for target: {target_column}")
        
        # Prepare features and target
        if target_column not in features_df.columns:
            raise ValueError(f"Target column '{target_column}' not found in DataFrame")
        
        # Remove rows with missing target values
        df = features_df.dropna(subset=[target_column])
        
        # Explicitly remove columns that introduce data leakage (values only known after prediction time)
        leaky_columns = [
            'max_temp', 'min_temp', 'max_temp_f', 'min_temp_f',
            'max_temp_above_avg', 'min_temp_above_avg', 'temp_range', 'temp_mean',
            'above_80F', 'above_90F', 'above_95F', 'above_98F', 'below_32F', 'below_20F',
            'had_precipitation', 'heavy_precipitation', 'precipitation', 'precipitation_inches',
            'is_rainy_day', 'is_dry_day', 'date', target_column
        ]
        X = df.drop(columns=[c for c in leaky_columns if c in df.columns], errors='ignore')
        y = df[target_column]
        
        # Store feature list for metrics/importance tracking
        feature_columns = X.columns.tolist()
        
        # Handle missing values in features
        X = X.fillna(0)  # Simple imputation
        
        # Convert to numeric
        X = X.apply(pd.to_numeric, errors='coerce').fillna(0)
        y = pd.to_numeric(y, errors='coerce').fillna(0)
        
        
        
        # Split data (no stratification for regression)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train XGBoost model
        model = xgb.XGBRegressor(**self.model_params)
        model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test)
        from sklearn.metrics import mean_squared_error
        import numpy as np
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        
        # Cross-validation RMSE
        cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='neg_root_mean_squared_error')
        cv_rmse_mean = (-cv_scores).mean()
        cv_rmse_std = (-cv_scores).std()
        
        metrics = {
            'rmse': rmse,
            'cv_mean_rmse': cv_rmse_mean,
            'cv_std_rmse': cv_rmse_std,
            'n_samples': len(X),
            'n_features': len(feature_columns)
        }
        
        logger.info(f"Model trained with {len(X)} samples and {len(feature_columns)} features")
        logger.info(f"Test RMSE: {rmse:.4f}")
        logger.info(f"CV RMSE: {cv_rmse_mean:.4f} (+/- {cv_rmse_std * 2:.4f})")
        
        # Save feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        logger.info("Top 10 most important features:")
        for i, row in feature_importance.head(10).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")
        
        # Save model and metrics
        os.makedirs('models', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f"models/philly_weather_xgb_regressor_{target_column}_{timestamp}.joblib"
        metrics_filename = f"models/philly_weather_metrics_{target_column}_{timestamp}.json"
        
        joblib.dump({'model': model, 'rmse': rmse}, model_filename)
        feature_importance.to_csv(f"models/philly_feature_importance_regressor_{target_column}_{timestamp}.csv", index=False)
        
        # Save metrics
        import json
        with open(metrics_filename, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Model saved to {model_filename}")
        logger.info(f"Metrics saved to {metrics_filename}")
        logger.info(f"Feature importance saved to models/philly_feature_importance_{target_column}_{timestamp}.csv")
        
        return model, metrics
    
    def save_model(self, model: Any, filepath: str) -> None:
        """
        Save a trained model to disk.
        
        Args:
            model: Trained model
            filepath: Path to save model
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(model, filepath)
        logger.info(f"Model saved to {filepath}")
