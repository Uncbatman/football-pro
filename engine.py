import numpy as np
from scipy.stats import poisson

def predict_match_probs(h_lambda, a_lambda, max_goals=10):
    """Calculate match outcome probabilities using Double Poisson."""
    h_probs = [poisson.pmf(i, h_lambda) for i in range(max_goals + 1)]
    a_probs = [poisson.pmf(i, a_lambda) for i in range(max_goals + 1)]
    matrix = np.outer(h_probs, a_probs)
    home_win = np.sum(np.tril(matrix, -1))
    draw = np.sum(np.diag(matrix))
    away_win = np.sum(np.triu(matrix, 1))
    return float(home_win), float(draw), float(away_win)

def get_kelly_stake(bankroll, prob, odds, fraction=0.25):
    """Quarter-Kelly stake calculation for risk management."""
    if prob <= 0 or prob >= 1 or odds <= 1:
        return 0.0
    b = odds - 1
    q = 1 - prob
    full_kelly = (b * prob - q) / b
    kelly_stake = bankroll * fraction * full_kelly
    return max(0.0, min(kelly_stake, bankroll * 0.05))

def calculate_expected_value(prob, odds):
    """EV = (Probability * Odds) - 1"""
    if prob <= 0 or odds <= 1:
        return 0.0
    return float((prob * odds) - 1)

def calculate_clv(opening_odds, closing_odds):
    """CLV = (Opening / Closing) - 1"""
    if closing_odds <= 0 or opening_odds <= 0:
        return 0.0
    return float((opening_odds / closing_odds) - 1)

def adjust_for_elo(base_lambda, my_elo, opponent_elo, adjustment_factor=0.0008):
    """Adjust expected goals based on Elo difference."""
    elo_diff = my_elo - opponent_elo
    adjusted = base_lambda * (1 + adjustment_factor * elo_diff)
    return max(0.1, float(adjusted))
