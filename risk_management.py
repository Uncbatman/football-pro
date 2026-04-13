"""
Risk management and bankroll optimization using Kelly Criterion.
Prevents ruin and ensures long-term survival in betting operations.
"""

from typing import Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KellyCalculator:
    """
    Implements the Kelly Criterion for optimal bet sizing.
    
    Kelly Formula: f* = (bp - q) / b
    where:
        - f* = fraction of bankroll to bet
        - b = decimal odds - 1
        - p = probability of winning
        - q = probability of losing (1 - p)
    
    The Kelly Criterion maximizes long-term wealth while minimizing ruin risk.
    """
    
    def __init__(self, kelly_fraction: float = 0.25):
        """
        Initialize Kelly Calculator.
        
        Args:
            kelly_fraction: Fraction of full Kelly to use (0.25 = "quarter Kelly", safer)
                           Full Kelly (1.0) is mathematically optimal but risky
                           Fractional Kelly is recommended for real-world betting
        """
        if not (0 < kelly_fraction <= 1):
            raise ValueError("kelly_fraction must be between 0 and 1")
        
        self.kelly_fraction = kelly_fraction
        logger.info(f"Using {kelly_fraction * 100}% Kelly strategy")
    
    def calculate_kelly_fraction(
        self,
        decimal_odds: float,
        probability: float
    ) -> float:
        """
        Calculate the Kelly fraction (bf* value).
        
        f* = (bp - q) / b
        
        Returns negative value if no edge (don't bet).
        
        Args:
            decimal_odds: Decimal odds for the bet
            probability: Predicted probability of winning
            
        Returns:
            Kelly fraction (-1 to 1, where 0 = no bet)
        """
        if not (0 < decimal_odds and 0 <= probability <= 1):
            raise ValueError(f"Invalid odds ({decimal_odds}) or probability ({probability})")
        
        b = decimal_odds - 1  # Odds - 1
        p = probability  # Probability of winning
        q = 1 - probability  # Probability of losing
        
        kelly_frac = (b * p - q) / b if b > 0 else 0
        
        return kelly_frac
    
    def calculate_stake(
        self,
        bankroll: float,
        decimal_odds: float,
        probability: float
    ) -> float:
        """
        Calculate optimal stake amount using fractional Kelly.
        
        Args:
            bankroll: Current bankroll size
            decimal_odds: Decimal odds for the bet
            probability: Predicted probability of winning
            
        Returns:
            Optimal stake amount (0 if no positive Kelly value)
        """
        kelly_frac = self.calculate_kelly_fraction(decimal_odds, probability)
        
        # Apply fractional Kelly (e.g., 0.25 Kelly if kelly_fraction = 0.25)
        stake = bankroll * max(0, kelly_frac * self.kelly_fraction)
        
        return stake
    
    def calculate_multiple_stakes(
        self,
        bankroll: float,
        bets: list
    ) -> list:
        """
        Calculate stakes for multiple concurrent bets.
        Adjusted to ensure total doesn't exceed safe limits.
        
        Args:
            bankroll: Current bankroll
            bets: List of dicts with 'odds' and 'probability'
            
        Returns:
            List of dicts with original bet info + 'stake'
        """
        results = []
        total_stake = 0
        max_total_risk = bankroll * 0.10  # Never risk more than 10% of bankroll
        
        # Calculate individual stakes first
        stakes = []
        for bet in bets:
            stake = self.calculate_stake(
                bankroll,
                bet['odds'],
                bet['probability']
            )
            stakes.append(stake)
        
        total_stake = sum(stakes)
        
        # Scale down if exceeds safe limit
        scale_factor = 1.0
        if total_stake > max_total_risk:
            scale_factor = max_total_risk / total_stake
            logger.warning(
                f"Total stakes ({total_stake:.2f}) exceed safe limit "
                f"({max_total_risk:.2f}). Scaling by {scale_factor:.2f}"
            )
        
        # Build results
        for bet, stake in zip(bets, stakes):
            result = bet.copy()
            result['stake'] = stake * scale_factor
            result['kelly_frac'] = self.calculate_kelly_fraction(
                bet['odds'],
                bet['probability']
            )
            results.append(result)
        
        return results


class BankrollManager:
    """
    Manages bankroll and tracks betting history for risk assessment.
    """
    
    def __init__(self, initial_bankroll: float):
        """
        Initialize bankroll manager.
        
        Args:
            initial_bankroll: Starting bankroll amount
        """
        if initial_bankroll <= 0:
            raise ValueError("Initial bankroll must be positive")
        
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.history = []
    
    def place_bet(self, stake: float, decimal_odds: float, outcome: str) -> Dict:
        """
        Record a placed bet and update bankroll if result is known.
        
        Args:
            stake: Amount staked
            decimal_odds: Decimal odds
            outcome: 'pending', 'won', or 'lost'
            
        Returns:
            Bet record dict
        """
        if stake > self.current_bankroll:
            logger.warning(f"Stake {stake} exceeds bankroll {self.current_bankroll}")
        
        bet_record = {
            'stake': stake,
            'odds': decimal_odds,
            'outcome': outcome,
            'potential_return': stake * decimal_odds,
            'potential_profit': stake * (decimal_odds - 1)
        }
        
        if outcome == 'won':
            self.current_bankroll += stake * (decimal_odds - 1)
            bet_record['result'] = 'WIN'
        elif outcome == 'lost':
            self.current_bankroll -= stake
            bet_record['result'] = 'LOSS'
        else:
            bet_record['result'] = 'PENDING'
        
        self.history.append(bet_record)
        return bet_record
    
    def get_statistics(self) -> Dict:
        """
        Calculate bankroll statistics.
        
        Returns:
            Dict with win rate, ROI, etc.
        """
        if not self.history:
            return {
                'total_bets': 0,
                'wins': 0,
                'losses': 0,
                'pending': 0,
                'win_rate': 0,
                'current_bankroll': self.current_bankroll,
                'initial_bankroll': self.initial_bankroll,
                'roi': 0,
                'profit': 0
            }
        
        wins = sum(1 for b in self.history if b['result'] == 'WIN')
        losses = sum(1 for b in self.history if b['result'] == 'LOSS')
        pending = sum(1 for b in self.history if b['result'] == 'PENDING')
        
        completed = wins + losses
        win_rate = (wins / completed * 100) if completed > 0 else 0
        
        profit = self.current_bankroll - self.initial_bankroll
        roi = (profit / self.initial_bankroll * 100) if self.initial_bankroll > 0 else 0
        
        return {
            'total_bets': len(self.history),
            'wins': wins,
            'losses': losses,
            'pending': pending,
            'win_rate': win_rate,
            'current_bankroll': self.current_bankroll,
            'initial_bankroll': self.initial_bankroll,
            'roi': roi,
            'profit': profit,
            'ruin_risk': self._calculate_ruin_risk()
        }
    
    def _calculate_ruin_risk(self) -> float:
        """
        Estimate risk of bankroll ruin based on recent performance.
        
        Returns:
            Risk percentage (0-100)
        """
        if len(self.history) < 10:
            return 0  # Need more data
        
        recent = self.history[-10:]
        win_rate = sum(1 for b in recent if b['result'] == 'WIN') / 10
        
        # Simple ruin risk: if < 40% win rate, increase risk perception
        if win_rate < 0.40:
            return min(100, (1 - win_rate) * 100)
        
        return max(0, 10 - (win_rate * 10))
