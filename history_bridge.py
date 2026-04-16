import os
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

def sync_history():
    # 1. Fetch Mapping
    teams = supabase.table('teams').select("id, team_name").execute().data
    name_to_id = {t['team_name'].lower(): t['id'] for t in teams}

    # 2. API Fetch (Finished Matches)
    url = "https://api.football-data.org/v4/competitions/PL/matches?status=FINISHED"
    headers = {'X-Auth-Token': os.getenv("FOOTBALL_DATA_API_KEY")}
    matches = requests.get(url, headers=headers).json().get('matches', [])

    for m in matches:
        h_id = name_to_id.get(m['homeTeam']['name'].lower())
        a_id = name_to_id.get(m['awayTeam']['name'].lower())
        
        if h_id and a_id:
            # Note: Fetch closing odds from your live_predictions table or external source
            # For this bridge, we insert the core result
            payload = {
                "match_date": m['utcDate'].split('T')[0],
                "home_team_id": h_id,
                "away_team_id": a_id,
                "home_goals": m['score']['fullTime']['home'],
                "away_goals": m['score']['fullTime']['away'],
                "result": m['score']['winner'][0] if m['score']['winner'] else 'D'
            }
            supabase.table('historical_stats').upsert(payload, on_conflict='match_date, home_team_id').execute()

if __name__ == "__main__":
    sync_history()
