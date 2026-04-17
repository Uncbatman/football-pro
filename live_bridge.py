import os
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

def calculate_ev(prob, odds):
    # EV = (Probability * Odds) - 1
    return (prob * odds) - 1

def live_value_scanner():
    print("--- 🔍 Scanning Market for Value ---")
    
    # 1. Fetch upcoming matches (Scheduled)
    url = "https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED"
    headers = {'X-Auth-Token': os.getenv("FOOTBALL_DATA_API_KEY")}
    matches = requests.get(url, headers=headers).json().get('matches', [])

    for m in matches:
        home_team = m['homeTeam']['name']
        away_team = m['awayTeam']['name']
        
        # --- THE LOGIC STEP ---
        # In a full setup, your .pkl model would provide 'my_prob'
        # For now, we use a 0.50 baseline for demonstration
        my_prob = 0.55 
        market_odds = 2.10 # This would come from an odds API or manual entry
        
        # Apply Keystone Buffer if a star is out (Manual toggle for now)
        keystone_missing = False 
        if keystone_missing:
            my_prob -= 0.05
            
        edge = calculate_ev(my_prob, market_odds)

        if edge > 0.05: # Only log if Edge > 5%
            payload = {
                "match_id": m['id'],
                "home_team": home_team,
                "away_team": away_team,
                "kickoff_time": m['utcDate'],
                "model_prob": my_prob,
                "market_odds": market_odds,
                "edge_percent": edge * 100
            }
            supabase.table('live_predictions').upsert(payload, on_conflict='match_id').execute()
            print(f"⭐ VALUE FOUND: {home_team} vs {away_team} ({edge*100:.1f}% Edge)")

if __name__ == "__main__":
    live_value_scanner()