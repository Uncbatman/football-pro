"""
Analytics engine for model learning and performance tracking.
Implements Bayesian updating and Brier Score calculation.
"""

from typing import Dict, List, Tuple
from datetime import datetime
import logging
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrierScoreCalculator:
    """
    Calculates Brier Score to measure prediction accuracy.
    
    Brier Score = mean((predicted_prob - actual_outcome)^2)
    - 0.0 = perfect predictions
    - 0.25 = random guessing
    - 1.0 = worst possible predictions
    
    Lower is better.
    """
    
    @staticmethod
    def calculate(predictions: List[float], outcomes: List[int]) -> float:
        """
        Calculate Brier Score for a set of predictions.
        
        Args:
            predictions: List of predicted probabilities (0-1)
            outcomes: List of actual outcomes (0 or 1)
            
        Returns:
            Brier Score (0-1, lower is better)
        """
        if len(predictions) != len(outcomes):
            raise ValueError("Predictions and outcomes must have same length")
        
        if not predictions:
            return 0.0
        
        squared_errors = [
            (pred - outcome) ** 2 
            for pred, outcome in zip(predictions, outcomes)
        ]
        
        return sum(squared_errors) / len(squared_errors)
    
    @staticmethod
    def calculate_by_category(
        match_results: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate Brier Score broken down by match category.
        
        Args:
            match_results: List of result dicts with predictions and outcomes
            
        Returns:
            Dict with overall score and per-category scores
        """
        overall_predictions = []
        overall_outcomes = []
        
        category_scores = {}
        
        for result in match_results:
            # For "home win" probability
            home_win_pred = result['predictions']['home_win']
            home_win_actual = 1 if result['actual_outcome'] == 'home_win' else 0
            
            overall_predictions.append(home_win_pred)
            overall_outcomes.append(home_win_actual)
            
            # Track by team
            team_key = f"team_{result['home_team']}"
            if team_key not in category_scores:
                category_scores[team_key] = {'predictions': [], 'outcomes': []}
            category_scores[team_key]['predictions'].append(home_win_pred)
            category_scores[team_key]['outcomes'].append(home_win_actual)
        
        results = {
            'overall': BrierScoreCalculator.calculate(
                overall_predictions,
                overall_outcomes
            )
        }
        
        # Calculate per-category scores
        for category, data in category_scores.items():
            results[category] = BrierScoreCalculator.calculate(
                data['predictions'],
                data['outcomes']
            )
        
        return results


class BayesianUpdater:
    """
    Implements Bayesian updating for continuous model refinement.
    Updates model beliefs based on prediction surprises.
    """
    
    def __init__(self, prior_confidence: float = 0.8):
        """
        Initialize Bayesian updater.
        
        Args:
            prior_confidence: Initial confidence in model (0-1)
        """
        self.prior_confidence = prior_confidence
        self.posterior_confidence = prior_confidence
        self.update_history = []
    
    def calculate_surprise(
        self,
        predicted_prob: float,
        actual_outcome: bool
    ) -> float:
        """
        Calculate surprise magnitude (prediction error).
        
        Surprise = |predicted_prob - actual_outcome|
        
        Args:
            predicted_prob: Predicted probability (0-1)
            actual_outcome: Actual outcome (True/False)
            
        Returns:
            Surprise value (0-1, where 0 = perfectly predicted)
        """
        actual_prob = 1.0 if actual_outcome else 0.0
        return abs(predicted_prob - actual_prob)
    
    def update_belief(
        self,
        predicted_prob: float,
        actual_outcome: bool
    ) -> float:
        """
        Update model belief based on prediction result.
        Uses Bayesian logic: if surprised, reduce confidence; if correct, increase.
        
        Args:
            predicted_prob: Predicted probability
            actual_outcome: Actual outcome (True/False)
            
        Returns:
            Updated confidence level
        """
        surprise = self.calculate_surprise(predicted_prob, actual_outcome)
        
        # Bayesian update: surprise reduces confidence
        # Maximum surprise (0.5 prob, opposite outcome) reduces confidence most
        confidence_adjustment = (0.5 - surprise) * 0.1  # Max 5% change per update
        
        self.posterior_confidence = max(
            0.1,  # Never go below 10% confidence
            min(
                0.95,  # Never exceed 95% confidence
                self.posterior_confidence + confidence_adjustment
            )
        )
        
        self.update_history.append({
            'timestamp': datetime.now().isoformat(),
            'predicted_prob': predicted_prob,
            'actual_outcome': actual_outcome,
            'surprise': surprise,
            'posterior': self.posterior_confidence
        })
        
        return self.posterior_confidence
    
    def batch_update(self, match_results: List[Dict]) -> float:
        """
        Update belief based on multiple match results.
        
        Args:
            match_results: List of dicts with predictions and outcomes
            
        Returns:
            New confidence level
        """
        for result in match_results:
            self.update_belief(
                result['predictions']['home_win'],
                result['actual_outcome'] == 'home_win'
            )
        
        return self.posterior_confidence
    
    def get_confidence(self) -> float:
        """Get current model confidence."""
        return self.posterior_confidence


class ClosingLineValueCalculator:
    """
    Calculates Closing Line Value (CLV) to measure market alpha.
    
    CLV measures whether you beat the closing odds with your opening bet.
    This is the gold standard metric for evaluating betting skill.
    
    CLV Formula: ((opening_odds / closing_odds) - 1) × 100
    - CLV > 0%: You beat the closing line (market moved in your favor)
    - CLV < 0%: You lost to the closing line (market moved against you)
    - CLV > 2-3%: Statistically significant edge
    """
    
    @staticmethod
    def calculate_clv(opening_odds: float, closing_odds: float) -> float:
        """
        Calculate Closing Line Value as a percentage.
        
        Formula: ((opening / closing) - 1) × 100
        
        Args:
            opening_odds: The odds at which you placed your bet
            closing_odds: The final odds before the match starts
            
        Returns:
            CLV as a percentage (e.g., 2.5 for +2.5% CLV)
        """
        if closing_odds <= 0:
            return 0.0
        
        return ((opening_odds / closing_odds) - 1) * 100
    
    @staticmethod
    def batch_calculate_clv(match_results: List[Dict]) -> Dict:
        """
        Calculate CLV statistics across multiple matches.
        
        Args:
            match_results: List of dicts with 'opening_odds' and 'closing_odds'
            
        Returns:
            Dict with overall CLV, per-market breakdown, and statistical summary
        """
        if not match_results:
            return {
                'total_matches': 0,
                'average_clv': 0.0,
                'winning_clv_matches': 0,
                'losing_clv_matches': 0,
                'clv_distribution': {}
            }
        
        clv_values = []
        for result in match_results:
            clv = ClosingLineValueCalculator.calculate_clv(
                result['opening_odds'],
                result['closing_odds']
            )
            clv_values.append(clv)
        
        average_clv = sum(clv_values) / len(clv_values) if clv_values else 0
        winning_clv = sum(1 for clv in clv_values if clv > 0)
        losing_clv = sum(1 for clv in clv_values if clv <= 0)
        
        return {
            'total_matches': len(clv_values),
            'average_clv': average_clv,
            'winning_clv_matches': winning_clv,
            'losing_clv_matches': losing_clv,
            'clv_values': clv_values,
            'statistical_significance': 'YES' if average_clv > 2.5 else 'NO'
        }
    
    @staticmethod
    def evaluate_clv_edge(average_clv: float, sample_size: int) -> Dict:
        """
        Determine if CLV provides statistically significant edge.
        
        Args:
            average_clv: Average CLV across matches
            sample_size: Number of matches analyzed
            
        Returns:
            Dict with edge assessment and confidence
        """
        # Rough confidence threshold: 2.5% CLV with 20+ matches is significant
        is_significant = average_clv > 2.5 and sample_size >= 20
        
        return {
            'average_clv': average_clv,
            'sample_size': sample_size,
            'is_significant': is_significant,
            'recommendation': (
                'Betting model shows edge. Continue with current approach.'
                if is_significant
                else 'Insufficient edge. Recalibrate model or reduce stakes.'
            )
        }



    """
    Analyzes prediction surprises to identify patterns and weaknesses.
    """
    
    def __init__(self):
        self.analyses = []
    
    def analyze_match(self, match_result: Dict) -> Dict:
        """
        Analyze a single match result for surprises.
        
        Args:
            match_result: Dict with match info, predictions, and outcome
            
        Returns:
            Analysis report
        """
        predictions = match_result['predictions']
        outcome = match_result['actual_outcome']
        
        # Determine which prediction was correct
        correct_pred = None
        if outcome == 'home_win':
            correct_pred = 'home_win'
            correct_prob = predictions['home_win']
        elif outcome == 'away_win':
            correct_pred = 'away_win'
            correct_prob = predictions['away_win']
        else:
            correct_pred = 'draw'
            correct_prob = predictions['draw']
        
        # Calculate surprise
        surprise = 1 - correct_prob if correct_prob > 0 else 1.0
        
        analysis = {
            'match': f"{match_result['home_team']} vs {match_result['away_team']}",
            'home_team': match_result['home_team'],
            'away_team': match_result['away_team'],
            'actual_outcome': outcome,
            'correct_prediction': correct_pred,
            'confidence_in_correct': correct_prob,
            'surprise_magnitude': surprise,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add team stats for analysis
        if 'home_stats' in match_result:
            analysis['home_stats'] = match_result['home_stats']
        if 'away_stats' in match_result:
            analysis['away_stats'] = match_result['away_stats']
        
        self.analyses.append(analysis)
        return analysis
    
    def get_biggest_surprises(self, n: int = 10) -> List[Dict]:
        """
        Get the n biggest prediction surprises.
        
        Args:
            n: Number of surprises to return
            
        Returns:
            Sorted list of biggest surprises
        """
        sorted_analyses = sorted(
            self.analyses,
            key=lambda x: x['surprise_magnitude'],
            reverse=True
        )
        return sorted_analyses[:n]
    
    def get_team_accuracy(self, team_name: str) -> Dict:
        """
        Get prediction accuracy for a specific team.
        
        Args:
            team_name: Name of team to analyze
            
        Returns:
            Accuracy statistics for team
        """
        team_analyses = [
            a for a in self.analyses
            if a['home_team'].lower() == team_name.lower() or
               a['away_team'].lower() == team_name.lower()
        ]
        
        if not team_analyses:
            return {'team': team_name, 'matches': 0}
        
        avg_surprise = sum(a['surprise_magnitude'] for a in team_analyses) / len(team_analyses)
        avg_confidence = sum(a['confidence_in_correct'] for a in team_analyses) / len(team_analyses)
        
        return {
            'team': team_name,
            'matches_analyzed': len(team_analyses),
            'avg_surprise': avg_surprise,
            'avg_confidence': avg_confidence,
            'prediction_quality': 1 - avg_surprise  # Higher is better
        }
    
    def get_summary(self) -> Dict:
        """
        Get overall summary of prediction performance.
        
        Returns:
            Summary statistics
        """
        if not self.analyses:
            return {'total_matches': 0}
        
        avg_surprise = sum(a['surprise_magnitude'] for a in self.analyses) / len(self.analyses)
        avg_confidence = sum(a['confidence_in_correct'] for a in self.analyses) / len(self.analyses)
        
        return {
            'total_matches_analyzed': len(self.analyses),
            'avg_surprise_magnitude': avg_surprise,
            'avg_confidence_in_correct': avg_confidence,
            'overall_accuracy': 1 - avg_surprise,
            'biggest_surprise': max(a['surprise_magnitude'] for a in self.analyses),
            'timestamp': datetime.now().isoformat()
        }
