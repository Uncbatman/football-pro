import requests
from pyairtable import Api

# Configuration
AIRTABLE_API_KEY = 'patRV0Ftx6TwcR9M5.64e8132bb75468b3e7f34113c0c304717cb6e84215755d20bb09ee582514f117'
AIRTABLE_BASE_ID = 'appEKWpp4qIrJkZS1'
FOOTBALL_DATA_API_KEY = 'a5738ee9571c46e09dd373c3f1c83312'

# Initialize Airtable
api = Api(AIRTABLE_API_KEY)
teams_table = api.table(AIRTABLE_BASE_ID, 'Teams')
stats_table = api.table(AIRTABLE_BASE_ID, 'Historical Stats')

def sync_epl_teams():
    url = "https://api.football-data.org/v4/competitions/PL/teams"
    headers = {'X-Auth-Token': FOOTBALL_DATA_API_KEY}
    response = requests.get(url, headers=headers).json()
    
    for team in response['teams']:
        # Create or update team record
        teams_table.create({
            "Team Name": team['name'],
            "League": "Premier League",
            "API_ID": str(team['id'])
        })
    print(f"Synced {len(response['teams'])} teams to Airtable.")

# Run the sync
sync_epl_teams()