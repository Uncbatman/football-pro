"""
Elo Rating System for Football Teams
Implements strength-based rankings that improve over time based on match results.
"""


def calculate_elo_change(rating_a: float, rating_b: float, actual_score: float, k_factor: float = 32.0) -> float:
    """
    Calculate the new Elo rating for team A after a match against team B.
    
    Args:
        rating_a (float): Current Elo rating of team A
        rating_b (float): Current Elo rating of team B (opponent)
        actual_score (float): Match result from team A's perspective
                             1.0 = Win, 0.5 = Draw, 0.0 = Loss
        k_factor (float): K-factor controlling rating volatility (default 32, standard in chess)
    
    Returns:
        float: New Elo rating for team A
    
    Formula:
        Expected Score = 1 / (1 + 10^((rating_b - rating_a) / 400))
        New Rating = rating_a + K * (actual_score - expected_score)
    
    Example:
        >>> calculate_elo_change(1600, 1400, 1.0, k_factor=32)
        # Team rated 1600 beats team rated 1400: rating increases by ~16 points
    """
    expected_score = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    new_rating = rating_a + k_factor * (actual_score - expected_score)
    return new_rating


def get_adjusted_lambdas(home_avg: float, away_avg: float, home_elo: float, away_elo: float) -> tuple:
    """
    Adjusts the base goal-scoring rates (Poisson lambdas) based on team strength (Elo rating difference).
    
    This prevents "simple averages" from being fooled by outlier scores.
    A stronger team (higher Elo) gets a slightly higher expected goal count.
    
    Args:
        home_avg (float): Home team's average goals scored per match
        away_avg (float): Away team's average goals scored per match
        home_elo (float): Home team's current Elo rating
        away_elo (float): Away team's current Elo rating
    
    Returns:
        tuple: (adjusted_home_lambda, adjusted_away_lambda)
               Both values are floored at 0.1 to ensure non-zero probability
    
    Logic:
        - Calculate Elo difference (positive = home is stronger)
        - Scale by 0.0008 to keep adjustments realistic
        - Home lambda increases if home is stronger
        - Away lambda decreases if home is stronger (and vice versa)
    
    Example:
        >>> get_adjusted_lambdas(1.5, 1.2, 1650, 1550)
        # Home team is 100 Elo points stronger: their lambda increases, away decreases
        (1.56, 1.14)
    """
    # Calculate the 'Quality Gap' between teams
    elo_diff = home_elo - away_elo
    
    # Adjust lambdas: stronger team gets higher lambda, weaker gets lower
    # Scaling factor of 0.0008 keeps adjustments realistic (~0.08 per 100 Elo points)
    home_lambda_adj = home_avg * (1 + (elo_diff * 0.0008))
    away_lambda_adj = away_avg * (1 - (elo_diff * 0.0008))
    
    # Ensure lambdas never drop below 0.1 (teams always have a tiny chance to score)
    return max(0.1, home_lambda_adj), max(0.1, away_lambda_adj)


def update_elo_ratings(home_id: str, away_id: str, result: str, supabase) -> dict:
    """
    Update Elo ratings in Supabase based on match result.
    
    This is the "Maintenance" task that keeps ratings current after each match.
    
    Args:
        home_id (str): Supabase ID of home team
        away_id (str): Supabase ID of away team
        result (str): Match result from home team's perspective
                     'H' = Home Win, 'A' = Away Win, 'D' = Draw
        supabase: Supabase client instance
    
    Returns:
        dict: {
            'home_id': str,
            'away_id': str,
            'old_home_elo': float,
            'new_home_elo': float,
            'old_away_elo': float,
            'new_away_elo': float,
            'elo_change_home': float,
            'elo_change_away': float
        }
    
    Process:
        1. Fetch current Elo ratings from Supabase 'teams' table
        2. Determine match outcome scores (1.0 for win, 0.5 for draw, 0.0 for loss)
        3. Calculate new ratings using Elo formula (K=32)
        4. Push new ratings back to Supabase
    """
    K_FACTOR = 32
    
    # 1. Fetch current Elos from Supabase
    h_data = supabase.table('teams').select("elo_rating").eq("id", home_id).single().execute().data
    a_data = supabase.table('teams').select("elo_rating").eq("id", away_id).single().execute().data
    
    r_h = h_data['elo_rating']
    r_a = a_data['elo_rating']
    
    old_home_elo = r_h
    old_away_elo = r_a
    
    # 2. Determine match outcome for Elo math
    if result == 'H':  # Home win
        s_h, s_a = 1.0, 0.0
    elif result == 'A':  # Away win
        s_h, s_a = 0.0, 1.0
    else:  # Draw
        s_h, s_a = 0.5, 0.5
    
    # 3. Calculate New Ratings
    expected_h = 1 / (1 + 10 ** ((r_a - r_h) / 400))
    expected_a = 1 / (1 + 10 ** ((r_h - r_a) / 400))
    
    new_r_h = r_h + K_FACTOR * (s_h - expected_h)
    new_r_a = r_a + K_FACTOR * (s_a - expected_a)
    
    # 4. Push back to Supabase
    supabase.table('teams').update({"elo_rating": new_r_h}).eq("id", home_id).execute()
    supabase.table('teams').update({"elo_rating": new_r_a}).eq("id", away_id).execute()
    
    return {
        'home_id': home_id,
        'away_id': away_id,
        'old_home_elo': old_home_elo,
        'new_home_elo': new_r_h,
        'old_away_elo': old_away_elo,
        'new_away_elo': new_r_a,
        'elo_change_home': new_r_h - old_home_elo,
        'elo_change_away': new_r_a - old_away_elo
    }
