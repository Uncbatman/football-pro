import os
import requests
import time
from supabase import create_client, Client

# Configuration - Use environment variables for security
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")

# Initialize Supabase Client 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_historical_results():
    print("--- Starting Sync (Supabase) ---")
    
    # 1. Pull Teams from Supabase 
    # Replaces: team_records = teams_table.all()
    response = supabase.table('teams').select("id, team_name").execute()
    team_records = response.data
    
    print(f"Checking Supabase: Found {len(team_records)} rows in teams table.")
    
    # Map team names to their Supabase Primary Keys (IDs) 
    name_to_id = {r['team_name'].strip().lower(): r['id'] for r in team_records if 'team_name' in r}
    
    if not name_to_id:
        print("ERROR: No teams found in Supabase.")
        return

    # 2. Fetch from API 
    print("Connecting to Football-Data.org...")
    url = "https://api.football-data.org/v4/competitions/PL/matches?status=FINISHED"
    headers = {'X-Auth-Token': FOOTBALL_DATA_API_KEY}
    
    response = requests.get(url, headers=headers).json()
    matches = response.get('matches', [])
    
    print(f"API Response: Found {len(matches)} total finished matches.")

    if not matches:
        print("ERROR: API returned 0 matches.") [cite: 3]
        return

    # 3. Process Matches [cite: 4]
    success_count = 0
    # Process the most recent 50 matches [cite: 3]
    for match in matches[-50:]:
        home_raw = match['home_team']['name']
        away_raw = match['away_team']['name']
        
        home_id = name_to_id.get(home_raw.strip().lower())
        away_id = name_to_id.get(away_raw.strip().lower())
        
        if home_id and away_id: [cite: 4]
            try:
                # Clean the date [cite: 4]
                raw_date = match['utcDate'].split('T')[0] 

                # In Supabase, you don't need the list format [id] used by Airtable 
                payload = {
                    "home_team_id": home_id, 
                    "away_team_id": away_id, 
                    "home_goals": int(match['score']['fullTime']['home']),
                    "away_goals": int(match['score']['fullTime']['away']),
                    "match_date": raw_date
                } [cite: 5, 6]
                
                # Insert record into Supabase historical_stats table 
                supabase.table('historical_stats').insert(payload).execute()
                
                print(f"✅ Synced: {home_raw} {match['score']['fullTime']['home']} - {match['score']['fullTime']['away']} {away_raw}")
                success_count += 1
                time.sleep(0.1) # Faster than Airtable's 0.5s requirement 
            except Exception as e:
                print(f"❌ Error for {home_raw} vs {away_raw}: {e}") [cite: 7]

    print(f"--- Sync Complete: {success_count} matches added ---")

if __name__ == "__main__":
    sync_historical_results()