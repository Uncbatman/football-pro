import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

# 1. Load configuration
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

def populate_teams():
    # 2. Read the baseline CSV
    df = pd.read_csv('Teams-Grid view.csv')
    
    # 3. Clean the data (Drop empty rows and select relevant columns)
    df = df.dropna(subset=['Team Name'])
    teams_to_add = df[['Team Name', 'League']].copy()
    
    # 4. Standardize column names to match Supabase
    teams_to_add.columns = ['team_name', 'league']
    
    # 5. Push to Supabase
    print(f"--- Starting Population: {len(teams_to_add)} teams identified ---")
    
    records = teams_to_add.to_dict(orient='records')
    
    for record in records:
        try:
            # Upsert ensures we don't create duplicates if you run this twice
            supabase.table('teams').upsert(record, on_conflict='team_name').execute()
            print(f"✅ Synced: {record['team_name']}")
        except Exception as e:
            print(f"❌ Error adding {record['team_name']}: {e}")

    print("--- Population Complete ---")

if __name__ == "__main__":
    populate_teams()