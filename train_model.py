import pickle

import pandas as pd
from pyairtable import Api
from sklearn.linear_model import LogisticRegression

# --- Configuration ---
AIRTABLE_API_KEY = "patRV0Ftx6TwcR9M5.64e8132bb75468b3e7f34113c0c304717cb6e84215755d20bb09ee582514f117"
AIRTABLE_BASE_ID = "appEKWpp4qIrJkZS1"

api = Api(AIRTABLE_API_KEY)
teams_table = api.table(AIRTABLE_BASE_ID, "Teams")
stats_table = api.table(AIRTABLE_BASE_ID, "Historical Stats")


def train_model():
    """Train logistic regression model on historical match data from Airtable."""
    print("--- Model Training Started ---")
    
    # Load data from Airtable
    records = stats_table.all()
    print(f"Retrieved {len(records)} records from Historical Stats.")

    data = []
    for r in records:
        fields = r.get("fields", {})

        # Validate required fields
        required_fields = ["Home Goals", "Away Goals", "Home Team", "Away Team"]
        if not all(field in fields for field in required_fields):
            continue

        home_goals = int(fields["Home Goals"])
        away_goals = int(fields["Away Goals"])

        # Determine outcome: 1=Home Win, 0=Draw, 2=Away Win
        if home_goals > away_goals:
            outcome = 1
        elif home_goals < away_goals:
            outcome = 2
        else:
            outcome = 0

        data.append(
            {
                "home_id": fields["Home Team"][0],
                "away_id": fields["Away Team"][0],
                "home_goals": home_goals,
                "away_goals": away_goals,
                "outcome": outcome,
            }
        )

    if not data:
        print(
            "ERROR: No valid data found to train on. "
            "Check your Airtable column names."
        )
        return

    df = pd.DataFrame(data)
    print(f"Training on {len(df)} valid match records.")

    # Prepare features and target
    X = df[["home_goals", "away_goals"]]
    y = df["outcome"]

    # Train logistic regression model
    model = LogisticRegression(solver="lbfgs", max_iter=200)
    model.fit(X, y)

    # Save model
    with open("football_model.pkl", "wb") as f:
        pickle.dump(model, f)

    print("✓ Model trained and saved as 'football_model.pkl'")
    

if __name__ == "__main__":
    train_model()