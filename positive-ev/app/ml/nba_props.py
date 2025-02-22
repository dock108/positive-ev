import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
import logging
from pathlib import Path

class NBAPropsPredictor:
    """Class to handle NBA props predictions using trained models."""
    
    def __init__(self):
        """Initialize the predictor with trained models and scalers."""
        self.model_dir = Path("models")
        self.logger = logging.getLogger(__name__)
        
        # Load the latest models and scalers
        try:
            self.model = joblib.load(self.model_dir / "logistic_model_20250206_114800.joblib")
            self.scaler = joblib.load(self.model_dir / "scaler_20250206_114800.joblib")
            
            # Load feature names
            with open(self.model_dir / "feature_names_20250206_114800.txt") as f:
                self.feature_names = [line.strip() for line in f.readlines()]
                
            self.logger.info("Successfully loaded NBA props prediction models")
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
            raise
    
    def prepare_features(self, prop_data):
        """Prepare features for model prediction."""
        features = {}
        
        try:
            # Time-based features
            event_time = datetime.strptime(prop_data['event_time'], '%Y-%m-%d %H:%M:%S')
            current_time = datetime.strptime(prop_data['timestamp'], '%Y-%m-%d %H:%M:%S')
            time_to_event = (event_time - current_time).total_seconds() / 3600
            features['time_log'] = np.log1p(time_to_event)
            
            # Player performance features
            stats = prop_data.get('stats', {})
            for feature in self.feature_names:
                if feature in stats:
                    features[feature] = stats[feature]
                elif feature.endswith(('_avg', '_std', '_consistency', '_trend')):
                    # If we don't have the stat, use a default value
                    features[feature] = 0.0
            
            # Line movement features
            features['line_movement_direction'] = 0  # Default to no movement
            
            # EV and CLV features
            features['ev_by_clv_by_time'] = prop_data.get('ev_percent', 0) / (time_to_event + 1)
            
            # Rolling win rate (default to neutral)
            features['rolling_win_rate'] = 0.5
            
        except Exception as e:
            self.logger.error(f"Error preparing features: {e}")
            raise
        
        return features
    
    def predict(self, prop_data):
        """Make predictions for a prop bet."""
        try:
            # Prepare features
            features = self.prepare_features(prop_data)
            
            # Create feature vector in correct order
            feature_vector = np.array([features.get(f, 0) for f in self.feature_names]).reshape(1, -1)
            
            # Scale features
            scaled_features = self.scaler.transform(feature_vector)
            
            # Make prediction
            win_probability = self.model.predict_proba(scaled_features)[0][1]
            
            # Get feature importances for this prediction
            importances = dict(zip(self.feature_names, 
                                 self.model.coef_[0] * scaled_features[0]))
            
            # Sort features by absolute importance
            top_features = sorted(importances.items(), 
                                key=lambda x: abs(x[1]), 
                                reverse=True)[:5]
            
            return {
                'win_probability': win_probability,
                'confidence_score': abs(win_probability - 0.5) * 200,  # 0 to 100 scale
                'top_features': top_features,
                'prediction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            self.logger.error(f"Error making prediction: {e}")
            return None
    
    def batch_predict(self, props_data):
        """Make predictions for multiple props."""
        predictions = {}
        for prop_id, prop_data in props_data.items():
            try:
                prediction = self.predict(prop_data)
                if prediction:
                    predictions[prop_id] = prediction
            except Exception as e:
                self.logger.error(f"Error predicting for prop {prop_id}: {e}")
                continue
        return predictions 