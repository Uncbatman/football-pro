import os
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

def update_elo(r_h, r_a, result, k=32):
    """Update Elo ratings based on match result.
    result: 1 for Home Win, 0.5 for Draw, 0 for Away Win"""
    exp_h = 1 / (1 + 10 ** ((r_a - r_h) / 400))
    return r_h + k * (result - exp_h)

def sync_teams():
    """Fetch PL Teams from football-data.org and seed the 'teams' table."""
    url = "https://api.football-data.org/v4/competitions/PL/teams"
    headers = {'X-Auth-Token': os.getenv("FOOTBALL_DATA_API_KEY")}
    
    try:
        response = requests.get(url, headers=headers).json()
        teams = response.get('teams', [])
        
        for t in teams:
            payload = {
                "id": t['id'],
                "team_name": t['name'],
                "elo_rating": 1500.0
            }
            supabase.table('teams').upsert(payload).execute()
        
        print(f"✅ Synced {len(teams)} teams with 1500 Elo rating.")
    except Exception as e:
        print(f"❌ Error syncing teams: {e}")

if __name__ == "__main__":
    sync_teams()
