import pandas as pd
from pyairtable import Api
from sklearn.linear_model import LogisticRegression
import pickle

# Configuration
AIRTABLE_API_KEY = 'patRV0Ftx6TwcR9M5.64e8132bb75468b3e7f34113c0c304717cb6e84215755d20bb09ee582514f117'
AIRTABLE_BASE_ID = 'appEKWpp4qIrJkZS1'

api = Api(AIRTABLE_API_KEY)
teams_table = api.table(AIRTABLE_BASE_ID, 'Teams')
stats_table = api.table(AIRTABLE_BASE_ID, 'Historical Stats')

def train_analysis_agent():
    print("--- Analysis Agent: Training Started ---")
    
    # 1. Load Data from Airtable
    records = stats_table.all()
    print(f"Retrieved {len(records)} records from Historical Stats.")
    
    data = []
    for r in records:
        f = r.get('fields', {})
        
        # Check if the necessary fields exist in this row
        if 'Home Goals' in f and 'Away Goals' in f and 'Home Team' in f and 'Away Team' in f:
            home_goals = int(f['Home Goals'])
            away_goals = int(f['Away Goals'])
            
            # Define outcome: 1 for Home Win, 0 for Draw, 2 for Away Win
            if home_goals > away_goals:
                outcome = 1
            elif home_goals < away_goals:
                outcome = 2
            else:
                outcome = 0
                
            data.append({
                'home_id': f['Home Team'][0],
                'away_id': f['Away Team'][0],
                'home_goals': home_goals,
                'away_goals': away_goals,
                'outcome': outcome
            })
        else:
            # This skips empty rows or rows missing data
            continue

    if not data:
        print("❌ ERROR: No valid data found to train on. Check your Airtable column names.")
        return

    df = pd.DataFrame(data)
    print(f"Training on {len(df)} valid match records.")

    # 2. Features and Target
    X = df[['home_goals', 'away_goals']] 
    y = df['outcome']

    # 3. Train the Model
    # We remove multi_class as modern scikit-learn handles this automatically
    model = LogisticRegression(solver='lbfgs', max_iter=200)
    model.fit(X, y)
    
    # 4. Save the Model
    with open('football_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    print("✅ Model trained and saved as 'football_model.pkl'")
    

if __name__ == "__main__":
    train_analysis_agent()