"""
Value detection engine for identifying profitable betting opportunities.
Uses Expected Value (EV) calculation to find market inefficiencies.
"""

from typing import Dict, Tuple, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValueDetector:
    """
    Identifies value betting opportunities by comparing predicted probabilities
    against market odds using Expected Value calculation.
    
    EV Formula: EV = (Odds × Probability) - 1
    Positive EV indicates a profitable bet (on average).
    """
    
    # Minimum EV threshold for recommendations
    MIN_EV_THRESHOLD = 0.05  # 5% edge
    
    def __init__(self, min_ev: float = MIN_EV_THRESHOLD):
        """
        Initialize value detector.
        
        Args:
            min_ev: Minimum EV threshold to consider a bet as valuable
        """
        self.min_ev = min_ev
    
    def calculate_ev(
        self, 
        decimal_odds: float, 
        probability: float
    ) -> float:
        """
        Calculate Expected Value for a single bet.
        
        EV = (Odds × Probability) - 1
        - EV > 0: Profitable bet (on average)
        - EV < 0: Losing bet (on average)
        - EV = 0: Fair value
        
        Args:
            decimal_odds: Decimal odds for the outcome (e.g., 2.10)
            probability: Predicted probability (0-1)
            
        Returns:
            EV as a decimal (-1 to infinity)
        """
        if not (0 < decimal_odds and 0 <= probability <= 1):
            raise ValueError(f"Invalid odds ({decimal_odds}) or probability ({probability})")
        
        return (decimal_odds * probability) - 1
    
    def implied_probability(self, decimal_odds: float) -> float:
        """
        Convert decimal odds to implied probability.
        
        Implied Prob = 1 / Decimal Odds
        
        Args:
            decimal_odds: Decimal odds
            
        Returns:
            Implied probability (0-1)
        """
        if decimal_odds <= 0:
            raise ValueError(f"Invalid odds: {decimal_odds}")
        return 1.0 / decimal_odds
    
    def is_value_bet(
        self, 
        decimal_odds: float, 
        probability: float
    ) -> bool:
        """
        Determine if a bet has positive expected value.
        
        Args:
            decimal_odds: Market decimal odds
            probability: Predicted probability
            
        Returns:
            True if EV > min_ev threshold
        """
        ev = self.calculate_ev(decimal_odds, probability)
        return ev > self.min_ev
    
    def analyze_match(
        self,
        home_team: str,
        away_team: str,
        predictions: Dict[str, float],
        market_odds: Dict[str, float]
    ) -> Dict:
        """
        Analyze a single match for value opportunities across all outcomes.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            predictions: Dict with 'home_win', 'draw', 'away_win' probabilities
            market_odds: Dict with 'home', 'draw', 'away' decimal odds
            
        Returns:
            Analysis dict with EV, implied probs, and recommendations
        """
        home_ev = self.calculate_ev(market_odds['home'], predictions['home_win'])
        draw_ev = self.calculate_ev(market_odds['draw'], predictions['draw'])
        away_ev = self.calculate_ev(market_odds['away'], predictions['away_win'])
        
        home_implied = self.implied_probability(market_odds['home'])
        draw_implied = self.implied_probability(market_odds['draw'])
        away_implied = self.implied_probability(market_odds['away'])
        
        opportunities = []
        
        if self.is_value_bet(market_odds['home'], predictions['home_win']):
            opportunities.append({
                'outcome': f"{home_team} Win",
                'odds': market_odds['home'],
                'ev': home_ev,
                'confidence': predictions['home_win']
            })
        
        if self.is_value_bet(market_odds['draw'], predictions['draw']):
            opportunities.append({
                'outcome': 'Draw',
                'odds': market_odds['draw'],
                'ev': draw_ev,
                'confidence': predictions['draw']
            })
        
        if self.is_value_bet(market_odds['away'], predictions['away_win']):
            opportunities.append({
                'outcome': f"{away_team} Win",
                'odds': market_odds['away'],
                'ev': away_ev,
                'confidence': predictions['away_win']
            })
        
        return {
            'match': f"{home_team} vs {away_team}",
            'predictions': predictions,
            'market_odds': market_odds,
            'implied_probabilities': {
                'home_win': home_implied,
                'draw': draw_implied,
                'away_win': away_implied
            },
            'expected_values': {
                'home_win': home_ev,
                'draw': draw_ev,
                'away_win': away_ev
            },
            'value_opportunities': opportunities,
            'has_value': len(opportunities) > 0
        }
    
    def analyze_batch(
        self,
        matches: List[Dict]
    ) -> List[Dict]:
        """
        Analyze multiple matches for value opportunities.
        
        Args:
            matches: List of match dicts with home_team, away_team, predictions, market_odds
            
        Returns:
            List of analysis dicts
        """
        results = []
        for match in matches:
            analysis = self.analyze_match(
                match['home_team'],
                match['away_team'],
                match['predictions'],
                match['market_odds']
            )
            results.append(analysis)
        return results
    
    def rank_by_ev(self, analyses: List[Dict]) -> List[Dict]:
        """
        Rank match analyses by highest EV opportunity.
        
        Args:
            analyses: List of analysis dicts from analyze_batch
            
        Returns:
            Sorted list (highest EV first)
        """
        def get_best_ev(analysis):
            if not analysis['value_opportunities']:
                return -1
            return max(opp['ev'] for opp in analysis['value_opportunities'])
        
        return sorted(analyses, key=get_best_ev, reverse=True)
