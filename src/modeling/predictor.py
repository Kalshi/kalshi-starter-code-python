"""
XGBoost-based Weather Predictor for Philadelphia
"""

import logging
import pandas as pd
import joblib
import numpy as np
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WeatherPredictor:
    """XGBoost-based predictor for Philadelphia weather outcomes."""
    
    def __init__(self):
        """Initialize the predictor."""
        self.model = None
        self.feature_columns = None
    
    def load_model(self, model_path: str) -> None:
        """
        Load a trained XGBoost model from disk.
        
        Args:
            model_path: Path to the saved model
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
            
        self.model = joblib.load(model_path)
        logger.info(f"XGBoost model loaded from {model_path}")
    
    def predict_proba(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        Make probability predictions using the loaded XGBoost model.
        
        Args:
            features_df: DataFrame with features
            
        Returns:
            Array of prediction probabilities
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")
        
        # Ensure we only use the features the model was trained on
        if hasattr(self.model, 'feature_names_in_'):
            feature_columns = self.model.feature_names_in_
            # Select only the columns the model expects
            features_df = features_df[feature_columns].copy()
        
        # Handle missing values
        features_df = features_df.fillna(0)
        
        # Convert to numeric
        features_df = features_df.apply(pd.to_numeric, errors='coerce').fillna(0)
        
        # Make probability predictions
        probabilities = self.model.predict_proba(features_df)
        return probabilities
    
    def predict(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        Make binary predictions using the loaded XGBoost model.
        
        Args:
            features_df: DataFrame with features
            
        Returns:
            Array of binary predictions
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")
        
        # Ensure we only use the features the model was trained on
        if hasattr(self.model, 'feature_names_in_'):
            feature_columns = self.model.feature_names_in_
            # Select only the columns the model expects
            features_df = features_df[feature_columns].copy()
        
        # Handle missing values
        features_df = features_df.fillna(0)
        
        # Convert to numeric
        features_df = features_df.apply(pd.to_numeric, errors='coerce').fillna(0)
        
        # Make predictions
        predictions = self.model.predict(features_df)
        
        # Ensure predictions are in [0, 1] range for probabilities
        predictions = np.clip(predictions, 0, 1)
        
        return predictions
    

