"""
Core prediction engine for football match outcomes.
Handles model management, probability generation, and prediction utilities.
"""

import pickle
import pandas as pd
from sklearn.linear_model import LogisticRegression
from typing import Tuple, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    Main prediction engine for football matches.
    Loads trained model and generates probability predictions.
    """
    
    def __init__(self, model_path: str = 'football_model.pkl'):
        """
        Initialize prediction engine with trained model.
        
        Args:
            model_path: Path to serialized model file
        """
        self.model_path = model_path
        self.model = None
        self.load_model()
    
    def load_model(self) -> None:
        """Load trained model from disk."""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            logger.info(f"Model loaded successfully from {self.model_path}")
        except FileNotFoundError:
            logger.error(f"Model file not found at {self.model_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def predict_match(
        self, 
        home_avg_goals: float, 
        away_avg_conceded: float
    ) -> Dict[str, float]:
        """
        Generate probability predictions for a match.
        
        Args:
            home_avg_goals: Home team's average goals scored
            away_avg_conceded: Away team's average goals conceded
            
        Returns:
            Dictionary with probabilities for each outcome:
            {
                'draw': float (0-1),
                'home_win': float (0-1),
                'away_win': float (0-1)
            }
        """
        if not self.model:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        input_df = pd.DataFrame(
            [[home_avg_goals, away_avg_conceded]], 
            columns=["home_goals", "away_goals"]
        )
        
        probs = self.model.predict_proba(input_df)[0]
        
        return {
            'draw': probs[0],
            'home_win': probs[1],
            'away_win': probs[2]
        }
    
    def predict_batch(
        self, 
        matches: List[Tuple[float, float]]
    ) -> List[Dict[str, float]]:
        """
        Generate predictions for multiple matches.
        
        Args:
            matches: List of tuples (home_avg_goals, away_avg_conceded)
            
        Returns:
            List of prediction dictionaries
        """
        results = []
        for home_goals, away_conceded in matches:
            pred = self.predict_match(home_goals, away_conceded)
            results.append(pred)
        return results
    
    def get_model_confidence(self) -> float:
        """
        Get a measure of model confidence (for future enhancement).
        Currently returns 1.0 (neutral confidence).
        
        Returns:
            Confidence score between 0 and 1
        """
        # Future: Calculate based on training accuracy, recency, etc.
        return 1.0


class PredictionCache:
    """Cache predictions to avoid redundant model calls."""
    
    def __init__(self):
        self.cache = {}
    
    def get(self, key: str) -> Dict[str, float] | None:
        """Retrieve cached prediction."""
        return self.cache.get(key)
    
    def set(self, key: str, predictions: Dict[str, float]) -> None:
        """Cache a prediction."""
        self.cache[key] = predictions
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
