import requests
from pyairtable import Api
import time

# Configuration
AIRTABLE_API_KEY = 'patRV0Ftx6TwcR9M5.64e8132bb75468b3e7f34113c0c304717cb6e84215755d20bb09ee582514f117'
AIRTABLE_BASE_ID = 'appEKWpp4qIrJkZS1'
FOOTBALL_DATA_API_KEY = 'a5738ee9571c46e09dd373c3f1c83312'

api = Api(AIRTABLE_API_KEY)
teams_table = api.table(AIRTABLE_BASE_ID, 'Teams')
stats_table = api.table(AIRTABLE_BASE_ID, 'Historical Stats')

def sync_historical_results():
    print("--- Starting Sync ---")
    
    # 1. Pull Teams from Airtable
    team_records = teams_table.all()
    print(f"Checking Airtable: Found {len(team_records)} rows in Teams table.")
    
    name_to_id = {r['fields']['Team Name'].strip().lower(): r['id'] for r in team_records if 'Team Name' in r['fields']}
    
    if not name_to_id:
        print("ERROR: No teams found in Airtable. Did you run the first script successfully?")
        return

    # 2. Fetch from API
    print("Connecting to Football-Data.org...")
    url = "https://api.football-data.org/v4/competitions/PL/matches?status=FINISHED"
    headers = {'X-Auth-Token': FOOTBALL_DATA_API_KEY}
    
    response = requests.get(url, headers=headers).json()
    matches = response.get('matches', [])
    
    print(f"API Response: Found {len(matches)} total finished matches.")

    if not matches:
        print("ERROR: API returned 0 matches. Check your API key and ensure 'PL' is the correct league code.")
        return

    # 3. Process Matches
    success_count = 0
    for match in matches[-50:]:
        home_raw = match['homeTeam']['name']
        away_raw = match['awayTeam']['name']
        
        home_id = name_to_id.get(home_raw.strip().lower())
        away_id = name_to_id.get(away_raw.strip().lower())
        
        if home_id and away_id:
            try:
                # Clean the date: Airtable prefers YYYY-MM-DD for Date fields
                raw_date = match['utcDate'].split('T')[0] 

                payload = {
                    "Home Team": [home_id], 
                    "Away Team": [away_id], 
                    "Home Goals": int(match['score']['fullTime']['home']),
                    "Away Goals": int(match['score']['fullTime']['away']),
                    "Match Date": raw_date
                }
                stats_table.create(payload)
                print(f"✅ Synced: {home_raw} {match['score']['fullTime']['home']} - {match['score']['fullTime']['away']} {away_raw}")
                success_count += 1
                time.sleep(0.5) 
            except Exception as e:
                print(f"❌ Date Error or Field mismatch for {home_raw} vs {away_raw}: {e}")

    print(f"--- Sync Complete: {success_count} matches added ---")

# CRITICAL: This line actually runs the function
if __name__ == "__main__":
    sync_historical_results()