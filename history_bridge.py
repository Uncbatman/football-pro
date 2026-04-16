import os
import requests
import time
from supabase import create_client, Client
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

# Initialize Bridge
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_historical_data():
    print("--- 🌉 Opening the Data Bridge ---")
    
    # 1. Fetch our Teams 'Dictionary' from Supabase
    teams_res = supabase.table('teams').select("id, team_name").execute()
    name_to_id = {t['team_name'].lower(): t['id'] for t in teams_res.data}
    
    # 2. Fetch Finished Matches from Football-Data.org
    url = "https://api.football-data.org/v4/competitions/PL/matches?status=FINISHED"
    headers = {'X-Auth-Token': FOOTBALL_API_KEY}
    
    try:
        response = requests.get(url, headers=headers).json()
        matches = response.get('matches', [])
    except Exception as e:
        print(f"❌ API Connection Failed: {e}")
        return

    # 3. Process and Insert
    new_records = 0
    for m in matches[-50:]: # Sync the most recent 50 matches
        home_name = m['homeTeam']['name']
        away_name = m['awayTeam']['name']
        
        home_id = name_to_id.get(home_name.lower())
        away_id = name_to_id.get(away_name.lower())
        
        if home_id and away_id:
            # Extract match data
            raw_date = m['utcDate'].split('T')[0]
            h_score = m['score']['fullTime']['home']
            a_score = m['score']['fullTime']['away']
            
            # Determine result: 'H' (home win), 'A' (away win), 'D' (draw)
            if h_score > a_score:
                winner_letter = 'H'
            elif a_score > h_score:
                winner_letter = 'A'
            else:
                winner_letter = 'D'
            
            payload = {
                "match_date": raw_date,
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_goals": h_score,
                "away_goals": a_score,
                "result": winner_letter
            }
            
            # Upsert prevents duplicates if you run this script twice
            try:
                supabase.table('historical_stats').upsert(
                    payload, on_conflict='match_date, home_team_id'
                ).execute()
                new_records += 1
            except Exception as e:
                print(f"⚠️ Skip {home_name} vs {away_name}: {e}")

    print(f"--- ✅ Sync Complete: {new_records} matches stored in Supabase ---")

if __name__ == "__main__":
    sync_historical_data()