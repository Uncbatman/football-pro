import os
from dotenv import load_dotenv

load_dotenv()

def calculate_kelly(prob, odds, keystone_missing=False):
    """
    Calculate Kelly Criterion with Keystone Variance Buffer.
    
    Args:
        prob: Probability of winning (0-1)
        odds: Decimal odds
        keystone_missing: If True, reduces probability by 5% for key personnel absence
    
    Returns:
        Optimal bet fraction (0-1), reduced to 25% Kelly for safety
    """
    # Variance Buffer: Reduce probability by 5% if key personnel are missing
    p = (prob - 0.05) if keystone_missing else prob
    q = 1 - p
    b = odds - 1
    
    kelly_f = (b * p - q) / b
    return max(0, kelly_f * 0.25)  # Quarter Kelly for survival

def scan_market():
    """
    Scan the betting market for value opportunities.
    
    Workflow:
    1. Fetch upcoming matches from football-data API
    2. Run prediction model (.pkl) to get probabilities
    3. Calculate optimal stake with calculate_kelly()
    4. Upsert results to 'live_predictions' table
    """
    # Implementation will integrate with:
    # - prediction_engine.py for model inference
    # - value_detection.py for EV calculation
    # - risk_management.py for stake sizing
    pass

if __name__ == "__main__":
    scan_market()
